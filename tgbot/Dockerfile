ARG MODE

FROM python:3.11-slim as builder-common
RUN apt-get update \
&& apt-get install gcc g++ git golang -y \
&& apt-get clean
WORKDIR /app
ADD tgbot/requirements.txt tgbot/requirements.txt
RUN python3 -m venv venv
RUN venv/bin/pip3 install -r tgbot/requirements.txt
COPY fabrica fabrica
COPY library library
COPY tgbot tgbot
COPY infra/hub/aioclient infra/hub/aioclient
COPY infra/hub/proto infra/hub/proto
ENV PYTHONPATH=/app
RUN mkdir /usr/lib/stc-tgbot
RUN mkdir /var/log/stc-tgbot
CMD ["/app/venv/bin/python3", "tgbot/main.py"]