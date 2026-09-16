from quant_brain.research.live_worker import (
    build_research_prompt,
    validate_research_payload,
)


def snapshots():
    return [
        {
            "source_id": "S1",
            "title": "Official RSI documentation",
            "url": "https://example.com/rsi",
            "source_quality": "primary",
            "text": "The source defines RSI entries but does not define an exit rule or maximum holding period.",
            "snapshot_path": "brain/00_Inbox/Source_Snapshots/RQ-test/S1.md",
            "content_hash": "a" * 64,
        },
        {
            "source_id": "S2",
            "title": "Anonymous strategy video",
            "url": "https://video.example/secret",
            "source_quality": "discovery-only",
            "text": "The description promises 95 percent wins but provides no rules, data, or costs.",
            "snapshot_path": "brain/00_Inbox/Source_Snapshots/RQ-test/S2.md",
            "content_hash": "b" * 64,
        },
    ]


def valid_payload():
    return {
        "research_id": "RQ-test",
        "decision": "needs_more_work",
        "sources": [
            {
                "source_id": "S1",
                "title": "Official RSI documentation",
                "url": "https://example.com/rsi",
                "source_type": "docs",
                "source_quality": "primary",
                "main_claim": "The evidence does not define an exit or holding period.",
                "evidence_quote": "does not define an exit rule or maximum holding period",
                "possible_strategy_rule": "",
                "risks": ["Exit rules remain unresolved."],
                "confidence": "high",
                "asset_classes": ["equities"],
                "data_required": ["daily close"],
                "data_access": "available-now",
                "mvp_testable": False,
            },
            {
                "source_id": "S2",
                "title": "Anonymous strategy video",
                "url": "https://video.example/secret",
                "source_type": "video",
                "source_quality": "discovery-only",
                "main_claim": "The performance claim is not reproducible.",
                "evidence_quote": "provides no rules, data, or costs",
                "possible_strategy_rule": "",
                "risks": ["Untraceable performance claim."],
                "confidence": "low",
                "asset_classes": [],
                "data_required": [],
                "data_access": "not-realistic",
                "mvp_testable": False,
            },
        ],
        "open_questions": ["Which source supports an exit rule?"],
        "curator_recommendation": "needs_more_work",
    }


def test_live_worker_prompt_contains_bounded_sources_and_no_web_authority():
    prompt = build_research_prompt(
        "RQ-test",
        "Find an RSI exit rule",
        snapshots(),
    )

    assert "RQ-test" in prompt
    assert "Find an RSI exit rule" in prompt
    assert "[S1]" in prompt and "[S2]" in prompt
    assert "Do not invent URLs" in prompt
    assert "Evidence quotes must appear verbatim" in prompt


def test_live_worker_prompt_bounds_large_snapshot_context():
    large = []
    for index in range(5):
        large.append(
            {
                "source_id": f"S{index + 1}",
                "title": f"Source {index + 1}",
                "url": f"https://example.com/{index + 1}",
                "source_quality": "primary",
                "text": "evidence " * 5000,
                "snapshot_path": f"snapshot-{index + 1}.md",
                "content_hash": str(index) * 64,
            }
        )

    prompt = build_research_prompt("RQ-test", "Question", large)

    assert len(prompt) < 40000
    assert prompt.count("[TRUNCATED]") == 5


def test_validate_research_payload_accepts_exact_quotes_and_known_sources():
    result = validate_research_payload("RQ-test", valid_payload(), snapshots())

    assert result["passed"] is True
    assert result["failures"] == []


def test_validate_research_payload_rejects_invented_quote_and_unknown_source():
    payload = valid_payload()
    payload["sources"][0]["evidence_quote"] = "This quote was invented."
    payload["sources"][1]["source_id"] = "S99"

    result = validate_research_payload("RQ-test", payload, snapshots())

    assert result["passed"] is False
    failures = " ".join(result["failures"]).lower()
    assert "quote" in failures
    assert "unknown source" in failures
