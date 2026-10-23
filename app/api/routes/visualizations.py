from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/visualizations", tags=["Visualizations"])

# Manim rendering is NOT exposed here any more: animations are created, de-duplicated, stored and served through the
# artifact registry (/api/v1/artifacts). Exposing the raw job API as well would be a second render pipeline whose output
# is not registered, and would let a client start renders that bypass the registry's de-duplication.


@router.get("/config")
async def config(request: Request) -> Response:
    return await reverse_proxy(request)


@router.post("/repair")
async def repair(request: Request) -> Response:
    return await reverse_proxy(request)
