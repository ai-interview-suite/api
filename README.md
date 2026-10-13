# AI Interview Service

A FastAPI service that runs AI-powered mock technical interviews. Upload a resume
and a job description, answer five generated questions, and get a scored
evaluation with per-question feedback and a hiring recommendation.

Users register and log in with email and password; interviews are stored in
PostgreSQL and scoped to the user who created them.

Question generation and answer evaluation run through [OpenRouter](https://openrouter.ai).

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

## Setup

Requires Python 3.12 and a running PostgreSQL server.

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

## Running

```bash
uvicorn app.main:app --reload
```

Interactive API docs are then at `http://127.0.0.1:8000/docs`.

CORS allows only `http://localhost:3000` (the [front](https://github.com/ai-interview-suite/front)
dev server); change `allow_origins` in `app/main.py` to serve another origin.

## API

Every endpoint except the health check, register and login needs an
`Authorization: Bearer <access_token>` header. Users can only see their own
interviews.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Health check |
| `POST` | `/auth/register` | Create a user (`email`, `password` of 8+ characters) |
| `POST` | `/auth/login` | Exchange email and password for an access token |
| `GET` | `/auth/me` | The current user |
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
which overrides `DATABASE_URL` from `.env`. Its name must contain `test`; tables
are created and dropped around each test, so never point it at real data.

```bash
sudo -u postgres psql -c "CREATE USER interview_test WITH PASSWORD '<password>';"
sudo -u postgres psql -c "CREATE DATABASE interview_test_db OWNER interview_test;"
pytest
```

## Project layout

```
app/
  main.py                    FastAPI app, CORS and router wiring
  config.py                  Pydantic settings loaded from .env
  database.py                Async SQLAlchemy engine and session dependency
  dependencies.py            Current-user dependency (bearer token)
  models/                    SQLAlchemy models: users and interviews
  repositories/              Database queries for users and interviews
  routers/
    auth.py                  Register, login and current-user endpoints
    interview.py             Interview endpoints
  schemas/                   Request/response models and enums
  services/
    ai_service.py            OpenRouter calls for questions and evaluation
    auth.py                  JWT creation and verification
    password.py              Password hashing (bcrypt)
    resume_parser.py         PDF text extraction
    interview_completion.py  Evaluates answers and stores the result
    evaluation_validation.py Checks evaluations match the interview questions
    scoring.py               Weighted answer and overall scoring
    result_service.py        Recommendation and conclusion text
    exceptions.py            AI service error types
migrations/                  Alembic migrations
check_openrouter.py          Manual OpenRouter connectivity check
tests/                       Pytest suite
```

## Notes and limitations

- The service expects the model to return exactly five questions and five
  evaluations; malformed responses surface as `502`, and upstream outages as `503`.
