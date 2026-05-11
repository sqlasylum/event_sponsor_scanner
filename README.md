# Event Sponsor Scanner

An open-source QR code lead-capture system for events. Sponsors scan attendee badge QR codes with any phone. The system records who scanned whom and stores it in PostgreSQL.

```
Attendee badge QR code
        │
        ▼
  https://scan.example.com/scan/{attendee_id}
        │
        ├── No session cookie? → Email login page → Set cookie → Redirect back
        │
        └── Session cookie present? → Record scan → Show confirmation + notes box
```

## Quick Start (Local)

**Prerequisites:** Docker, Docker Compose

```bash
git clone https://github.com/your-org/event_sponsor_scanner.git
cd event_sponsor_scanner

# Create your .env file
cp .env.example .env
# Edit .env — set SECRET_KEY and ADMIN_PASSWORD at minimum
```

Generate a secret key:
```bash
openssl rand -hex 32
```

Then start the service:
```bash
docker compose up -d --build
```

Service is now running at **http://localhost:8000**

Test it:
```
http://localhost:8000/scan/badge-001
```

## Generating QR Codes

Use the built-in endpoint to generate a PNG QR code for any attendee ID:

```
http://localhost:8000/admin/generate-qr?attendee_id=badge-001
```

This returns a PNG image you can print on badges. The QR code encodes the URL:
`{BASE_URL}/scan/{attendee_id}`

> **Note:** This endpoint requires admin credentials (see [Admin Access](#admin-access) below).

## Admin Access

All `/admin/*` routes are protected with HTTP Basic Auth. When accessed in a browser, you will be prompted for a username and password.

- **Username:** `admin`
- **Password:** the value of `ADMIN_PASSWORD` in your `.env`

From the command line:
```bash
curl -u admin:your-password http://localhost:8000/admin/scans
curl -u admin:your-password "http://localhost:8000/admin/scans?format=csv"
curl -u admin:your-password "http://localhost:8000/admin/generate-qr?attendee_id=badge-001"
```

## Exporting Scan Data

### JSON
```bash
curl -u admin:your-password http://localhost:8000/admin/scans
```

### CSV
```bash
curl -u admin:your-password "http://localhost:8000/admin/scans?format=csv" -o scans.csv
```

The export includes: `id`, `attendee_id`, `sponsor_email`, `scanned_at`, `notes`.

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `DATABASE_URL` | Postgres connection string (`postgresql+asyncpg://...`) | Yes |
| `SECRET_KEY` | Signs session cookies — generate with `openssl rand -hex 32` | Yes |
| `ADMIN_PASSWORD` | Password for `/admin/*` routes (username is always `admin`) | Yes |
| `EVENT_NAME` | Display name shown on the status page | No (default: `Event Sponsor Scanner`) |
| `BASE_URL` | Public URL of the service, used in QR code links | No (default: `http://localhost:8000`) |

## Deployment

See **[terraform/README.md](terraform/README.md)** for three deployment options:
- **Local** — Docker Compose managed by Terraform
- **AWS ECS Fargate + RDS** — fully managed, auto-scaling
- **AWS EC2** — single VM running Docker Compose (simpler, cheaper)

## Database Schema

```sql
CREATE TABLE sponsors (
    id         SERIAL PRIMARY KEY,
    email      TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE scans (
    id            SERIAL PRIMARY KEY,
    attendee_id   TEXT NOT NULL,
    sponsor_email TEXT NOT NULL REFERENCES sponsors(email),
    scanned_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes         TEXT
);
```

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | None | Status page with scan counts |
| `GET` | `/scan/{attendee_id}` | Cookie | Main scan flow |
| `GET` | `/login` | None | Login page (shows scan count if already logged in) |
| `POST` | `/login` | None | Submit email, set session cookie |
| `GET` | `/logout` | None | Clear session cookie |
| `POST` | `/scan/{scan_id}/notes` | Cookie | Save notes for a scan |
| `GET` | `/admin/scans` | Basic Auth | Export all scans (JSON or CSV) |
| `GET` | `/admin/generate-qr` | Basic Auth | Generate QR code PNG for an attendee |
| `GET` | `/health` | None | Health check |

## Contributing

Pull requests are welcome. This project is MIT licensed — see [LICENSE](LICENSE).
