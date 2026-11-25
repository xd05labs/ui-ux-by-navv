# Your generated workspace

You may customize, publish, redistribute and sell this generated application. Retain GENERATED_APP_LICENSE.txt with the incorporated AppForge-generated material; your original application content may use your own license. This permission does not apply to the AppForge Builder or its unrendered template library. Dependencies keep their own licenses.

Python 3.11+ is required. No dependency install is needed for local development.

```sh
python server.py
```

Open http://127.0.0.1:8000. Create your own account; there are no default credentials. The first registered account has the admin role. Subsequent accounts are editors. All records, including administrator records, are private to their creator. Admin accounts do not bypass ownership. Viewer accounts can view and export their records but cannot write when role based access is enabled.

```sh
python manage.py create-user viewer@example.com --role viewer
python manage.py role someone@example.com viewer
python -m unittest discover -s tests -v
```

Role changes revoke that account's sessions. Passwords are entered through a hidden terminal prompt. For a different local port, export APP_ORIGIN with that port and pass --port to server.py. Environment variables are read from the process; .env is an example, not automatically loaded.

## Deployment

```sh
python -m pip install -r requirements.txt
waitress-serve --listen=127.0.0.1:8000 app:application
# Or:
docker compose up --build -d
```

Terminate HTTPS with a reverse proxy. Set APP_ORIGIN to the exact HTTPS public origin and APP_SECURE_COOKIES=true. Preserve the public Host header. Do not trust arbitrary forwarded headers. If source-IP login limits are required behind a proxy, configure Waitress with the specific trusted proxy address and headers; otherwise all proxied clients share a rate-limit bucket. Restrict the server port to the proxy. Use a persistent volume, automated backups and a restore drill. Disable public registration with APP_ALLOW_REGISTRATION=false after provisioning accounts when appropriate.

Waitress is pinned in requirements.txt. The Python base image uses a minor-version tag; pin a reviewed digest for your production release. Run dependency/security scans against the deployed image. No external secrets are needed by this local-first adapter.

## Data and APIs

SQLite files live in .data/ or APP_DATABASE. Migrations in migrations/ are applied once on startup and recorded in schema_migrations. Never edit an applied migration. Backup using SQLite's backup API while online, or stop the application before copying all database/WAL files. Do not run several independent replicas against one SQLite volume.

GET /api/session returns public application configuration, current user and a CSRF token. POST /api/register and /api/login accept email/password JSON. Authenticated mutations require X-CSRF-Token and the session cookie. Records use title, description, status and a fields object matching app.config.json. GET /api/records supports q and status. The list is capped at 500; CSV export includes all owned records. GET /api/activity returns the latest 100 events when enabled. POST /api/logout revokes the session. manage.py is a local operator tool, not a remote admin endpoint.

Backend-only mode omits static files and serves the same APIs. Use a cookie-aware HTTP client to register/sign in, then supply the returned CSRF token on mutations.

## Release limits

This is an operational register starter. Domain workflows listed as extensions in app.config.json are not implemented. There is no email verification, account recovery, SSO, organization sharing, payments, live telemetry or compliance certification. Audit records are database records, not tamper-proof evidence. Treat regulated blueprints as synthetic-data prototypes until specialist review. Complete the parent workspace's twelve quality gates before making a production-readiness claim.
