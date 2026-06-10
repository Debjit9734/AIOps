# AIOps Monorepo

Django + DRF backend with a Vite + React frontend in `frontend/`.

## Local development

1. Backend setup:
```bash
cd aiops_project
python -m venv .venv
.venv\Scripts\activate
pip install django djangorestframework django-cors-headers requests scikit-learn joblib numpy
```

2. Environment:
```bash
copy .env.example .env
copy frontend\.env.example frontend\.env
```

3. Run backend:
```bash
python manage.py runserver
```

4. Run frontend (new terminal):
```bash
cd frontend
npm install
npm run dev
```

Frontend dev uses Vite proxy for `/api/*` to `http://127.0.0.1:8000`.

## Training the ML model

The training CSV lives at `data/training_data.csv`.

- Every successful `POST /api/analyze/` call now appends one labeled training row automatically.
- You can also bulk-generate rows from a list of GitHub repositories.

Install the ML dependencies first if they are not already available:

```bash
pip install pandas scikit-learn joblib numpy requests
```

Generate rows from a list of repos:

1. Create a text file with one GitHub URL per line, or a CSV with a `repo_url` column.
2. Run:

```bash
cd aiops_project
python analyzer\utils\recommender\generate_dataset.py data\repo_list.txt
```

Train the model:

```bash
cd aiops_project
python analyzer\utils\recommender\train.py
```

This saves the trained model to `trained_model.pkl`, which the recommendation flow loads automatically.

## Build frontend and serve via Django

```bash
cd frontend
npm run build
cd ..
python manage.py collectstatic --noinput
python manage.py runserver
```

- React `index.html` is served from `frontend/dist` via Django templates.
- Built assets are served under `/static/`.
- SPA fallback routes everything except `/api/*`, `/admin/*`, `/static/*` to `index.html`.

## Production notes

- Set `DEBUG=0` and configure `ALLOWED_HOSTS`.
- CORS is enabled only when `DEBUG=1`.
- Optional static serving with WhiteNoise:
  - `pip install whitenoise`
  - set `USE_WHITENOISE=1`

## Deployment guide endpoint overview

`POST /api/deployment-plan/`

Request body:
```json
{
  "repo_url": "https://github.com/org/repo",
  "cloud": "aws",
  "target": {
    "stack": "django",
    "deployment": "aws_ecs_fargate"
  }
}
```

Response includes:
- `deployment_steps`
- `required_files` (e.g., `Dockerfile`, `.env.example`, `README_DEPLOYMENT.md`, cloud-specific files)
- `recommended_resources` (ML and optional LLM-based)
- UI-friendly sections:
  - `prerequisites`
  - `console_clickpath`
  - `commands`
  - `verification_steps`
  - `rollback_steps`
