# Django Modbus Poller

Poll up to 8 Modbus TCP devices and view them on a live dashboard. Supports reading Discrete Inputs, Input Registers, Holding Registers (with decoding), and Coils (read/write). Includes an async polling worker, REST APIs, configurable dashboard cards, action cards (Open/Close), and optional charts.

## Features
- Devices: host/port/unit, per-range starts/counts (DI/IR/HR/Coils), per-device HR decoding (datatype, byte/word order, decimals).
- Async poller: asyncio-based; dynamically picks up device changes without restart.
- Dashboard: Bootstrap UI at `/` with live values, per-device refresh interval, coil write/toggle, and named “cards”.
- Cards: Configure points to display (DI/IR/HR/Coil @ address) with optional unit/decimals; each shows current value and a mini time-series chart.
- Action cards: Define coil write actions with Open/Close payloads (e.g., breaker control) and trigger from the dashboard.
- APIs: list devices, last poll per device, coil writes, card series, execute actions.
- Dockerized: Postgres + Django web (Gunicorn/WhiteNoise) + poller services.

## Quick start (local)
1) Create venv and install dependencies
2) Migrate DB and create a superuser
3) Run the web app and the poller

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
# in another terminal
python manage.py poll_modbus --interval 1.0
```

Open http://localhost:8000 and log in (if admin-only). Add devices in `/admin/`.

## Docker (web + db + poller)

1) Copy env template and adjust if needed:

```bash
cp .env.example .env
```

2) Build and start services:

```bash
docker compose up --build
```

Services:
- db: PostgreSQL 16
- web: Django + Gunicorn on http://localhost:8001
- poller: async polling worker

Run individually:

```bash
docker compose up --build web
docker compose up --build poller
```

For development, the project directory is bind-mounted into containers for hot reload. For production, remove bind mounts and configure environment (DEBUG, SECRET_KEY, ALLOWED_HOSTS).

## Configuring devices and cards
- Devices: `/admin/modbusapp/modbusdevice/` — set host/port/unit, ranges (DI/IR/HR/Coils), HR decoding (datatype, byte/word order, decimals), and poll interval.
- Cards: `/admin/modbusapp/modbuscard/` — choose device, name, source (hr/ir/di/coil), absolute address, optional unit label and decimals.
- Action cards: `/admin/modbusapp/modbusactioncard/` — choose device, set a name, starting coil address, and boolean lists for Open and Close.

## REST API
- GET `/api/devices/`
- GET `/api/devices/<id>/last/`
- POST `/api/devices/<id>/write_coils/` body: `{ "start": 0, "values": [true, false] }`
- GET `/api/devices/<id>/cards/<card_id>/series/?limit=300` → `{ series: [{t, v}, ...] }`
- POST `/api/devices/<id>/actions/<action_id>/execute/` body: `{ "which": "open"|"close" }`

## Notes on holding register decoding
Per-device decoding supports u16/s16/u32/s32/u64/s64/f32/f64, byte order (big/little), and word order (MSW first/LSW first). Floating values can be rounded via `hr_decimals`.

## Optional: TimescaleDB
You can keep using plain Postgres or switch to TimescaleDB:
- Minimal change: enable the extension and convert `modbusapp_pollresult` to a hypertable; add retention/compression policies.
- Full change: add a narrow hypertable for samples (device, source, address, value, created_at) and point the card series API at it. Contact us to wire this if desired.

## Admin tips
- Device duplication: On a device page, use “Save as new” to clone and rename. Bulk duplicate is available from the list view.
- Superuser in Docker: you can create a superuser with `docker compose exec web python manage.py createsuperuser`.

## Security
APIs are open in this demo. In production, restrict write endpoints (coils/actions) and ensure authentication/CSRF as needed.