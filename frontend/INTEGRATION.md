# Manual `main.py` Changes

After placing the entire `frontend` folder in the backend project root, make these changes in the root `main.py`.

## 1. Add imports

Add these imports only if they are not already present:

```python
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from frontend.routers.frontend_router import router as frontend_router
```

## 2. Mount the frontend assets

Place this after `app = FastAPI(...)`:

```python
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_STATIC_DIRECTORY = BASE_DIR / "frontend" / "static"
UPLOADS_DIRECTORY = BASE_DIR / "uploads"

FRONTEND_STATIC_DIRECTORY.mkdir(parents=True, exist_ok=True)
UPLOADS_DIRECTORY.mkdir(parents=True, exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_STATIC_DIRECTORY)),
    name="static",
)

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOADS_DIRECTORY)),
    name="uploads",
)
```

If `/static` or `/uploads` is already mounted, replace that old mount instead of adding a duplicate.

## 3. Include the frontend router

Add this once alongside the existing router registrations:

```python
app.include_router(frontend_router)
```

## 4. Resolve an existing `/` route

The frontend uses `/` for the storefront. If `main.py` already has a JSON route at `/`, remove it or change it to `/api`, for example:

```python
@app.get("/api", tags=["System"])
def api_root():
    return {
        "message": "Smart Cash & Carry API is running."
    }
```

## 5. Check the dependency

Ensure this line exists in the root `requirements.txt`:

```text
jinja2
```

Restart the application:

```powershell
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/`.
