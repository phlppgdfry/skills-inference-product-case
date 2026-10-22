"""The FastAPI adapter gives the same answers as the stdlib server. Runs where FastAPI is
installed (CI job 'ml'); skipped otherwise."""
import json
import unittest

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

JD = "Warehouse Supervisor\nYour profile\nYou have experience with WMS and forklift driving.\nYou speak fluent Dutch."


@unittest.skipIf(TestClient is None, "FastAPI not installed")
class FastApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from skilldraft.adapters.fastapi_app import create_app
        from skilldraft.api import App

        cls.core = App(api_keys=["k"], person_profiles=True)
        cls.client = TestClient(create_app(cls.core))
        cls.h = {"Authorization": "Bearer k"}

    def test_same_profile_as_the_core(self):
        r = self.client.post("/v1/skill-profiles", json={"text": JD}, headers=self.h)
        self.assertEqual(r.status_code, 200)
        core = self.core.profile({"text": JD}, "x")
        strip = lambda o: [(s["id"], s["status"], s["confidence"]) for s in o["skills"]]  # noqa: E731
        self.assertEqual(strip(r.json()), strip(core))

    def test_problem_details(self):
        self.assertEqual(self.client.post("/v1/skill-profiles", json={"text": JD}).status_code, 401)
        r = self.client.post("/v1/skill-profiles", json={"txt": JD}, headers=self.h)
        self.assertEqual((r.status_code, r.headers["content-type"]), (422, "application/problem+json"))
        r = self.client.post("/v1/skill-profiles", json={"text": ""}, headers=self.h)
        self.assertEqual(r.json()["title"], "Invalid request")

    def test_person_profile_and_plan(self):
        cv = "Ann Peeters\nExperience\n- Worked daily with PLC programming."
        self.assertEqual(self.client.post("/v1/person-profiles", json={"text": cv}, headers=self.h).status_code, 422)
        r = self.client.post("/v1/person-profiles", json={"text": cv, "consent": True}, headers=self.h)
        self.assertNotIn("Peeters", json.dumps(r.json()))
        r = self.client.post("/v1/development-plans", headers=self.h,
                             json={"role_skills": [{"id": "plc-programming", "importance": "required"}], "person_skills": ["plc-programming"]})
        self.assertEqual(r.json()["coverage"], 1.0)

    def test_generated_openapi_has_the_routes(self):
        paths = set(self.client.get("/openapi.json").json()["paths"])
        self.assertTrue({"/v1/skill-profiles", "/v1/person-profiles", "/v1/development-plans", "/v1/matches", "/v1/feedback"} <= paths)


if __name__ == "__main__":
    unittest.main()
