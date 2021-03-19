FROM python:3.8-buster

ENV DEBIAN_FRONTEND noninteractive

RUN mkdir /app
WORKDIR /app

COPY script/chrome_setup.bash /
RUN chmod +x /chrome_setup.bash
RUN /chrome_setup.bash

COPY requirements.txt .
RUN pip install -r requirements.txt

ARG SECRET_KEY=blank
ARG ALLOW_PLAIN=TRUE

ENV VEGALITE_SERVER_PRODUCTION=TRUE VEGALITE_SERVER_ALLOW_PLAIN_SPEC=$ALLOW_PLAIN VEGALITE_SERVER_SECRET_KEY=$SECRET_KEY

COPY . .

CMD ["python", "main.py"]