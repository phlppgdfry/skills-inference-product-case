"""The same API on FastAPI, for teams that run their services on it.

    pip install ".[api]"
    uvicorn skilldraft.adapters.fastapi_app:app --port 8080

Typed request models (Pydantic) and generated OpenAPI docs at /docs; the business logic,
limits, feedback rules and problem details are the ones in skilldraft/api.py, so the two
servers cannot drift apart (tests/test_fastapi.py runs the same scenarios against both).
"""

from __future__ import annotations

from typing import Literal

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .. import __version__
from ..api import METRICS, App, Problem
from ..obs import new_id


class ProfileRequest(BaseModel):
    text: str = Field(..., description="Job description, at most 20,000 characters")


class PersonProfileRequest(BaseModel):
    text: str = Field(..., description="CV text; personal data is masked before processing")
    consent: bool = Field(False, description="The person was informed and agreed")


class RoleSkill(BaseModel):
    id: str
    importance: Literal["required", "preferred"]
    status: Literal["suggested", "needs_review"] = "suggested"
    confidence: float = 1.0


class Person(BaseModel):
    id: str
    skills: list[str]


class MatchRequest(BaseModel):
    skills: list[RoleSkill]
    people: list[Person]
    limit: int = 20


class FeedbackRequest(BaseModel):
    request_id: str
    skill_id: str
    verdict: Literal["accept", "reject", "add"]


class DevelopmentPlanRequest(BaseModel):
    role_skills: list[RoleSkill]
    person_skills: list[str]


def create_app(core: App | None = None) -> FastAPI:
    core = core or App()
    api = FastAPI(title="SkillDraft API", version=__version__,
                  description="Draft skill profiles with evidence, for people to review. Fictional portfolio case.")

    @api.exception_handler(Problem)
    async def problem(_: Request, p: Problem) -> JSONResponse:
        return JSONResponse({"type": "about:blank", "title": p.title, "status": p.status, "detail": p.detail},
                            status_code=p.status, media_type="application/problem+json")

    @api.exception_handler(RequestValidationError)
    async def invalid(_: Request, e: RequestValidationError) -> JSONResponse:
        detail = "; ".join(f"{'.'.join(str(x) for x in err['loc'][1:])}: {err['msg']}" for err in e.errors())
        return JSONResponse({"type": "about:blank", "title": "Invalid request", "status": 422, "detail": detail},
                            status_code=422, media_type="application/problem+json")

    def auth(authorization: str | None = Header(default=None)) -> None:
        if not core.authorised(authorization):
            raise Problem(401, "Unauthorised", "Send Authorization: Bearer <api key>")

    def rid(x_request_id: str | None = Header(default=None)) -> str:
        return "".join(c for c in (x_request_id or "") if c.isalnum() or c == "-")[:64] or new_id()

    @api.post("/v1/skill-profiles", dependencies=[Depends(auth)])
    def skill_profile(req: ProfileRequest, request_id: str = Depends(rid)) -> dict:
        return core.profile(req.model_dump(), request_id)

    @api.post("/v1/person-profiles", dependencies=[Depends(auth)])
    def person_profile(req: PersonProfileRequest, request_id: str = Depends(rid)) -> dict:
        return core.person_profile(req.model_dump(), request_id)

    @api.post("/v1/matches", dependencies=[Depends(auth)])
    def matches(req: MatchRequest, request_id: str = Depends(rid)) -> dict:
        return core.matches(req.model_dump(), request_id)

    @api.post("/v1/development-plans", dependencies=[Depends(auth)])
    def development_plan(req: DevelopmentPlanRequest, request_id: str = Depends(rid)) -> dict:
        return core.development_plan(req.model_dump(), request_id)

    @api.post("/v1/feedback", status_code=202, dependencies=[Depends(auth)])
    def feedback(req: FeedbackRequest, request_id: str = Depends(rid)) -> dict:
        return core.feedback(req.model_dump(), request_id)

    @api.get("/v1/skills", dependencies=[Depends(auth)])
    def skills(q: str = "") -> dict:
        return core.handle("GET", "/v1/skills", {"q": [q]} if q else {}, None, new_id())[1]

    @api.get("/v1/skills/{skill_id}", dependencies=[Depends(auth)])
    def skill(skill_id: str) -> dict:
        return core.handle("GET", f"/v1/skills/{skill_id}", {}, None, new_id())[1]

    @api.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "version": __version__}

    @api.get("/readyz")
    def readyz() -> dict:
        return core.handle("GET", "/readyz", {}, None, new_id())[1]

    @api.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> str:
        return METRICS.render()

    return api


def __getattr__(name: str):
    # `uvicorn skilldraft.adapters.fastapi_app:app` builds the app on first access, not at import
    if name == "app":
        return create_app()
    raise AttributeError(name)
