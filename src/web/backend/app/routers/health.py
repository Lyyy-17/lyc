from fastapi import APIRouter

router = APIRouter(tags=["meta"])


@router.get("/")
def root_status():
    return {
        "service": "OceanRace Backend API",
        "status": "ok",
        "docs": "/docs",
        "health": "/healthz",
    }


@router.get("/healthz")
def healthz():
    return {"status": "ok"}
