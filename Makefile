COMPOSE = docker compose --env-file .env -f deploy/compose.yaml


OPENSSL_IMAGE = alpine/openssl:3.5.8
export MSYS_NO_PATHCONV = 1
ifneq ($(OS),Windows_NT)
DOCKER_USER = --user $(shell id -u):$(shell id -g)
endif

.PHONY: up down init zrzut logs reset certs sprawdz

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
logs:
		$(COMPOSE) logs -f prestashop
reset:
		$(COMPOSE) down -v
test:
		$(COMPOSE) exec playwright npx playwright test
sprawdz:
		$(COMPOSE) exec -T db sh -c 'MYSQL_PWD="$$MARIADB_PASSWORD" mariadb -u"$$MARIADB_USER" "$$MARIADB_DATABASE" -t' < deploy/sprawdz/metryki.sql