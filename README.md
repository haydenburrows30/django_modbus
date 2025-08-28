# Django Modbus Poller

A minimal Django app to poll up to 8 Modbus TCP devices for:
- Discrete Inputs
- Input Registers
- Holding Registers
- Coils (read and write)

## Quick start
1. Create venv and install deps
2. Run migrations
3. Create superuser
4. Add devices via admin
5. Start poller
6. Query APIs / write coils

### Commands
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
# in another terminal
python manage.py poll_modbus --interval 1.0
```

### API
- GET /api/devices/
- GET /api/devices/<id>/last/
- POST /api/devices/<id>/write_coils/ {"start": 0, "values": [true, false]}

## Docker (app + Postgres + poller)

1) Copy env template and adjust if needed:

```bash
cp .env.example .env
```

2) Build and start services:

```bash
docker compose up --build
```

This starts:
- db: PostgreSQL 16
- web: Django + Gunicorn on http://localhost:8001
- poller: async polling worker

To run only the web app:

```bash
docker compose up --build web
```

To run only the poller:

```bash
docker compose up --build poller
```

For development, the project directory is bind-mounted into containers for hot reload. For production, remove the bind mounts and set DEBUG off.