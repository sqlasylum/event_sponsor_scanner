import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

templates = Jinja2Templates(directory="templates")
router = APIRouter()

SECRET_KEY = os.environ["SECRET_KEY"]
signer = URLSafeTimedSerializer(SECRET_KEY)
COOKIE_NAME = "sponsor_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def get_sponsor_email(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        return signer.loads(token, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


@router.get("/login")
async def login_page(request: Request, next: str = "/login"):
    email = get_sponsor_email(request)
    if email and next.startswith("/") and next != "/login":
        return RedirectResponse(url=next, status_code=302)
    scan_count = None
    company = None
    if email:
        from sqlalchemy import select, func
        from database import SessionLocal
        from models import Scan, Sponsor
        async with SessionLocal() as db:
            result = await db.execute(
                select(func.count()).where(Scan.sponsor_email == email)
            )
            scan_count = result.scalar()
            sponsor = await db.execute(select(Sponsor).where(Sponsor.email == email))
            sponsor = sponsor.scalar_one_or_none()
            if sponsor:
                company = sponsor.company
    return templates.TemplateResponse(
        "login.html", {"request": request, "next": next, "email": email, "scan_count": scan_count, "company": company}
    )


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    company: str = Form(...),
    next: str = Form(default="/"),
):
    email = email.strip().lower()
    company = company.strip()

    if not email or "@" not in email:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "next": next, "error": "Please enter a valid email address."},
            status_code=422,
        )

    if not next.startswith("/"):
        next = "/"

    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from database import SessionLocal
    from models import Sponsor
    async with SessionLocal() as db:
        stmt = pg_insert(Sponsor).values(email=email, company=company).on_conflict_do_update(
            index_elements=["email"],
            set_={"company": company},
        )
        await db.execute(stmt)
        await db.commit()

    token = signer.dumps(email)
    response = RedirectResponse(url=next, status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key=COOKIE_NAME)
    return response
