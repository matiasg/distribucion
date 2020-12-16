#!/bin/bash

DIR=$(dirname $0)
cd ${DIR}

echo "genero backup"
docker run --rm -v distribucion_pgdata:/source:ro busybox tar -czC /source . > data_backup_$(date "+%F_%T").tar.gz

echo "dejo solo los últimos 30 backups y los ultimos 24 primeros de mes"
PRIMERO_DE_MES='-[0-9][0-9]-01_[0-9][0-9]:' 
ls data_backup*.tar.gz | grep -v -- ${PRIMERO_DE_MES} | sort | head -n-30 | xargs rm
ls data_backup*.tar.gz | grep -- ${PRIMERO_DE_MES} | sort | head -n-24 | xargs rm
