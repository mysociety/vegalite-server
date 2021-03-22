import atexit
import base64
import os
from typing import Any, Dict, List, Optional, Union

from altair_viewer import get_bundled_script
import selenium.webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException

from altair_saver.types import JSONDict, MimebundleContent
from altair_saver.savers._selenium import (SeleniumSaver, CDN_URL,
                                           EXTRACT_CODE, HTML_TEMPLATE,
                                           JavascriptError)

webfont_url = "https://ajax.googleapis.com/ajax/libs/webfont/1.6.26/webfont.js"

FONT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Embedding Vega-Lite</title>
  <script src="{webfont_url}"></script>
  <script src="{vega_url}"></script>
  <script src="{vegalite_url}"></script>
  <script src="{vegaembed_url}"></script>
</head>
<body>
  <div id="vis"></div>
</body>
</html>
"""

FONT_EXTRACT_CODE_TEMPLATE = """
let spec = arguments[0];
const embedOpt = arguments[1];
const format = arguments[2];
const done = arguments[3];
load_chart = function() {
    if (format === 'vega') {
        if (embedOpt.mode === 'vega-lite') {
            vegaLite = (typeof vegaLite === "undefined") ? vl : vegaLite;
            try {
                const compiled = vegaLite.compile(spec);
                spec = compiled.spec;
            } catch(error) {
                done({error: error.toString()})
            }
        }
        done({result: spec});
    }
        vegaEmbed('#vis', spec, embedOpt).then(function(result) {
            if (format === 'png') {
                result.view
                    .toCanvas(embedOpt.scaleFactor || 1)
                    .then(function(canvas){return canvas.toDataURL('image/png');})
                    .then(result => done({result}))
                    .catch(function(err) {
                        console.error(err);
                        done({error: err.toString()});
                    });
            } else if (format === 'svg') {
                result.view
                    .toSVG(embedOpt.scaleFactor || 1)
                    .then(result => done({result}))
                    .catch(function(err) {
                        console.error(err);
                        done({error: err.toString()});
                    });
            } else {
                const error = "Unrecognized format: " + format;
                console.error(error);
                done({error});
            }
        }).catch(function(err) {
            console.error(err);
            done({error: err.toString()});
        });
}
WebFont.load({
            google: {
            families: ['INSERT_FONT_HERE']
            },
    active: load_chart
    })
"""


class _DriverRegistry:
    """Registry of web driver singletons.
    This prevents the need to start and stop drivers repeatedly.
    """

    drivers: Dict[str, WebDriver]

    def __init__(self) -> None:
        self.drivers = {}

    def get(self, webdriver: Union[str, WebDriver], driver_timeout: float) -> WebDriver:
        """Get a webdriver by name.
        Parameters
        ----------
        webdriver : string or WebDriver
            The webdriver to use.
        driver_timeout : float
            The per-page driver timeout.
        Returns
        -------
        webdriver : WebDriver
        """
        webdriver = self.drivers.get(webdriver, webdriver)
        if isinstance(webdriver, WebDriver):
            return webdriver

        if webdriver == "chrome":
            webdriver_class = selenium.webdriver.Chrome
            webdriver_options_class = selenium.webdriver.chrome.options.Options
        elif webdriver == "firefox":
            webdriver_class = selenium.webdriver.Firefox
            webdriver_options_class = selenium.webdriver.firefox.options.Options
        else:
            raise ValueError(
                f"Unrecognized webdriver: '{webdriver}'. Expected 'chrome' or 'firefox'"
            )

        webdriver_options = webdriver_options_class()

        # For linux/osx root user with Chrome, need to add --no-sandbox option, which
        # must come before the --headless option. Note: geteuid doesn't exist on windows.
        if (
            issubclass(webdriver_class, selenium.webdriver.Chrome)
            and hasattr(os, "geteuid")
            and os.geteuid() == 0
        ):
            pass
            # this used to turn on the no sandbox argument, but need that all the time for 
            # heruko
        webdriver_options.add_argument("--no-sandbox")

        webdriver_options.add_argument("--headless")
        webdriver_options.add_argument("--disable-dev-shm-usage")

        driver_obj = webdriver_class(options=webdriver_options)
        atexit.register(driver_obj.quit)
        driver_obj.set_page_load_timeout(driver_timeout)
        self.drivers[webdriver] = driver_obj

        return driver_obj


class FontSeleniumSaver(SeleniumSaver):
    """Save charts using a selenium engine."""

    _registry: _DriverRegistry = _DriverRegistry()

    def __init__(self, *args, font_str="", **kwargs):
        self.font_str = font_str
        super().__init__(*args, **kwargs)

    def get_html_template(self):
        if self.font_str:
            return FONT_HTML_TEMPLATE
        else:
            return HTML_TEMPLATE

    def get_extract_code(self):
        if self.font_str:
            temp = FONT_EXTRACT_CODE_TEMPLATE
            return temp.replace("INSERT_FONT_HERE", self.font_str)
        else:
            return EXTRACT_CODE

    def _extract(self, fmt: str) -> MimebundleContent:
        driver = self._registry.get(self._webdriver, self._driver_timeout)

        if self._offline:
            js_resources = {
                "vega.js": get_bundled_script("vega", self._package_versions["vega"]),
                "vega-lite.js": get_bundled_script(
                    "vega-lite", self._package_versions["vega-lite"]
                ),
                "vega-embed.js": get_bundled_script(
                    "vega-embed", self._package_versions["vega-embed"]
                ),
            }
            html = self.get_html_template().format(
                vega_url="/vega.js",
                vegalite_url="/vega-lite.js",
                vegaembed_url="/vega-embed.js",
                webfont_url=webfont_url
            )
        else:
            js_resources = {}
            html = self.get_html_template().format(
                vega_url=CDN_URL.format(
                    package="vega", version=self._package_versions["vega"]
                ),
                vegalite_url=CDN_URL.format(
                    package="vega-lite", version=self._package_versions["vega-lite"]
                ),
                vegaembed_url=CDN_URL.format(
                    package="vega-embed", version=self._package_versions["vega-embed"],
                ),
                webfont_url=webfont_url
            )

        url = self._serve(html, js_resources)
        driver.get("about:blank")
        driver.get(url)
        try:
            driver.find_element_by_id("vis")
        except NoSuchElementException:
            raise RuntimeError(f"Could not load {url}")
        if not self._offline:
            online = driver.execute_script("return navigator.onLine")
            if not online:
                raise RuntimeError(
                    f"Internet connection required for saving chart as {fmt} with offline=False."
                )
        opt = self._embed_options.copy()
        opt["mode"] = self._mode
        extract_code = self.get_extract_code()
        result = driver.execute_async_script(
            extract_code, self._spec, opt, fmt)
        if "error" in result:
            raise JavascriptError(result["error"])
        return result["result"]
