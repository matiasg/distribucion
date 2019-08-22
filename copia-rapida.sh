#!/bin/bash

rm -rf dockerfiles

BRANCH=master
curl --fail --silent --show-error --location https://codeload.github.com/matiasg/distribucion/tar.gz/${BRANCH} | tar xvz -C . distribucion-${BRANCH}/Makefile distribucion-${BRANCH}/dockerfiles distribucion-${BRANCH}/docker-compose.yaml
mv distribucion-${BRANCH}/* .
rmdir distribucion-${BRANCH}

echo "Esta instalación se hace dentro de la uba?"
select uba in "Si" "No"; do
    case $uba in
        Si ) echo "generando el archivo de docker"; make uba_prebuild; break;;
        No ) echo "generando el archivo de docker"; make prebuild; break;;
    esac
done

cat << EOE


Si contestaste la pregunta anterior mal, podés hacer
$ make prebuild
o
$ make uba_prebuild

En cualquier caso, los pasos que siguen son
$ make build
o, si querés una branch especial,
$ BRANCH=mi_branch_querida make build

Tal vez,
$ docker-compose run --rm web sh tools/create_db
$ docker-compose run --rm bash python tools/dump_to_db.py
$ make populate

Y finalmente
$ make empezar
EOE


