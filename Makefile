prebuild:
	cat dockerfiles/dockerfile_header dockerfiles/dockerfile_body > Dockerfile

uba_prebuild:
	cat dockerfiles/dockerfile_header dockerfiles/uba_docker_setting dockerfiles/dockerfile_body > Dockerfile

build:
	docker build -t distribucion .
	docker-compose build
	docker volume create --name=distribucion_pgdata
	docker-compose up --no-start
	echo -e "sugerencia: correr \n\ndocker-compose run --rm web sh tools/create_db"

rebuild:
	docker build -t distribucion . --no-cache
	docker-compose build

empezar:
	docker-compose up

terminar:
	docker-compose down

populate:
	docker-compose run --rm web python tools/current_html_to_db.py V 2020
	docker-compose run --rm web python tools/current_html_to_db.py 1 2020
	docker-compose run --rm web python tools/current_html_to_db.py 2 2020

demo: build populate
	docker-compose run --rm web python tools/inventar_encuestas.py -a 2019 -c S -d J
	docker-compose run --rm web python tools/inventar_encuestas.py -a 2019 -c S -d A1
	docker-compose run --rm web python tools/inventar_encuestas.py -a 2019 -c S -d A2

FECHA := $(shell date +%F_%T)
backup:
	docker run --rm -v distribucion_pgdata:/source:ro busybox tar -czC /source . > data_backup_$(FECHA).tar.gz

ULTIMO_BACKUP := $(shell ls data_backup*.tar.gz | tail -1)
restore:
	@echo Voy a parar el sistema de distribucion
	docker-compose stop
	@echo Voy a sobre-escribir la db con el backup $(ULTIMO_BACKUP)
	docker run --rm -i -v distribucion_pgdata:/target busybox tar -xzC /target < $(ULTIMO_BACKUP)
	@echo Levanto el sistema de nuevo
	docker-compose start
