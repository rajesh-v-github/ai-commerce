# AI Commerce Support

AI Commerce Support is a full-stack customer-support workspace with a React
frontend and a FastAPI backend. It includes a support dashboard, orders,
products, tickets, customer records, and AI-assisted support workflows.

## Project layout

- `backend/` — FastAPI API, database models, seed scripts, and tests. See
  [backend setup and API documentation](backend/README.md).
- `frontend/` — React and Vite support workspace.
- `TEMPORARY-SHARING.md` — Windows instructions for sharing a local demo
  temporarily through LocalTunnel.

## Local development

Configure and start the backend using the instructions in
[backend/README.md](backend/README.md). Do not commit `backend/.env`; create it
locally with a strong, private `JWT_SECRET_KEY` as documented there.

In another terminal, start the frontend:

```powershell
Set-Location .\frontend
npm install
npm run dev
```

The Vite development server runs at `http://localhost:5173/` and proxies API
requests to the backend at `http://127.0.0.1:8000`.

## Demo data

The backend README documents optional seed scripts for local sample users,
products, orders, and tickets. The local SQLite database files are intentionally
not included in this repository.

## Notes

- Keep secrets, local databases, virtual environments, and generated build
  output out of source control; the root `.gitignore` excludes these.
- AI features require the additional setup described in the backend README.