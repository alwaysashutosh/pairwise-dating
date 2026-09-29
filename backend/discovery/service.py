from __future__ import annotations

from backend.discovery.apify_google_search import ApifyGoogleSearchSource
from backend.discovery.candidates import CandidateValidator, IdentityMatcher, PublicProfileCandidate


LINKEDIN_QUERIES = (
    'site:linkedin.com/in "software engineer"',
    'site:linkedin.com/in "AI engineer"',
    'site:linkedin.com/in "machine learning engineer"',
    'site:linkedin.com/in "data scientist"',
    'site:linkedin.com/in "product manager"',
    'site:linkedin.com/in "software developer"',
    'site:linkedin.com/in "startup founder"',
)


class CandidateDiscoveryService:
    def __init__(self, search_source: ApifyGoogleSearchSource):
        self.search_source = search_source

    async def discover(self, limit: int, search_limit: int = 20) -> tuple[list[PublicProfileCandidate], list[str]]:
        if not 1 <= limit <= 25:
            raise ValueError("Discovery limit must be between 1 and 25.")
        linkedin_by_url = {}
        failures: list[str] = []
        target_pool = min(75, max(limit * 3, limit + 5))
        for query_index, query in enumerate(LINKEDIN_QUERIES):
            try:
                items = await self.search_source.search(query, limit=search_limit)
            except (RuntimeError, ValueError) as exc:
                failures.append(str(exc))
                if not linkedin_by_url:
                    continue
                break
            for item in CandidateValidator.extract_results(items):
                url = CandidateValidator.canonical_profile_url(item.url, "linkedin")
                name = IdentityMatcher.candidate_name(item.title)
                if url and len(IdentityMatcher._tokens(name)) >= 2:
                    linkedin_by_url.setdefault(url, (name, item.title, item.snippet))
            if query_index >= 2 and len(linkedin_by_url) >= target_pool:
                break

        candidates: list[PublicProfileCandidate] = []
        seen_instagram: set[str] = set()
        for linkedin_url, (name, linkedin_title, linkedin_snippet) in linkedin_by_url.items():
            if len(candidates) >= limit:
                break
            query = f'site:instagram.com "{name}"'
            try:
                items = await self.search_source.search(query, limit=search_limit)
            except (RuntimeError, ValueError) as exc:
                failures.append(str(exc))
                continue
            linkedin_context = f"{linkedin_title} {linkedin_snippet}"
            for result in CandidateValidator.extract_results(items):
                instagram_url = CandidateValidator.canonical_profile_url(result.url, "instagram")
                if not instagram_url or instagram_url in seen_instagram:
                    continue
                instagram_context = f"{result.title} {result.snippet}"
                evidence = IdentityMatcher.match(name, linkedin_context, instagram_context)
                if len(evidence) < 2:
                    continue
                seen_instagram.add(instagram_url)
                candidates.append(PublicProfileCandidate(name=name, linkedin_url=linkedin_url,
                    instagram_url=instagram_url, linkedin_title=linkedin_title,
                    linkedin_snippet=linkedin_snippet, instagram_title=result.title,
                    instagram_snippet=result.snippet, identity_evidence_terms=len(evidence)))
                break
        return candidates[:limit], failures
