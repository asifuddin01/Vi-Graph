# Vi-Graph frontend

Next.js (App Router) + React + TypeScript + Tailwind CSS.

```bash
npm install
npm run dev          # http://localhost:3000
npm run lint
npm run typecheck
npm run build
```

The backend URL comes from `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).
Next.js only reads env files from this directory, so set it in `frontend/.env.local`
for local development. It is inlined at build time.

| Path          | Contents                                   |
| ------------- | ------------------------------------------ |
| `app/`        | Routes and layouts                         |
| `components/` | React components                           |
| `lib/`        | API client and shared helpers              |
| `public/`     | Static assets                              |

This Next.js version has breaking changes relative to older releases — see `AGENTS.md`
and the bundled docs in `node_modules/next/dist/docs/` before changing framework-level
code.
