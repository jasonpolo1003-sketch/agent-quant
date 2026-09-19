"""Snapshot attribution and explicit scope review; no promotion side effects."""

from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from quant_brain.curation.executor import promotion_block_reason
from quant_brain.discovery.acquisition import assess_fetched_content
from quant_brain.discovery.live_discovery import MAX_FETCH_BYTES, jina_fetch
from quant_brain.research.schema import RawResearchSource


def normalized(text):
    # Deliberately preserve negation, inequalities, numbers and punctuation.
    return " ".join(str(text).replace("\u00ad", "").split())


# Characters that join two digits into one value: decimals and thousands
# separators, percentages, ratios, times, and hyphenated figures. A quote that
# stops on either side of one of these is holding half a number.
#
# The typographic forms are here for the same reason the digit test is
# Unicode-aware: a source that writes its decimal as a middle dot or its range
# with an en dash would otherwise re-open the truncation this guards against.
# The em dash (U+2014) is deliberately absent -- it is sentence punctuation far
# more often than a range, and including it wrongly refused "It rose 20" quoted
# from "It rose 20 -- then fell." They are named by code point rather than
# pasted because these glyphs are indistinguishable from ASCII in a diff.
_NUMBER_JOINERS = ".,:/%-" + "".join(map(chr, (0x00B7, 0x2212, 0x2013, 0x2012, 0x2010, 0x2044)))


def _alnum(char):
    # Unicode-aware on purpose: fullwidth and Arabic-Indic digits are digits
    # too, and an ASCII-only class would let the same truncation through in a
    # different script.
    return char.isalnum()


def _severs_token(left, right):
    """True when a span edge cuts through a word or a number.

    Symmetric by construction. An earlier version guarded only a quote *ending*
    in "." or "," followed by a digit, which left the mirror case wide open:
    "Threshold is 1" out of "Threshold is 1,250" passed every gate while
    misstating the value 1250-fold, and "Win rate 0" out of "0.55" asserted a
    zero win rate. The more misleading truncation was the one being accepted.
    """
    if _alnum(left) and _alnum(right):
        return True
    # A separator only joins a number when digits sit on both sides of it, so
    # "Hold for 10 days," followed by a space stays a clean quotation.
    if left in _NUMBER_JOINERS:
        return right.isdigit()
    if right in _NUMBER_JOINERS:
        return left.isdigit()
    return False


def source_span(body, quote):
    """Return where `quote` sits in `body` on token boundaries, else None.

    Raw substring containment accepted a changed numeric threshold: "Exit when
    RSI > 5" sits inside "Exit when RSI > 50 or after 10 trading days.", which
    passed the exact-quotation gate while asserting a rule the source never
    states, and carried that fabricated span to the curator handoff as
    verbatim evidence. Truncation at either edge did it.

    Quoting a complete fragment stays legitimate -- "Exit when RSI > 50" ends
    on a boundary and still matches. Only a severed token is refused. This is
    text matching alone; whether the full rule and its context are supported
    remains a separate judgement made elsewhere.
    """
    if not quote:
        return None
    start = body.find(quote)
    while start != -1:
        end = start + len(quote)
        if (start == 0 or not _severs_token(body[start - 1], quote[0])) and (
            end == len(body) or not _severs_token(quote[-1], body[end])
        ):
            return start
        start = body.find(quote, start + 1)
    return None


def public_url(url):
    p = urlsplit(url)
    host = p.hostname or ""
    if (
        p.scheme not in {"https", "http"}
        or p.username
        or p.password
        or p.port not in {None, 80, 443}
    ):
        return False
    if "." not in host or host.endswith((".local", ".localhost", ".internal", ".test")):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return True


def load(store, table, key):
    if table not in {"claims", "reports", "fetches", "evaluations"}:
        raise ValueError("invalid table")
    with store.connection() as c:
        row = c.execute(f"SELECT data FROM {table} WHERE id=?", (key,)).fetchone()
    if not row:
        raise ValueError(f"unknown {table} id")
    return json.loads(row[0])


def snapshot_text(store, item):
    from .external_intake import digest, safe_target

    if not item.get("snapshot_path"):
        return ""
    p = safe_target(store.root, Path(item["snapshot_path"]))
    if not p.exists() or digest(p.read_bytes()) != item["content_sha256"]:
        raise ValueError("snapshot integrity failure")
    return p.read_text(encoding="utf-8")


def verify_claim(store, claim_id, *, allow_network=False, fetch=None, force=False):
    from .external_intake import digest, now, safe_target

    claim = load(store, "claims", claim_id)
    with store.connection() as c:
        target = c.execute("SELECT url FROM targets WHERE id=?", (claim["target_id"],)).fetchone()
        previous = c.execute(
            "SELECT id,data FROM fetches WHERE target_id=? ORDER BY id DESC LIMIT 1",
            (claim["target_id"],),
        ).fetchone()
    url = target[0]
    if force and not allow_network:
        raise ValueError("force refresh requires --allow-network")
    if previous and not force:
        source = json.loads(previous[1])
        body = snapshot_text(store, source)
        fetch_id = previous[0]
    else:
        if public_url(url) and not allow_network:
            return dict(
                claim_id=claim_id, outcome="not_attempted", reason="network permission required"
            )
        body = ""
        source = dict(
            target_id=claim["target_id"],
            url=url,
            attempted_at=now(),
            outcome="blocked",
            reason="No public source URL; obtain original citation",
            snapshot_path=None,
        )
        if public_url(url):
            try:
                body = str((fetch or jina_fetch)(url)["content"])
                if len(body.encode("utf-8")) >= MAX_FETCH_BYTES:
                    raise ValueError("source reached fetch size cap; completeness unknown")
                assessment = assess_fetched_content(url, body)
                wall = bool(
                    re.search(
                        r"captcha|verify you are human|access denied|cloudflare challenge",
                        body,
                        re.I,
                    )
                )
                source["outcome"] = (
                    "access_blocked"
                    if wall
                    or (
                        assessment
                        and any(
                            x in assessment.signals
                            for x in (
                                "thin-content",
                                "empty-content",
                                "cookie-banner",
                                "access-denied",
                            )
                        )
                    )
                    else ("content_rejected" if assessment else "fetched")
                )
                source["reason"] = (
                    "access wall or insufficient content; inspect snapshot"
                    if source["outcome"] == "access_blocked"
                    else "content acquired; attribution and scope still separate"
                )
            except Exception as exc:
                source.update(outcome="fetch_error", reason=f"{type(exc).__name__}: {exc}")
        if body:
            sha = digest(body.encode())
            artifact = safe_target(
                store.root, store.root / f"snapshot-{digest(url.encode())}-{sha}.txt"
            )
            if artifact.exists() and digest(artifact.read_bytes()) != sha:
                raise ValueError("snapshot integrity failure")
            artifact.write_text(body, encoding="utf-8", newline="")
            source.update(snapshot_path=str(artifact), content_sha256=sha)
        with store.connection() as c:
            cur = c.execute(
                "INSERT INTO fetches(target_id,data) VALUES (?,?)",
                (claim["target_id"], json.dumps(source)),
            )
            fetch_id = cur.lastrowid
    with store.connection() as c:
        old = c.execute(
            "SELECT id,data FROM evaluations WHERE claim_id=? AND fetch_id=?", (claim_id, fetch_id)
        ).fetchone()
        if old:
            return dict(json.loads(old[1]), id=old[0])
    quote = normalized(claim["quote"])
    full = normalized(claim["claim"])
    matched = bool(
        source["outcome"] == "fetched" and source_span(normalized(body), quote) is not None
    )
    exact = bool(matched and full == quote)
    result = dict(
        claim_id=claim_id,
        fetch_id=fetch_id,
        outcome=source["outcome"],
        quote_match=matched,
        full_rule_match=exact,
        scope="review_required",
        snapshot_path=source.get("snapshot_path"),
        reason=(
            "Quotation located; full scope requires explicit review"
            if matched
            else "Quotation not located or absent; not evidence of contradiction"
        )
        if source["outcome"] == "fetched"
        else source["reason"],
    )
    with store.connection() as c:
        cur = c.execute(
            "INSERT INTO evaluations(claim_id,fetch_id,data) VALUES (?,?,?)",
            (claim_id, fetch_id, json.dumps(result)),
        )
        result["id"] = cur.lastrowid
    store.record_review(
        claim_id,
        state="partially_supported"
        if matched
        else ("unresolved" if source["outcome"] == "fetched" else "blocked"),
        reason=result["reason"],
        reviewer="deterministic-verifier",
        evidence_id=result["id"],
    )
    return result


def latest_evaluation(store, claim_id):
    with store.connection() as c:
        row = c.execute(
            "SELECT id,data FROM evaluations WHERE claim_id=? ORDER BY id DESC LIMIT 1", (claim_id,)
        ).fetchone()
    if not row:
        raise ValueError("claim has no verification")
    return dict(json.loads(row[1]), id=row[0])


def approve_scope(store, claim_id, *, reason, reviewer):
    from .external_intake import now

    if not reason.strip() or not reviewer.strip():
        raise ValueError("scope review requires reason and attributed reviewer")
    v = latest_evaluation(store, claim_id)
    claim = load(store, "claims", claim_id)
    source = load(store, "fetches", v["fetch_id"])
    body = snapshot_text(store, source)
    # Re-derived from the snapshot rather than trusted from the evaluation: a
    # catalog verified under the old substring rule keeps quote_match true, and
    # UNIQUE(claim_id,fetch_id) prevents a corrected row replacing it.
    if (
        not v["full_rule_match"]
        or normalized(claim["claim"]) != normalized(claim["quote"])
        or source_span(normalized(body), normalized(claim["quote"])) is None
    ):
        raise ValueError(
            "full claim must exactly match the verified quote; adaptations require separate research"
        )
    with store.connection() as c:
        newest = c.execute(
            "SELECT max(id) FROM fetches WHERE target_id=?", (claim["target_id"],)
        ).fetchone()[0]
        if newest != v["fetch_id"]:
            raise ValueError("stale verification; reverify claim against latest fetch")
        old = c.execute(
            "SELECT seq,state,reason,reviewer,evidence_id FROM history WHERE claim_id=? ORDER BY seq DESC LIMIT 1",
            (claim_id,),
        ).fetchone()
        if old and tuple(old[1:]) == ("supported_in_scope", reason, reviewer, v["id"]):
            return old[0]
        return c.execute(
            "INSERT INTO history(claim_id,state,reason,reviewer,evidence_id,recorded_at) VALUES (?,?,?,?,?,?)",
            (claim_id, "supported_in_scope", reason, reviewer, v["id"], now()),
        ).lastrowid


def handoff(store):
    result = []
    for claim in store.summary()["claims"]:
        if claim["state"] != "supported_in_scope":
            continue
        v = latest_evaluation(store, claim["id"])
        source = load(store, "fetches", v["fetch_id"])
        body = snapshot_text(store, source)
        with store.connection() as c:
            url, tier = c.execute(
                "SELECT url,tier FROM targets WHERE id=?", (claim["target_id"],)
            ).fetchone()
            newest = c.execute(
                "SELECT max(id) FROM fetches WHERE target_id=?", (claim["target_id"],)
            ).fetchone()[0]
        if newest != v["fetch_id"] or claim["history"][-1]["evidence_id"] != v["id"]:
            continue
        # Re-derived from the snapshot, not trusted from the evaluation, so a
        # stale substring-era match cannot reach the curator.
        compact = normalized(body)
        q = normalized(claim["quote"])
        at = source_span(compact, q)
        if not v["full_rule_match"] or normalized(claim["claim"]) != q or at is None:
            continue
        # Use the exact source span, not the report's transcription.
        evidence = compact[at : at + len(q)]
        payload = RawResearchSource(
            title=url,
            source_type="web",
            url_or_citation=url,
            main_claim=claim["claim"],
            evidence=evidence,
            possible_strategy_rule="",
            risks=[
                "Attribution and explicit scope review only; empirical performance not assessed.",
                claim["context"],
            ],
            confidence="low",
            source_quality=tier,
            asset_classes=[],
            data_required=[],
            data_access="available-now",
            mvp_testable=True,
        ).model_dump()
        if promotion_block_reason(payload) is None:
            result.append(payload)
    return result
