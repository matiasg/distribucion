FROM python:3.7.2-slim-stretch

ENV PYTHONUNBUFFERED 1

RUN mkdir /codigo
WORKDIR /codigo

COPY requirements.txt /codigo/
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y git
RUN git clone https://github.com/matiasg/allocation.git && pip install -e allocation

RUN git clone https://ecebb780114e159b713bbdb48dd3434c57b8c24a@github.com/matiasg/distribucion.git
COPY settings.py distribucion/distribucion/settings.py
COPY create_db distribucion/create_db
WORKDIR distribucion
