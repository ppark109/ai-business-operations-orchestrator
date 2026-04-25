from fastapi import APIRouter

from workflows.routing import ROUTES

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meta")
def meta() -> dict[str, object]:
    return {
        "workflow": "commercial_intake_to_operational_handoff",
        "routes": list(ROUTES),
    }
