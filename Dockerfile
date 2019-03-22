FROM python:3.7.2-slim-stretch

ENV PYTHONUNBUFFERED 1

RUN mkdir /codigo
WORKDIR /codigo

RUN apt-get update && apt-get install -y git

RUN git clone https://ecebb780114e159b713bbdb48dd3434c57b8c24a@github.com/matiasg/distribucion.git
#RUN cd /codigo/distribucion && git pull && cd /codigo
COPY settings.py /codigo/distribucion/distribucion/settings.py
RUN chmod +x /codigo/distribucion/tools/create_db

RUN git clone https://github.com/matiasg/allocation.git
RUN pip install -e allocation
RUN pip install -r allocation/requirements.txt

WORKDIR distribucion

RUN pip install -r requirements.txt
