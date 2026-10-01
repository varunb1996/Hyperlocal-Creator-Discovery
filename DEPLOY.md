# Deploy

Three free services, each updating automatically on every push to `main`:

```
GitHub (this repo) ──► GitHub Actions: tests + frontend build check (.github/workflows/ci.yml)
                   ├─► Render:  FastAPI backend   (render.yaml)
                   └─► Vercel:  Next.js frontend  (web/)
Render ──► Supabase
```

Render and Vercel build and deploy; GitHub Actions only runs checks. GitHub Pages is not used: it serves static files only, and both the API and the Next.js server need to run code.

## 1. Supabase (database)

1. Create a project at [supabase.com](https://supabase.com).
2. **SQL Editor** → paste [`schema.sql`](schema.sql) → **Run**.
3. **Settings → API**: note the **Project URL** and the **service_role** key. Keep the key private.
4. Seed the creators from your machine (needs the private workbook; see README → Data):
   ```bash
   cp .env.example .env    # fill SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
   python seed.py
   ```
   **Table Editor → creators** should show 115 rows.

## 2. Render (backend API)

1. [render.com](https://render.com) → **New → Blueprint** → connect this GitHub repo.
2. Render reads [`render.yaml`](render.yaml) and proposes the `creator-discovery-api` service.
3. When asked, enter:
   - `SUPABASE_URL`: your Project URL
   - `SUPABASE_SERVICE_ROLE_KEY`: your service_role key
4. **Apply**. When it's live, open `https://<your-service>.onrender.com/health` → `{"status":"ok"}`. `/docs` gives the interactive API.

The free plan sleeps after ~15 minutes idle; the first request then takes ~30–50 s. Open the app a minute before a demo.

## 3. Vercel (frontend)

1. [vercel.com](https://vercel.com) → **Add New → Project** → import this repo.
2. **Root Directory**: `web` (Next.js is detected automatically).
3. **Environment Variables**: `API_URL` = `https://<your-service>.onrender.com` (no trailing slash).
4. **Deploy**. Open the Vercel URL, submit a Pune brief, and you should get a ranked top 5.

`API_URL` is read only on the server (server actions and server components); it is never sent to the browser.

## 4. Check

- GitHub → **Actions**: the CI run is green. (Data-dependent tests show as skipped: the creator workbook is private.)
- Render `/health` returns ok.
- On a phone, the Vercel URL loads the form; submitting opens `/shortlist/<id>`; Supabase `cafe_briefs` and `shortlists` each gain a row.

## Updating

Push to `main`. CI runs, and Render and Vercel redeploy automatically. To refresh creator data, update the private workbook and run `python seed.py` again (upserts by handle).

## Secrets checklist

- Real keys exist only in local `.env` / `web/.env.local` (both gitignored) and in Render/Vercel settings.
- Only `.env.example` files with placeholders are committed.
- `render.yaml` declares the Supabase variables with `sync: false`, so values are never stored in the repo.
