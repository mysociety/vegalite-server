"""
Flask app to convert vegalite specs
to images
"""
import io
import json
import os
import urllib.parse

from altair_saver import save
from cryptography.fernet import Fernet
from flask import Flask, request, send_file
from waitress import serve


def str_to_bool(x): return x.lower() == "true"


allow_plain = str_to_bool(os.environ.get(
    "VEGALITE_SERVER_ALLOW_PLAIN_SPEC", "true"))
secret_key = os.environ.get("VEGALITE_SERVER_SECRET_KEY", "blank")
production_server = str_to_bool(
    os.environ.get("VEGALITE_SERVER_PRODUCTION", "true"))
PORT = int(os.environ.get('PORT', 5000))

app = Flask(__name__)

mime_type_lookup = {"png": "image/png",
                    "json": "application/json",
                    "vl.json": "application/json",
                    "html": "text/html",
                    "svg": "image/svg+xml",
                    "pdf": "application/pdf"}


def construct_url_from_spec(spec, width=500, encrypted=True):
    root = "/convert_spec"
    if encrypted:
        coded_spec = Fernet(secret_key).encrypt(spec.encode())
    else:
        coded_spec = spec
    parameters = {"type": "png",
                  "spec": coded_spec,
                  "width": width,
                  "encrypted": encrypted}
    return root + "?" + urllib.parse.urlencode(parameters)

@app.route("/")
def home():
    messages = ["The endpoint you are looking for is /convert_spec."]
    if secret_key != "blank":
        messages.append("Server key configured.")
    if allow_plain:
        messages.append("Unencrypted allowed.")        

    return("<br>".join(messages))

@app.route("/convert_spec")
def convert_spec():
    """
    View to convert spec to image based on
    url parameters
    """

    # get parameters
    spec = request.args.get('spec', default="", type=str)
    image_format = request.args.get('format', default='png', type=str)
    image_width = request.args.get('width', default=500, type=int)
    image_scale = request.args.get('scale', default=1, type=int)
    encrypted = str_to_bool(request.args.get(
                            'encrypted', default="false", type=str))

    if spec == "":
        return ("No spec provided")
    if not encrypted and allow_plain is False:
        return ("Spec must be encoded with key shared key")
    if image_format not in mime_type_lookup:
        return ("Invalid image format")
    mime_type = mime_type_lookup[image_format]

    if encrypted is True:
        if secret_key == "blank":
            return("Encrypted chart sent, but server key not configured.")
        key = secret_key.encode()
        spec = Fernet(key).decrypt(spec.encode()).decode()

    # adjust spec
    json_spec = json.loads(spec)
    json_spec["width"] = image_width

    # create binary
    if image_format in ["png", "pdf"]:
        out = io.BytesIO()
        node_args = ["-s {0}".format(image_scale)]
        save(json_spec, out, fmt=image_format, vega_cli_options=node_args)
    else:
        sout = io.StringIO()
        save(json_spec, sout, fmt=image_format)
        out = io.BytesIO()
        out.write(sout.getvalue().encode())
    out.seek(0)

    # return file
    return send_file(out, mimetype=mime_type)


if __name__ == "__main__":
    if production_server:
        serve(app, host='0.0.0.0', port=PORT)
    else:
        app.run(host="0.0.0.0", debug=True)
