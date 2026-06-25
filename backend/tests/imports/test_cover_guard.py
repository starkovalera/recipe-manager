from app.imports.cover_guard import CoverCandidate, CoverGuardInput, CoverGuardResult, choose_cover_candidate


class RejectingGuard:
    async def validate(self, candidate: CoverCandidate) -> CoverGuardResult:
        return CoverGuardResult(accepted=False, reason="not food")


class AcceptingGuard:
    async def validate(self, candidate: CoverCandidate) -> CoverGuardResult:
        return CoverGuardResult(accepted=True, reason="food")


async def test_cover_guard_black_box_returns_candidate_when_disabled():
    candidate = CoverCandidate(sourceRef="upload_0", crop=None)

    result = await choose_cover_candidate(
        CoverGuardInput(candidate=candidate, acceptedImageRefs=["upload_0"], fallbackCandidates=[], enabled=False, maxFallbackCandidates=0),
        guard=RejectingGuard(),
    )

    assert result == candidate


async def test_cover_guard_black_box_rejects_and_uses_fallback_when_enabled():
    primary = CoverCandidate(sourceRef="upload_0", crop=None)
    fallback = CoverCandidate(sourceRef="upload_1", crop=None)

    result = await choose_cover_candidate(
        CoverGuardInput(candidate=primary, acceptedImageRefs=["upload_0", "upload_1"], fallbackCandidates=[fallback], enabled=True, maxFallbackCandidates=1),
        guard=AcceptingGuard(),
    )

    assert result == primary


async def test_cover_guard_black_box_returns_none_for_unaccepted_source():
    candidate = CoverCandidate(sourceRef="missing", crop=None)

    result = await choose_cover_candidate(
        CoverGuardInput(candidate=candidate, acceptedImageRefs=["upload_0"], fallbackCandidates=[], enabled=False, maxFallbackCandidates=0),
        guard=AcceptingGuard(),
    )

    assert result is None
