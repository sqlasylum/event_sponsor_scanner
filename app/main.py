import io
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer
from fastapi import HTTPException

import config
from database import engine, Base
from routers import scan, auth

signer = URLSafeTimedSerializer(config.SECRET_KEY)
templates = Jinja2Templates(directory="templates")
_basic = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(_basic)):
    ok_user = secrets.compare_digest(credentials.username.encode(), b"admin")
    ok_pass = secrets.compare_digest(
        credentials.password.encode(), config.ADMIN_PASSWORD.encode()
    )
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


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


@app.get("/admin", dependencies=[Depends(require_admin)])
async def admin_dashboard(request: Request):
    from sqlalchemy import text
    from database import SessionLocal

    db_ok = False
    scans_last_day = 0
    by_email = []
    by_sponsor = []
    recent_scans = []

    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
            db_ok = True

            scans_last_day = (await db.execute(
                text("SELECT COUNT(*) FROM scans WHERE scanned_at > NOW() - INTERVAL '24 hours'")
            )).scalar()

            by_email = (await db.execute(
                text("SELECT sponsor_email, COUNT(*) as cnt FROM scans GROUP BY sponsor_email ORDER BY cnt DESC")
            )).all()

            by_sponsor = (await db.execute(text("""
                SELECT COALESCE(NULLIF(sp.company, ''), sc.sponsor_email) as sponsor, COUNT(*) as cnt
                FROM scans sc
                LEFT JOIN sponsors sp ON sc.sponsor_email = sp.email
                GROUP BY COALESCE(NULLIF(sp.company, ''), sc.sponsor_email)
                ORDER BY cnt DESC
            """))).all()

            recent_scans = (await db.execute(text("""
                SELECT sc.id, sc.attendee_id, sc.sponsor_email,
                       COALESCE(NULLIF(sp.company, ''), '') as company,
                       sc.scanned_at, sc.notes
                FROM scans sc
                LEFT JOIN sponsors sp ON sc.sponsor_email = sp.email
                ORDER BY sc.scanned_at DESC
                LIMIT 10
            """))).all()
    except Exception:
        pass

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "event_name": config.EVENT_NAME,
        "db_ok": db_ok,
        "scans_last_day": scans_last_day,
        "by_email": by_email,
        "by_sponsor": by_sponsor,
        "recent_scans": recent_scans,
    })


@app.get("/admin/generate-qr", dependencies=[Depends(require_admin)])
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


@app.get("/admin/scans", dependencies=[Depends(require_admin)])
async def export_scans(format: str = "json", email: str = ""):
    import csv
    from io import StringIO
    from sqlalchemy import select
    from database import SessionLocal
    from models import Scan, Sponsor

    async with SessionLocal() as db:
        query = select(Scan, Sponsor.company).join(
            Sponsor, Scan.sponsor_email == Sponsor.email, isouter=True
        ).order_by(Scan.scanned_at.desc())
        if email:
            query = query.where(Scan.sponsor_email == email.strip().lower())
        result = await db.execute(query)
        rows = result.all()

    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "attendee_id", "sponsor_email", "company", "scanned_at", "notes"])
        for s, company in rows:
            writer.writerow([s.id, s.attendee_id, s.sponsor_email, company or "", s.scanned_at.isoformat(), s.notes or ""])
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
            "company": company,
            "scanned_at": s.scanned_at.isoformat(),
            "notes": s.notes,
        }
        for s, company in rows
    ]
