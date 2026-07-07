from app.imports.cover_guard import CoverCandidate, CoverGuardInput, CoverGuardResult, choose_cover_candidate


class RejectingGuard:
    async def validate(self, candidate: CoverCandidate) -> CoverGuardResult:
        return CoverGuardResult(accepted=False, reason="not food")


class AcceptingGuard:
    async def validate(self, candidate: CoverCandidate) -> CoverGuardResult:
        return CoverGuardResult(accepted=True, reason="food")


async def test_cover_guard_black_box_returns_candidate_when_disabled():
    candidate = CoverCandidate(source_ref="upload_0", crop=None)

    result = await choose_cover_candidate(
        CoverGuardInput(
            candidate=candidate,
            accepted_image_refs=["upload_0"],
            fallback_candidates=[],
            enabled=False,
            max_fallback_candidates=0,
        ),
        guard=RejectingGuard(),
    )

    assert result == candidate


async def test_cover_guard_black_box_rejects_and_uses_fallback_when_enabled():
    primary = CoverCandidate(source_ref="upload_0", crop=None)
    fallback = CoverCandidate(source_ref="upload_1", crop=None)

    result = await choose_cover_candidate(
        CoverGuardInput(
            candidate=primary,
            accepted_image_refs=["upload_0", "upload_1"],
            fallback_candidates=[fallback],
            enabled=True,
            max_fallback_candidates=1,
        ),
        guard=AcceptingGuard(),
    )

    assert result == primary


async def test_cover_guard_black_box_returns_none_for_unaccepted_source():
    candidate = CoverCandidate(source_ref="missing", crop=None)

    result = await choose_cover_candidate(
        CoverGuardInput(
            candidate=candidate,
            accepted_image_refs=["upload_0"],
            fallback_candidates=[],
            enabled=False,
            max_fallback_candidates=0,
        ),
        guard=AcceptingGuard(),
    )

    assert result is None
