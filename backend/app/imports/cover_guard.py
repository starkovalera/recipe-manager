from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CoverCandidate:
    source_ref: str
    crop: dict[str, float] | None = None


@dataclass(frozen=True)
class CoverGuardInput:
    candidate: CoverCandidate | None
    accepted_image_refs: list[str]
    fallback_candidates: list[CoverCandidate]
    enabled: bool
    max_fallback_candidates: int


@dataclass(frozen=True)
class CoverGuardResult:
    accepted: bool
    reason: str | None = None


# Guard provider seam is intentionally unused in production while
# ENABLE_COVER_CANDIDATE_GUARD stays default-off. Keep this interface isolated
# so the experimental guard can be removed or replaced without touching import
# materialization.
class CoverCandidateGuard(Protocol):
    async def validate(self, candidate: CoverCandidate) -> CoverGuardResult:
        raise NotImplementedError


async def choose_cover_candidate(
    guard_input: CoverGuardInput,
    guard: CoverCandidateGuard | None = None,
) -> CoverCandidate | None:
    accepted_refs = set(guard_input.accepted_image_refs)
    candidate = guard_input.candidate
    if candidate is None or candidate.source_ref not in accepted_refs:
        return None
    if not guard_input.enabled:
        return candidate
    if guard is None:
        return candidate
    validation = await guard.validate(candidate)
    if validation.accepted:
        return candidate
    for fallback in guard_input.fallback_candidates[: guard_input.max_fallback_candidates]:
        if fallback.source_ref not in accepted_refs:
            continue
        fallback_validation = await guard.validate(fallback)
        if fallback_validation.accepted:
            return fallback
    return None
