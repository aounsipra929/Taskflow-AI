# TaskFlow – Full-Stack To-Do App

React (Vite) · FastAPI · PostgreSQL · SQLAlchemy 2 · Alembic · JWT · bcrypt

```
todo-app/
├── docker-compose.yml          # PostgreSQL for local dev
├── backend/
│   ├── app/
│   │   ├── main.py             # app, CORS, routers, error handlers
│   │   ├── core/               # config (.env), security (bcrypt + JWT)
│   │   ├── db/                 # engine/session, Base, first-admin bootstrap
│   │   ├── models/             # SQLAlchemy models (User, Task) + enums
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── services/           # task filtering/sorting/pagination + CRUD
│   │   │   ├── llm_client.py   # OpenRouter client (native tool calling + validated-JSON fallback)
│   │   │   ├── chat_tools.py   # the only actions the LLM may request (validated, permission-checked)
│   │   │   └── chat_service.py # chat loop, confirmations, system prompt
│   │   └── api/                # deps (auth, roles, query params) + routes/
│   ├── alembic/                # migrations (0001_initial)
│   ├── tests/                  # pytest (SQLite in-memory, no Postgres needed)
│   ├── schema.sql              # reference SQL
│   └── requirements.txt
└── frontend/
    └── src/
        ├── api/                # axios client (JWT interceptor) + service modules
        ├── context/            # AuthContext
        ├── components/         # Navbar, ProtectedRoute, TaskBrowser, TaskForm, ...
        │   └── chatbot/        # floating Chatbot Assistant (window, task cards, confirmations)
        ├── pages/              # Login, Register, dashboards, task pages, profile
        └── utils/
```

## 1. Database
```bash
docker compose up -d          # or use any PostgreSQL 14+ and edit DATABASE_URL
```
Manual alternative:
```sql
CREATE USER todo_user WITH PASSWORD 'todo_pass';
CREATE DATABASE todo_db OWNER todo_user;
```

## 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # set SECRET_KEY (python -c "import secrets; print(secrets.token_hex(32))")
alembic upgrade head            # creates tables
uvicorn app.main:app --reload   # http://localhost:8000/docs  (Swagger)  /redoc
```
If `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` are set in `.env`, that admin is created on startup
(default `admin@example.com` / `Admin12345` — **change it**). Public registration always creates `user` accounts.

Tests: `pytest` (uses in-memory SQLite).

### Chatbot Assistant (OpenRouter)
Add to `backend/.env` (see `.env.example`), then run `alembic upgrade head` (new `pending_actions` table) and
`pip install -r requirements.txt` (httpx is now a runtime dependency):
```
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=your_free_model_id      # any id from https://openrouter.ai/models (filter: free)
OPENROUTER_TOOL_MODE=auto                # auto | native | json
```
The key is only read by the backend; the browser talks to `/api/v1/chat` on your own server.
If the key/model are missing or OpenRouter is down, the chat shows a clear message and the rest of the app keeps working.

How it stays safe:
* The LLM can only call a fixed list of tools (`list_tasks`, `get_task`, `suggest_next_tasks`, `get_task_stats`,
  `create_task`, `update_task`, `delete_task`, plus admin-only `find_users`). Arguments are validated with Pydantic and run
  through the existing `task_service`; there is no SQL or code execution from model output.
* Who you are comes from the JWT/database, never from the model. Users only reach their own tasks; admins can reach all.
* Create / update / delete are only *proposed*. They are stored in `pending_actions` and executed when you press
  **Confirm** (once, only by the same user, within 10 minutes). The task row is re-fetched at that moment, and the
  request is rejected if the task changed in the meantime.
* `OPENROUTER_TOOL_MODE=auto` uses native tool calling and falls back to a Pydantic-validated JSON protocol for models
  that do not support tools.

## 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_URL=http://localhost:8000/api/v1
npm run dev                     # http://localhost:5173
```

## API (prefix `/api/v1`)
| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | /auth/register | public | register (role `user`) |
| POST | /auth/login | public | OAuth2 form (`username`=email, `password`) → JWT |
| GET | /auth/me | any | current user |
| GET/PUT | /users/me | any | view / update own name & password |
| GET | /tasks | any | own tasks: `q,status,priority,due_from,due_to,sort_by,order,page,page_size` |
| POST | /tasks | any | create own task |
| GET/PUT/DELETE | /tasks/{id} | owner or admin | read / update / delete |
| PATCH | /tasks/{id}/status | owner or admin | mark pending/completed |
| GET | /admin/stats | admin | total users, tasks, completed, pending |
| GET | /admin/users | admin | list users (`q,role,is_active,page`) |
| GET | /admin/users/{id} | admin | one user |
| PATCH | /admin/users/{id}/status | admin | activate / deactivate |
| GET | /admin/tasks | admin | all tasks (`user_id` + same filters) |
| POST | /admin/tasks | admin | create task for any user |
| GET | /chat/status | any | is the Chatbot Assistant configured? |
| POST | /chat | any | one chat turn (`message`, `history`, `client_date`) → reply, task cards, optional pending action |
| POST | /chat/actions/{id}/confirm | owner of the action | execute a proposed create/update/delete |
| POST | /chat/actions/{id}/cancel | owner of the action | discard a proposed change |

## Manual test checklist (curl)
```bash
API=http://localhost:8000/api/v1
curl -X POST $API/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"jane@example.com","full_name":"Jane Doe","password":"Passw0rd1"}'
TOKEN=$(curl -s -X POST $API/auth/login -d 'username=jane@example.com&password=Passw0rd1' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -X POST $API/tasks -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Buy milk","priority":"high","due_date":"2026-11-01"}'
curl "$API/tasks?q=milk&sort_by=priority&order=desc" -H "Authorization: Bearer $TOKEN"
```
Then in the UI: register → create/edit/complete/delete tasks → log out → log in as admin → dashboard,
user list, deactivate a user (they can no longer log in), edit any task.

## Production notes
Set a strong `SECRET_KEY`, restrict `CORS_ORIGINS`, serve behind HTTPS, run
`uvicorn app.main:app --workers 4` (or gunicorn), and `npm run build` for the frontend (`dist/`).
