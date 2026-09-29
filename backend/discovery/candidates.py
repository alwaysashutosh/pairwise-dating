from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse, urlunparse
import re


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str


@dataclass
class PublicProfileCandidate:
    name: str
    linkedin_url: str
    instagram_url: str
    linkedin_title: str
    linkedin_snippet: str
    instagram_title: str
    instagram_snippet: str
    identity_evidence_terms: int


class CandidateValidator:
    LINKEDIN_RESERVED = {"company", "jobs", "feed", "search", "posts", "pulse", "learning", "events"}
    INSTAGRAM_RESERVED = {"p", "reel", "reels", "stories", "explore", "accounts", "tags", "direct", "about", "developer", "web"}

    @staticmethod
    def canonical_profile_url(url: str, platform: str) -> str | None:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower().removeprefix("www.")
        expected = "linkedin.com" if platform == "linkedin" else "instagram.com"
        if parsed.scheme != "https" or not (host == expected or host.endswith("." + expected)):
            return None
        segments = [part for part in parsed.path.split("/") if part]
        reserved = CandidateValidator.LINKEDIN_RESERVED if platform == "linkedin" else CandidateValidator.INSTAGRAM_RESERVED
        if platform == "linkedin":
            if len(segments) != 2 or segments[0].lower() != "in" or segments[1].lower() in reserved:
                return None
            path = f"/in/{segments[1]}"
        else:
            if len(segments) != 1 or segments[0].lower() in reserved or segments[0].startswith("#"):
                return None
            path = f"/{segments[0]}"
        return urlunparse(("https", expected, path, "", "", ""))

    @staticmethod
    def unwrap_search_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.hostname and parsed.hostname.endswith("google.com"):
            query = parse_qs(parsed.query)
            return (query.get("q") or query.get("url") or [url])[0]
        return url

    @staticmethod
    def extract_results(value) -> list[SearchResult]:
        results: list[SearchResult] = []
        visited: set[int] = set()

        def walk(node):
            if isinstance(node, list):
                for item in node:
                    walk(item)
                return
            if not isinstance(node, dict) or id(node) in visited:
                return
            visited.add(id(node))
            raw_url = next((node.get(key) for key in ("url", "link", "href", "profileUrl", "resultUrl") if isinstance(node.get(key), str)), None)
            title = next((node.get(key) for key in ("title", "name", "headline") if isinstance(node.get(key), str)), "")
            snippet = next((node.get(key) for key in ("snippet", "description", "text", "content") if isinstance(node.get(key), str)), "")
            if raw_url:
                results.append(SearchResult(CandidateValidator.unwrap_search_url(raw_url), title.strip(), snippet.strip()))
            for key in ("organicResults", "organic_results", "results", "items", "organic", "data", "searchResults"):
                if key in node:
                    walk(node[key])

        walk(value)
        return results


class IdentityMatcher:
    COMMON = {"the", "and", "for", "with", "from", "linkedin", "instagram", "profile", "official", "engineer",
              "developer", "software", "machine", "learning", "data", "science", "scientist", "product", "manager",
              "designer", "founder", "director", "senior", "lead", "based", "work", "works", "company", "people"}

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {token for token in re.findall(r"[^\W_]+", value.casefold()) if len(token) > 1}

    @classmethod
    def candidate_name(cls, title: str) -> str:
        title = re.sub(r"\s*[|–—-]\s*LinkedIn.*$", "", title, flags=re.IGNORECASE).strip()
        return re.split(r"\s+[|–—-]\s+", title, maxsplit=1)[0].strip()

    @classmethod
    def match(cls, name: str, linkedin_context: str, instagram_context: str) -> set[str]:
        name_tokens = cls._tokens(name)
        instagram_tokens = cls._tokens(instagram_context)
        if len(name_tokens) < 2 or not name_tokens.issubset(instagram_tokens):
            return set()
        linkedin_tokens = cls._tokens(linkedin_context) - name_tokens - cls.COMMON
        instagram_context_tokens = instagram_tokens - name_tokens - cls.COMMON
        return linkedin_tokens & instagram_context_tokens
