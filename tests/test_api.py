import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from skilldraft.api import ROUTES, App, make_handler

ROOT = Path(__file__).resolve().parent.parent
JD = "Warehouse Supervisor\nYour profile\nYou have experience with WMS and forklift driving.\nYou speak fluent Dutch."


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.log = Path(cls.tmp.name) / "feedback.jsonl"
        cls.app = App(feedback_log=cls.log, api_keys=["secret-key"])
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.app))
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def call(self, method, path, body=None, key="secret-key", raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if key:
            req.add_header("Authorization", "Bearer " + key)
        try:
            with urllib.request.urlopen(req) as r:
                text = r.read().decode()
                return r.status, (json.loads(text) if r.headers["Content-Type"].startswith("application/json") else text), r.headers
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode()), e.headers

    def test_profile_and_feedback_loop(self):
        status, out, headers = self.call("POST", "/v1/skill-profiles", {"text": JD})
        self.assertEqual(status, 200)
        self.assertEqual(headers["X-Request-Id"], out["request_id"])
        ids = {s["id"] for s in out["skills"]}
        self.assertTrue({"wms", "forklift", "dutch"} <= ids)
        status, _, _ = self.call("POST", "/v1/feedback", {"request_id": out["request_id"], "skill_id": "wms", "verdict": "accept"})
        self.assertEqual(status, 202)
        row = json.loads(self.log.read_text().splitlines()[-1])
        self.assertEqual((row["skill_id"], row["verdict"]), ("wms", "accept"))
        self.assertNotIn("text", row)
        status, p, _ = self.call("POST", "/v1/feedback", {"request_id": out["request_id"], "skill_id": "welding", "verdict": "reject"})
        self.assertEqual((status, p["title"]), (409, "Unknown suggestion"))

    def test_auth(self):
        self.assertEqual(self.call("POST", "/v1/skill-profiles", {"text": JD}, key=None)[0], 401)
        self.assertEqual(self.call("POST", "/v1/skill-profiles", {"text": JD}, key="wrong")[0], 401)
        self.assertEqual(self.call("GET", "/healthz", key=None)[0], 200)

    def test_problem_details(self):
        for body, raw, status in [({"text": ""}, None, 422), (None, b"{not json", 400), ({"text": "x" * 20001}, None, 413), (["a"], None, 422)]:
            code, p, headers = self.call("POST", "/v1/skill-profiles", body, raw=raw)
            self.assertEqual(code, status)
            self.assertEqual(headers["Content-Type"], "application/problem+json")
            self.assertEqual(p["status"], status)
        self.assertEqual(self.call("GET", "/v1/skills/nope")[0], 404)
        self.assertEqual(self.call("GET", "/v1/skill-profiles")[0], 405)
        self.assertEqual(self.call("GET", "/v2/anything")[0], 404)

    def test_matches(self):
        body = {"skills": [{"id": "wms", "importance": "required"}, {"id": "forklift", "importance": "preferred"}],
                "people": [{"id": "p1", "skills": ["forklift"]}, {"id": "p2", "skills": ["wms", "forklift"]}]}
        status, out, _ = self.call("POST", "/v1/matches", body)
        self.assertEqual([r["person_id"] for r in out["results"]], ["p2", "p1"])
        self.assertIn("not a decision", out["note"])
        bad = {"skills": [{"id": "made-up", "importance": "required"}], "people": [{"id": "p", "skills": []}]}
        self.assertEqual(self.call("POST", "/v1/matches", bad)[0], 422)

    def test_skills_and_metrics(self):
        _, out, _ = self.call("GET", "/v1/skills?q=k8s")
        self.assertEqual(out["items"][0]["id"], "kubernetes")
        _, s, _ = self.call("GET", "/v1/skills/kubernetes")
        self.assertEqual(s["label"], "Kubernetes")
        self.call("POST", "/v1/skill-profiles", {"text": JD})
        status, metrics, _ = self.call("GET", "/metrics", key=None)
        self.assertIn('skilldraft_http_requests_total{route="/v1/skill-profiles",status="200"}', metrics)
        self.assertIn("skilldraft_http_request_duration_ms_bucket", metrics)

    def test_routes_match_the_openapi_contract(self):
        spec = (ROOT / "docs" / "02-design" / "openapi.yaml").read_text()
        paths = re.findall(r"^  (/[^:]*):\n    (get|post):", spec, re.M)
        self.assertEqual(sorted((m.upper(), p) for p, m in paths), sorted(ROUTES))


if __name__ == "__main__":
    unittest.main()
