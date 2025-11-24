.PHONY: help build up down logs test clean

# Основные команды
help: ## Показать справку по командам
	@echo "Доступные команды:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Собрать Docker образы
	docker-compose build

up: ## Запустить сервисы
	docker-compose up -d
	@echo "🚀 Сервис запущен! Доступен по адресу: http://localhost:8000"
	@echo "📚 Документация API: http://localhost:8000/docs"

down: ## Остановить сервисы
	docker-compose down

logs: ## Показать логи в реальном времени
	docker-compose logs -f

test: ## Запустить тесты
	docker-compose run --rm web python test.py

clean: ## Остановить сервисы и очистить volumes
	docker-compose down -v

# Короткие алиасы
start: up
stop: down
restart: down up

status: ## Показать статус контейнеров
	docker-compose ps

shell: ## Открыть shell в контейнере
	docker-compose exec web bash


docs: ## Открыть документацию API в браузере
	@echo "Открытие документации API..."
	@if command -v xdg-open > /dev/null; then \
		xdg-open http://localhost:8000/docs; \
	elif command -v open > /dev/null; then \
		open http://localhost:8000/docs; \
	else \
		echo "📖 Документация доступна по адресу: http://localhost:8000/docs"; \
	fi


dev: ## Запуск в режиме разработки (с логами)
	docker-compose up

build-force: ## Принудительная пересборка образов
	docker-compose build --no-cache


info: ## Информация о проекте
	@echo "=== Сервис назначения ревьюеров ==="
	@echo "📍 API: http://localhost:8000"
	@echo "📚 Docs: http://localhost:8000/docs"
	@echo "🔍 ReDoc: http://localhost:8000/redoc"
	@echo "================================"