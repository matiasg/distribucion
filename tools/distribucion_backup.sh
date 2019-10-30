#!/bin/bash

echo "generating backup"
DIR=$(dirname $0)
docker run --rm -v distribucion_pgdata:/source:ro busybox tar -czC /source . > ${DIR}/data_backup_$(date "+%F_%T").tar.gz

echo "keeping only last 30 files"
ls ${DIR} | sort | head -n-30 | xargs rm
