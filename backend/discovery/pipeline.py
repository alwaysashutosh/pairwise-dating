from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.discovery.apify_google_search import ApifyGoogleSearchSource
from backend.discovery.service import CandidateDiscoveryService
from backend.ingestion.apify_source import ApifySource
from backend.ingestion.normalizer import normalize_sources
from backend.llm import GeminiProvider
from backend.main import Person, Profile, Ranking, candidate_score, ensure_agents, normalized_profile, run_date


def validate_discovery_configuration() -> list[str]:
    required = {
        "APIFY_API_TOKEN": os.getenv("APIFY_API_TOKEN"),
        "APIFY_GOOGLE_SEARCH_ACTOR_ID": os.getenv("APIFY_GOOGLE_SEARCH_ACTOR_ID"),
        "APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE": os.getenv("APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE"),
        "APIFY_LINKEDIN_ACTOR_ID": os.getenv("APIFY_LINKEDIN_ACTOR_ID"),
        "APIFY_INSTAGRAM_ACTOR_ID": os.getenv("APIFY_INSTAGRAM_ACTOR_ID"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    }
    missing = [key for key, value in required.items() if not value]
    template = os.getenv("APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE", "")
    if template:
        try:
            parsed_template = json.loads(template)
            if not isinstance(parsed_template, dict) or not any("{{query}}" in str(value) for value in parsed_template.values()):
                missing.append("APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE (must be an object containing {{query}})")
        except json.JSONDecodeError:
            missing.append("APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE (invalid JSON)")
    if os.getenv("GEMINI_MODEL", "gemini-2.5-flash") != "gemini-2.5-flash":
        missing.append("GEMINI_MODEL=gemini-2.5-flash")
    return missing


def _person_id(linkedin_url: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", linkedin_url.rsplit("/", 1)[-1].casefold()).strip("-")[:36] or "profile"
    suffix = hashlib.sha256(linkedin_url.encode()).hexdigest()[:8]
    return f"public-{slug}-{suffix}"


def _apply_analysis(profile: Profile, data: dict[str, Any]) -> None:
    for key, value in data.items():
        setattr(profile, "profile_summary" if key == "summary" else key, value)
    profile.analysis_json = {**data, "source_type": "public_profile_simulation",
                             "simulation_mode": "Public-profile simulation"}


async def run_public_simulation(db: Session, limit: int = 25, force: bool = False,
                               search_source: ApifyGoogleSearchSource | None = None,
                               source: ApifySource | None = None,
                               provider: GeminiProvider | None = None) -> dict[str, int]:
    missing = validate_discovery_configuration() if search_source is None or source is None or provider is None else []
    if missing:
        raise ValueError("Missing or invalid configuration: " + ", ".join(missing))
    search_source = search_source or ApifyGoogleSearchSource()
    source = source or ApifySource()
    provider = provider or GeminiProvider(model="gemini-2.5-flash")
    if provider.model != "gemini-2.5-flash":
        raise ValueError("Public-profile simulation requires Gemini 2.5 Flash.")

    candidates, discovery_errors = await CandidateDiscoveryService(search_source).discover(limit)
    people: list[Person] = []
    candidate_by_person_id = {}
    for candidate in candidates:
        person = db.scalar(select(Person).where(Person.linkedin_url == candidate.linkedin_url))
        if person is None:
            person = Person(id=_person_id(candidate.linkedin_url), name=candidate.name,
                linkedin_url=candidate.linkedin_url, instagram_url=candidate.instagram_url,
                source_type="public_profile_simulation", ingestion_status="identity_validated")
            db.add(person)
            db.flush()
        else:
            person.name = candidate.name
            person.instagram_url = candidate.instagram_url
            person.source_type = "public_profile_simulation"
        people.append(person)
        candidate_by_person_id[person.id] = candidate
    db.commit()

    enriched = analyzed = 0
    usable_people: list[Person] = []
    for person in people:
        profile = person.profile
        if profile is None:
            profile = Profile(person_id=person.id)
            person.profile = profile
            db.add(profile)
        source_cache = profile.source_data_json or {}
        linkedin_cache = source_cache.get("linkedin") or {}
        instagram_cache = source_cache.get("instagram") or {}
        cached_sources = (linkedin_cache.get("status") == "success" and
                          instagram_cache.get("status") == "success" and
                          linkedin_cache.get("source_url") == person.linkedin_url and
                          instagram_cache.get("source_url") == person.instagram_url)
        cached_analysis = (profile.analysis_json or {}).get("source_type") == "public_profile_simulation"
        needs_reacquire = not ((profile.raw_linkedin_text or "").strip() or (profile.raw_instagram_text or "").strip()) and not cached_analysis
        if force or not cached_sources or needs_reacquire:
            linkedin, instagram = await source.fetch_linkedin(person.linkedin_url), await source.fetch_instagram(person.instagram_url)
            normalized = normalize_sources(linkedin, instagram)
            profile.raw_linkedin_text = normalized["linkedin_text"]
            profile.raw_instagram_text = normalized["instagram_text"]
            profile.source_data_json = {
                "linkedin": {key: normalized["linkedin"][key] for key in ("source_url", "source_type", "platform", "status", "metadata", "error")},
                "instagram": {key: normalized["instagram"][key] for key in ("source_url", "source_type", "platform", "status", "metadata", "error")},
                "identity_match": {"method": "public name and professional-context overlap",
                                   "evidence_term_count": candidate_by_person_id[person.id].identity_evidence_terms},
            }
            person.ingestion_status = "success" if linkedin.status == instagram.status == "success" else "partial"
            db.commit()
            if linkedin.status != "success" or instagram.status != "success":
                continue
        else:
            linkedin_ok = (profile.source_data_json.get("linkedin") or {}).get("status") == "success"
            instagram_ok = (profile.source_data_json.get("instagram") or {}).get("status") == "success"
            if not (linkedin_ok and instagram_ok):
                person.ingestion_status = "partial"
                db.commit()
                continue

        if not ((profile.raw_linkedin_text or "").strip() or (profile.raw_instagram_text or "").strip()):
            person.ingestion_status = "incomplete_public_profile"
            db.commit()
            continue
        if force or not cached_analysis:
            result = await provider.analyze(profile.raw_linkedin_text, profile.raw_instagram_text)
            _apply_analysis(profile, result.model_dump())
            profile.raw_linkedin_text = ""
            profile.raw_instagram_text = ""
            person.ingestion_status = "analyzed"
            analyzed += 1
            db.commit()
        if person.profile and (person.profile.analysis_json or {}).get("source_type") == "public_profile_simulation":
            usable_people.append(person)
            enriched += 1

    ensure_agents(db)
    ranked_count = conversation_count = 0
    for person in usable_people:
        candidates_for_person = sorted((other for other in usable_people if other.id != person.id),
            key=lambda other: (-candidate_score(person, other), other.id))[:4]
        for other in candidates_for_person:
            date = await run_date(db, person, other, force=force, provider=provider)
            conversation_count += 1
            dimensions = date.compatibility_json["dimensions"]
            existing = db.scalar(select(Ranking).where(Ranking.person_id == person.id, Ranking.matched_person_id == other.id))
            fields = {"date_id": date.id, "score": date.compatibility_score,
                "shared_interests_score": dimensions["shared_interests"], "lifestyle_score": dimensions["lifestyle"],
                "conversation_score": dimensions["conversation"], "goals_score": dimensions["goals"],
                "overall_reason": "Public-profile simulation; scores describe only this AI-generated exchange, not actual personal preferences."}
            if existing:
                for key, value in fields.items():
                    setattr(existing, key, value)
            else:
                db.add(Ranking(person_id=person.id, matched_person_id=other.id, **fields))
            ranked_count += 1
            db.commit()

    return {"discovered": len(candidates), "enriched": enriched, "analyzed": analyzed,
            "agents": sum(1 for person in usable_people if person.agent),
            "conversation_passes": conversation_count, "rankings": ranked_count,
            "discovery_errors": len(discovery_errors)}
