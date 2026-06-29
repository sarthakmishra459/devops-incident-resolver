# Deploying the app on Render + Vercel

## Backend on Render
1. Create a new Web Service on Render.
2. Connect this repository and choose the root directory as the repository root.
3. Render will use [render.yaml](render.yaml).
4. Set the service to use the Python environment and let Render install dependencies from the backend package.
5. After deployment, copy the Render URL.

## Frontend on Vercel
1. Import the repository into Vercel.
2. Set the project root to the repository root.
3. Vercel will use [vercel.json](vercel.json).
4. Replace the placeholder backend URL in [vercel.json](vercel.json) with your Render app URL.
5. Redeploy.

## Environment variables
- Backend: set `DIR_LLM_PROVIDER=local`, `DIR_USE_MOCK_LLM=true`, and optionally `DIR_CORS_ORIGINS` to include your Vercel domain.
- Frontend: if you need to point the UI at a custom backend URL, set `VITE_API_BASE_URL` in a local `.env` file or in Vercel Project Settings → Environment Variables. If you leave it unset, the app uses `/api` by default.

## Notes
- The app works in demo mode without external databases or LLMs.
- For production, you can later add PostgreSQL, Redis, and an LLM provider.
