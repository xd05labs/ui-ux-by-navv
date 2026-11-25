"""Execute real WSGI requests against isolated SQLite databases."""
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class Client:
    def __init__(self, app):
        self.app, self.cookie, self.csrf = app, "", ""

    def call(self, path, method="GET", data=None, headers=None, raw=None):
        body = raw if raw is not None else json.dumps(data or {}).encode()
        route, _, query = path.partition("?")
        environ = {"PATH_INFO": route, "QUERY_STRING": query, "REQUEST_METHOD": method,
                   "HTTP_HOST": "127.0.0.1:8000", "REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http",
                   "wsgi.input": io.BytesIO(body), "CONTENT_LENGTH": str(len(body)), "CONTENT_TYPE": "application/json",
                   "HTTP_COOKIE": self.cookie, "HTTP_X_CSRF_TOKEN": self.csrf, **(headers or {})}
        response = {}
        result = b"".join(self.app.application(environ, lambda status, hdrs: response.update(status=int(status.split()[0]), headers=dict(hdrs))))
        if "Set-Cookie" in response["headers"]:
            self.cookie = response["headers"]["Set-Cookie"].split(";")[0]
        if response["headers"].get("Content-Type", "").startswith("application/json"):
            result = json.loads(result)
            if "csrf" in result and result["csrf"]:
                self.csrf = result["csrf"]
        return response["status"], result, response["headers"]

    def register(self, email="owner@example.com"):
        return self.call("/api/register", "POST", {"email": email, "password": "a long test password"})


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        os.environ["APP_DATABASE"] = str(Path(self.temp.name) / "test.sqlite3")
        os.environ["APP_ORIGIN"] = "http://127.0.0.1:8000"
        os.environ["APP_SECURE_COOKIES"] = "false"
        os.environ["APP_ALLOW_REGISTRATION"] = "true"
        import app
        self.app = importlib.reload(app)
        self.client = Client(self.app)

    def payload(self, title="A working record"):
        values = {}
        for field in self.app.BP["fields"]:
            values[field["name"]] = 42 if field["type"] == "number" else "2026-11-25" if field["type"] == "date" else "https://example.com" if field["type"] == "url" else "Test value"
        return {"title": title, "description": "Integration test", "status": self.app.BP["statuses"][0], "fields": values}

    def create(self, title="A working record"):
        status, body, _ = self.client.call("/api/records", "POST", self.payload(title))
        self.assertEqual(status, 201, body)
        return body["record"]["id"]

    def test_health_and_migrations_are_idempotent(self):
        self.app.initialize()
        self.assertEqual(self.client.call("/api/health")[0], 200)
        with self.app.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 1)

    def test_private_records_require_session(self):
        self.assertEqual(self.client.call("/api/records")[0], 401)

    def test_registration_cookie_hash_and_logout(self):
        status, body, headers = self.client.register()
        self.assertEqual(status, 200)
        self.assertEqual(body["user"]["role"], "admin")
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        with self.app.connect() as db:
            row = db.execute("SELECT * FROM users").fetchone()
            self.assertNotEqual(row["password_hash"], "a long test password")
            stored = db.execute("SELECT token_hash FROM sessions").fetchone()[0]
            self.assertNotEqual(stored, self.client.cookie.split("=", 1)[1])
        self.assertEqual(self.client.call("/api/logout", "POST")[0], 200)
        self.assertEqual(self.client.call("/api/records")[0], 401)

    def test_login_wrong_password_and_expired_session(self):
        self.client.register()
        self.client.call("/api/logout", "POST")
        self.assertEqual(self.client.call("/api/login", "POST", {"email": "owner@example.com", "password": "incorrect test password"})[0], 401)
        self.assertEqual(self.client.call("/api/login", "POST", {"email": "owner@example.com", "password": "a long test password"})[0], 200)
        with self.app.connect() as db:
            db.execute("UPDATE sessions SET expires_at=0")
        self.assertEqual(self.client.call("/api/records")[0], 401)

    def test_crud_and_audit(self):
        self.client.register()
        record_id = self.create()
        self.assertEqual(len(self.client.call("/api/records")[1]["records"]), 1)
        self.assertEqual(self.client.call(f"/api/records/{record_id}", "PUT", self.payload("Changed"))[0], 200)
        self.assertEqual(self.client.call(f"/api/records/{record_id}", "DELETE")[0], 200)
        self.assertEqual(self.client.call("/api/records")[1]["total"], 0)
        if self.app.FEATURES["auditLog"]:
            self.assertEqual([row["action"] for row in self.client.call("/api/activity")[1]["events"]], ["deleted", "updated", "created"])
        else:
            self.assertEqual(self.client.call("/api/activity")[0], 404)

    def test_ownership_is_enforced(self):
        self.client.register()
        record_id = self.create()
        other = Client(self.app)
        self.assertEqual(other.register("other@example.com")[1]["user"]["role"], "editor")
        self.assertEqual(other.call("/api/records")[1]["total"], 0)
        self.assertEqual(other.call(f"/api/records/{record_id}", "PUT", self.payload("Stolen"))[0], 404)
        self.assertEqual(other.call(f"/api/records/{record_id}", "DELETE")[0], 404)
        if self.app.FEATURES["export"]:
            self.assertNotIn(b"A working record", other.call("/api/export")[1])

    def test_viewer_role_blocks_writes(self):
        self.client.register()
        self.create()
        with self.app.connect() as db:
            db.execute("UPDATE users SET role='viewer'")
        status = self.client.call("/api/records", "POST", self.payload())[0]
        self.assertEqual(status, 403 if self.app.FEATURES["roleBasedAccess"] else 201)
        self.assertEqual(self.client.call("/api/records")[0], 200)

    def test_csrf_and_origin(self):
        self.client.register()
        self.assertEqual(self.client.call("/api/records", "POST", self.payload(), {"HTTP_X_CSRF_TOKEN": "invalid"})[0], 403)
        self.assertEqual(self.client.call("/api/records", "POST", self.payload(), {"HTTP_X_CSRF_TOKEN": "\u00e9"})[0], 403)
        self.assertEqual(self.client.call("/api/records", "POST", self.payload(), {"HTTP_ORIGIN": "https://evil.example"})[0], 403)
        self.assertEqual(self.client.call("/api/login", "POST", {}, {"HTTP_SEC_FETCH_SITE": "cross-site"})[0], 403)

    def test_validation_and_json_bounds(self):
        self.client.register()
        for payload in [{"title": "", "status": "x"}, {**self.payload(), "status": "unknown"}, {**self.payload(), "fields": {"unknown": 1}}, {**self.payload(), "extra": True}]:
            self.assertEqual(self.client.call("/api/records", "POST", payload)[0], 400)
        self.assertEqual(self.client.call("/api/records", "POST", raw=b'{"x":NaN}')[0], 400)
        self.assertEqual(self.client.call("/api/records", "POST", raw=b'{bad')[0], 400)
        self.assertEqual(self.client.call("/api/records", "POST", raw=b'{"title":"\\ud800"}')[0], 400)
        self.assertEqual(self.client.call("/api/records", "POST", {}, {"CONTENT_LENGTH": "200000"})[0], 413)
        self.assertEqual(self.client.call("/api/records", "POST", {}, {"CONTENT_TYPE": "text/plain"})[0], 415)

    def test_search_filter_and_sql_input(self):
        self.client.register()
        self.create("Find me")
        self.create("Other")
        count = len(self.client.call("/api/records?q=Find")[1]["records"])
        self.assertEqual(count, 1 if self.app.FEATURES["search"] else 2)
        self.assertEqual(self.client.call("/api/records?q=%27%20OR%201%3D1--")[0], 200)
        self.assertEqual(self.client.call("/api/records?status=missing")[1]["records"], [])

    def test_export_formula_injection_is_escaped(self):
        self.client.register()
        self.create(' =HYPERLINK("https://evil.example")')
        status, body, _ = self.client.call("/api/export")
        self.assertEqual(status, 200 if self.app.FEATURES["export"] else 404)
        if self.app.FEATURES["export"]:
            self.assertIn(b"'=HYPERLINK", body)
            self.assertIn("text/csv", self.client.call("/api/export")[2]["Content-Type"])

    def test_host_and_static_allowlist(self):
        self.assertEqual(self.client.call("/api/health", headers={"HTTP_HOST": "evil.example"})[0], 400)
        for path in ("/.env", "/app.py", "/../app.py", "/app.config.json"):
            self.assertEqual(self.client.call(path)[0], 404)
        status, _, headers = self.client.call("/")
        self.assertEqual(status, 200 if (self.app.ROOT / "static" / "index.html").exists() else 404)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

    def test_auth_rate_limit_counts_failures(self):
        for _ in range(20):
            self.assertEqual(self.client.call("/api/login", "POST", {"email": "missing@example.com", "password": "incorrect test password"})[0], 401)
        self.assertEqual(self.client.call("/api/login", "POST", {"email": "missing@example.com", "password": "incorrect test password"})[0], 429)

    def test_disabled_registration_and_secure_cookies(self):
        self.app.REGISTRATION = False
        self.assertEqual(self.client.register()[0], 403)
        self.app.REGISTRATION = True
        self.app.SECURE = True
        self.assertIn("Secure", self.client.register()[2]["Set-Cookie"])


if __name__ == "__main__":
    unittest.main()
