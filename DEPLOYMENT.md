# Conwo — Production Deployment Runbook

**Stack:** Python 3.11 + FastAPI (uvicorn) · Angular 17 · nginx · systemd  
**Topology:** Single Linux VM — nginx reverse-proxies both frontend and backend  
**Production path:** `/opt/conwo/`

---

## VM Prerequisites

```bash
# Python 3.11
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Node.js 18 (only needed once to build the Angular frontend)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# nginx, git, rclone
sudo apt-get install -y nginx git rclone
```

---

## Step 1 — Create directories and clone the repo

```bash
sudo mkdir -p /opt/conwo /var/log/conwo
sudo chown $USER:$USER /opt/conwo /var/log/conwo

git clone <BITBUCKET_REPO_URL> /opt/conwo
cd /opt/conwo
```

---

## Step 2 — Create and populate `.env`

The `.env` file holds all secrets. It is **never committed to git**.

```bash
cp /opt/conwo/.env.example /opt/conwo/.env
chmod 600 /opt/conwo/.env    # only the deploy user can read it
nano /opt/conwo/.env
```

Fill in every value. Reference table:

| Variable | Required | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic console → API keys |
| `JIRA_API_TOKEN` | Yes (for Jira sync) | Atlassian account → Security → API tokens |
| `JIRA_EMAIL` | Yes (for Jira sync) | Your Atlassian login email |
| `JIRA_BASE_URL` | Yes | `https://moveinsync.atlassian.net` |
| `PMS_TOKEN_COM` | Yes (for PMS debug) | Bearer token for `.com` server |
| `PMS_COOKIE_COM` | Yes (for PMS debug) | Cookie string for `.com` server |
| `PMS_TOKEN_IN` | Yes (for PMS debug) | Bearer token for `.in` server |
| `PMS_COOKIE_IN` | Yes (for PMS debug) | Cookie string for `.in` server |
| `GOOGLE_CLIENT_ID` | Yes | `394997129475-vptjprrehufpvhnlh3tad78uqk69u54h.apps.googleusercontent.com` |
| `ALLOWED_ORIGINS` | Yes | `https://YOUR_PRODUCTION_DOMAIN` |
| `TRACE_USER_HASH_SALT` | Recommended | Any random string (e.g. `openssl rand -hex 16`) |
| `ANTHROPIC_MODEL` | No | Default: `claude-sonnet-4-6` |
| `ANTHROPIC_COMPACTOR_MODEL` | No | Default: `claude-haiku-4-5` |
| `MAX_TOOL_ROUNDS` | No | Default: `12` |

Verify `.env` is not tracked by git:
```bash
git status .env
# Expected: nothing (gitignored)
```

---

## Step 3 — Python backend setup

```bash
cd /opt/conwo

python3.11 -m venv venv
venv/bin/pip install -r requirements-backend.txt
venv/bin/pip install -r requirements.txt

# Initialize the traces database (idempotent — safe to re-run)
venv/bin/python scripts/init_traces_db.py
```

---

## Step 4 — Build the Angular frontend

Run once after cloning, and again after any frontend code change.

```bash
cd /opt/conwo/frontend
npm install
npx ng build --configuration production
```

Output lands at `frontend/dist/frontend/browser/`. Confirm:
```bash
ls /opt/conwo/frontend/dist/frontend/browser/index.html
# Expected: file exists
```

---

## Step 5 — Set up admin user

The `config/allowed_users.toml` file ships with an empty token. Generate and fill in the
admin token before starting the backend:

```bash
# Generate admin token (replace email with your actual login email)
python3.11 -c "import hashlib; print(hashlib.sha256(b'YOUR_EMAIL@moveinsync.com').hexdigest()[:32])"

# Edit the file and paste the generated token
nano /opt/conwo/config/allowed_users.toml
# Set: token = "<generated-value>"
# Set: email = "YOUR_EMAIL@moveinsync.com"
```

---

## Step 6 — systemd service

Create `/etc/systemd/system/conwo.service`:

```ini
[Unit]
Description=Conwo FastAPI Backend
After=network.target

[Service]
Type=simple
User=YOUR_DEPLOY_USER
WorkingDirectory=/opt/conwo
EnvironmentFile=/opt/conwo/.env
ExecStart=/opt/conwo/venv/bin/uvicorn backend.api:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

> **Important:** `--host 127.0.0.1` binds to localhost only. nginx is the only public entry point.
> Do **not** use `--reload` in production.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable conwo
sudo systemctl start conwo

# Verify
sudo systemctl status conwo
# Expected: Active: active (running)

# Smoke-test the backend (localhost only — port 8000 is not public)
curl http://127.0.0.1:8000/health
# Expected: {"status":"ok","wiki_pages":<N>,"has_server_key":true}
```

---

## Step 7 — nginx configuration

Create `/etc/nginx/sites-available/conwo`:

```nginx
server {
    listen 80;
    server_name YOUR_PRODUCTION_DOMAIN;

    # Uncomment after TLS is set up (Step 8):
    # return 301 https://$host$request_uri;

    root /opt/conwo/frontend/dist/frontend/browser;
    index index.html;

    client_max_body_size 50M;

    # ── Backend API routes ──────────────────────────────────────────────────

    location /query {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # Streaming (SSE) support
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
        proxy_read_timeout 300s;
    }

    location /search {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /wiki/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /trace/health {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /status {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /feedback {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /conversations {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /agent/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /api/traces/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ingest/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        client_max_body_size 50M;
    }

    # ── Angular SPA fallback ────────────────────────────────────────────────
    # Static assets (JS, CSS, fonts) served directly from disk.
    # All other paths → index.html so Angular Router handles navigation.

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Enable and test:
```bash
sudo ln -s /etc/nginx/sites-available/conwo /etc/nginx/sites-enabled/conwo
sudo nginx -t
# Expected: syntax is ok / test is successful

sudo systemctl enable nginx
sudo systemctl start nginx
```

---

## Step 8 — TLS with Let's Encrypt (do once the domain is live)

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_PRODUCTION_DOMAIN
# Accept the "redirect HTTP → HTTPS" prompt
sudo systemctl reload nginx
```

After TLS is active, update `.env`:
```
ALLOWED_ORIGINS=https://YOUR_PRODUCTION_DOMAIN
```
Then restart the backend:
```bash
sudo systemctl restart conwo
```

---

## Step 9 — Google OAuth (do after TLS is live)

Google OAuth requires HTTPS. Once TLS is active:

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Open the Web application credential with Client ID `394997129475-...apps.googleusercontent.com`
3. **Authorized JavaScript origins** → add `https://YOUR_PRODUCTION_DOMAIN`
4. **Authorized redirect URIs** → add `https://YOUR_PRODUCTION_DOMAIN`
5. Save (changes propagate in ~5 minutes)

---

## Step 10 — Install cron jobs

```bash
crontab -e
# Paste the contents of deploy/crontab.example
```

Verify log directory is writable:
```bash
ls /var/log/conwo/
```

---

## Step 11 — First-boot verification checklist

```bash
# 1. Backend health (localhost)
curl http://127.0.0.1:8000/health
# Expected: {"status":"ok","wiki_pages":<N>,"has_server_key":true}

# 2. Public health through nginx
curl http://YOUR_PRODUCTION_DOMAIN/health
# Expected: same JSON

# 3. Frontend SPA
curl http://YOUR_PRODUCTION_DOMAIN/
# Expected: HTML starting with <!DOCTYPE html>

# 4. Backend startup logs (no errors)
sudo journalctl -u conwo -n 50 --no-pager
# Expected: uvicorn startup lines, no NameError or import errors

# 5. nginx access log
sudo tail -f /var/log/nginx/access.log
# Browse to the app and confirm requests route correctly
```

In a real browser:
- Navigate to `https://YOUR_PRODUCTION_DOMAIN/login`
- Click **Sign in with Google** and complete the flow
- After redirect to `/ask`, submit a test question and confirm a response

---

## Updating after code changes

```bash
cd /opt/conwo
git pull origin main          # or: git pull bitbucket main

# If backend Python files changed:
sudo systemctl restart conwo

# If frontend files changed:
cd frontend
npm install                   # only if package.json changed
npx ng build --configuration production
# nginx picks up new static files immediately (no reload needed)

# Verify
curl http://127.0.0.1:8000/health
```

---

## Rollback

```bash
cd /opt/conwo
git log --oneline -10          # find the last good commit
git checkout <commit-hash> -- backend/ frontend/src/
# Rebuild frontend if frontend files were reverted
sudo systemctl restart conwo
```

---

## Data backup (run daily via cron)

These files hold live user data — back them up daily:

```bash
# Add to crontab:
0 1 * * * tar -czf /var/backups/conwo-$(date +\%Y\%m\%d).tar.gz \
  /opt/conwo/raw/auth \
  /opt/conwo/raw/conversations \
  /opt/conwo/raw/traces \
  /opt/conwo/wiki \
  >> /var/log/conwo/backup.log 2>&1
```

| Directory | Contents |
|---|---|
| `raw/auth/` | User sessions and tokens |
| `raw/conversations/` | Chat history |
| `raw/traces/` | Observability data |
| `wiki/` | AI-maintained wiki pages |

> `raw/jira/tickets.sqlite` is regenerable from the Jira API (cron re-syncs it nightly),
> but backup is cheap and recommended.

---

## Full environment variable reference

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for AI query mode |
| `JIRA_API_TOKEN` | Yes | Atlassian API token |
| `JIRA_EMAIL` | Yes | Your Atlassian login email |
| `JIRA_BASE_URL` | Yes | `https://moveinsync.atlassian.net` |
| `PMS_TOKEN_COM` | Yes | Bearer token for `.com` PMS server |
| `PMS_COOKIE_COM` | Yes | Cookie string for `.com` PMS server |
| `PMS_TOKEN_IN` | Yes | Bearer token for `.in` PMS server |
| `PMS_COOKIE_IN` | Yes | Cookie string for `.in` PMS server |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `ALLOWED_ORIGINS` | Yes | Comma-separated CORS origins, e.g. `https://conwo.moveinsync.com` |
| `TRACE_USER_HASH_SALT` | Recommended | Random salt for user ID hashing in traces |
| `ANTHROPIC_MODEL` | No | Default: `claude-sonnet-4-6` |
| `ANTHROPIC_COMPACTOR_MODEL` | No | Default: `claude-haiku-4-5` |
| `MAX_TOOL_ROUNDS` | No | Default: `12` |

---

## Network access requirements

The production VM must have outbound internet access to:

| Host | Port | Purpose |
|---|---|---|
| `api.anthropic.com` | 443 | AI query processing |
| `moveinsync.atlassian.net` | 443 | Jira API (ticket sync) |
| `accounts.google.com` | 443 | Google OAuth verification |
| `www.googleapis.com` | 443 | Google OAuth token exchange |
| `cmsapp.moveinsync.com` | 443 | PMS `.com` server (config debug) |
| `cmsapp.moveinsync.in` | 443 | PMS `.in` server (config debug) |
