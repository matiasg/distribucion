#!/bin/bash

DIR=$(dirname $0)
cd ${DIR}

echo "genero backup"
docker run --rm -v distribucion_pgdata:/source:ro busybox tar -czC /source . > data_backup_$(date "+%F_%T").tar.gz

echo "dejo solo los últimos 30 backups"
ls data_backup*.tar.gz | sort | head -n-30 | xargs rm
