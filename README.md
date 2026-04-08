# wh_tourn — SaaS control de comisiones (MVP)

Django + Bootstrap 5 + HTMX + PostgreSQL + Redis + Celery + Docker.

## Requisitos locales (sin Docker)

- Python 3.12+
- `pip install -r requirements.txt`
- Crea un archivo **`.env` en la raíz del proyecto** (junto a `manage.py`) a partir de [`.env.example`](.env.example). Django lo carga al iniciar vía `python-dotenv`.
- Variables opcionales: `DATABASE_URL` (Postgres), `REDIS_URL`. Sin `DATABASE_URL` se usa SQLite.

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`, inicia sesión. Si eres superusuario, elige compañía en **Seleccionar compañía**.

## Docker Compose

```powershell
docker compose build
docker compose up
```

Servicios: **web** (puerto 8000, **Gunicorn** + WSGI), **db** (Postgres 16), **redis**, **celery_worker**, **celery_beat**.

Los servicios **web** y **celery_worker** usan `env_file: .env` (opcional): coloca tu `.env` en la **misma carpeta que `docker-compose.yml`**.

Crear superusuario dentro del contenedor:

```powershell
docker compose exec web python manage.py createsuperuser
```

## Flujo sugerido (admin)

1. Crear **Company**.
2. **Project** y **Team**; asociar equipos al proyecto (**Project team** en admin del proyecto).
3. **Commission types** y **Project commission types** (activar tipos por proyecto).
4. **Commission rules** (condiciones JSON + `action_type` + `action_params`).
5. **Employees** y vínculos a equipo/proyecto.
6. **Commission period** (borrador).
7. En la app: **Registrar** eventos; **Resumen empleados** y exportación Excel; **Tipo de cambio** con guardado HTMX.

## Recalcular periodo

Desde **Inicio**, botón *Recalcular (async)* encola la tarea Celery `recalculate_period`.

## Estructura

- `apps/companies` — `Company`
- `apps/accounts` — membresías, alcance proyecto/equipo, middleware `request.company`
- `apps/projects`, `apps/staff`, `apps/fx`, `apps/rules`, `apps/commissions` — dominio y motor (`engine.py`)
