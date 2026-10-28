# AI Interview Service

A FastAPI service that runs AI-powered mock technical interviews. Upload a resume
and a job description, answer five generated questions, and get a scored
evaluation with per-question feedback and a hiring recommendation.

Users register and log in with email and password, or sign in with Google;
interviews are stored in
PostgreSQL and scoped to the user who created them.

Question generation and answer evaluation run through [OpenRouter](https://openrouter.ai).

## Live

| | URL |
| --- | --- |
| API | https://ai-interview-suite-api.onrender.com |
| API docs | https://ai-interview-suite-api.onrender.com/docs |
| Frontend | https://aiinterviewsuite.vercel.app |

## How it works

1. **Start** — the resume PDF is parsed to text and sent with the job description
   to the model, which returns exactly five questions, each tagged with a category
   (technical, behavioral, experience, problem solving, system design), a difficulty
   and its expected topics.
2. **Answer** — answers are submitted one at a time against the interview id.
3. **Submit** — once every question is answered, each answer is scored on four
   axes and the results are aggregated into an overall score and recommendation.

### Scoring

Each answer is rated 0-10 on four axes, combined into a 0-100 score:

| Axis | Weight |
| --- | --- |
| Technical accuracy | 40% |
| Relevance | 25% |
| Completeness | 20% |
| Communication | 15% |

The overall score is the mean of the per-answer scores, which maps to a
recommendation of `excellent`, `good`, `borderline` or `needs_improvement`.

### Data model

```
users 1─* interviews 1─* interview_attempts 1─* questions 1─1 answers 1─1 answer_evaluations
                                   └──1─1 interview_attempt_evaluations
```

An interview holds the resume and job description; each attempt holds its own
questions, answers and evaluation. Every interview currently has one attempt,
and the API works on the latest one. The API's integer `question_id` is the
question's `position` (1-5) within its attempt. Results are rebuilt from the
evaluation rows, so `/submit` and `/result` always return the same report.

Primary keys are named after their table (`user_id`, `interview_id`,
`interview_attempt_id`, ...), so a foreign key has the same name as the key it
points to.

## Setup

Requires Python 3.12, a running PostgreSQL server and a Redis server (e.g. a
free [Upstash](https://upstash.com) database) for Google sign-in.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy the example environment file, then fill in your OpenRouter API key, a JWT
secret and real database credentials:

```bash
cp .env.example .env
```

The `DATABASE_URL` in `.env.example` is a placeholder — the user, password and
database must exist in your PostgreSQL server, otherwise every request that
touches the database fails with `500`. To create them:

```bash
sudo -u postgres psql -c "CREATE USER <db_user> WITH PASSWORD '<db_password>';"
sudo -u postgres psql -c "CREATE DATABASE interview_db OWNER <db_user>;"
```

| Variable | Required | Default |
| --- | --- | --- |
| `DATABASE_URL` | yes | — (e.g. `postgresql+asyncpg://<db_user>:<db_password>@localhost:5432/interview_db`) |
| `OPENROUTER_API_KEY` | yes | — |
| `OPENROUTER_BASE_URL` | yes | — (e.g. `https://openrouter.ai/api/v1`) |
| `AI_MODEL` | yes | — (e.g. `nvidia/nemotron-3-super-120b-a12b:free`) |
| `JWT_SECRET_KEY` | yes | — |
| `CORS_ORIGINS` | yes | — (comma-separated, e.g. `http://localhost:3000,https://aiinterviewsuite.vercel.app`) |
| `GOOGLE_CLIENT_ID` | yes | — (Google Cloud OAuth client) |
| `GOOGLE_CLIENT_SECRET` | yes | — |
| `SESSION_SECRET_KEY` | yes | — (signs the OAuth state cookie) |
| `REDIS_URL` | yes | — (e.g. `rediss://default:<password>@<host>.upstash.io:6379`) |
| `GOOGLE_REDIRECT_URI` | no | `http://localhost:8000/auth/google/callback` |
| `FRONTEND_URL` | no | `http://localhost:3000` |
| `JWT_ALGORITHM` | no | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `30` |
| `APP_NAME` | no | `AI Interview Service` |
| `APP_VERSION` | no | `1.0.0` |
| `DEBUG` | no | `true` |

Create the tables:

```bash
alembic upgrade head
```

To confirm your OpenRouter key and model work, run `python check_openrouter.py`.
To confirm `REDIS_URL` works, run `python check_redis.py` (prints `True`).

### Google sign-in

Create an OAuth client of type *Web application* in the
[Google Cloud console](https://console.cloud.google.com/apis/credentials) and add
`GOOGLE_REDIRECT_URI` (the API's `/auth/google/callback`) as an authorised
redirect URI. The flow is:

1. The front links to `GET /auth/google/login`, which redirects to Google.
2. Google redirects back to `GET /auth/google/callback`. The API finds the user
   by Google id (`users.google_sub`) or creates one without a password, stores
   a one-time code in Redis for 60 seconds, and redirects to
   `FRONTEND_URL/auth/google/callback?code=...`.
3. The front posts the code to `POST /auth/google/exchange` and gets the usual
   access token. Each code works once.

A Google account whose email is not verified is rejected. If a password account
already uses that email, sign-in is refused (`?error=account_exists`) rather
than linking the two. Users created through Google cannot log in with a
password. Failures redirect to `FRONTEND_URL/login?error=<reason>`.

### Hosted PostgreSQL (Neon)

To use a [Neon](https://neon.tech) database, set `DATABASE_URL` to its connection
string with the `postgresql+asyncpg://` scheme. asyncpg does not accept Neon's
`sslmode` and `channel_binding` query parameters; replace them with `ssl=require`:

```
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>.neon.tech/<db>?ssl=require
```

Run `python check_neon.py` and paste the Neon URL (input is hidden) to list the
tables and Alembic revision in that database, e.g. to confirm migrations ran.

## Running

```bash
uvicorn app.main:app --reload
```

Interactive API docs are then at `http://127.0.0.1:8000/docs`.

Browser requests are only accepted from the origins listed in `CORS_ORIGINS`.
Add the URL of every [front](https://github.com/ai-interview-suite/front)
deployment there (the local dev server is `http://localhost:3000`).

## Deployment

| Part | Host | Notes |
| --- | --- | --- |
| API | [Render](https://render.com) web service | Python, deployed from this repo |
| Database | [Neon](https://neon.tech) serverless PostgreSQL | AWS `ap-southeast-1` (Singapore) |
| Frontend | [Vercel](https://vercel.com) | Deployed from the [front](https://github.com/ai-interview-suite/front) repo |

Render service settings:

- **Source:** `ai-interview-suite/api`, branch `main`, repository root
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port "$PORT"`
- **Auto-deploy:** on every commit to `main`
- **Environment:** every variable from the [Setup](#setup) table. `DATABASE_URL`
  is the Neon connection string in the asyncpg form shown under
  [Hosted PostgreSQL (Neon)](#hosted-postgresql-neon), and `CORS_ORIGINS` must
  include `https://aiinterviewsuite.vercel.app`. Set `GOOGLE_REDIRECT_URI` to
  `https://ai-interview-suite-api.onrender.com/auth/google/callback` (and add it
  to the Google OAuth client) and `FRONTEND_URL` to
  `https://aiinterviewsuite.vercel.app`.

Migrations are **not** run by Render. Before merging a change that adds an
Alembic revision, apply it to Neon from your machine:

```bash
DATABASE_URL='postgresql+asyncpg://<user>:<password>@<host>.neon.tech/<db>?ssl=require' \
  alembic upgrade head
python check_neon.py   # confirm the new revision is listed
```

Because the migration runs while the previous version is still live, each
revision must keep that version working: add tables and columns (with server
defaults) first, and only drop or rename them in a later revision once no
deployed code uses them. Before a revision that copies or drops data, take a
backup by creating a branch in the Neon console.

Revision `70750a06dc62` (interview attempts) converts `users.email` to
case-insensitive `citext` and stops if two emails differ only by case. Check
production first; the query must return no rows:

```sql
SELECT lower(email) FROM users GROUP BY lower(email) HAVING count(*) > 1;
```

Revision `943dab65b4f8` copies every existing interview into attempt #1 with
its questions, answers and evaluations. It only inserts, and it stops (rolling
everything back) if any interview, answer or evaluation was not copied. Run it
on a Neon branch first, then on production immediately before deploying the
code that reads the new tables: answers saved by the old code in between are
not copied.

Revision `6bb6c25402bc` first copies any interview still missing from the new
tables, then drops the old interview columns and `interview_answers`, and
renames `users.id` / `interviews.id` to `user_id` / `interview_id`. The renamed
columns and the code must change together, so run it on production and merge
straight away; requests fail for the few minutes until Render's deploy is
live.

Revisions `86be904e60f1` (nullable `users.password_hash`) and `b89864d5d044`
(`users.google_sub` with a unique constraint) only relax or add columns, so they
can run before the Google sign-in code is deployed.

The Neon project and its connection string are managed in the
[Neon console](https://console.neon.tech).

The service is on Render's free plan, so it sleeps when idle and the first
request after a quiet period can take up to a minute.

## API

Every endpoint except the health check, register, login and the Google
sign-in endpoints needs an
`Authorization: Bearer <access_token>` header. Users can only see their own
interviews. Emails are case-insensitive. A user whose `status` is `disabled`
gets `403` on login and on every authenticated request.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Health check |
| `POST` | `/auth/register` | Create a user (`email`, `password` of 8+ characters) |
| `POST` | `/auth/login` | Exchange email and password for an access token |
| `GET` | `/auth/me` | The current user |
| `GET` | `/auth/google/login` | Redirect to Google sign-in |
| `GET` | `/auth/google/callback` | Google redirect target; redirects to the front with a one-time code |
| `POST` | `/auth/google/exchange` | Exchange the one-time `code` for an access token |
| `GET` | `/interview/` | List the current user's interviews, newest first |
| `POST` | `/interview/start` | Upload a resume PDF + job description, get five questions |
| `POST` | `/interview/{interview_id}/answers` | Submit one answer |
| `GET` | `/interview/{interview_id}` | Progress: answered vs. total, completion flag |
| `POST` | `/interview/{interview_id}/submit` | Evaluate all answers and return the result |
| `GET` | `/interview/{interview_id}/result` | The stored result of a completed interview (`409` if not completed) |

`GET /interview/` is defined with a trailing slash; requesting `/interview`
redirects to it, and some clients drop the `Authorization` header on redirect.

### Example

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "me@example.com", "password": "secret123"}'

TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "me@example.com", "password": "secret123"}' | jq -r .access_token)

curl -X POST http://127.0.0.1:8000/interview/start \
  -H "Authorization: Bearer $TOKEN" \
  -F "resume=@resume.pdf" \
  -F "job_description=Senior Python engineer with FastAPI experience"
```

## Tests

The tests run against a separate PostgreSQL database configured in `.env.test`,
which overrides `DATABASE_URL` and `CORS_ORIGINS` from `.env`. Its name must contain `test`; the
schema is built with `alembic upgrade head` and removed with `alembic downgrade base` around each
test, so never point it at real data. Because tests use the migrations, every migration needs a
working `downgrade()`.

```bash
sudo -u postgres psql -c "CREATE USER interview_test WITH PASSWORD '<password>';"
sudo -u postgres psql -c "CREATE DATABASE interview_test_db OWNER interview_test;"
pytest
```

After changing a model, confirm the migrations match it (prints
`No new upgrade operations detected.` when they do):

```bash
alembic check
```

## Project layout

```
app/
  main.py                    FastAPI app, CORS, session middleware and router wiring
  config.py                  Pydantic settings loaded from .env
  database.py                Async SQLAlchemy engine and session dependency
  dependencies.py            Current-user dependency (bearer token)
  models/                    SQLAlchemy models, one file per table
  repositories/              Database queries for users and interviews
  routers/
    auth.py                  Register, login, Google sign-in and current-user endpoints
    interview.py             Interview endpoints
  schemas/                   Request/response models and enums
  services/
    ai_service.py            OpenRouter calls for questions and evaluation
    auth.py                  JWT creation and verification
    google_oauth.py          Authlib OAuth client for Google
    redis_client.py          Async Redis client (one-time Google login codes)
    password.py              Password hashing (bcrypt)
    resume_parser.py         PDF text extraction
    interview_completion.py  Evaluates answers and stores the result
    evaluation_validation.py Checks evaluations match the interview questions
    scoring.py               Weighted answer and overall scoring
    result_service.py        Recommendation, conclusion and result report
    exceptions.py            AI service error types
migrations/                  Alembic migrations
check_openrouter.py          Manual OpenRouter connectivity check
check_neon.py                Manual Neon database check (tables, Alembic revision)
check_redis.py               Manual Redis connectivity check
tests/                       Pytest suite
```

## Notes and limitations

- The session cookie used during the Google redirect is not marked `Secure`
  (`https_only=False` in `app/main.py`).

- The service expects the model to return exactly five questions and five
  evaluations; malformed responses surface as `502`, and upstream outages as `503`.
