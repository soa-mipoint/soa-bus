# MiPoint SOA — Development Commands

.PHONY: up down logs restart build ps clean monitoring

# ─── Local Development ──────────────────────────────────────────────────────

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

restart:
	docker-compose down && docker-compose up -d --build

logs:
	docker-compose logs -f

ps:
	docker-compose ps

# ─── Individual Service Logs ────────────────────────────────────────────────

logs-customer:
	docker-compose logs -f customer-service

logs-catalog:
	docker-compose logs -f space-catalog-service

logs-booking:
	docker-compose logs -f booking-service

logs-notification:
	docker-compose logs -f notification-service

logs-kong:
	docker-compose logs -f kong

logs-rabbit:
	docker-compose logs -f rabbitmq

# ─── Monitoring ─────────────────────────────────────────────────────────────

monitoring-up:
	docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

monitoring-down:
	docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml down

# ─── Clean ──────────────────────────────────────────────────────────────────

clean:
	docker-compose down -v --remove-orphans

# ─── Quick API Tests (requires httpie or curl) ──────────────────────────────

test-health:
	curl -s http://localhost:8001/health | python -m json.tool
	curl -s http://localhost:8002/health | python -m json.tool
	curl -s http://localhost:8003/health | python -m json.tool
	curl -s http://localhost:8004/health | python -m json.tool
	curl -s http://localhost:8000/api/v1/spaces | python -m json.tool
