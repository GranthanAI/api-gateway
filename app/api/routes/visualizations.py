from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/visualizations", tags=["Visualizations"])


@router.get("/config")
async def config(request: Request) -> Response:
    return await reverse_proxy(request)


@router.post("/repair")
async def repair(request: Request) -> Response:
    return await reverse_proxy(request)


@router.post("/manim/jobs")
async def create_job(request: Request) -> Response:
    return await reverse_proxy(request)


@router.get("/manim/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> Response:
    return await reverse_proxy(request)


@router.get("/manim/jobs/{job_id}/media")
async def get_media(job_id: str, request: Request) -> Response:
    """The rendered video. Authenticated like every other route, so the clip is never a public URL."""
    return await reverse_proxy(request)


@router.delete("/manim/jobs/{job_id}")
async def cancel_job(job_id: str, request: Request) -> Response:
    return await reverse_proxy(request)
