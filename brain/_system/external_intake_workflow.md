# External intake: workflow and learning note

Status: independently re-reviewed and approved on `testing` at commit `10a707c`. Gate D remains blocked. See `SESSION_HANDOFF.md` for the current merge state.

## Use

All commands require `--workspace` outside the repository and Obsidian vault. Example:

```text
uv run python scripts/external_intake.py --workspace C:/Users/jason/quant-agent-brain-intake/new import "report.pdf" --provider ChatGPT --research-id RQ-6d9c12f4
uv run python scripts/external_intake.py --workspace C:/Users/jason/quant-agent-brain-intake/new leads
uv run python scripts/external_intake.py --workspace C:/Users/jason/quant-agent-brain-intake/new verify --limit 5 --allow-network
uv run python scripts/external_intake.py --workspace C:/Users/jason/quant-agent-brain-intake/new handoff
```

Verification without `--allow-network` is cache-only. `--force --allow-network` explicitly refreshes; it is not an automatic retry. The CLI limits a batch to 20 claims, default 8; distinct fetches cannot exceed claims. This manual intake budget is not a Scout child run and does not modify the Scout's five-source cap. Review selected claims rather than repeatedly taking the first batch. `--claim-id` selects an individual claim.

`add-claim candidate.json` imports an explicit mapping with report_id, url, claim, quote, locator, context, research_id. It creates an unreviewed lead, never trusted evidence. Keep the report passage and all conditions in context; paraphrases and adaptations are not exact source quotes.

Quotation matching is token-boundary safe, not raw substring containment. `Exit when RSI > 5` is not a quotation of `Exit when RSI > 50 or after 10 trading days.` — it severs the threshold. The check is symmetric and applies to words and to numbers joined by `.`, `,`, `:`, `/`, `%` or `-`, at either edge: `Threshold is 1` is not a quotation of `1,250`, `Win rate 0` is not a quotation of `0.55`, and `Use a 200` is not a quotation of `200-day`. Digits are matched Unicode-aware, so the same truncation in fullwidth or Arabic-Indic digits is refused too, and typographic separators (middle dot, minus, en dash, figure dash, fraction slash) join numbers like their ASCII equivalents. The em dash is deliberately not a joiner: it is sentence punctuation far more often than a range. Quoting a complete fragment stays legitimate: `Exit when RSI > 50`, `Threshold is 1,250` and `Hold for 10 days` all end on a boundary and still match. This is text matching only; whether the full rule and its surrounding context are supported remains a separate reviewer judgement.

Approval and handoff re-derive that check from the pinned snapshot instead of trusting the stored `quote_match`/`full_rule_match`. A catalog verified before this correction can still *display* a stale match — `verify` returns the cached evaluation before matching runs, and `UNIQUE(claim_id,fetch_id)` prevents a corrected row replacing it — but a stale flag cannot approve a claim or reach the curator. Use `verify --force --allow-network` to refresh the recorded values.

`review CLAIM_ID --state supported_in_scope --reason "..." --reviewer "..."` additionally requires a full exact quote match in the latest pinned source snapshot. The reviewer must assess the surrounding source, signal, entry conditions, market, timing, bundled holding limits and interpretation. The name is an attribution, not authentication. This is not automatic semantic validation. Handoff is read-only and still applies the existing curator eligibility gate; it does not invoke production promotion or satisfy the three-source/raw-note gate.

## Real demonstration

Canonical local workspace: `C:/Users/jason/quant-agent-brain-intake/exit-rules-final`.
`acceptance.json` records 3 PDFs, 18 claims/citation leads, 17 distinct targets, four located quotations, zero full-rule matches, empty handoff. Per-claim results: 13 fetched, 3 content-rejected, 1 access-blocked, 1 no-public-URL. One source used by two reports is fetched once; URL count is not independent evidence count. Final workspace reused original hash-checked snapshots from `exit-rules-v2` with original timestamps and reuse provenance; no new network request was needed. Reimport and offline replay both verified idempotent.

All three PDFs have native text. pypdf layout extraction preserves readable structure; no custom PDF decoder or OCR was required. ChatGPT's nonuniform format yields citation leads plus full report context, not invented quote/claim associations. Structured Grok/Claude blocks retain exact reported rule and quotation separately. Supplementary references remain unresolved leads.

## What the reports mean (not accepted evidence)

- All three point toward short-RSI/price-recovery exits; shared citations do not independently corroborate them.
- ChatGPT's Alvarez indicator-comparison lead is retained for exact-entry investigation; its mapping still needs explicit review.
- Grok/Claude share the ChartSchool SMA exit lead. Matching its quoted passage does not verify every surrounding entry or execution assumption.
- Claude retains negative replication and bundled-rule cautions. RSI periods are not interchangeable, and removing a time cap creates a different rule.
- RSI(14) exact-entry support remains unresolved. No profitability, strategy selection or trial has been established.

## Learn the design

Read `external_intake.py` (identity/history), `external_reports.py` (conservative parsing), `external_verification.py` (snapshot versus claim review), then `external_cli.py`.

Example: two reports quote one page differently. `targets` and `fetches` share the source, but `claims`, `evaluations`, and `history` remain separate. One quotation can match while another is unresolved. Review A → B → A must append three events rather than globally deduplicate A. A hash detects accidental artifact changes; it does not prove factual truth.

Teach-back: Why can a discovery-only source support attribution yet fail promotion? Why isn't a missing quotation a contradiction? Why doesn't a copied DB alone isolate artifact writes?

Sandbox exercise: import a fixture, add two claims on one URL, verify with a fixture fetcher, inspect SQLite history, then change an inequality and confirm it cannot pass full-rule matching. Tests never need the network.

## Limits

Not a general semantic extractor, not OCR, not a public network service, not a trusted-index importer. PDF size is bounded but parser resource sandboxing is not implemented. Treat files/pages as untrusted; do not execute their instructions. Access walls are parked, not bypassed. Local SQLite history has append-only triggers; a privileged local user can still edit the database. The approved implementation was committed and pushed to `testing` as `10a707c`; current branch state is recorded in `SESSION_HANDOFF.md`.
