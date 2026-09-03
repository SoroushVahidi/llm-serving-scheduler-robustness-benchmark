from robustbench.real_llm.engineering_fixture import (
    ENGINEERING_SMOKE_ONLY,
    NOT_FOR_PAPER_EVIDENCE,
    build_engineering_fixture,
    fixture_manifest,
)


def test_fixture_is_stamped_engineering_only():
    assert ENGINEERING_SMOKE_ONLY is True
    assert NOT_FOR_PAPER_EVIDENCE is True


def test_fixture_is_small_and_deterministic():
    a = build_engineering_fixture()
    b = build_engineering_fixture()
    assert [r.request_id for r in a] == [r.request_id for r in b]
    assert [r.prompt for r in a] == [r.prompt for r in b]
    assert 1 < len(a) <= 10


def test_fixture_covers_required_variation():
    reqs = build_engineering_fixture()
    groups = {r.concurrency_group for r in reqs}
    assert "single" in groups
    assert "concurrent" in groups
    assert sum(1 for r in reqs if r.concurrency_group == "concurrent") >= 2
    lengths = {len(r.prompt) for r in reqs if r.concurrency_group == "single"}
    assert len(lengths) >= 2  # at least one short and one longer prefill


def test_fixture_request_ids_are_unique():
    reqs = build_engineering_fixture()
    ids = [r.request_id for r in reqs]
    assert len(ids) == len(set(ids))


def test_fixture_manifest_matches_fixture():
    manifest = fixture_manifest()
    reqs = build_engineering_fixture()
    assert manifest["request_count"] == len(reqs)
    assert manifest["request_ids"] == [r.request_id for r in reqs]
    assert manifest["ENGINEERING_SMOKE_ONLY"] is True
    assert manifest["NOT_FOR_PAPER_EVIDENCE"] is True
