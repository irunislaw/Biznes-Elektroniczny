COMPOSE = docker compose --env-file .env -f deploy/compose.yaml


OPENSSL_IMAGE = alpine/openssl:3.5.8
export MSYS_NO_PATHCONV = 1
ifneq ($(OS),Windows_NT)
DOCKER_USER = --user $(shell id -u):$(shell id -g)
endif

.PHONY: up down init zrzut backup restore logs reset certs sprawdz wyglad duplikaty test raport

certs:
		docker run --rm $(DOCKER_USER) -v "$(CURDIR):/work" -w /work --entrypoint sh $(OPENSSL_IMAGE) deploy/scripts/gen-cert.sh
up: certs
		$(COMPOSE) up -d 
down: 
		$(COMPOSE) down 
init:
		COMPOSE="$(COMPOSE)" sh deploy/scripts/init.sh
zrzut:
		COMPOSE="$(COMPOSE)" sh deploy/scripts/zrzut.sh
backup:
		COMPOSE="$(COMPOSE)" sh deploy/scripts/backup.sh
restore:
		PLIK="$(PLIK)" COMPOSE="$(COMPOSE)" sh deploy/scripts/restore.sh
logs:
		$(COMPOSE) logs -f prestashop
reset:
		$(COMPOSE) down -v
test:
		$(COMPOSE) exec -T playwright npx playwright test
raport:
		$(COMPOSE) exec playwright npx playwright show-report playwright-report --host 0.0.0.0 --port 9323
wyglad:
		$(COMPOSE) exec playwright npx playwright test -c zrzuty.config.ts
sprawdz:
		$(COMPOSE) exec -T db sh -c 'MYSQL_PWD="$$MARIADB_PASSWORD" mariadb -u"$$MARIADB_USER" "$$MARIADB_DATABASE" -t' < deploy/sprawdz/metryki.sql
duplikaty:
		$(COMPOSE) exec -T db sh -c 'MYSQL_PWD="$$MARIADB_PASSWORD" mariadb -u"$$MARIADB_USER" "$$MARIADB_DATABASE" -t' < deploy/import/duplikaty.sql
