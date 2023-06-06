ARG MODE

FROM python:3.10-slim-buster as builder-common
RUN apt-get update \
&& apt-get install gcc g++ -y \
&& apt-get clean
WORKDIR /app
COPY tgbot/requirements.common.txt tgbot/requirements.common.txt
RUN python3 -m venv venv && venv/bin/pip3 install -r tgbot/requirements.common.txt

FROM python:3.10-slim-buster as seed-common
WORKDIR /app
COPY library library
COPY tgbot tgbot
ENV PYTHONPATH=/app
RUN mkdir /usr/lib/stc-tgbot
RUN mkdir /var/log/stc-tgbot

FROM builder-common as builder-light
COPY tgbot/requirements.light.txt tgbot/requirements.light.txt
RUN python3 -m venv venv && venv/bin/pip3 install -r tgbot/requirements.common.txt && venv/bin/pip3 install -r tgbot/requirements.light.txt

FROM builder-common as builder-full
COPY tgbot/requirements.txt tgbot/requirements.txt
RUN venv/bin/pip3 install -r tgbot/requirements.txt

# Here is the production image
FROM seed-common as tgbot-light
COPY --from=builder-light /app/venv /app/venv

# Here is the production image
FROM seed-common as tgbot-full
COPY --from=builder-full /app/venv /app/venv
COPY infra/hub/aioclient infra/hub/aioclient
COPY infra/hub/proto infra/hub/proto

FROM tgbot-${MODE}
CMD ["/app/venv/bin/python3", "tgbot/main.py"]