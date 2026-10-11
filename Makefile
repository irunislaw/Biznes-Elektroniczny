COMPOSE = docker compose --env-file .env -f deploy/compose.yaml

.PHONY: up down init logs reset

up:
		$(COMPOSE) up -d 
down: 
		$(COMPOSE) down 
init:
		@echo "init: brak krokow - konfiguracja sklepu dojdzie w kolejnych ticketach"
logs:
		$(COMPOSE) logs -f prestashop
reset:
		$(COMPOSE) down -v