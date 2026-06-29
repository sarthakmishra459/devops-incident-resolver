import json
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from devops_resolver.application.schemas import (
    CreateIncidentRequest,
    CreateIncidentResponse,
    DemoIncidentResponse,
    IncidentHistoryResponse,
    InvestigationResponse,
    RunbookResponse,
)
from devops_resolver.application.use_cases import IncidentService
from devops_resolver.domain.models import AgentTraceEvent, IncidentSeverity
from devops_resolver.presentation.api.dependencies import get_container, get_incident_service
from devops_resolver.shared.ids import new_id

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/incidents",
    response_model=CreateIncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident(
    request: CreateIncidentRequest,
    background_tasks: BackgroundTasks,
    service: IncidentService = Depends(get_incident_service),
) -> CreateIncidentResponse:
    incident = await service.create_incident(request)
    background_tasks.add_task(service.investigate_background, incident.id)
    return CreateIncidentResponse(incident=incident)


@router.post(
    "/incidents/upload",
    response_model=CreateIncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident_from_upload(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(...),
    severity: IncidentSeverity = Form(IncidentSeverity.high),
    file: UploadFile = File(...),
    service: IncidentService = Depends(get_incident_service),
) -> CreateIncidentResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")
    if file.content_type and not (
        file.content_type.startswith("text/") or file.content_type in {"application/octet-stream"}
    ):
        raise HTTPException(status_code=400, detail="Only text log files are supported")

    upload_dir = get_container().settings.upload_dir
    safe_name = Path(file.filename).name.replace(" ", "_")
    destination = upload_dir / f"{new_id('log')}_{safe_name}"
    async with aiofiles.open(destination, "wb") as handle:
        while chunk := await file.read(1024 * 1024):
            await handle.write(chunk)

    incident = await service.create_incident(
        CreateIncidentRequest(title=title, description=description, severity=severity),
        uploaded_log_path=str(destination),
    )
    background_tasks.add_task(service.investigate_background, incident.id)
    return CreateIncidentResponse(incident=incident)


@router.get("/incidents", response_model=IncidentHistoryResponse)
async def list_incidents(
    service: IncidentService = Depends(get_incident_service),
) -> IncidentHistoryResponse:
    return IncidentHistoryResponse(incidents=await service.list_incidents())


@router.get("/incidents/{incident_id}", response_model=InvestigationResponse)
async def get_incident(
    incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> InvestigationResponse:
    incident = await service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return InvestigationResponse(incident=incident, report=incident.report)


@router.post("/incidents/{incident_id}/investigate", response_model=InvestigationResponse)
async def investigate_incident(
    incident_id: str,
    background_tasks: BackgroundTasks,
    service: IncidentService = Depends(get_incident_service),
) -> InvestigationResponse:
    incident = await service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    background_tasks.add_task(service.investigate_background, incident.id)
    return InvestigationResponse(incident=incident, report=incident.report)


@router.get("/incidents/{incident_id}/trace")
async def list_trace(
    incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> dict[str, list[AgentTraceEvent]]:
    incident = await service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"trace": await service.list_traces(incident_id)}


@router.get("/incidents/{incident_id}/stream")
async def stream_incident(
    incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> StreamingResponse:
    if await service.get_incident(incident_id) is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    async def event_source() -> AsyncIterator[str]:
        async for event in service.stream(incident_id):
            payload = event.model_dump(mode="json")
            yield f"event: {event.type}\ndata: {json.dumps(payload, default=str)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@router.get("/runbooks", response_model=list[RunbookResponse])
async def list_runbooks(
    service: IncidentService = Depends(get_incident_service),
) -> list[RunbookResponse]:
    return [
        RunbookResponse(
            id=document.id,
            title=document.title,
            category=document.category,
            tags=document.tags,
            content=document.content,
        )
        for document in await service.list_runbooks()
    ]


@router.get("/demos", response_model=DemoIncidentResponse)
async def list_demos(
    service: IncidentService = Depends(get_incident_service),
) -> DemoIncidentResponse:
    return DemoIncidentResponse(demos=await service.list_demo_incidents())
