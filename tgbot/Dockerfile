ARG MODE

FROM python:3.10-slim-buster as builder-common
RUN apt-get update \
&& apt-get install gcc g++ -y \
&& apt-get clean
WORKDIR /app
COPY tgbot/requirements.txt tgbot/requirements.txt
RUN python3 -m venv venv && venv/bin/pip3 install -r tgbot/requirements.txt
COPY library library
COPY tgbot tgbot
COPY infra/hub/aioclient infra/hub/aioclient
COPY infra/hub/proto infra/hub/proto
ENV PYTHONPATH=/app
RUN mkdir /usr/lib/stc-tgbot
RUN mkdir /var/log/stc-tgbot
CMD ["/app/venv/bin/python3", "tgbot/main.py"]