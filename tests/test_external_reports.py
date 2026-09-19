from quant_brain.research import external_reports as parser


def test_structured_sources_preserve_rule_quote_context_and_wrapped_url():
    text = """Source 1 — Example
1. Link: https://example.org/a-\nlong-page
2. Author/institution: Author
3. Exact exit rule (as stated): Exit when RSI > 50 or after 10 trading days.
4. Supporting quotation (verbatim): “Exit when RSI > 50 or after 10 trading days.”
5. Locator: Exit section
6. Market/frequency: stocks daily
7. Limitations: Not an ETF test.
Source 2 — Book (2009)
Citation: Author, Book (2009).
Exact exit rule: Exit above average.
Related open implementation (not primary evidence): https://github.com/some/repo
Locator: Chapter not verified.
"""
    rows = parser.candidates([text], [])
    assert len(rows) == 3  # two source blocks plus the secondary implementation lead
    assert rows[2]["quote"] == "" and "association" in rows[2]["claim"]
    assert rows[0]["url"] == "https://example.org/a-long-page"
    assert rows[0]["quote"] == "Exit when RSI > 50 or after 10 trading days."
    assert "Not an ETF test" in rows[0]["context"]
    assert rows[1]["url"] == ""  # implementation is NOT original book


def test_unstructured_report_links_are_leads_not_invented_quote_pairs():
    rows = parser.candidates(
        ["An oversold exit rule uses RSI > 70."], ["https://example.org/article"]
    )
    assert rows and all(not x["quote"] for x in rows)
    assert any("RSI > 70" in x["context"] for x in rows)
    assert all("association" in x["claim"] for x in rows)


def test_provider_links_not_external_evidence():
    rows = parser.candidates(
        ["Download the report."], ["https://chatgpt.com/?utm_src=x", "sandbox:/mnt/data/file.pdf"]
    )
    assert len(rows) == 1 and rows[0]["url"] == ""
