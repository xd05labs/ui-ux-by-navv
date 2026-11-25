"""Same-origin, owner-scoped WSGI application. No external service calls."""
import csv
import hashlib
import hmac
import io
import json
import math
import os
import re
import secrets
import sqlite3
import time
from datetime import date
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "app.config.json").read_text(encoding="utf-8"))
BP = CONFIG["blueprint"]
FEATURES = CONFIG["features"]
DB_PATH = Path(os.environ.get("APP_DATABASE", str(ROOT / ".data" / "app.sqlite3")))
ORIGIN = os.environ.get("APP_ORIGIN", "http://127.0.0.1:8000").rstrip("/")
SECURE = os.environ.get("APP_SECURE_COOKIES", "false").lower() == "true"
REGISTRATION = os.environ.get("APP_ALLOW_REGISTRATION", "true").lower() == "true"
SESSION_AGE = 60 * 60 * 12


class HTTPError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect():
    connection = sqlite3.connect(DB_PATH, timeout=10, factory=Connection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at INTEGER NOT NULL)")
        for path in sorted((ROOT / "migrations").glob("*.sql")):
            if not db.execute("SELECT 1 FROM schema_migrations WHERE version=?", (path.name,)).fetchone():
                # Filename is a bundled migration, not user input; quote it defensively.
                version = path.name.replace("'", "''")
                db.executescript("BEGIN IMMEDIATE;\n" + path.read_text(encoding="utf-8") +
                                 f"\nINSERT INTO schema_migrations VALUES ('{version}', {int(time.time())});\nCOMMIT;")


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32).hex()


def json_body(environ):
    if environ.get("CONTENT_TYPE", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPError(415, "Send application/json")
    try:
        size = int(environ.get("CONTENT_LENGTH") or "0")
        if size < 1 or size > 131072:
            raise HTTPError(413, "Request body must be between 1 and 131072 bytes")
        raw = environ["wsgi.input"].read(size)
        if len(raw) != size:
            raise HTTPError(400, "Incomplete request body")
        data = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        if not isinstance(data, dict):
            raise ValueError("object required")
        json.dumps(data, ensure_ascii=False).encode("utf-8")  # Reject lone surrogate escapes.
        return data
    except (ValueError, UnicodeDecodeError) as error:
        raise HTTPError(400, "Invalid JSON object") from error


def session(environ, db, required=True):
    cookies = SimpleCookie()
    try:
        cookies.load(environ.get("HTTP_COOKIE", ""))
        token = cookies["app_session"].value if "app_session" in cookies else ""
    except Exception:
        token = ""
    if len(token) > 200:
        token = ""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = db.execute("SELECT users.id, email, role, csrf, token_hash FROM sessions JOIN users ON users.id=sessions.user_id WHERE token_hash=? AND expires_at>?",
                     (token_hash, int(time.time()))).fetchone()
    if not row and required:
        raise HTTPError(401, "Sign in to continue")
    return row


def cookie(token, age=SESSION_AGE):
    return f"app_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={age}" + ("; Secure" if SECURE else "")


def user_info(user):
    return {key: user[key] for key in ("id", "email", "role")}


def auth(environ, db, data, register):
    email = data.get("email", "")
    password = data.get("password", "")
    if not isinstance(email, str) or len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPError(400, "Enter a valid email address")
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise HTTPError(400, "Use a password between 12 and 1024 characters")
    email = email.strip().lower()
    address = environ.get("REMOTE_ADDR", "unknown")[:100]
    stamp = int(time.time())
    db.execute("BEGIN IMMEDIATE")
    db.execute("DELETE FROM auth_attempts WHERE window_start<?", (stamp - 900,))
    attempt = db.execute("SELECT * FROM auth_attempts WHERE address=?", (address,)).fetchone()
    if attempt and attempt["attempts"] >= 20:
        raise HTTPError(429, "Too many sign-in attempts; wait 15 minutes")
    db.execute("INSERT INTO auth_attempts VALUES (?,1,?) ON CONFLICT(address) DO UPDATE SET attempts=attempts+1", (address, stamp))
    db.commit()  # Failed logins must still count toward the limit.
    if register:
        if not REGISTRATION:
            raise HTTPError(403, "Account registration is closed")
        salt = secrets.token_hex(16)
        encoded = password_hash(password, salt)
        db.execute("BEGIN IMMEDIATE")
        # Serialize first-account provisioning to avoid two initial administrators.
        role = "editor" if db.execute("SELECT 1 FROM users LIMIT 1").fetchone() else "admin"
        try:
            cursor = db.execute("INSERT INTO users(email,password_hash,salt,role,created_at) VALUES (?,?,?,?,?)", (email, encoded, salt, role, stamp))
        except sqlite3.IntegrityError as error:
            raise HTTPError(409, "Account could not be created with this email") from error
        user = db.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
    else:
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        encoded = password_hash(password, user["salt"] if user else "0" * 32)
        if not user or not hmac.compare_digest(encoded, user["password_hash"]):
            raise HTTPError(401, "Email or password is incorrect")
    db.execute("DELETE FROM sessions WHERE expires_at<=?", (stamp,))
    db.execute("DELETE FROM auth_attempts WHERE address=?", (address,))
    previous = session(environ, db, required=False)
    if previous:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (previous["token_hash"],))
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.execute("INSERT INTO sessions VALUES (?,?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user["id"], csrf, stamp + SESSION_AGE))
    return {"user": user_info(user), "csrf": csrf}, [("Set-Cookie", cookie(token))]


def record_payload(data):
    if set(data) - {"title", "description", "status", "fields"}:
        raise HTTPError(400, "Unknown record properties")
    title, description, status = data.get("title"), data.get("description", ""), data.get("status")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 160:
        raise HTTPError(400, "Title must contain 1 to 160 characters")
    if not isinstance(description, str) or len(description) > 5000:
        raise HTTPError(400, "Description must contain at most 5000 characters")
    if status not in BP["statuses"]:
        raise HTTPError(400, "Choose a valid status")
    fields = data.get("fields", {})
    names = {field["name"] for field in BP["fields"]}
    if not isinstance(fields, dict) or set(fields) - names:
        raise HTTPError(400, "Unknown blueprint field")
    for spec in BP["fields"]:
        value = fields.get(spec["name"], "")
        if value == "" or value is None:
            if spec["required"]:
                raise HTTPError(400, spec["label"] + " is required")
            continue
        if spec["type"] == "number":
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1e15:
                raise HTTPError(400, spec["label"] + " must be a nonnegative number")
        else:
            if not isinstance(value, str) or len(value) > 500:
                raise HTTPError(400, spec["label"] + " must be a short text value")
            if spec["type"] == "date":
                try:
                    date.fromisoformat(value)
                except ValueError as error:
                    raise HTTPError(400, "Enter an ISO date") from error
            if spec["type"] == "url":
                try:
                    parsed = urlsplit(value)
                    if parsed.scheme not in ("https", "http") or not parsed.netloc:
                        raise ValueError("invalid URL")
                except ValueError as error:
                    raise HTTPError(400, "URLs must use https or http with a valid host") from error
    return title.strip(), description, status, json.dumps(fields, allow_nan=False)


def record_info(row):
    result = dict(row)
    result.pop("owner_id", None)
    result["fields"] = json.loads(result["fields"])
    return result


def audit(db, user, action, record_id, title):
    if FEATURES["auditLog"]:
        db.execute("INSERT INTO audit_events(user_id,action,record_id,title,created_at) VALUES (?,?,?,?,?)", (user["id"], action, record_id, title, int(time.time())))


def csv_safe(value):
    value = str(value)
    # Spreadsheet formula injection also includes whitespace before the operator.
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value


def api(environ, db):
    path, method = environ["PATH_INFO"], environ["REQUEST_METHOD"]
    if method not in ("GET", "POST", "PUT", "DELETE"):
        raise HTTPError(405, "Method not allowed")
    if method != "GET":
        if environ.get("HTTP_ORIGIN") not in (None, "", ORIGIN) or environ.get("HTTP_SEC_FETCH_SITE") == "cross-site":
            raise HTTPError(403, "Cross-origin requests are not allowed")
    if path == "/api/health" and method == "GET":
        db.execute("SELECT 1 FROM schema_migrations").fetchone()
        return 200, {"status": "ok"}, []
    if path == "/api/session" and method == "GET":
        user = session(environ, db, required=False)
        return 200, {"user": user_info(user) if user else None, "csrf": user["csrf"] if user else None,
                     "registration": REGISTRATION, "config": CONFIG}, []
    if path in ("/api/login", "/api/register") and method == "POST":
        result, headers = auth(environ, db, json_body(environ), path == "/api/register")
        return 200, result, headers
    user = session(environ, db)
    if method != "GET":
        csrf = environ.get("HTTP_X_CSRF_TOKEN", "")
        if not hmac.compare_digest(csrf.encode(), user["csrf"].encode()):
            raise HTTPError(403, "Invalid CSRF token; reload and try again")
        data = json_body(environ)
    if path == "/api/logout" and method == "POST":
        db.execute("DELETE FROM sessions WHERE token_hash=?", (user["token_hash"],))
        return 200, {"ok": True}, [("Set-Cookie", cookie("", 0))]
    if method != "GET" and FEATURES["roleBasedAccess"] and user["role"] == "viewer":
        raise HTTPError(403, "Viewer accounts cannot change records")
    if path == "/api/records" and method == "GET":
        params = parse_qs(environ.get("QUERY_STRING", ""))
        query = params.get("q", [""])[0][:200].lower() if FEATURES["search"] else ""
        status = params.get("status", [""])[0]
        rows = db.execute("SELECT * FROM records WHERE owner_id=? AND instr(lower(title || ' ' || description),?)>0 AND (?='' OR status=?) ORDER BY updated_at DESC,id DESC LIMIT 500", (user["id"], query, status, status)).fetchall()
        total = db.execute("SELECT count(*) FROM records WHERE owner_id=?", (user["id"],)).fetchone()[0]
        return 200, {"records": [record_info(row) for row in rows], "total": total, "limit": 500}, []
    if path == "/api/records" and method == "POST":
        payload = record_payload(data)
        stamp = int(time.time())
        result = db.execute("INSERT INTO records(owner_id,title,description,status,fields,created_at,updated_at) VALUES (?,?,?,?,?,?,?)", (user["id"], *payload, stamp, stamp))
        audit(db, user, "created", result.lastrowid, payload[0])
        row = db.execute("SELECT * FROM records WHERE id=?", (result.lastrowid,)).fetchone()
        return 201, {"record": record_info(row)}, []
    match = re.fullmatch(r"/api/records/([1-9][0-9]{0,15})", path)
    if match and method in ("PUT", "DELETE"):
        row = db.execute("SELECT * FROM records WHERE id=? AND owner_id=?", (int(match[1]), user["id"])).fetchone()
        if not row:
            raise HTTPError(404, "Record not found")
        if method == "DELETE":
            db.execute("DELETE FROM records WHERE id=? AND owner_id=?", (row["id"], user["id"]))
            audit(db, user, "deleted", row["id"], row["title"])
            return 200, {"ok": True}, []
        payload = record_payload(data)
        db.execute("UPDATE records SET title=?,description=?,status=?,fields=?,updated_at=? WHERE id=? AND owner_id=?", (*payload, int(time.time()), row["id"], user["id"]))
        audit(db, user, "updated", row["id"], payload[0])
        return 200, {"record": record_info(db.execute("SELECT * FROM records WHERE id=?", (row["id"],)).fetchone())}, []
    if path == "/api/activity" and method == "GET":
        if not FEATURES["auditLog"]:
            raise HTTPError(404, "Activity history is disabled")
        rows = db.execute("SELECT action,record_id,title,created_at FROM audit_events WHERE user_id=? ORDER BY id DESC LIMIT 100", (user["id"],)).fetchall()
        return 200, {"events": [dict(row) for row in rows]}, []
    if path == "/api/export" and method == "GET":
        if not FEATURES["export"]:
            raise HTTPError(404, "Export is disabled")
        rows = db.execute("SELECT * FROM records WHERE owner_id=? ORDER BY id", (user["id"],)).fetchall()
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        names = [field["name"] for field in BP["fields"]]
        writer.writerow(["Title", "Description", "Status", *[field["label"] for field in BP["fields"]]])
        for row in rows:
            extra = json.loads(row["fields"])
            writer.writerow([csv_safe(value) for value in [row["title"], row["description"], row["status"], *[extra.get(key, "") for key in names]]])
        return 200, stream.getvalue().encode(), [("Content-Type", "text/csv; charset=utf-8"), ("Content-Disposition", 'attachment; filename="records.csv"')]
    raise HTTPError(404, "Endpoint not found")


def application(environ, start_response):
    headers = [("X-Content-Type-Options", "nosniff"), ("X-Frame-Options", "DENY"), ("Referrer-Policy", "same-origin"),
               ("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"),
               ("Cache-Control", "no-store")]
    if SECURE:
        headers.append(("Strict-Transport-Security", "max-age=31536000"))
    status, body = 200, b""
    try:
        host = environ.get("HTTP_HOST", "")
        if host != urlsplit(ORIGIN).netloc:
            raise HTTPError(400, "Unrecognized host; configure APP_ORIGIN")
        if environ["PATH_INFO"].startswith("/api/"):
            db = connect()
            try:
                with db:
                    status, result, extra = api(environ, db)
                headers.extend(extra)
                body = result if isinstance(result, bytes) else json.dumps(result, allow_nan=False).encode()
                if not any(key.lower() == "content-type" for key, _ in extra):
                    headers.append(("Content-Type", "application/json; charset=utf-8"))
            finally:
                db.close()
        else:
            if environ["REQUEST_METHOD"] != "GET":
                raise HTTPError(405, "Method not allowed")
            files = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                     "/workspace.css": ("workspace.css", "text/css"), "/tokens.css": ("tokens.css", "text/css")}
            file = files.get(environ["PATH_INFO"])
            if not file or not (ROOT / "static" / file[0]).is_file():
                raise HTTPError(404, "Page not found")
            body = (ROOT / "static" / file[0]).read_bytes()
            headers.append(("Content-Type", file[1] + "; charset=utf-8"))
    except HTTPError as error:
        status = error.status
        body = json.dumps({"error": error.message}).encode()
        headers.append(("Content-Type", "application/json; charset=utf-8"))
    except Exception:
        # Keep exception messages, SQL, secrets and request bodies out of responses.
        status, body = 500, b'{"error":"Internal server error"}'
        headers.append(("Content-Type", "application/json; charset=utf-8"))
    labels = {200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed", 409: "Conflict", 413: "Content Too Large", 415: "Unsupported Media Type", 429: "Too Many Requests", 500: "Internal Server Error"}
    headers.append(("Content-Length", str(len(body))))
    start_response(f"{status} {labels[status]}", headers)
    return [body]


initialize()
