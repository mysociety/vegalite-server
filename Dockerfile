FROM python:3.8-buster

ENV DEBIAN_FRONTEND noninteractive

RUN curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - \
      && echo 'deb https://deb.nodesource.com/node_14.x buster main' > /etc/apt/sources.list.d/nodesource.list

RUN apt-get -qq update \
      && apt-get -qq install \
            nodejs \
         --no-install-recommends \
      && rm -rf /var/lib/apt/lists/*

RUN npm install -g vega vega-lite vega-cli canvas --unsafe-perm

RUN mkdir /app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

ARG secret_key=blank
ARG allow_plain=TRUE

ENV VEGALITE_SERVER_PRODUCTION=TRUE VEGALITE_SERVER_ALLOW_PLAIN_SPEC=$allow_plain VEGALITE_SERVER_SECRET_KEY=$secret_key

COPY . .

CMD ["python", "main.py"]