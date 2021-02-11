# Vegalite server

Flask-based vegalite server. Converts vegalite specs to images.

Accepts encrypted specs to allow public access to results without being generally useful as an endpoint. 

## URL parameters

`\convert_spec?` is the root url.

Accepted parameters are:

* `spec` - html encoded vegalite spec [or encrypted variety]
* `format` - options accepted by `altair-saver` package - png, svg, json, html, pdf, etc.
* `width` - override width in spec.
* `scale` - for image formats that accept it, scale factor for the image output. 
* `encrypted` - Spec has been encrypted using fernet.

## Enviromental variables

* `VEGALITE_SERVER_ALLOW_PLAIN_SPEC` - If false, does not allow unencrypted vega-lite specs.
* `VEGALITE_SERVER_SECRET` - Encryption key for encrypted specs.
* `VEGALITE_SERVER_PRODUCTION` - if false uses debug server rather than waitress.

These can be set through args to the dockerfile build (see below).

## Run locally

Using the dockerfile, the following will run at `http://localhost:5000`.

```
# build
docker build -t vegalite_server --build-arg secret_key={{secret_key}} --build-arg allow_plain=TRUE .

# running server
docker run -dp 5000:5000 vegalite_server

```