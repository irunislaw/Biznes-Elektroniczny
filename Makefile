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
		$(COMPOSE) exec -T prestashop php /opt/prestashop-config/locale.php
		$(COMPOSE) exec -T prestashop php /opt/prestashop-config/taxes.php
		$(COMPOSE) exec -T prestashop php /opt/prestashop-config/payments.php
		$(COMPOSE) exec -T prestashop php /opt/prestashop-config/mail.php
		$(COMPOSE) exec -T prestashop php /var/www/html/bin/console prestashop:mail:generate modern pl-PL /var/www/html/mails /var/www/html/modules --overwrite=1
		$(COMPOSE) exec -T -u www-data prestashop mkdir -p /var/www/html/themes/classic/mails
		$(COMPOSE) exec -T prestashop php /var/www/html/bin/console prestashop:mail:generate modern pl-PL /var/www/html/themes/classic/mails /var/www/html/themes/classic/modules --overwrite=1
		$(COMPOSE) exec -T -u root prestashop chown -R www-data:www-data /var/www/html/var/cache/prod
logs:
		$(COMPOSE) logs -f prestashop
reset:
		$(COMPOSE) down -v
test:
		$(COMPOSE) exec playwright npx playwright test
	