# API

Contract: [openapi.yaml](openapi.yaml). Run locally:

```bash
SKILLDRAFT_ENV=dev python -m skilldraft serve --port 8080
```

## Draft a profile

```bash
curl -s localhost:8080/v1/skill-profiles -H 'Content-Type: application/json' -d '{
  "text": "Warehouse Supervisor\nYour profile\nYou have experience with WMS and forklift driving.\nYou speak fluent Dutch."
}'
```

```json
{
  "request_id": "5f2c0e9b1a7d4c33",
  "skills": [
    {"id": "dutch", "label": "Dutch", "status": "suggested", "importance": "required", "confidence": 0.999,
     "evidence": [{"start": 102, "end": 107, "quote": "Dutch", "kind": "exact", "section": "req", "sentence": 3},
                  {"start": 85, "end": 108, "quote": "You speak fluent Dutch.", "kind": "semantic", "section": "req", "sentence": 3}]},
    {"id": "forklift", "label": "Forklift operation", "status": "suggested", "importance": "required", "confidence": 0.995,
     "evidence": [{"start": 67, "end": 75, "quote": "forklift", "kind": "exact", "section": "req", "sentence": 2}, "…"]},
    {"id": "wms", "label": "Warehouse management systems", "status": "suggested", "importance": "required", "confidence": 0.947,
     "evidence": [{"start": 59, "end": 62, "quote": "WMS", "kind": "exact", "section": "req", "sentence": 2}]}
  ],
  "uncovered_requirements": [],
  "language_flags": [],
  "meta": {"config": "D", "taxonomy_version": "2026.10", "embedder": "hashing-v1",
           "model_version": "scorer-…", "language": "en", "latency_ms": 0.92}
}
```

(Real output of the current model; one evidence list shortened with "…".)

## Record a verdict

```bash
curl -s localhost:8080/v1/feedback -H 'Content-Type: application/json' \
  -d '{"request_id": "5f2c0e9b1a7d4c33", "skill_id": "wms", "verdict": "accept"}'
```

`accept` and `reject` must refer to a skill the request returned (otherwise `409`); `add` can name any taxonomy skill.

## Rank people (phase 2)

```bash
curl -s localhost:8080/v1/matches -H 'Content-Type: application/json' -d '{
  "skills": [{"id": "wms", "importance": "required"}, {"id": "forklift", "importance": "preferred"}],
  "people": [{"id": "EMP-1", "skills": ["forklift"]}, {"id": "EMP-2", "skills": ["wms", "inventory-management"]}]
}'
```

## Errors

RFC 9457 problem details, content type `application/problem+json`:

| Status | When |
|---|---|
| 400 | Body is not JSON |
| 401 | Missing or wrong bearer token |
| 404 | Unknown path or skill id |
| 405 | Known path, wrong method |
| 409 | Feedback on a skill the request did not return |
| 413 | Body over 64 KB, text over 20,000 characters, or more than 5,000 people |
| 422 | Valid JSON, invalid content |

## Design notes

- **Versioned path** (`/v1`) and explicit versions in every response (`taxonomy_version`, `model_version`), so a stored profile can always be traced to what produced it.
- **Request id** from `X-Request-Id` (sanitised) or generated; returned in the header and the body; in every log line.
- **Idempotent by nature:** the same text gives the same profile. Feedback is append-only.
- **No text in logs, metrics or feedback.** The API logs lengths and counts.
