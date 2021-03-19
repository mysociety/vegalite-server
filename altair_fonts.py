"""
Include google font in code
"""

import altair_saver.savers._selenium
import selenium.webdriver


# this is a bit horrible, but wrap the webdriver in an extra option
chrome_driver_options = selenium.webdriver.chrome.options.Options


def override_chrome_options():
    print("overriding selenium to add option")
    options = chrome_driver_options()
    options.add_argument('--disable-dev-shm-usage')
    return options


selenium.webdriver.chrome.options.Options = override_chrome_options

"""
update html template and extract code used to add reference to font
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Embedding Vega-Lite</title>
  <script src="https://ajax.googleapis.com/ajax/libs/webfont/1.6.26/webfont.js"></script>
  <script src="{vega_url}"></script>
  <script src="{vegalite_url}"></script>
  <script src="{vegaembed_url}"></script>
</head>
<body>
  <div id="vis"></div>
</body>
</html>
"""

EXTRACT_CODE_TEMPLATE = """
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


def load_font(font_options):
    """
    override altair settings to use font
    ideally would create a subclass on the saver so it could
    be passed as a parameter, but for these purposes
    all can have the same font
    """
    if not font_options:
        # if any explictly empty value has been set, do nothing
        return None
    altair_saver.savers._selenium.HTML_TEMPLATE = HTML_TEMPLATE
    EXTRACT_CODE = EXTRACT_CODE_TEMPLATE.replace(
        "INSERT_FONT_HERE", font_options)
    altair_saver.savers._selenium.EXTRACT_CODE = EXTRACT_CODE
