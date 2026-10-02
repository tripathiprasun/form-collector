# Form Collector

A small Django app for collecting responses. The admin builds a form in Django Admin
(title, questions, options), shares its link, and downloads the responses as CSV.
The server records the submission time and, optionally, the submitter's IP address.
Built for Render + PostgreSQL.

## Features

- Create as many forms as you like in `/admin/`: short/long answer, email, number, date,
  dropdown, multiple choice, checkboxes; required or optional; reorderable
- Each form gets its own link: `https://your-site/f/<link-name>/`
- Optional "No duplicates" on one question (e.g. email): enforced by a database constraint
- Open/close a form with one tick; per-form IP recording on/off
- Server-side IP logging (never taken from the form), proxy-safe and configurable
- CSV export per form (admin action or staff-only `/export/<link-name>/csv/`)
- POST -> redirect -> GET success page, CSRF protection, per-IP rate limit, honeypot field
- Responses are read-only in the admin and never shown publicly

## Local setup

### 1. Virtual environment and dependencies

macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. PostgreSQL

Open a SQL shell as the postgres user:

- Linux: `sudo -u postgres psql`
- macOS (Homebrew): `psql postgres`
- Windows: "SQL Shell (psql)" from the Start menu

```sql
CREATE USER formcollector WITH PASSWORD 'choose-a-password';
CREATE DATABASE formcollector OWNER formcollector;
\q
```

(With `DEBUG=True` and no `DATABASE_URL`, the app falls back to SQLite so you can try it quickly.)

### 3. Environment variables

macOS / Linux: `cp .env.example .env`
Windows: `copy .env.example .env`

Edit `.env`: set `DATABASE_URL=postgres://formcollector:choose-a-password@localhost:5432/formcollector`
and generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

### 4. Migrate, create admin, run

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Admin: http://127.0.0.1:8000/admin/

If you ever change `models.py`: `python manage.py makemigrations` and commit the result.

## Using it

1. Log in at `/admin/` -> Forms -> Add form.
2. Give it a title, optional intro text, and fill in questions in the table below
   (3 empty rows are shown; save and re-open to add more).
3. Save. The "Link to share" shows on the form's page and in the Forms list. Send that link.
4. Look at responses: Forms list -> open a form -> "View responses", or Responses in the sidebar.
5. Export: open Responses, filter by form, tick rows (or "Select all"), choose
   "Download selected responses as CSV" and click Go. Or, while logged in, open
   `/export/<link-name>/csv/` for everything from that form. The Forms list has a Download link too.

Notes:
- Avoid deleting or retyping a question after people have answered it. Answers are stored per
  question, so a deleted question's answers drop out of the CSV.
- Setting a question to "No duplicates" only checks new responses; it doesn't touch old ones.
- The CSV time is UTC. The admin shows `TIME_ZONE`.

## Environment variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key (required in production) |
| `DEBUG` | `True` locally, `False` in production |
| `DATABASE_URL` | PostgreSQL connection string |
| `ALLOWED_HOSTS` | Comma-separated hostnames (Render's is added automatically) |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins incl. scheme, e.g. `https://forms.example.com` (Render's is added automatically) |
| `TRUSTED_PROXY_COUNT` | Number of trusted reverse proxies in front of Django (default 0) |
| `SITE_URL` | Base URL used to show full links in the admin (defaults to Render's URL, or localhost when DEBUG) |
| `TIME_ZONE` | Admin display timezone, default `UTC` |
| `ADMIN_URL` | Admin path, default `admin/` (change it to something less guessable if you like) |
| `RATE_LIMIT_POSTS` / `RATE_LIMIT_WINDOW` | Posts allowed per IP per window in seconds (default 10 / 60) |
| `HSTS_SECONDS` | HSTS max-age, default 31536000 |
| `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD` | Optional: auto-create an admin during build |

## IP address handling

`collector/utils.py::get_client_ip` decides the IP:

- `TRUSTED_PROXY_COUNT=0` (default): uses `REMOTE_ADDR` and ignores `X-Forwarded-For` completely.
- `TRUSTED_PROXY_COUNT=N`: reads the Nth entry from the right of `X-Forwarded-For`, i.e. the
  address your own N proxies recorded. Entries further left are client-controlled and ignored.

Security: if you trust `X-Forwarded-For` when there is no proxy, anyone can send a fake header
and write any IP into your database. Set N too high and you may read a spoofed value; too low
and you record a proxy's address. Only change it after testing.

Shared networks: people on the same Wi-Fi often share one public IP, so identical IPs are normal.
The rate limit is per IP (and per gunicorn worker), so keep `RATE_LIMIT_POSTS` generous if a whole
class submits from one network.

### Testing IP logging locally

Create a form in the admin, note its link name (say `abc123`), and give it one required
question. Find its question id in the admin URL when you open that question, or just use the
browser at `/f/abc123/` for the normal path. For the proxy header test:

```bash
curl -c jar.txt -s http://127.0.0.1:8000/f/abc123/ -o /dev/null
TOKEN=$(grep csrftoken jar.txt | awk '{print $7}')
curl -b jar.txt -H "X-Forwarded-For: 1.2.3.4" \
  -d "csrfmiddlewaretoken=$TOKEN&q_1=hello" \
  http://127.0.0.1:8000/f/abc123/ -i
```
Replace `q_1` with `q_<id of your question>` (ids start at 1 on a fresh database). With
`TRUSTED_PROXY_COUNT=0` the response shows `127.0.0.1` (header ignored). Set it to `1`,
restart, and submit again: it shows `1.2.3.4`. Delete the test rows afterwards.

## Deploying to Render

### Option A: Blueprint (uses `render.yaml`)
1. Push the project to GitHub (make sure `.env` is not committed).
2. Render -> New -> Blueprint -> select the repo. It creates the database and web service.
3. When prompted, enter `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`.
4. Deploy. After the first successful deploy, delete `DJANGO_SUPERUSER_PASSWORD` from the service's environment.

### Option B: Manual
1. New -> PostgreSQL. Name it, create it, copy the **Internal Database URL**.
2. New -> Web Service -> connect your GitHub repo.
3. Runtime: Python 3. Build command: `./build.sh`. Start command: `gunicorn project.wsgi:application --workers 2`.
4. Environment variables: `SECRET_KEY` (random), `DEBUG=False`, `DATABASE_URL` (from step 1),
   `PYTHON_VERSION=3.12.8`, `TRUSTED_PROXY_COUNT=1`, optionally the `DJANGO_SUPERUSER_*` ones.
   `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` are only needed for a custom domain.
5. Deploy.

If the build fails with "permission denied" on `build.sh`: `git update-index --chmod=+x build.sh`, commit, push.

### Superuser on Render
- Easiest: set the `DJANGO_SUPERUSER_*` variables before deploying (works on any plan).
- With Shell access (paid plans): service -> Shell -> `python manage.py createsuperuser`.

### Verify production
1. Log in at `https://<your-service>.onrender.com/admin/`, create a form, open its link.
2. Submit it yourself and check the IP in the admin against https://ifconfig.me.
3. If the IP is a Render/Cloudflare address instead of yours, set `TRUSTED_PROXY_COUNT=2` and test again.
4. Submit the same answer to a "No duplicates" question again to see the duplicate message.

Check Render's current free-tier limits: free web services sleep when idle (first load is slow)
and free databases may expire, so export your CSVs regularly.

## Static files

WhiteNoise serves static files; `build.sh` runs `collectstatic`. With `DEBUG=True` Django serves
them directly.

## Privacy

Each form tells people what it saves: their answers, the submission time, and (if enabled) their
IP address. Nothing is sent to third parties and there is no analytics. Only admin users can see
responses. Only ask for what you need, delete data you no longer need, tell people how long you keep it,
and check your school's rules on collecting student data.
