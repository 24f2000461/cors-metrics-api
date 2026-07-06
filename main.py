import time
import uuid
import jwt
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

# ---- CONFIG ----
ALLOWED_ORIGIN = "https://dash-6uol4t.example.com"
EMAIL = "24f2000461@ds.study.iitm.ac.in"

# ---- OIDC / JWT verification config ----
ISSUER = "https://idp.exam.local"
AUDIENCE = "tds-juqjpkjr.apps.exam.local"
PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----"""

app = FastAPI()


class TokenRequest(BaseModel):
    token: str


# ---- Custom middleware: request id + process time ----
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        request_id = str(uuid.uuid4())
        response = await call_next(request)
        duration = time.perf_counter() - start
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration:.6f}"
        return response


app.add_middleware(MetricsMiddleware)


# ---- Manual strict CORS handling (no wildcard, single allowed origin) ----
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin")

    if request.method == "OPTIONS":
        headers = {}
        if origin == ALLOWED_ORIGIN:
            headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
            headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "*"
            headers["Access-Control-Max-Age"] = "600"
        headers["X-Request-ID"] = str(uuid.uuid4())
        headers["X-Process-Time"] = "0.000000"
        return JSONResponse(content={}, status_code=200, headers=headers)

    response = await call_next(request)

    if origin == ALLOWED_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
        response.headers["Vary"] = "Origin"

    return response


@app.get("/stats")
async def stats(values: str = Query(...)):
    nums = [int(v.strip()) for v in values.split(",") if v.strip() != ""]

    count = len(nums)
    total = sum(nums)
    minimum = min(nums)
    maximum = max(nums)
    mean = total / count

    return {
        "email": EMAIL,
        "count": count,
        "sum": total,
        "min": minimum,
        "max": maximum,
        "mean": mean,
    }


@app.post("/verify")
async def verify(body: TokenRequest):
    try:
        claims = jwt.decode(
            body.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iss", "aud"]},
        )
        return {
            "valid": True,
            "email": claims.get("email"),
            "sub": claims.get("sub"),
            "aud": claims.get("aud"),
        }
    except jwt.PyJWTError:
        return JSONResponse(status_code=401, content={"valid": False})


@app.get("/")
async def root():
    return {"status": "ok"}
