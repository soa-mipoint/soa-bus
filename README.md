# MiPoint — SOA Platform

Plataforma de reserva de espacios para eventos. Arquitectura orientada a servicios (SOA) de 5 capas.

## Arquitectura

```
[Portal Web / Admin Panel]
        │ HTTPS/REST
        ▼
[Kong API Gateway :8000]     ← JWT auth, Rate limiting, Routing
        │ AMQP/REST interno
        ▼
[RabbitMQ ESB :5672]         ← booking_events, user_events, space_events
        │ Pub/Subscribe
        ▼
┌─────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Customer Service│ Space Catalog    │ Booking Service  │ Notification Svc │
│ :8001           │ Service :8002    │ :8003            │ :8004            │
│ FastAPI         │ FastAPI          │ FastAPI          │ FastAPI (ESB)    │
└────────┬────────┴────────┬─────────┴────────┬─────────┴──────────────────┘
         │ ORM             │ ORM              │ ORM
         ▼                 ▼                  ▼
  [customers_db]    [catalog_db]       [bookings_db]
  PostgreSQL         PostgreSQL         PostgreSQL
                                        ↕ Redis (distributed locks)
```

## Stack

| Componente | Local | Producción |
|---|---|---|
| API Gateway | Kong 3.8 (DB-less) | Cloud Run |
| ESB | RabbitMQ 3.13 Docker | CloudAMQP (Lemur, free) |
| PostgreSQL | 1 instancia, 3 DBs | Neon SQL (free tier) |
| Cache | Redis 7 Docker | Upstash (free) |
| Monitoring | Prometheus + Grafana | Cloud Monitoring |

## Quick Start

```bash
# 1. Copiar variables de entorno
cp .env.example .env

# 2. Levantar todos los servicios
make up

# 3. (Opcional) Levantar monitoring
make monitoring-up

# 4. Verificar health
make test-health
```

## URLs locales

| Servicio | URL | Descripción |
|---|---|---|
| API Gateway | http://localhost:8000 | Entry point principal |
| Customer Service | http://localhost:8001/docs | Swagger UI |
| Space Catalog | http://localhost:8002/docs | Swagger UI |
| Booking Service | http://localhost:8003/docs | Swagger UI |
| Notification Svc | http://localhost:8004/health | Health only (ESB consumer) |
| RabbitMQ UI | http://localhost:15672 | mipoint / mipoint_secret |
| Prometheus | http://localhost:9090 | Métricas |
| Grafana | http://localhost:3000 | admin / admin |

## Flujo principal: Reserva de espacio

```
1. POST /api/v1/users/register     → Customer Service emite JWT
2. GET  /api/v1/spaces/search      → Space Catalog (Redis cache)
3. POST /api/v1/bookings           → Booking Service
                                      ├─ Redis distributed lock (anti double-booking)
                                      └─ Publica booking.created → RabbitMQ
4. PUT  /api/v1/bookings/{id}/confirm → Anfitrión confirma
                                        ├─ Space Catalog locks availability
                                        └─ Publica booking.confirmed → RabbitMQ
5. Notification Service consume booking.confirmed → Email + SMS
```

## Exchanges RabbitMQ

| Exchange | Routing Keys |
|---|---|
| `user_events` | `user.registered`, `user.updated` |
| `booking_events` | `booking.created`, `booking.confirmed`, `booking.cancelled` |
| `space_events` | `space.created`, `space.activated`, `space.availability_updated` |
| `payment_events` | `payment.completed`, `payment.failed` |

## Notificaciones de reservas

- Booking mantiene el request publico de reservas sin datos derivados como nombre/email del cliente o nombre del espacio.
- Booking guarda snapshots minimos: email, telefono y nombre del cliente desde JWT, y nombre del espacio desde Space Catalog.
- Redis se usa para locks anti doble-reserva y para cache temporal del nombre del espacio.
- RabbitMQ transporta eventos de reserva en tiempo real asincrono hacia Notification Service.
- Notification Service envia email con Resend y SMS con Twilio, registrando `notification_logs` en `notifications_db` para auditoria e idempotencia durable.
- Los correos escapan datos dinamicos antes de renderizar HTML y no dependen de consultas a bases de otros servicios.

## Servicios

### Customer Service (`/api/v1/users`)
- `POST /register` requiere `phone` en formato E.164, por ejemplo `+51999999999`.
- `POST /register` — Registro de usuario (cliente o anfitrión)
- `POST /login` — Login → JWT token
- `GET /profile` — Perfil del usuario autenticado
- `PUT /profile` — Actualizar perfil

### Space Catalog Service (`/api/v1/spaces`)
- `POST /` — Crear espacio (anfitrión)
- `GET /` — Buscar espacios con filtros
- `GET /{id}` — Detalle de espacio
- `PUT /{id}/status` — Activar/Desactivar espacio
- `GET /{id}/availability` — Disponibilidad en rango de fechas

### Booking Service (`/api/v1/bookings`)
- `POST /` — Crear reserva (Redis lock automático)
- `PUT /{id}/confirm` — Confirmar reserva (anfitrión)
- `PUT /{id}/cancel` — Cancelar reserva
- `GET /{id}` — Detalle de reserva
- `GET /client/{id}` — Reservas de un cliente

## Variables de entorno clave

Ver `.env.example` para la lista completa.

Para producción necesitas:
- `NEON_DATABASE_URL` — Neon SQL connection string
- `RABBITMQ_URL` — CloudAMQP connection string  
- `REDIS_URL` — Upstash Redis URL
- `RESEND_API_KEY` — Para emails
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` - Para SMS
- `JWT_SECRET_KEY` — Mínimo 32 caracteres, seguro

## Deployment (Cloud Run)

Cada servicio tiene su propio `Dockerfile`. Para desplegar:

```bash
# Build y push a Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/customer-service ./services/customer-service

# Deploy a Cloud Run
gcloud run deploy customer-service \
  --image gcr.io/PROJECT_ID/customer-service \
  --set-env-vars DATABASE_URL=... \
  --region us-central1
```
