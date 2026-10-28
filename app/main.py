from fastapi import FastAPI
from app.config import settings
from app.routers import interview, auth
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    same_site="lax",
    https_only=False,  # Local development only
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(interview.router)

@app.get("/")
def health_check():
    return {
        "message": "AI Interview Service is running!"
    }