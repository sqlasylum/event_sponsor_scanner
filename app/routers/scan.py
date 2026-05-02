from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import get_db
from models import Sponsor, Scan
from routers.auth import get_sponsor_email

templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get("/scan/{attendee_id}")
async def scan_badge(attendee_id: str, request: Request):
    email = get_sponsor_email(request)

    if not email:
        return RedirectResponse(url=f"/login?next=/scan/{attendee_id}", status_code=302)

    async for db in get_db():
        # Upsert sponsor
        stmt = pg_insert(Sponsor).values(email=email).on_conflict_do_nothing(index_elements=["email"])
        await db.execute(stmt)

        # Record scan
        await db.execute(insert(Scan).values(attendee_id=attendee_id, sponsor_email=email))
        await db.commit()

    return templates.TemplateResponse(
        "scanned.html",
        {"request": request, "attendee_id": attendee_id, "email": email},
    )
