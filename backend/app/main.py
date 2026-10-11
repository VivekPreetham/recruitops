from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routers import auth, jobs
from app.core.errors import AppError

app = FastAPI(
    title="RecruitOps API",
    version="0.1.0"
)

@app.exception_handler(AppError)
def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"type": exc.code, "status": exc.status_code, "detail": exc.message},
    )

@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")