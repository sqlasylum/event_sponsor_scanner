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
async def login_page(request: Request, next: str = "/"):
    return templates.TemplateResponse(
        "login.html", {"request": request, "next": next}
    )


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    next: str = Form(default="/"),
):
    email = email.strip().lower()
    if not email or "@" not in email:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "next": next, "error": "Please enter a valid email address."},
            status_code=422,
        )

    # Prevent open redirect — only allow relative paths
    if not next.startswith("/"):
        next = "/"

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
