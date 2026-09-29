from __future__ import annotations

import logging

from backend.llm import CompatibilityEvaluation, LLMProvider, NormalizedProfile

logger = logging.getLogger(__name__)
WEIGHTS = {"shared_interests": 0.30, "lifestyle": 0.25, "conversation": 0.25, "goals": 0.20}


def weighted_score(evaluation: CompatibilityEvaluation) -> int:
    return round(sum(getattr(evaluation, dimension) * weight for dimension, weight in WEIGHTS.items()))


async def evaluate_compatibility(provider: LLMProvider, profile_a: NormalizedProfile, profile_b: NormalizedProfile,
                                 conversation: list[dict[str, str]]) -> tuple[CompatibilityEvaluation, int]:
    logger.info("COMPATIBILITY_ANALYSIS_STARTED")
    result = await provider.evaluate_compatibility(profile_a, profile_b, conversation)
    score = weighted_score(result)
    logger.info("COMPATIBILITY_ANALYSIS_COMPLETED score=%s", score)
    return result, score
