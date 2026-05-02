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
        └── Session cookie present? → Record scan → Show confirmation
```

## Quick Start (Local)

**Prerequisites:** Docker, Docker Compose

```bash
git clone https://github.com/your-org/event_sponsor_scanner.git
cd event_sponsor_scanner

# Create your .env file
cp .env.example .env
# Edit .env — at minimum, set SECRET_KEY to the output of: openssl rand -hex 32

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

For batch generation, loop over your attendee list and call this endpoint for each one.

## Exporting Scan Data

### JSON
```bash
curl http://localhost:8000/admin/scans
```

### CSV
```bash
curl "http://localhost:8000/admin/scans?format=csv" -o scans.csv
```

If `ADMIN_TOKEN` is set in `.env`, include it as a Bearer token:
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" "http://localhost:8000/admin/scans?format=csv"
```

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `DATABASE_URL` | Postgres connection string (`postgresql+asyncpg://...`) | Yes |
| `SECRET_KEY` | Signs session cookies — generate with `openssl rand -hex 32` | Yes |
| `BASE_URL` | Public URL of the service, used in QR code links | No (default: `http://localhost:8000`) |
| `ADMIN_TOKEN` | Bearer token for `/admin/*` routes | No |

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
    scanned_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/scan/{attendee_id}` | Main scan flow |
| `GET` | `/login` | Login page |
| `POST` | `/login` | Submit email, set session cookie |
| `GET` | `/admin/scans` | Export all scans (JSON or CSV) |
| `GET` | `/admin/generate-qr` | Generate QR code PNG for an attendee |
| `GET` | `/health` | Health check |

## Contributing

Pull requests are welcome. This project is MIT licensed — see [LICENSE](LICENSE).
