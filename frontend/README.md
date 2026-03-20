# AuditAI Frontend

Modern React/Next.js dashboard for AuditAI anomaly detection platform.

## Getting Started

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment
```bash
cp .env.local.example .env.local
# Edit .env.local and set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

## Tech Stack

- **Framework:** Next.js 14 (React 18, TypeScript)
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui patterns
- **State Management:** TanStack Query (React Query)
- **HTTP Client:** Axios
- **Deployment:** Vercel

## Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js app router pages
│   ├── components/       # Reusable React components
│   ├── hooks/           # Custom React hooks (useApi.ts)
│   └── lib/             # API client, types, utilities
├── package.json
├── next.config.ts
├── tsconfig.json
└── tailwind.config.ts
```

## Available Pages

- **Dashboard** (`/`) - KPI overview, risk distribution
- **Anomalies** (`/anomalies`) - Paginated anomaly list
- **Anomaly Detail** (`/anomalies/[id]`) - Full transaction details + explanation
- **Reports** (`/reports`) - Generate & view audit reports
- **Chat** (`/chat`) - AI Q&A about anomalies
- **Reconciliation** (`/reconciliation`) - Account balance reconciliation

## Building for Production

```bash
npm run build
npm start
```

## Deployment to Vercel

```bash
vercel deploy
```

Ensure `NEXT_PUBLIC_API_BASE_URL` production URL is set in Vercel environment variables.
