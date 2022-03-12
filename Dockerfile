FROM python:3.9.7-slim-buster AS base

FROM base AS build

RUN apt-get update \
    && apt-get install libpq-dev gcc git make -y

WORKDIR /tmp

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN pip install -r requirements.txt

###

FROM base AS deploy

COPY --from=build /usr/local /usr/local

WORKDIR /app
COPY . /app

ENV PYTHONPATH=/app \
    GUNICORN_CMD_ARGS=$GUNICORN_CMD_ARGS


EXPOSE 80

CMD ["gunicorn", "-b", "0.0.0.0:80", "lists.lists:app"]
