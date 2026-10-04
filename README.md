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

## Deployment

Build independent containers with `docker build -f backend/Dockerfile -t dating-backend .` and `docker build -f frontend/Dockerfile -t dating-frontend .`. The backend and Next standalone server listen on `0.0.0.0:$PORT`. Same-origin `/api/*` routes proxy to server-only `BACKEND_URL`. For GCP, deploy frontend and backend to Cloud Run, publish images to Artifact Registry, use Cloud SQL PostgreSQL via `DATABASE_URL`, and provide `GEMINI_API_KEY` and `APIFY_API_TOKEN` through Secret Manager. Configure Actor IDs and service URLs at runtime. This project does not deploy resources.

SAGE_GENERATED`, and `COMPATIBILITY_ANALYSIS_COMPLETED`. It does not log prompts, profile text, or credentials.
