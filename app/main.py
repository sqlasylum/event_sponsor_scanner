import os
import io
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer

from database import engine, Base
from routers import scan, auth

SECRET_KEY = os.environ["SECRET_KEY"]
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

signer = URLSafeTimedSerializer(SECRET_KEY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Event Sponsor Scanner", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(scan.router)
app.include_router(auth.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/admin/generate-qr")
async def generate_qr(attendee_id: str):
    import qrcode

    url = f"{BASE_URL}/scan/{attendee_id}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    filename = f"qr-{attendee_id}.png"
    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/admin/scans")
async def export_scans(request: Request, format: str = "json"):
    import csv
    from io import StringIO
    from sqlalchemy import select
    from database import SessionLocal
    from models import Scan

    admin_token = os.environ.get("ADMIN_TOKEN", "")
    if admin_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {admin_token}":
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    async with SessionLocal() as db:
        result = await db.execute(select(Scan).order_by(Scan.scanned_at.desc()))
        scans = result.scalars().all()

    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "attendee_id", "sponsor_email", "scanned_at"])
        for s in scans:
            writer.writerow([s.id, s.attendee_id, s.sponsor_email, s.scanned_at.isoformat()])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=scans.csv"},
        )

    return [
        {
            "id": s.id,
            "attendee_id": s.attendee_id,
            "sponsor_email": s.sponsor_email,
            "scanned_at": s.scanned_at.isoformat(),
        }
        for s in scans
    ]
