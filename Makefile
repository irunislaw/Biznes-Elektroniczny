COMPOSE = docker compose --env-file .env -f deploy/compose.yaml


OPENSSL_IMAGE = alpine/openssl:3.5.8
export MSYS_NO_PATHCONV = 1
ifneq ($(OS),Windows_NT)
DOCKER_USER = --user $(shell id -u):$(shell id -g)
endif

.PHONY: up down init logs reset certs

certs:
		docker run --rm $(DOCKER_USER) -v "$(CURDIR):/work" -w /work --entrypoint sh $(OPENSSL_IMAGE) deploy/scripts/gen-cert.sh
up: certs
		$(COMPOSE) up -d 
down: 
		$(COMPOSE) down 
init:
		@echo "init: brak krokow - konfiguracja sklepu dojdzie w kolejnych ticketach"
logs:
		$(COMPOSE) logs -f prestashop
reset:
		$(COMPOSE) down -v
test:
		-cd tests && npx playwright test
		cd tests && npx playwright show-report test-results