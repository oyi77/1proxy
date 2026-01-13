from app.db_models import CandidateSource


def test_candidate_source_defaults():
    # SQLAlchemy models don't apply 'default' on __init__ without a session
    # So we check the Column configuration instead
    assert CandidateSource.status.default.arg == "pending"
    assert CandidateSource.confidence_score.default.arg == 0
    assert CandidateSource.proxies_found_count.default.arg == 0
    assert CandidateSource.fail_count.default.arg == 0

    candidate = CandidateSource(
        url="http://example.com/proxies.txt", discovery_method="github"
    )
    # Explicitly check what we set
    assert candidate.url == "http://example.com/proxies.txt"
    assert candidate.discovery_method == "github"


def test_candidate_source_fields():
    candidate = CandidateSource(
        url="http://test.com",
        domain="test.com",
        discovery_method="ai",
        status="approved",
        confidence_score=90,
        meta_data={"summary": "found by ai"},
    )

    assert candidate.domain == "test.com"
    assert candidate.status == "approved"
    assert candidate.confidence_score == 90
    assert candidate.meta_data == {"summary": "found by ai"}
