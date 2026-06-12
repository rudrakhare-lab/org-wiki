# Conwo — Production Deployment Runbook

**Stack:** Python 3.11 + FastAPI · Angular 17 · Docker  
**Deployment method:** Docker Compose (single container, port 8000)

---

## Prerequisites

The server must have:
- Docker + Docker Compose installed
- Outbound internet access (see Network Requirements at the bottom)
- A domain/URL assigned to the server

---

## Step 1 — Clone the repository

```bash
git clone https://bitbucket.org/moveinsync-engineering/convo-chatbot
cd convo-chatbot
```

This gives you: all application code, wiki knowledge base pages, PMS config database, and all scripts. The only thing NOT included is the Jira database (too large for git — handled in Step 3).

---

## Step 2 — Create the `.env` file

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Fill in all values:

| Variable | Required | Value |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `JIRA_API_TOKEN` | Yes | Atlassian account → Security → API tokens |
| `JIRA_EMAIL` | Yes | Atlassian login email |
| `JIRA_BASE_URL` | Yes | `https://moveinsync.atlassian.net` |
| `PMS_TOKEN_COM` | Yes | Bearer token for `.com` PMS server |
| `PMS_COOKIE_COM` | Yes | Cookie string for `.com` PMS server |
| `PMS_TOKEN_IN` | Yes | Bearer token for `.in` PMS server |
| `PMS_COOKIE_IN` | Yes | Cookie string for `.in` PMS server |
| `GOOGLE_CLIENT_ID` | Yes | `394997129475-vptjprrehufpvhnlh3tad78uqk69u54h.apps.googleusercontent.com` |
| `ALLOWED_ORIGINS` | Yes | `https://conwo.moveinsync.com` |
| `TRACE_USER_HASH_SALT` | Recommended | Any random string: `openssl rand -hex 16` |

Verify `.env` is not tracked by git:
```bash
git status .env
# Expected: nothing (it is gitignored)
```

---

## Step 3 — Transfer the Jira database (CRITICAL)

The Jira knowledge base (`raw/jira/tickets.sqlite`) is not in the repository — it is 624MB and contains all 37,000+ internal Jira tickets with AI classifications. Without this file the app starts but has no Jira knowledge.

Rudra will share this file. Place it at:
```
convo-chatbot/raw/jira/tickets.sqlite
```

Transfer options:
```bash
# Option A — scp from Rudra's machine directly to the server
scp raw/jira/tickets.sqlite user@SERVER_IP:/path/to/convo-chatbot/raw/jira/

# Option B — download from shared Google Drive link (Rudra will share)
wget -O raw/jira/tickets.sqlite "GOOGLE_DRIVE_LINK"
```

Verify the file is in place before continuing:
```bash
ls -lh raw/jira/tickets.sqlite
# Expected: file exists, size ~600MB
```

---

## Step 4 — Start the application

```bash
docker compose up -d
```

This builds the Docker image (Angular frontend + Python backend) and starts the container. First build takes ~5 minutes.

Verify it is running:
```bash
docker compose ps
# Expected: conwo   running   0.0.0.0:8000->8000/tcp

curl http://localhost:8000/health
# Expected: {"status":"ok","wiki_pages":<N>,"has_server_key":true}
```

---

## Step 5 — TLS + reverse proxy (nginx)

The container listens on port 8000. Set up nginx as a reverse proxy with TLS:

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/conwo`:

```nginx
server {
    listen 80;
    server_name conwo.moveinsync.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name conwo.moveinsync.com;

    ssl_certificate     /etc/letsencrypt/live/conwo.moveinsync.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/conwo.moveinsync.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

Enable and get TLS certificate:
```bash
sudo ln -s /etc/nginx/sites-available/conwo /etc/nginx/sites-enabled/conwo
sudo certbot --nginx -d conwo.moveinsync.com
sudo systemctl reload nginx
```

---

## Step 6 — Google OAuth configuration

Google OAuth requires HTTPS. Once TLS is active:

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Open the credential with Client ID `394997129475-...apps.googleusercontent.com`
3. Add `https://conwo.moveinsync.com` to **Authorized JavaScript origins**
4. Add `https://conwo.moveinsync.com` to **Authorized redirect URIs**
5. Save (changes propagate in ~5 minutes)

Then update `.env`:
```
ALLOWED_ORIGINS=https://conwo.moveinsync.com
```

Restart the container to pick up the new value:
```bash
docker compose restart
```

---

## Step 7 — Nightly Jira sync cron job (CRITICAL)

This keeps the Jira knowledge base updated automatically every night. Set up once:

```bash
crontab -e
```

Add this line:
```
0 2 * * * cd /path/to/convo-chatbot && docker compose exec -T conwo python scripts/jira_daily_sync.py >> /var/log/conwo-jira-sync.log 2>&1
```

What this does every night at 2am:
- **Stage 1** — pulls new/updated Jira tickets from the Jira API into SQLite
- **Stage 2** — AI-classifies each new ticket into the correct module (visitor, meeting rooms, etc.) using Claude Haiku

Verify after first run:
```bash
tail -5 /var/log/conwo-jira-sync.log
# Expected: [timestamp] DONE total=<N>s cost=$<X> sync_ok=True classify_ok=True
```

---

## Step 8 — Final verification

```bash
# Health check
curl https://conwo.moveinsync.com/health
# Expected: {"status":"ok","wiki_pages":<N>,"has_server_key":true}

# Container logs (no errors)
docker compose logs --tail=50
```

In a browser:
1. Navigate to `https://conwo.moveinsync.com`
2. Sign in with Google
3. Ask a test question — confirm a response is returned

---

## Updating after code or knowledge base changes

When Rudra pushes updates to Bitbucket:

```bash
cd /path/to/convo-chatbot
git pull bitbucket main
docker compose up -d --build
```

The `--build` flag rebuilds the image with the latest code and wiki pages.

---

## Data backup (recommended daily)

```bash
# Add to crontab:
0 1 * * * tar -czf /var/backups/conwo-$(date +\%Y\%m\%d).tar.gz \
  /path/to/convo-chatbot/raw/jira \
  /path/to/conwo-chatbot/raw/auth \
  /path/to/conwo-chatbot/raw/conversations \
  /path/to/convo-chatbot/raw/traces \
  /path/to/convo-chatbot/wiki \
  >> /var/log/conwo-backup.log 2>&1
```

---

## Network access requirements

The server must have outbound access to:

| Host | Port | Purpose |
|---|---|---|
| `api.anthropic.com` | 443 | AI query processing |
| `moveinsync.atlassian.net` | 443 | Jira API (nightly sync) |
| `accounts.google.com` | 443 | Google OAuth |
| `www.googleapis.com` | 443 | Google OAuth token exchange |
| `cms.moveinsync.com` | 443 | PMS `.com` server |
| `cms.moveinsync.in` | 443 | PMS `.in` server |
