# Form Collector

A small Django app for collecting responses. The admin builds forms in Django Admin, shares a
link, and downloads the answers as CSV. It stores only the answers and the submission time.
No IP addresses are stored. Built for Render + PostgreSQL (Supabase works).

## Features

- Build forms in `/admin/`: short/long answer, email, number, date, dropdown, multiple choice, checkboxes
- Each form has its own link: `https://your-site/f/<link-name>/`
- Optional "No duplicates" on one question (e.g. email), enforced by a database constraint
- Open/close a form with one tick
- CSV export per form (admin action or staff-only `/export/<link-name>/csv/`)
- CSRF protection, honeypot field, site-wide flood guard, POST -> redirect -> GET

## Local setup

macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`: keep `DEBUG=True`, and either set `DATABASE_URL` to your PostgreSQL URL or comment it
out to use SQLite locally. Generate a secret key with:
```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Using it

1. Log in at `/admin/` -> Forms -> Add form.
2. Add a title and questions, then save. The "Link to share" appears on the form's page.
3. Responses: open a form -> "View responses", or Responses in the sidebar.
4. Export: Responses -> filter by form -> tick rows -> "Download selected responses as CSV" -> Go.
   Or open `/export/<link-name>/csv/` while logged in.

Don't delete or retype a question after people have answered it; its answers drop out of the CSV.

## Environment variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key (required in production) |
| `DEBUG` | `True` locally, `False` in production |
| `DATABASE_URL` | PostgreSQL connection string |
| `ADMIN_URL` | Admin path. Use something hard to guess, e.g. `manage-k7x2q9/` (keep the trailing slash) |
| `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` | Only needed for a custom domain (Render's are added automatically) |
| `SITE_URL` | Base URL for the links shown in the admin (defaults to Render's URL) |
| `TIME_ZONE` | Admin display timezone, default `UTC` |
| `RATE_LIMIT_POSTS` / `RATE_LIMIT_WINDOW` | Site-wide posts allowed per window in seconds (default 120 / 60) |
| `HSTS_SECONDS` | HSTS max-age, default 31536000 |
| `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD` | Optional: auto-create an admin during build |

## Deploying to Render

1. Push to GitHub (make sure `.env` is not committed).
2. Render -> New -> Web Service -> pick the repo.
3. Build command `./build.sh`. Start command `gunicorn project.wsgi:application --workers 2`.
4. Environment: `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`, `PYTHON_VERSION=3.12.8`, `ADMIN_URL`,
   and the `DJANGO_SUPERUSER_*` variables for the first deploy (delete the password afterwards).
5. Open `https://<service>.onrender.com/<ADMIN_URL>` and log in.

If using Supabase, use the Session pooler connection string (not the direct one), and enable
row-level security on the tables (see below).

## Security notes

What the app does:
- Only logged-in staff can see responses. No public page lists or shows them; the success page shows
  nothing but a message. CSV export requires staff login.
- Admin login is locked per username for 15 minutes after 5 failed attempts.
- Random, hard-to-guess form links; forms and admin are marked noindex.
- HTTPS-only cookies, HSTS, strict CSP on public pages, no framing, no sniffing, CSRF on every POST.
- Django's ORM (no raw SQL) and auto-escaping, so typed answers can't inject code. CSV export blocks
  spreadsheet formula injection.

What you must do (nothing is "unhackable"; most real breaches are weak passwords and leaked keys):
- Use a long, unique admin password and change `ADMIN_URL` to something unguessable.
- Turn on 2FA for GitHub, Render and Supabase.
- Never commit `.env`. If a database password or secret key leaks, rotate it.
- Turn on row-level security in Supabase (SQL Editor):
```sql
DO $$ DECLARE t record; BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
  END LOOP;
END $$;
```
- Keep the GitHub repo private and run `pip install -U -r requirements.txt` occasionally for updates.

## Privacy

Each form tells people it saves their answers and the submission time. Nothing is sent to third
parties and there is no analytics. Only ask for what you need, delete data you no longer need, and
check your school's rules on collecting student data.
