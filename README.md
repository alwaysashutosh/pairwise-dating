# AI Compatibility Simulation

## Overview

This is an AI engineering assessment demonstrating simulations generated from public profile information. Discovered people are not represented as participants or endorsers, agents do not speak for them, and no one is contacted. Compatibility scores describe only simulated exchanges, not real people's preferences. The fixture cohort contains 25 fictional profiles and no fabricated social URLs.

## Architecture

```text
Apify Google Search Results Actor: public LinkedIn and Instagram search candidates
        ↓
Conservative identity matching and Apify profile enrichment (Playwright alternative)
        ↓
Profile Normalization (Pydantic)
        ↓
Normalized non-sensitive profile facts and Gemini 2.5 Flash analysis
        ↓
Person Agent
        ↓
Candidate Generation (deterministic profile similarity)
        ↓
Simulated agent-only conversation (persisted transcript)
        ↓
Gemini compatibility dimensions and Python weighted score
        ↓
Ranking
        ↓
Next.js UI
```

## Tech Stack

- Python, FastAPI, Pydantic, SQLAlchemy and SQLite
- Next.js 14, React and TypeScript
- Apify REST API for search and profile acquisition; Playwright alternative adapter for permitted public pages
- Gemini 2.5 Flash for public-profile simulation; deterministic mock behavior for fixtures

## Project Structure

```text
backend/main.py       API, SQLite models and pipeline orchestration
backend/agents/       Profile-bound agents, date orchestration and weighted scoring
backend/llm.py        Gemini and mock provider interface
backend/ingestion/    Apify, Playwright and fixture adapters plus profile normalizer
backend/sources.py    Backward-compatible public-page Playwright adapter
backend/fixtures.py   25 fictional fixture profiles
frontend/app/         Overview, people, profile, date and ranking screens
scripts/              Seed, ingest, analyze, date and ranking commands
tests/                Pipeline and API checks
data/                  CSV template for real public profiles
```

## Setup

Python 3.10+ and Node.js 20.9+ are required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
cd frontend
npm install
```

## Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `GEMINI_API_KEY` | Backend key required for public-profile simulation | empty; fixture mode uses mock provider |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.5-flash` |
| `APIFY_API_TOKEN` | Backend-only official Apify API token | empty; ingestion records unavailable |
| `APIFY_GOOGLE_SEARCH_ACTOR_ID` | Configured Google Search Results Actor | required for discovery |
| `APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE` | JSON input following Actor schema; `{{query}}` placeholder | required for discovery |
| `APIFY_LINKEDIN_ACTOR_ID` | Configured LinkedIn Actor ID | empty |
| `APIFY_INSTAGRAM_ACTOR_ID` | Configured Instagram Actor ID | empty |
| `APIFY_LINKEDIN_URL_FIELD`, `APIFY_INSTAGRAM_URL_FIELD` | Actor input property for profile URL | `startUrls` |
| `PROFILE_SOURCE` | Choose `apify` (default) or `playwright` | `apify` |
| `DATABASE_URL` | SQLAlchemy connection URL | `sqlite:///./agentic_dating.db` |
| `FRONTEND_URL` | Allowed browser origin | `http://localhost:3000` |
| `BACKEND_URL` | API URL used for deployment documentation | `http://localhost:8000` |
| `NEXT_PUBLIC_API_URL` | Optional API origin; blank uses same-origin server proxy | blank |

Never commit `.env` or API keys.

## Running Locally

Start the backend from the repository root:

```powershell
uvicorn backend.main:app --reload
```

Start the frontend in another terminal:

```powershell
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs). The SQLite schema is created on backend startup.

## Running Fixture Demo

From the repository root:

```powershell
python scripts/seed.py --fixture
python scripts/analyze.py --fixture
python scripts/generate_dates.py --fixture
python scripts/generate_rankings.py --fixture
```

The scripts are idempotent. Re-run a stage with `--force` to replace cached analyses/dates/rankings. Fixture records and profile pages carry an explicit synthetic label.

## Using Two Supplied Public Profiles

For a controlled pair test, `data/people.csv` may contain just two rows with the header `id,name,linkedin_url,instagram_url,source_type`; each row must be a real public profile record you are permitted to process. From the repository root, run:

```powershell
python scripts/seed.py
python scripts/ingest.py
python scripts/analyze.py
python scripts/generate_dates.py
python scripts/generate_rankings.py
```

Seeding is local. Ingestion calls the configured Apify profile Actors, and analysis/date generation call Gemini 2.5 Flash. This workflow uses the CSV rows; it does not run Google Search discovery.

## Public-Profile Discovery Simulation

The public workflow discovers profiles through the configured Apify Google Search Results Actor; `data/people.csv` is optional. It searches LinkedIn across multiple professions, searches for Instagram candidates, and accepts a pair only when public result text includes the full name plus corroborating professional context. Ambiguous candidates are rejected; results are never padded with invented people or URLs.

Set `APIFY_GOOGLE_SEARCH_ACTOR_ID` and `APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE` in `.env`. The template must follow the selected Actor's documented input schema and contain `{{query}}`; `{{limit}}` may optionally be used. The adapter does not guess field names. Also configure `APIFY_API_TOKEN`, the LinkedIn/Instagram Actor IDs and URL input fields, `GEMINI_API_KEY`, and `GEMINI_MODEL=gemini-2.5-flash`.

```powershell
python scripts/discover_people.py --limit 2
python scripts/discover_people.py --limit 25
```

This command performs discovery, identity matching, Apify profile enrichment, Gemini profile analysis, simulation agent creation, six-turn agent-only conversations among each profile's top four candidates, Gemini compatibility evaluation, Python weighted scoring, and ranking persistence. `--force` refreshes cached results. Configuration is validated before network calls. Search snippets are not persisted, raw Actor results are not returned to the frontend, and normalized profile analysis plus minimal source metadata are kept. Playwright remains an alternative for explicitly supplied public URLs. The workflow never logs in, contacts, messages, follows, connects to, bypasses access controls, or recommends approaching discovered people.

Every discovered record is labeled **PUBLIC-PROFILE SIMULATION** with the notice that the person is not represented as a participant or endorser. Conversations and compatibility scores are AI simulations, not claims about actual preferences or compatibility.

## API Documentation

- `GET /api/health`, `GET /api/stats`
- `GET /api/people`, `GET /api/people/{id}`, `GET /api/people/{id}/profile`
- `GET /api/people/{id}/rankings`, `GET /api/rankings/{id}`, `GET /api/people/{id}/sources`
- `GET /api/dates/{id}`, `GET /api/dates/{id}/activity`, `POST /api/dates`
- `POST /api/ingestion/run`, `POST /api/analysis/run`, `POST /api/rankings/generate`

Interactive OpenAPI documentation: `/docs`.

## Agent Architecture

Each `PersonAgent` receives only its normalized profile and visible simulated conversation history. Public-profile runs require Gemini 2.5 Flash and do not fall back to mocks. Fixture runs use deterministic `MockProvider`. The UI distinguishes `FIXTURE MODE` and `PUBLIC-PROFILE SIMULATION`; public pages state that the person is not represented as a participant or endorser. Agents never speak for a real person or generate outreach/contact suggestions. Python computes the weighted score: 30% shared interests, 25% lifestyle, 25% conversation and 20% goals. Scores describe the simulation, not actual preferences.

## Ranking Algorithm

Candidate generation sorts profile pairs by Jaccard overlap across interests, hobbies, lifestyle and conversation topics, then selects at most four candidates per person. The evaluator produces four dimensions, and the backend computes the weighted score: shared interests 30%, lifestyle 25%, conversation 25%, goals 20%. Rankings and date results are cached in SQLite.

## Data / Privacy Considerations

Only publicly accessible profile information is queried. Apify is the acquisition layer, with Playwright as an alternative. The system does not bypass access controls or contact discovered people. Identity matching uses public name and professional context; sensitive traits are excluded. Search snippets are transient, raw Actor payloads are not retained by discovery or exposed to the frontend, and Gemini analysis is constrained to supported non-sensitive facts. Public-profile simulation does not imply participation or endorsement. Fixture records remain synthetic and clearly labeled.

## Limitations

Fixture conversations and compatibility are deterministic demo logic. Public-profile rankings are simulation outputs, not claims about people's preferences or actual compatibility. Gemini and Apify calls require configured credentials and network access; failures do not substitute fabricated LLM output. Public search may not return enough profiles with corroborating cross-platform evidence to reach the requested limit.

## Future Improvements

- Add configurable assessment-record retention and deletion.
- Add discovery-status auditing that stores no search snippets.
- Add deployment environment configuration and a managed database for hosted use.

## Deployment

Build independent containers with `docker build -f backend/Dockerfile -t dating-backend .` and `docker build -f frontend/Dockerfile -t dating-frontend .`. The backend and Next standalone server listen on `0.0.0.0:$PORT`. Same-origin `/api/*` routes proxy to server-only `BACKEND_URL`. For GCP, deploy frontend and backend to Cloud Run, publish images to Artifact Registry, use Cloud SQL PostgreSQL via `DATABASE_URL`, and provide `GEMINI_API_KEY` and `APIFY_API_TOKEN` through Secret Manager. Configure Actor IDs and service URLs at runtime. This project does not deploy resources.

## Gemini Agent Dates

Set `GEMINI_API_KEY` and optionally `GEMINI_MODEL` in `.env` (default: `gemini-2.5-flash`). Gemini structured calls are retried up to three times and validated with Pydantic. To create or refresh one real profile date, use two existing `public_profile` IDs:

```powershell
python scripts/run_date.py --person-a person-001 --person-b person-002 --force
```

`--force` replaces a cached conversation and compatibility evaluation. Without it, existing dates are reused. Fixture records always use `MockProvider`, even when a Gemini key is set:

```powershell
python scripts/seed.py --fixture
python scripts/analyze.py --fixture
python scripts/generate_dates.py --fixture
python scripts/generate_rankings.py --fixture
```

The app logs events such as `AGENT_DATE_STARTED`, `AGENT_MESSAGE_GENERATED`, and `COMPATIBILITY_ANALYSIS_COMPLETED`. It does not log prompts, profile text, or credentials.
