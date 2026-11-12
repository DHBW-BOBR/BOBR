from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import import_routes, validator_routes, correction_routes

app = FastAPI(title="BOBR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_routes.router, prefix="/api/import")
app.include_router(validator_routes.router, prefix="/api/validate")
app.include_router(correction_routes.router, prefix="/api/corrections")
