# Observability

## Logs (JSON lines on stderr)

| Event | Fields | Never |
|---|---|---|
| `http` | request id, method, route template, status, latency | path parameters with data, bodies |
| `skill_profile` | request id, characters, suggested, needs_review, uncovered, model version | the text, quotes, names |
| `span` | name, trace id (= request id), span id, status, duration | inputs |
| `error` | request id, route, exception type | messages, stack traces with data |

## Metrics (`GET /metrics`, Prometheus text)

| Metric | Type | Question it answers |
|---|---|---|
| `skilldraft_http_requests_total{route,status}` | counter | availability, error rate |
| `skilldraft_http_request_duration_ms{route}` | histogram | latency SLO |
| `skilldraft_skills_total{status}` | counter | review load: ratio of needs_review to suggested |
| `skilldraft_uncovered_requirements_total` | counter | taxonomy gaps (drift signal) |
| `skilldraft_language_flags_total` | counter | coded language in incoming ads |
| `skilldraft_feedback_total{verdict}` | counter | accept/reject/add rates: the online quality signal |

## SLOs (pilot)

| SLO | Target | Error budget (30 days) |
|---|---|---|
| Availability of `/v1/skill-profiles` (non-5xx) | 99.5% | ~3.6 hours |
| Latency p95 in process | < 250 ms | – |
| Online precision proxy: accept / (accept + reject) of suggested | ≥ 90% weekly | – |

## Drift: what moves before quality drops

- **Uncovered requirements per profile** going up: new kinds of roles or wording the taxonomy does not know.
- **needs_review / suggested** going up: inputs look less like the training data.
- **Reject rate** going up for one family or language: a targeted regression.

Each of these has an alert at two weeks above the pilot baseline; the runbook says what to look at.
