# AI Interview Service

A FastAPI service that runs AI-powered mock technical interviews. Upload a resume
and a job description, answer five generated questions, and get a scored
evaluation with per-question feedback and a hiring recommendation.

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

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy the example environment file and add your OpenRouter API key:

```bash
cp .env.example .env
```

| Variable | Required | Default |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | yes | — |
| `APP_NAME` | no | `AI Interview Service` |
| `APP_VERSION` | no | `1.0.0` |
| `DEBUG` | no | `true` |

## Running

```bash
uvicorn app.main:app --reload
```

Interactive API docs are then at `http://127.0.0.1:8000/docs`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Health check |
| `POST` | `/interview/start` | Upload a resume PDF + job description, get five questions |
| `POST` | `/interview/{interview_id}/answers` | Submit one answer |
| `GET` | `/interview/{interview_id}` | Progress: answered vs. total, completion flag |
| `POST` | `/interview/{interview_id}/submit` | Evaluate all answers and return the result |

### Example

```bash
curl -X POST http://127.0.0.1:8000/interview/start \
  -F "resume=@resume.pdf" \
  -F "job_description=Senior Python engineer with FastAPI experience"
```

## Tests

```bash
pytest
```

## Project layout

```
app/
  main.py                    FastAPI app and router wiring
  config.py                  Pydantic settings loaded from .env
  routers/interview.py       Interview endpoints
  schemas/interview.py       Request/response models and enums
  services/
    ai_service.py            OpenRouter calls for questions and evaluation
    resume_parser.py         PDF text extraction
    interview_state.py       In-memory interview sessions
    scoring.py               Weighted answer and overall scoring
    result_service.py        Recommendation and conclusion text
    exceptions.py            AI service error types
tests/                       Pytest suite
```

## Notes and limitations

- Interview sessions are held **in memory**, so they are lost on restart and are
  not shared across workers. A persistent store is needed before running more
  than one process.
- The service expects the model to return exactly five questions and five
  evaluations; malformed responses surface as `502`, and upstream outages as `503`.
