# Smart Cash & Carry Frontend

This is a complete drop-in frontend folder for the existing FastAPI backend.

## Installation

Copy this entire `frontend` folder into the backend project root. Do not move its internal files separately.

The backend root will look like this:

```text
smart-cash-and-carry/
├── frontend/
│   ├── routers/
│   ├── static/
│   ├── templates/
│   ├── __init__.py
│   └── INTEGRATION.md
├── main.py
├── models.py
├── schemas.py
├── routers/
├── services/
└── requirements.txt
```

After copying the folder, follow `frontend/INTEGRATION.md` for the small manual changes required in `main.py`.

This frontend uses FastAPI Jinja2 templates with plain CSS and JavaScript. It has no Node.js build step and contains no backend models, services, migrations, or database files.
