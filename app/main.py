import io
import csv
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, UploadFile, File, Query
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


# Column name normalization map for flexible CSV header matching
_ATTENDEE_COL_MAP = {
    "attendee id": "attendee_id",
    "attendee first name": "attendee_first_name",
    "first name": "attendee_first_name",
    "attendee last name": "attendee_last_name",
    "last name": "attendee_last_name",
    "organization": "organization",
    "attendee email": "attendee_email",
    "email": "attendee_email",
    "qr code": "qr_code",
    "qrcode": "qr_code",
}


@app.get("/admin/upload-attendees", dependencies=[Depends(require_admin)])
async def upload_attendees_page(request: Request, imported: int = 0, error: str = ""):
    return templates.TemplateResponse("admin_upload.html", {
        "request": request,
        "event_name": config.EVENT_NAME,
        "imported": imported,
        "error": error,
    })


@app.post("/admin/upload-attendees", dependencies=[Depends(require_admin)])
async def upload_attendees(request: Request, file: UploadFile = File(...)):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from database import SessionLocal

    if not file.filename.lower().endswith(".csv"):
        return templates.TemplateResponse("admin_upload.html", {
            "request": request,
            "event_name": config.EVENT_NAME,
            "imported": 0,
            "error": "Please upload a .csv file.",
        }, status_code=422)

    content = await file.read()
    # utf-8-sig handles BOM from Excel exports; falls back to latin-1 for accented chars
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        mapped = {}
        for k, v in row.items():
            key = _ATTENDEE_COL_MAP.get(k.strip().lower())
            if key:
                mapped[key] = v.strip() or None
        if "attendee_id" not in mapped or not mapped["attendee_id"]:
            continue
        try:
            mapped["attendee_id"] = int(mapped["attendee_id"])
        except (ValueError, TypeError):
            continue
        rows.append(mapped)

    if not rows:
        return templates.TemplateResponse("admin_upload.html", {
            "request": request,
            "event_name": config.EVENT_NAME,
            "imported": 0,
            "error": "No valid rows found. Check that your CSV has the expected headers.",
        }, status_code=422)

    from models import EventAttendee
    async with SessionLocal() as db:
        stmt = pg_insert(EventAttendee).values(rows).on_conflict_do_update(
            index_elements=["attendee_id"],
            set_={
                "attendee_first_name": pg_insert(EventAttendee).excluded.attendee_first_name,
                "attendee_last_name": pg_insert(EventAttendee).excluded.attendee_last_name,
                "organization": pg_insert(EventAttendee).excluded.organization,
                "attendee_email": pg_insert(EventAttendee).excluded.attendee_email,
                "qr_code": pg_insert(EventAttendee).excluded.qr_code,
            },
        )
        await db.execute(stmt)
        await db.commit()

    from fastapi.responses import RedirectResponse
    return RedirectResponse(f"/admin/upload-attendees?imported={len(rows)}", status_code=303)


@app.get("/admin/attendees", dependencies=[Depends(require_admin)])
async def admin_attendees(request: Request):
    from sqlalchemy import text
    from database import SessionLocal

    rows = []
    try:
        async with SessionLocal() as db:
            result = await db.execute(text("""
                SELECT attendee_id, attendee_first_name, attendee_last_name,
                       organization, attendee_email, qr_code
                FROM event_attendees
                ORDER BY attendee_last_name, attendee_first_name
            """))
            rows = result.all()
    except Exception:
        pass

    return templates.TemplateResponse("admin_attendees.html", {
        "request": request,
        "event_name": config.EVENT_NAME,
        "rows": rows,
    })


@app.get("/admin/leads", dependencies=[Depends(require_admin)])
async def admin_leads(request: Request, company: list[str] = Query(default=[]), format: str = "html"):
    from sqlalchemy import text, bindparam
    from database import SessionLocal

    rows = []
    all_companies = []
    try:
        async with SessionLocal() as db:
            result = await db.execute(text("""
                SELECT DISTINCT COALESCE(NULLIF(sp.company, ''), sp.email) as company
                FROM scans sc
                JOIN sponsors sp ON sc.sponsor_email = sp.email
                ORDER BY 1
            """))
            all_companies = [r[0] for r in result.all()]

            base_query = """
                SELECT DISTINCT ON (
                    COALESCE(NULLIF(sp.company, ''), sp.email),
                    sp.email,
                    ea.attendee_first_name,
                    ea.attendee_last_name,
                    ea.attendee_email
                )
                    COALESCE(NULLIF(sp.company, ''), sp.email) as company,
                    sp.email as scanner_email,
                    ea.attendee_first_name,
                    ea.attendee_last_name,
                    ea.organization,
                    ea.attendee_email,
                    sc.notes as attendee_notes
                FROM scans sc
                JOIN sponsors sp ON sc.sponsor_email = sp.email
                JOIN event_attendees ea ON sc.attendee_id = ea.attendee_id::text
            """
            if company:
                base_query += " WHERE COALESCE(NULLIF(sp.company, ''), sp.email) IN :companies"
                base_query += """
                    ORDER BY
                        COALESCE(NULLIF(sp.company, ''), sp.email),
                        sp.email,
                        ea.attendee_first_name,
                        ea.attendee_last_name,
                        ea.attendee_email,
                        sc.scanned_at DESC
                """
                stmt = text(base_query).bindparams(bindparam("companies", expanding=True))
                result = await db.execute(stmt, {"companies": company})
            else:
                base_query += """
                    ORDER BY
                        COALESCE(NULLIF(sp.company, ''), sp.email),
                        sp.email,
                        ea.attendee_first_name,
                        ea.attendee_last_name,
                        ea.attendee_email,
                        sc.scanned_at DESC
                """
                result = await db.execute(text(base_query))
            rows = result.all()
    except Exception:
        pass

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Company", "Scanner Email", "First Name", "Last Name", "Organization", "Attendee Email", "Notes"])
        for r in rows:
            writer.writerow([r.company, r.scanner_email, r.attendee_first_name or "", r.attendee_last_name or "", r.organization or "", r.attendee_email or "", r.attendee_notes or ""])
        output.seek(0)
        label = "-".join(company) if company else "all"
        filename = f"leads-{label}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return templates.TemplateResponse("admin_leads.html", {
        "request": request,
        "event_name": config.EVENT_NAME,
        "rows": rows,
        "companies": all_companies,
        "selected_companies": company,
    })


@app.post("/admin/reset", dependencies=[Depends(require_admin)])
async def reset_all_data():
    from sqlalchemy import text
    from database import SessionLocal
    from fastapi.responses import RedirectResponse

    async with SessionLocal() as db:
        await db.execute(text("DELETE FROM scans"))
        await db.execute(text("DELETE FROM sponsors"))
        await db.execute(text("DELETE FROM event_attendees"))
        await db.commit()

    return RedirectResponse("/admin", status_code=303)
