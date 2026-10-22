"""HTTP API on the standard library (contract: docs/02-design/openapi.yaml).

    POST /v1/skill-profiles   job description text → draft skill profile with evidence
    POST /v1/matches          role skills + people → ranked people with gaps
    GET  /v1/skills           search the taxonomy (?q=)
    GET  /v1/skills/{id}      one skill
    POST /v1/feedback         reviewer verdict on one suggested skill (the training signal)
    POST /v1/person-profiles  CV text → draft skills of a person, personal data masked (flag: person_profiles)
    POST /v1/development-plans role skills + a person's skills → coverage and ordered gaps
    GET  /healthz /readyz /metrics

Auth: Authorization: Bearer <key>, keys in SKILLDRAFT_API_KEYS (comma-separated). With
SKILLDRAFT_ENV=dev and no keys, the API is open on localhost for the demo.
Errors are RFC 9457 problem details. Request bodies are capped; text is never logged.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__, default_pipeline
from .match import rank
from .obs import METRICS, log, new_id, span

MAX_BODY = 64 * 1024
MAX_TEXT = 20_000
MAX_PEOPLE = 5_000
VERDICTS = {"accept", "reject", "add"}
ROUTES = [
    ("POST", "/v1/skill-profiles"), ("POST", "/v1/matches"), ("GET", "/v1/skills"), ("GET", "/v1/skills/{id}"),
    ("POST", "/v1/feedback"), ("POST", "/v1/person-profiles"), ("POST", "/v1/development-plans"),
    ("GET", "/healthz"), ("GET", "/readyz"), ("GET", "/metrics"),
]


class Problem(Exception):
    def __init__(self, status: int, title: str, detail: str = ""):
        super().__init__(detail or title)
        self.status, self.title, self.detail = status, title, detail


class App:
    def __init__(self, pipeline=None, feedback_log: Path | None = None, api_keys: list[str] | None = None, env: str | None = None,
                 person_profiles: bool | None = None):
        if pipeline is None:
            # SKILLDRAFT_VERIFIER=anthropic|bedrock sends the review band to Claude (skilldraft/llm.py)
            platform = os.environ.get("SKILLDRAFT_VERIFIER")
            verifier = None
            if platform:
                from .llm import ClaudeVerifier
                verifier = ClaudeVerifier(platform=platform)
            pipeline = default_pipeline(verifier=verifier)
        self.pipeline = pipeline
        # Phase 2: person profiles are high-risk territory (docs/04-quality/ai-act.md). Off unless
        # the flag is set; on by default only in dev.
        if person_profiles is None:
            person_profiles = os.environ.get("SKILLDRAFT_PERSON_PROFILES", "on" if os.environ.get("SKILLDRAFT_ENV") == "dev" else "off") == "on"
        self.cv_pipeline = default_pipeline(kind="cv", embedder="hf" if self.pipeline.embedder.name.startswith("hf-") else "hashing") \
            if person_profiles else None
        self.related = {s["id"]: s["related"] for s in self.pipeline.taxonomy.skills}
        keys = api_keys if api_keys is not None else [k for k in os.environ.get("SKILLDRAFT_API_KEYS", "").split(",") if k]
        self.api_keys = keys
        self.env = env or os.environ.get("SKILLDRAFT_ENV", "prod")
        self.feedback_log = feedback_log or Path(os.environ.get("SKILLDRAFT_FEEDBACK_LOG", "var/feedback.jsonl"))
        self.lock = threading.Lock()
        self.issued: dict[str, set[str]] = {}  # request id → skill ids it returned (bounded, see _remember)

    # ------------------------------------------------------------ auth
    def authorised(self, header: str | None) -> bool:
        if not self.api_keys:
            return self.env == "dev"
        token = (header or "").removeprefix("Bearer ").strip()
        return any(hmac.compare_digest(token, k) for k in self.api_keys)

    # ------------------------------------------------------------ handlers
    def handle(self, method: str, path: str, query: dict, body: dict | None, request_id: str) -> tuple[int, dict | str]:
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok", "version": __version__}
        if method == "GET" and path == "/readyz":
            return 200, {"status": "ready", "model_version": self.pipeline.model.version if self.pipeline.model else None,
                         "taxonomy_version": self.pipeline.taxonomy.version}
        if method == "GET" and path == "/metrics":
            return 200, METRICS.render()
        if method == "POST" and path == "/v1/skill-profiles":
            return 200, self.profile(body, request_id)
        if method == "POST" and path == "/v1/matches":
            return 200, self.matches(body, request_id)
        if method == "POST" and path == "/v1/feedback":
            return 202, self.feedback(body, request_id)
        if method == "POST" and path == "/v1/person-profiles":
            return 200, self.person_profile(body, request_id)
        if method == "POST" and path == "/v1/development-plans":
            return 200, self.development_plan(body, request_id)
        if method == "GET" and path == "/v1/skills":
            q = (query.get("q") or [""])[0]
            items = self.pipeline.taxonomy.search(q) if q else self.pipeline.taxonomy.skills
            return 200, {"taxonomy_version": self.pipeline.taxonomy.version, "items": [self.skill_view(s) for s in items]}
        m = re.fullmatch(r"/v1/skills/([a-z0-9-]+)", path)
        if method == "GET" and m:
            s = self.pipeline.taxonomy.by_id.get(m.group(1))
            if not s:
                raise Problem(404, "Unknown skill", f"No skill with id {m.group(1)!r} in taxonomy {self.pipeline.taxonomy.version}")
            return 200, self.skill_view(s)
        if any(p == path or (("{id}" in p) and re.fullmatch(p.replace("{id}", "[^/]+"), path)) for _, p in ROUTES):
            raise Problem(405, "Method not allowed")
        raise Problem(404, "Not found")

    def skill_view(self, s: dict) -> dict:
        return {"id": s["id"], "label": s["label"], "family": s["family"], "definition": s["definition"],
                "aliases": [a["text"] for a in s["aliases"]], "related": s["related"]}

    def profile(self, body: dict | None, request_id: str) -> dict:
        text = (body or {}).get("text")
        if not isinstance(text, str) or not text.strip():
            raise Problem(422, "Invalid request", "'text' must be a non-empty string")
        if len(text) > MAX_TEXT:
            raise Problem(413, "Text too long", f"At most {MAX_TEXT} characters")
        with span("skill_profile.infer", request_id, chars=len(text)):
            out = self.pipeline.infer(text)
        status_counts = {"suggested": 0, "needs_review": 0}
        for s in out["skills"]:
            status_counts[s["status"]] += 1
            METRICS.inc("skilldraft_skills_total", status=s["status"])
        METRICS.inc("skilldraft_uncovered_requirements_total", len(out["uncovered_requirements"]))
        METRICS.inc("skilldraft_language_flags_total", len(out["language_flags"]))
        self._remember(request_id, {s["id"] for s in out["skills"]})
        log("skill_profile", request_id=request_id, chars=len(text), **status_counts,
            uncovered=len(out["uncovered_requirements"]), model_version=out["meta"]["model_version"])
        return {"request_id": request_id, **out}

    def person_profile(self, body: dict | None, request_id: str) -> dict:
        if self.cv_pipeline is None:
            raise Problem(404, "Not enabled", "Person profiles are off for this deployment (feature flag person_profiles)")
        body = body or {}
        text = body.get("text")
        if body.get("consent") is not True:
            raise Problem(422, "Consent required", "Set 'consent': true to confirm the person was informed and agreed (ADR-0010)")
        if not isinstance(text, str) or not text.strip():
            raise Problem(422, "Invalid request", "'text' must be a non-empty string")
        if len(text) > MAX_TEXT:
            raise Problem(413, "Text too long", f"At most {MAX_TEXT} characters")
        with span("person_profile.infer", request_id, chars=len(text)):
            out = self.cv_pipeline.infer(text)
        for kind, n in out["redactions"].items():
            METRICS.inc("skilldraft_redactions_total", n, kind=kind)
        self._remember(request_id, {s["id"] for s in out["skills"]})
        log("person_profile", request_id=request_id, chars=len(text), skills=len(out["skills"]),
            redactions=sum(out["redactions"].values()), model_version=out["meta"]["model_version"])
        return {"request_id": request_id, **out,
                "note": "Draft for the person and HR to review. Personal data was masked before processing and is not stored."}

    def development_plan(self, body: dict | None, request_id: str) -> dict:
        from .development import plan

        body = body or {}
        role, person = body.get("role_skills"), body.get("person_skills")
        if not isinstance(role, list) or not isinstance(person, list):
            raise Problem(422, "Invalid request", "'role_skills' (list of {id, importance}) and 'person_skills' (list of ids) are required")
        tax = self.pipeline.taxonomy.by_id
        if any(not isinstance(s, dict) or s.get("id") not in tax or s.get("importance") not in ("required", "preferred") for s in role) \
                or any(p not in tax for p in person):
            raise Problem(422, "Invalid skill", "every skill must be a taxonomy id; role skills need importance 'required' or 'preferred'")
        return {"request_id": request_id, **plan(role, person, self.pipeline.taxonomy)}

    def matches(self, body: dict | None, request_id: str) -> dict:
        body = body or {}
        skills, people = body.get("skills"), body.get("people")
        if not isinstance(skills, list) or not isinstance(people, list) or not people:
            raise Problem(422, "Invalid request", "'skills' (list) and 'people' (non-empty list) are required")
        if len(people) > MAX_PEOPLE:
            raise Problem(413, "Too many people", f"At most {MAX_PEOPLE} per request")
        for s in skills:
            if not isinstance(s, dict) or s.get("id") not in self.pipeline.taxonomy.by_id or s.get("importance") not in ("required", "preferred"):
                raise Problem(422, "Invalid skill", "each skill needs a taxonomy 'id' and importance 'required' or 'preferred'")
        for p in people:
            if not isinstance(p, dict) or not isinstance(p.get("id"), str) or not isinstance(p.get("skills"), list):
                raise Problem(422, "Invalid person", "each person needs an 'id' and a list of skill ids")
        with span("match.rank", request_id, people=len(people)):
            ranked = rank(skills, people, related=self.related)
        return {"request_id": request_id, "results": ranked[: int(body.get("limit", 20))],
                "note": "A ranking to support a person's decision, not a decision (see docs/04-quality/ai-act.md)."}

    def feedback(self, body: dict | None, request_id: str) -> dict:
        body = body or {}
        ref, sid, verdict = body.get("request_id"), body.get("skill_id"), body.get("verdict")
        if verdict not in VERDICTS or sid not in self.pipeline.taxonomy.by_id or not isinstance(ref, str):
            raise Problem(422, "Invalid feedback", "'request_id', a taxonomy 'skill_id' and 'verdict' (accept, reject, add) are required")
        if verdict != "add" and sid not in self.issued.get(ref, set()):
            raise Problem(409, "Unknown suggestion", "accept/reject must refer to a skill returned by that request")
        row = {"ts": round(time.time(), 3), "request_id": ref, "skill_id": sid, "verdict": verdict,
               "model_version": self.pipeline.model.version if self.pipeline.model else None}
        with self.lock:
            self.feedback_log.parent.mkdir(parents=True, exist_ok=True)
            with self.feedback_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
        METRICS.inc("skilldraft_feedback_total", verdict=verdict)
        return {"request_id": request_id, "status": "recorded"}

    def _remember(self, request_id: str, ids: set[str]) -> None:
        with self.lock:
            self.issued[request_id] = ids
            while len(self.issued) > 10_000:
                self.issued.pop(next(iter(self.issued)))


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = "skilldraft/" + __version__

        def log_message(self, *args):  # replaced by structured logs
            pass

        def _send(self, status: int, payload, request_id: str, content_type: str = "application/json") -> None:
            data = payload.encode() if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False).encode()
            if isinstance(payload, str):
                content_type = "text/plain; version=0.0.4"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Request-Id", request_id)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _run(self, method: str) -> None:
            t0 = time.perf_counter()
            request_id = re.sub(r"[^A-Za-z0-9-]", "", self.headers.get("X-Request-Id", ""))[:64] or new_id()
            url = urlparse(self.path)
            route = re.sub(r"^/v1/skills/[^/]+$", "/v1/skills/{id}", url.path)
            status = 500
            try:
                if url.path.startswith("/v1/") and not app.authorised(self.headers.get("Authorization")):
                    raise Problem(401, "Unauthorised", "Send Authorization: Bearer <api key>")
                body = None
                if method == "POST":
                    length = int(self.headers.get("Content-Length") or 0)
                    if length > MAX_BODY:
                        raise Problem(413, "Body too large", f"At most {MAX_BODY} bytes")
                    try:
                        body = json.loads(self.rfile.read(length) or b"{}")
                    except json.JSONDecodeError:
                        raise Problem(400, "Malformed JSON") from None
                    if not isinstance(body, dict):
                        raise Problem(422, "Invalid request", "the body must be a JSON object")
                status, payload = app.handle(method, url.path, parse_qs(url.query), body, request_id)
                self._send(status, payload, request_id)
            except Problem as p:
                status = p.status
                self._send(status, {"type": "about:blank", "title": p.title, "status": p.status, "detail": p.detail,
                                    "request_id": request_id}, request_id, "application/problem+json")
            except Exception as e:  # never leak internals
                status = 500
                log("error", request_id=request_id, route=route, error=type(e).__name__)
                self._send(500, {"type": "about:blank", "title": "Internal error", "status": 500, "request_id": request_id},
                           request_id, "application/problem+json")
            finally:
                ms = (time.perf_counter() - t0) * 1000
                METRICS.inc("skilldraft_http_requests_total", route=route, status=status)
                METRICS.observe("skilldraft_http_request_duration_ms", ms, route=route)
                log("http", request_id=request_id, method=method, route=route, status=status, latency_ms=round(ms, 2))

        def do_GET(self):
            self._run("GET")

        def do_POST(self):
            self._run("POST")

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8080, app: App | None = None) -> None:
    app = app or App()
    httpd = ThreadingHTTPServer((host, port), make_handler(app))
    log("listening", host=host, port=port, model_version=app.pipeline.model.version if app.pipeline.model else None)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
