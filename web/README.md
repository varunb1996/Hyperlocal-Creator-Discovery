# Creator Discovery: frontend

Next.js 16 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + TanStack Table.

It talks only to the FastAPI backend, and only from the server (server components and server actions), using the server-only `API_URL`. It never calls Supabase.

```bash
npm install
cp .env.example .env.local   # API_URL=http://127.0.0.1:8000
npm run dev                  # http://localhost:3000
```

| Path | What |
|---|---|
| `src/app/page.tsx` | Brief form (dropdowns from `GET /vocab`) |
| `src/app/shortlist/[id]/page.tsx` | Saved shortlist (`GET /shortlist/{id}`), or the not-supported message |
| `src/app/history/page.tsx` | Past shortlists (`GET /shortlists`), each opening its `/shortlist/[id]` page |
| `src/app/actions.ts` | Server actions: submit brief, re-rank for the budget toggle |
| `src/lib/api.ts` | Server-side FastAPI client |
| `src/components/results/` | Cards (phone), table + side panel (desktop), score bar, confidence badges |

See the root [README](../README.md), [ARCHITECTURE](../ARCHITECTURE.md) and [DEPLOY](../DEPLOY.md).
