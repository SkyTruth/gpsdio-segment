FROM python:3

RUN mkdir -p /opt/project
WORKDIR /opt/project

COPY . .
RUN pip install -e .[dev]
