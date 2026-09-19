"""Conservative report parsing: ambiguous citation associations stay unresolved."""

from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

from pypdf import PdfReader


def external_url(value):
    value = value.strip().rstrip(".,;")
    try:
        p = urlsplit(value)
        return (
            p.scheme in {"http", "https"}
            and bool(p.hostname)
            and p.hostname not in {"chatgpt.com", "claude.ai", "grok.com"}
        )
    except ValueError:
        return False


def field(block, label):
    match = re.search(r"(?im)^\s*(?:\d+\.\s*)?" + label + r"[^:\n]*:\s*", block)
    if not match:
        return ""
    remaining = block[match.end() :]
    boundary = re.search(
        r"(?im)^\s*(?:\d+\.\s*)?(?:Link|Author|Exact|Supporting|Locator|Market|Important|Limitations|Source vs|What the source|Related open|Citation)\b[^\n]*:",
        remaining,
    )
    return remaining[: boundary.start() if boundary else len(remaining)].strip()


def candidates(pages, annotation_urls):
    text = "\n".join(pages)
    starts = list(re.finditer(r"(?im)^\s*Source\s+\d+\s*[\u2014\u2013-]", text))
    rows = []
    if starts:
        for i, start in enumerate(starts):
            block = text[
                start.start() : starts[i + 1].start() if i + 1 < len(starts) else len(text)
            ]
            # Stop at report synthesis, not at numbered fields within source sections.
            end = re.search(
                r"(?im)^\s*(?:\d+\.\s*)?(?:Cross-source synthesis|Recommendations|What was not used|Candidate exits for testing)\b",
                block,
            )
            if end:
                block = block[: end.start()]
            link = field(block, "Link")
            url = "".join(link.split()) if link else ""
            if not external_url(url):
                url = ""
            rule = " ".join(field(block, "Exact").split())
            quoted = field(block, "Supporting")
            quote = re.search(r'[“"]([^”"]+)[”"]', quoted, re.S)
            locator = f"Source block {i + 1}; " + " ".join(field(block, "Locator").split())
            rows.append(
                dict(
                    url=url,
                    claim=rule or block.strip().splitlines()[0].strip(),
                    quote=" ".join(quote[1].split()) if quote else "",
                    locator=locator,
                    context=block,
                )
            )
    else:
        urls = sorted({u for u in annotation_urls if external_url(u)})
        urls += sorted(set(re.findall(r"https?://[^\s<>]+", text)) - set(urls))
        urls = [u for u in urls if external_url(u)]
        for u in dict.fromkeys(urls):
            rows.append(
                dict(
                    url=u,
                    claim="Citation lead: claim association requires review.",
                    quote="",
                    locator="Report hyperlink/reference; exact association unresolved",
                    context=text,
                )
            )
        if not rows:
            rows.append(
                dict(
                    url="",
                    claim="Unstructured research lead: claim association requires review.",
                    quote="",
                    locator="Full extracted report",
                    context=text,
                )
            )
    # Preserve supplementary/excluded references as leads, never silently attach
    # their claims to the primary source block (e.g. a book's GitHub implementation).
    extras = list(annotation_urls) + re.findall(r"https?://[^\s<>]+", text)
    extras += [
        "https://doi.org/" + d.rstrip(".,;)") for d in re.findall(r"10\.\d{4,9}/[^\s)]+", text)
    ]
    known = [r["url"].rstrip("/") for r in rows if r["url"]]
    for raw in extras:
        url = raw.rstrip(".,;)")
        if not external_url(url) or any(k.startswith(url.rstrip("/")) for k in known):
            continue
        known.append(url.rstrip("/"))
        rows.append(
            dict(
                url=url,
                claim="Supplementary citation lead: claim association requires review.",
                quote="",
                locator="Supplementary/excluded reference in full report",
                context=text,
            )
        )
    return rows


def import_candidates(store, path, *, provider, research_id=""):
    report = store.import_report(path, provider=provider)
    if report["extraction_status"] != "extracted":
        return dict(
            report=report,
            claims=[],
            warning="Native extraction incomplete; recover text before claim parsing",
        )
    pages = json.loads(store.checked_report_text(report))
    reader = PdfReader(report["original_path"])
    urls = []
    for page in reader.pages:
        for ref in page.get("/Annots", []):
            action = ref.get_object().get("/A")
            if action and action.get("/URI"):
                urls.append(str(action["/URI"]))
    claims = [
        store.add_claim(report["id"], research_id=research_id, **c) for c in candidates(pages, urls)
    ]
    return dict(
        report=report,
        claims=claims,
        warning="Candidate extraction only; no source-scope acceptance",
    )
