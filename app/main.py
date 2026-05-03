import os
import io
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer

import config
from database import engine, Base
from routers import scan, auth

signer = URLSafeTimedSerializer(config.SECRET_KEY)
templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=config.EVENT_NAME, lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(scan.router)
app.include_router(auth.router)


@app.get("/")
async def index(request: Request):
    from sqlalchemy import text
    from database import SessionLocal
    from models import Scan, Sponsor

    db_ok = False
    scan_count = 0
    sponsor_count = 0
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
            scan_count = (await db.execute(text("SELECT COUNT(*) FROM scans"))).scalar()
            sponsor_count = (await db.execute(text("SELECT COUNT(*) FROM sponsors"))).scalar()
            db_ok = True
    except Exception:
        pass

    return templates.TemplateResponse("index.html", {
        "request": request,
        "event_name": config.EVENT_NAME,
        "db_ok": db_ok,
        "scan_count": scan_count,
        "sponsor_count": sponsor_count,
    })


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/admin/generate-qr")
async def generate_qr(attendee_id: str):
    import qrcode

    url = f"{config.BASE_URL}/scan/{attendee_id}"
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

    admin_token = config.ADMIN_TOKEN
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
        writer.writerow(["id", "attendee_id", "sponsor_email", "scanned_at", "notes"])
        for s in scans:
            writer.writerow([s.id, s.attendee_id, s.sponsor_email, s.scanned_at.isoformat(), s.notes or ""])
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
            "notes": s.notes,
        }
        for s in scans
    ]
