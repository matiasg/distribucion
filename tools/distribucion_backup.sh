#!/bin/bash

DIR=$(dirname $0)
docker run --rm -v distribucion_pgdata:/source:ro busybox tar -czC /source . > ${DIR}/data_backup_$(date "+%F_%T").tar.gz
