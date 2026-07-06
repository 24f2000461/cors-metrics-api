import time
import uuid
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ---- CONFIG ----
ALLOWED_ORIGIN = "https://dash-6uol4t.example.com"
EMAIL = "24f2000461@ds.study.iitm.ac.in"  # <-- REPLACE with your exact logged-in email

app = FastAPI()


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

    # Handle preflight requests directly
    if request.method == "OPTIONS":
        headers = {}
        if origin == ALLOWED_ORIGIN:
            headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
            headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "*"
            headers["Access-Control-Max-Age"] = "600"
        # Still need request id / process time headers on preflight per spec of "every response"
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


@app.get("/")
async def root():
    return {"status": "ok"}
