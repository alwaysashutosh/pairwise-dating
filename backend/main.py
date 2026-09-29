from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from backend.agents.compatibility import evaluate_compatibility
from backend.agents.dating_engine import run_date as run_agent_date
from backend.agents.person_agent import PersonAgent
from backend.llm import LLMProvider, MockProvider, NormalizedProfile, get_provider

load_dotenv()
logger = logging.getLogger("agentic_dating")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentic_dating.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "people"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String, default="fixture")
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    ingestion_status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    profile: Mapped[Profile | None] = relationship(back_populates="person", cascade="all, delete-orphan", uselist=False)
    agent: Mapped[Agent | None] = relationship(back_populates="person", cascade="all, delete-orphan", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id"), unique=True, index=True)
    profession: Mapped[str | None] = mapped_column(String, nullable=True)
    education: Mapped[str | None] = mapped_column(String, nullable=True)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    hobbies: Mapped[list[str]] = mapped_column(JSON, default=list)
    lifestyle: Mapped[list[str]] = mapped_column(JSON, default=list)
    conversation_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferences: Mapped[list[str]] = mapped_column(JSON, default=list)
    profile_summary: Mapped[str] = mapped_column(Text, default="")
    raw_linkedin_text: Mapped[str] = mapped_column(Text, default="")
    raw_instagram_text: Mapped[str] = mapped_column(Text, default="")
    source_data_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    analysis_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    person: Mapped[Person] = relationship(back_populates="profile")


class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id"), unique=True, index=True)
    system_prompt: Mapped[str] = mapped_column(Text)
    person: Mapped[Person] = relationship(back_populates="agent")


class Date(Base):
    __tablename__ = "dates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_a_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    agent_b_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    person_a_id: Mapped[str] = mapped_column(ForeignKey("people.id"), index=True)
    person_b_id: Mapped[str] = mapped_column(ForeignKey("people.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="complete")
    compatibility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    compatibility_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    messages: Mapped[list[Message]] = relationship(back_populates="date", cascade="all, delete-orphan", order_by="Message.turn_number")
    __table_args__ = (UniqueConstraint("person_a_id", "person_b_id", name="uq_date_pair"),)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dates.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    turn_number: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    date: Mapped[Date] = relationship(back_populates="messages")


class Ranking(Base):
    __tablename__ = "rankings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id"), index=True)
    matched_person_id: Mapped[str] = mapped_column(ForeignKey("people.id"), index=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dates.id"))
    score: Mapped[float] = mapped_column(Float)
    shared_interests_score: Mapped[float] = mapped_column(Float)
    lifestyle_score: Mapped[float] = mapped_column(Float)
    conversation_score: Mapped[float] = mapped_column(Float)
    goals_score: Mapped[float] = mapped_column(Float)
    overall_reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_ranking_owner_score", "person_id", "score"),)


Base.metadata.create_all(engine)
if engine.dialect.name == "sqlite" and "source_data_json" not in {column["name"] for column in inspect(engine).get_columns("profiles")}:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE profiles ADD COLUMN source_data_json JSON"))


def get_db():
    with SessionLocal() as session:
        yield session


def person_json(p: Person) -> dict[str, Any]:
    profile = p.profile
    public_simulation = p.source_type in {"public_profile", "public_profile_simulation"}
    return {"id": p.id, "name": p.name, "linkedin_url": p.linkedin_url, "instagram_url": p.instagram_url,
            "source_type": p.source_type, "image_url": p.image_url, "ingestion_status": p.ingestion_status,
            "simulation_mode": "Public-profile simulation" if public_simulation else "Fixture Mode" if p.source_type == "fixture" else "Profile simulation",
            "simulation_notice": "Public-profile simulation — this person is not represented as a participant or endorser of this system." if public_simulation else None,
            "profession": profile.profession if profile else None,
            "profile_summary": profile.profile_summary if profile else "Profile analysis pending.",
            "profile": ({"profession": profile.profession, "education": profile.education, "interests": profile.interests,
                         "hobbies": profile.hobbies, "lifestyle": profile.lifestyle,
                         "conversation_topics": profile.conversation_topics, "preferences": profile.preferences,
                         "summary": profile.profile_summary, "analysis": profile.analysis_json} if profile else None)}


def profile_facts(p: Person) -> set[str]:
    if not p.profile:
        return set()
    profile = p.profile
    return {str(v).casefold() for field in (profile.interests, profile.hobbies, profile.lifestyle, profile.conversation_topics) for v in field}


def candidate_score(a: Person, b: Person) -> float:
    af, bf = profile_facts(a), profile_facts(b)
    return len(af & bf) / max(1, len(af | bf))


def normalized_profile(p: Person) -> NormalizedProfile:
    if not p.profile:
        raise ValueError("Both people need analyzed profiles before a date.")
    profile = p.profile
    return NormalizedProfile(profession=profile.profession, education=profile.education,
        interests=profile.interests or [], hobbies=profile.hobbies or [], lifestyle=profile.lifestyle or [],
        conversation_topics=profile.conversation_topics or [], preferences=profile.preferences or [],
        summary=profile.profile_summary or "")


def make_agent_prompt(p: Person) -> str:
    profile = normalized_profile(p)
    return ("You are an AI compatibility simulation generated from profile information, never the real person. "
            "The person is not represented as participating in or endorsing this system. Use only normalized facts; "
            "do not infer or invent personal details, speak on the person's behalf, create messages for them to send, "
            "or recommend contacting or approaching them. Converse only with another simulated agent.\n"
            + profile.model_dump_json())


def ensure_agents(db: Session) -> None:
    for p in db.scalars(select(Person)).all():
        if p.profile:
            if not p.agent:
                p.agent = Agent(person_id=p.id, system_prompt=make_agent_prompt(p))
            else:
                p.agent.system_prompt = make_agent_prompt(p)
    db.commit()


async def run_date(db: Session, a: Person, b: Person, force: bool = False, fixture: bool = False,
                   provider: LLMProvider | None = None) -> Date:
    if (a.source_type == "fixture") != (b.source_type == "fixture"):
        raise ValueError("Fixture Mode and Public-profile simulation records cannot be mixed in one date.")
    first, second = sorted((a.id, b.id))
    existing = db.scalar(select(Date).where(Date.person_a_id == first, Date.person_b_id == second))
    if existing and not force:
        return existing
    ensure_agents(db)
    agent_a, agent_b = a.agent, b.agent
    if not agent_a or not agent_b:
        raise ValueError("Both people need an agent profile before dating.")
    if not a.profile or not b.profile:
        raise ValueError("Both people need analyzed profiles before a date.")
    if provider is None:
        if a.source_type == "fixture":
            provider = MockProvider()
        elif not os.getenv("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY is required for public-profile simulations; mock mode is not used for real profiles.")
        else:
            provider = get_provider()
    logger.info("AGENT_DATE_STARTED provider=%s", provider.simulation_mode)
    profile_a, profile_b = normalized_profile(a), normalized_profile(b)
    agent_a_sim = PersonAgent(profile_a, provider)
    agent_b_sim = PersonAgent(profile_b, provider)
    transcript = await run_agent_date(agent_a_sim, agent_b_sim, turns=6)
    for turn_number, _turn in enumerate(transcript, 1):
        logger.info("AGENT_MESSAGE_GENERATED turn=%s provider=%s", turn_number, provider.simulation_mode)
    evaluation, score = await evaluate_compatibility(provider, profile_a, profile_b,
        [{"speaker": f"Agent {'A' if int(turn['agent_index']) == 0 else 'B'}", "message": str(turn["message"])} for turn in transcript])
    dimensions = {"shared_interests": evaluation.shared_interests, "lifestyle": evaluation.lifestyle,
                 "conversation": evaluation.conversation, "goals": evaluation.goals}
    activity = [{"event": "date_started", "message": "Agent A is starting a conversation..."}]
    for idx, turn in enumerate(transcript):
        agent_letter = "A" if int(turn["agent_index"]) == 0 else "B"
        activity.append({"event": "message_generated", "turn_number": idx + 1,
                         "message": f"Agent {agent_letter} generated a response."})
    activity.append({"event": "compatibility_completed", "message": "Compatibility analysis completed."})
    result = {"overall_score": score, "dimensions": dimensions, "strengths": evaluation.strengths,
              "differences": evaluation.differences, "reason": evaluation.reason,
              "simulation_mode": ("Fixture Mode · Demo Simulation" if a.source_type == "fixture"
                  else f"Public-profile simulation · {getattr(provider, 'model', os.getenv('GEMINI_MODEL', 'Gemini'))}"),
              "activity": activity}
    first_person = a if a.id == first else b
    second_person = b if first_person is a else a
    if existing:
        existing.messages.clear()
        date = existing
        date.agent_a_id = first_person.agent.id
        date.agent_b_id = second_person.agent.id
        date.status = "complete"
        date.compatibility_score = score
        date.compatibility_json = result
        date.summary = evaluation.reason
    else:
        date = Date(agent_a_id=first_person.agent.id, agent_b_id=second_person.agent.id, person_a_id=first, person_b_id=second,
                    status="complete", compatibility_score=score, compatibility_json=result, summary=evaluation.reason)
        db.add(date)
    db.flush()
    for i, turn in enumerate(transcript, 1):
        owner = a if int(turn["agent_index"]) == 0 else b
        db.add(Message(date_id=date.id, agent_id=owner.agent.id, turn_number=i, message=str(turn["message"])))
    db.commit(); db.refresh(date)
    return date


class DateRequest(BaseModel):
    person_a_id: str
    person_b_id: str
    force: bool = False


class PipelineRequest(BaseModel):
    fixture: bool = False
    force: bool = False


class DirectAnalyzeRequest(BaseModel):
    linkedin_url: str | None = None
    instagram_url: str | None = None
    name: str | None = None



app = FastAPI(title="Agentic Dating API", version="1.0.0")
origins = [os.getenv("FRONTEND_URL", "http://localhost:3000"), "http://127.0.0.1:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "database": "connected"}


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    people = db.scalars(select(Person)).all()
    return {"people": len(people), "agents": db.query(Agent).count(), "dates": db.query(Date).count(), "rankings": db.query(Ranking).count()}


@app.get("/api/people")
def people(db: Session = Depends(get_db)):
    return [person_json(p) for p in db.scalars(select(Person).order_by(Person.name)).all()]


@app.get("/api/people/{person_id}")
@app.get("/api/people/{person_id}/profile")
def get_person(person_id: str, db: Session = Depends(get_db)):
    p = db.get(Person, person_id)
    if not p: raise HTTPException(404, "Person not found")
    return person_json(p)


@app.get("/api/people/{person_id}/rankings")
@app.get("/api/rankings/{person_id}")
def rankings(person_id: str, db: Session = Depends(get_db)):
    if not db.get(Person, person_id): raise HTTPException(404, "Person not found")
    rows = db.scalars(select(Ranking).where(Ranking.person_id == person_id).order_by(Ranking.score.desc())).all()
    out = []
    for row in rows:
        match = db.get(Person, row.matched_person_id); date = db.get(Date, row.date_id)
        out.append({"person": person_json(match), "score": row.score, "dimensions": date.compatibility_json.get("dimensions", {}),
                    "reason": row.overall_reason, "strengths": date.compatibility_json.get("strengths", []),
                    "differences": date.compatibility_json.get("differences", []), "date_id": date.id})
    return out


@app.get("/api/dates/{date_id}")
def get_date(date_id: int, db: Session = Depends(get_db)):
    date = db.get(Date, date_id)
    if not date: raise HTTPException(404, "Date not found")
    a, b = db.get(Person, date.person_a_id), db.get(Person, date.person_b_id)
    compatibility = dict(date.compatibility_json)
    label = compatibility.get("simulation_mode", "Demo Simulation")
    if a.source_type == "fixture" and b.source_type == "fixture":
        compatibility["simulation_mode"] = "Fixture Mode · Demo Simulation"
    else:
        if "llm" in label.casefold() or "gemini" in label.casefold():
            model_name = os.getenv("GEMINI_MODEL", "Gemini")
            compatibility["simulation_mode"] = f"Public-profile simulation · {model_name}"
        else:
            compatibility["simulation_mode"] = "Public-profile simulation · Demo Simulation"
    return {"id": date.id, "status": date.status, "person_a": person_json(a), "person_b": person_json(b),
            "messages": [{"turn_number": m.turn_number, "agent_person_id": db.get(Agent, m.agent_id).person_id,
                          "speaker": db.get(Person, db.get(Agent, m.agent_id).person_id).name, "message": m.message} for m in date.messages],
            "compatibility": compatibility, "summary": date.summary}


@app.post("/api/dates")
async def create_date(request: DateRequest, db: Session = Depends(get_db)):
    a, b = db.get(Person, request.person_a_id), db.get(Person, request.person_b_id)
    if not a or not b: raise HTTPException(404, "Both people must exist")
    if a.id == b.id: raise HTTPException(400, "A person cannot date their own agent")
    try: date = await run_date(db, a, b, force=request.force)
    except ValueError as e: raise HTTPException(409, str(e)) from e
    except RuntimeError as e: raise HTTPException(502, str(e)) from e
    return {"id": date.id, "status": date.status}


@app.post("/api/ingestion/run")
async def ingest(request: PipelineRequest, db: Session = Depends(get_db)):
    from backend.ingestion.apify_source import ApifySource
    from backend.ingestion.fixture_source import FixtureSource
    from backend.ingestion.normalizer import normalize_sources
    from backend.ingestion.playwright_source import PlaywrightSource
    source = PlaywrightSource() if os.getenv("PROFILE_SOURCE", "apify").lower() == "playwright" else ApifySource()
    people_list = db.scalars(select(Person)).all()
    failures = []
    for p in people_list:
        if p.source_type == "fixture":
            p.ingestion_status = "fixture"
        else:
            if p.profile and p.profile.source_data_json and not request.force:
                continue
            linkedin, instagram = await source.fetch_linkedin(p.linkedin_url), await source.fetch_instagram(p.instagram_url)
            normalized = normalize_sources(linkedin, instagram)
            good = [item for item in (linkedin, instagram) if item.status == "success"]
            errors = [item.error for item in (linkedin, instagram) if item.error]
            status = "success" if len(good) == 2 else "partial" if good else next((item.status for item in (linkedin, instagram) if item.status not in ("unavailable", "fixture")), "unavailable")
            p.ingestion_status = status
            profile = p.profile or Profile(person_id=p.id)
            profile.raw_linkedin_text = normalized["linkedin_text"]
            profile.raw_instagram_text = normalized["instagram_text"]
            profile.source_data_json = {"linkedin": normalized["linkedin"], "instagram": normalized["instagram"]}
            if p.profile is None: db.add(profile)
            if errors: failures.append({"id": p.id, "error": "; ".join(errors)})
    db.commit()
    return {"processed": len(people_list), "failures": failures}


@app.get("/api/people/{person_id}/sources")
def get_sources(person_id: str, db: Session = Depends(get_db)):
    person = db.get(Person, person_id)
    if not person: raise HTTPException(404, "Person not found")
    sources = (person.profile.source_data_json or {}) if person.profile else {}
    return {"ingestion_status": person.ingestion_status,
            "sources": [{"platform": key, "source_type": value.get("source_type"), "source_url": value.get("source_url"),
                         "status": value.get("status"), "metadata": value.get("metadata", {}), "error": value.get("error")}
                        for key, value in sources.items() if isinstance(value, dict)]}


@app.get("/api/dates/{date_id}/activity")
def get_date_activity(date_id: int, db: Session = Depends(get_db)):
    date = db.get(Date, date_id)
    if not date: raise HTTPException(404, "Date not found")
    activity = date.compatibility_json.get("activity")
    if activity is None:
        activity = [{"event": "message_generated", "turn_number": m.turn_number,
                     "message": f"Agent {'A' if m.agent_id == date.agent_a_id else 'B'} generated a response."} for m in date.messages]
        activity.append({"event": "compatibility_completed", "message": "Compatibility analysis completed."})
    return {"activity": activity}


@app.post("/api/analysis/run")
async def analyze(request: PipelineRequest, db: Session = Depends(get_db)):
    target_people = [p for p in db.scalars(select(Person)).all()
                     if ((p.source_type == "fixture") == request.fixture)]
    public_people = [] if request.fixture else target_people
    if public_people and not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(503, "GEMINI_API_KEY is required for public-profile simulation; mock fallback is disabled.")
    if public_people and os.getenv("GEMINI_MODEL", "gemini-2.5-flash") != "gemini-2.5-flash":
        raise HTTPException(503, "Public-profile simulation requires GEMINI_MODEL=gemini-2.5-flash.")
    provider = get_provider()
    for p in target_people:
        if p.profile and not request.force: continue
        if p.source_type == "fixture":
            continue
        logger.info("PROFILE_ANALYSIS_STARTED source_type=%s", p.source_type)
        profile = p.profile or Profile(person_id=p.id)
        if profile.raw_linkedin_text or profile.raw_instagram_text:
            try:
                result = await provider.analyze(profile.raw_linkedin_text, profile.raw_instagram_text)
                data = result.model_dump()
                for key, value in data.items(): setattr(profile, "profile_summary" if key == "summary" else key, value)
                profile.analysis_json = {**data, "source_type": p.source_type,
                                         "simulation_mode": "Public-profile simulation"}
                logger.info("PROFILE_ANALYSIS_COMPLETED provider=%s", provider.__class__.__name__)
            except Exception as exc:
                profile.profile_summary = "Analysis could not be completed. Extracted source text is retained; no profile facts were inferred."
                profile.analysis_json = {"status": "analysis_failed", "error": str(exc)[:250]}
        else:
            profile.profile_summary = "No permitted public profile content was available for analysis. No personal details were inferred."
            profile.analysis_json = {"status": p.ingestion_status or "unavailable"}
        if p.profile is None: db.add(profile)
    db.commit(); ensure_agents(db)
    return {"analyzed": db.query(Profile).count(), "agents": db.query(Agent).count(), "provider": "mock" if not os.getenv("GEMINI_API_KEY") else "gemini"}


@app.post("/api/people/analyze")
async def analyze_direct_profile(request: DirectAnalyzeRequest, db: Session = Depends(get_db)):
    linkedin_url = (request.linkedin_url or "").strip()
    instagram_url = (request.instagram_url or "").strip()
    if not linkedin_url and not instagram_url:
        raise HTTPException(400, "At least one profile URL (LinkedIn or Instagram) is required.")

    import uuid
    person_id = f"live-{uuid.uuid4().hex[:8]}"
    name = (request.name or "").strip()
    if not name:
        if linkedin_url and "in/" in linkedin_url:
            handle = linkedin_url.split("in/")[1].strip("/").split("?")[0].replace("-", " ").title()
            name = handle or "Live Profile"
        elif instagram_url and "instagram.com/" in instagram_url:
            handle = instagram_url.split("instagram.com/")[1].strip("/").split("?")[0]
            name = handle or "Live Profile"
        else:
            name = "Live Profile"

    person = Person(
        id=person_id,
        name=name,
        linkedin_url=linkedin_url or None,
        instagram_url=instagram_url or None,
        source_type="public_profile_simulation",
        ingestion_status="processing"
    )
    db.add(person)
    db.commit()

    from backend.ingestion.apify_source import ApifySource
    from backend.ingestion.normalizer import normalize_sources
    from backend.ingestion.playwright_source import PlaywrightSource

    source = PlaywrightSource() if os.getenv("PROFILE_SOURCE", "apify").lower() == "playwright" else ApifySource()
    linkedin_res = await source.fetch_linkedin(linkedin_url if linkedin_url else None)
    instagram_res = await source.fetch_instagram(instagram_url if instagram_url else None)
    normalized = normalize_sources(linkedin_res, instagram_res)

    good = [item for item in (linkedin_res, instagram_res) if item.status == "success"]
    status = "success" if len(good) == 2 else "partial" if good else next((item.status for item in (linkedin_res, instagram_res) if item.status not in ("unavailable", "fixture")), "unavailable")
    person.ingestion_status = status

    profile = Profile(person_id=person.id)
    profile.raw_linkedin_text = normalized["linkedin_text"]
    profile.raw_instagram_text = normalized["instagram_text"]
    profile.source_data_json = {"linkedin": normalized["linkedin"], "instagram": normalized["instagram"]}

    provider = get_provider()
    if normalized["linkedin_text"] or normalized["instagram_text"]:
        try:
            result = await provider.analyze(normalized["linkedin_text"], normalized["instagram_text"])
            data = result.model_dump()
            for key, value in data.items():
                setattr(profile, "profile_summary" if key == "summary" else key, value)
            profile.analysis_json = {
                **data,
                "source_type": "public_profile_simulation",
                "simulation_mode": f"Public-profile simulation · {getattr(provider, 'model', os.getenv('GEMINI_MODEL', 'Gemini'))}"
            }
        except Exception as exc:
            profile.profile_summary = f"Analysis attempted via {provider.simulation_mode}. Extracted source text is retained."
            profile.analysis_json = {"status": "analysis_failed", "error": str(exc)[:250]}
    else:
        profile.profile_summary = f"Profile registered via public URLs. Ingestion status: {status}."
        profile.analysis_json = {"status": status}

    db.add(profile)
    db.commit()
    ensure_agents(db)

    other_public = db.scalars(select(Person).where(Person.source_type == "public_profile_simulation", Person.id != person.id)).first()
    if not other_public:
        partner_id = f"live-partner-{uuid.uuid4().hex[:6]}"
        partner = Person(
            id=partner_id,
            name="Simulated Partner",
            source_type="public_profile_simulation",
            ingestion_status="success"
        )
        partner_profile = Profile(
            person_id=partner_id,
            profession="Architect & Explorer",
            interests=["design", "travel", "coffee"],
            hobbies=["photography", "sketching"],
            lifestyle=["city walks", "art exhibitions"],
            conversation_topics=["design", "travel"],
            profile_summary="Simulated partner for public-profile agent simulation."
        )
        db.add(partner)
        db.add(partner_profile)
        db.commit()
        ensure_agents(db)
        other_public = partner

    try:
        date = await run_date(db, person, other_public, force=True, provider=provider)
        dims = date.compatibility_json.get("dimensions", {"shared_interests": 75, "lifestyle": 75, "conversation": 75, "goals": 75})
        db.add(Ranking(
            person_id=person.id,
            matched_person_id=other_public.id,
            date_id=date.id,
            score=date.compatibility_score or 75.0,
            shared_interests_score=dims.get("shared_interests", 75),
            lifestyle_score=dims.get("lifestyle", 75),
            conversation_score=dims.get("conversation", 75),
            goals_score=dims.get("goals", 75),
            overall_reason=date.summary or "Live agent simulation completed."
        ))
        db.commit()
    except Exception as e:
        logger.warning("Live date creation skipped: %s", e)

    return person_json(person)


@app.post("/api/rankings/generate")
async def generate_rankings(request: PipelineRequest, db: Session = Depends(get_db)):
    all_people = [p for p in db.scalars(select(Person)).all() if p.profile and ((p.source_type == "fixture") == request.fixture)]
    ensure_agents(db)
    made = 0
    for a in all_people:
        candidates = sorted((b for b in all_people if b.id != a.id), key=lambda b: (-candidate_score(a, b), b.id))[:4]
        for b in candidates:
            try:
                date = await run_date(db, a, b, force=request.force, fixture=request.fixture)
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
            except RuntimeError as exc:
                raise HTTPException(502, str(exc)) from exc
            old = db.scalar(select(Ranking).where(Ranking.person_id == a.id, Ranking.matched_person_id == b.id))
            if old and not request.force: continue
            if old: db.delete(old); db.flush()
            dims = date.compatibility_json["dimensions"]
            db.add(Ranking(person_id=a.id, matched_person_id=b.id, date_id=date.id, score=date.compatibility_score,
                           shared_interests_score=dims["shared_interests"], lifestyle_score=dims["lifestyle"],
                           conversation_score=dims["conversation"], goals_score=dims["goals"], overall_reason=date.summary))
            made += 1
    db.commit()
    logger.info("RANKING_COMPLETED created=%s", made)
    return {"rankings_created": made, "people_processed": len(all_people), "dates": db.query(Date).count()}

