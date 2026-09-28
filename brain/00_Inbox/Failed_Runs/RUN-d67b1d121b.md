---
id: RUN-d67b1d121b
type: failed_run
research_id: RQ-6d9c12f4
stage: qwen_extract
agent_role: research_scout
retryable: true
---

# Failed Scout Run — RUN-d67b1d121b

## Research ID

RQ-6d9c12f4

## Stage Reached

qwen_extract

## Error

`QwenValidationError`: local Qwen failed closed: source_id: omitted supplied source S4; source_id: unknown source <missing>

## Detail

```json
{
  "task_id": "TASK-4faf7ea65f",
  "created_scaffold": true,
  "discovery_lane": {
    "lane": "preregistered_candidate_list",
    "candidate_list_path": "brain/00_Inbox/Scout_Candidates/RQ-6d9c12f4.md",
    "candidate_list_sha256": "88ba2d3ce98b69623d050197c15c8e5d7adf82e107b3a6bb8ea5e045022faeae",
    "candidate_count": 5,
    "candidate_urls": [
      "https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2",
      "https://articles.stockcharts.com/article/articles-arthurhill-2016-12-systemtrader---testing-and-tweaking-an-rsi-mean-reversion-system-for-spy-qqq-and-ijr",
      "https://connorsresearch.com/connors-research-traders-journal-volume-1-does-mean-reversion-still-work",
      "https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf",
      "https://thepatternsite.com/Double7sSetup.html"
    ]
  },
  "research_id": "RQ-6d9c12f4",
  "run_id": "RUN-d67b1d121b",
  "accepted_candidates": [
    {
      "url": "https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2",
      "title": "https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2",
      "tier": "practitioner",
      "snapshot_path": "brain/00_Inbox/Source_Snapshots/2026-09-28/a1fd76ffb87f-e90b0420.md",
      "snapshot_sha256": "a1fd76ffb87f15505e2e5a65645e4512df892c5deebee5f8ee7a7750ec1650e8"
    },
    {
      "url": "https://articles.stockcharts.com/article/articles-arthurhill-2016-12-systemtrader---testing-and-tweaking-an-rsi-mean-reversion-system-for-spy-qqq-and-ijr",
      "title": "https://articles.stockcharts.com/article/articles-arthurhill-2016-12-systemtrader---testing-and-tweaking-an-rsi-mean-reversion-system-for-spy-qqq-and-ijr",
      "tier": "practitioner",
      "snapshot_path": "brain/00_Inbox/Source_Snapshots/2026-09-28/13a68c8fe9c5-f90199dd.md",
      "snapshot_sha256": "13a68c8fe9c5bc7ae7404559bf7f75db724754ff430beda737ac330591259604"
    },
    {
      "url": "https://connorsresearch.com/connors-research-traders-journal-volume-1-does-mean-reversion-still-work",
      "title": "https://connorsresearch.com/connors-research-traders-journal-volume-1-does-mean-reversion-still-work",
      "tier": "discovery-only",
      "snapshot_path": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md",
      "snapshot_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"
    },
    {
      "url": "https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf",
      "title": "https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf",
      "tier": "discovery-only",
      "snapshot_path": "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md",
      "snapshot_sha256": "c5f9673f32a482a2940a96e28c8281db9247393e5fefb2cc907d81a410ca7c37"
    },
    {
      "url": "https://thepatternsite.com/Double7sSetup.html",
      "title": "https://thepatternsite.com/Double7sSetup.html",
      "tier": "discovery-only",
      "snapshot_path": "brain/00_Inbox/Source_Snapshots/2026-09-28/182d927c9c90-a5e96da3.md",
      "snapshot_sha256": "182d927c9c9082fab71730a537d7d4c66a2367fdb7d5f5db5c431871144a54ea"
    }
  ],
  "snapshot_paths": [
    "brain/00_Inbox/Source_Snapshots/2026-09-28/a1fd76ffb87f-e90b0420.md",
    "brain/00_Inbox/Source_Snapshots/2026-09-28/13a68c8fe9c5-f90199dd.md",
    "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md",
    "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md",
    "brain/00_Inbox/Source_Snapshots/2026-09-28/182d927c9c90-a5e96da3.md"
  ],
  "distinct_upstream_count": 5,
  "required_upstream_count": 3,
  "rejected_candidates": [],
  "search_query_expression": null,
  "extraction_windows": [
    {
      "source_id": "S4",
      "url_or_citation": "https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf",
      "snapshot_path": "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md",
      "snapshot_sha256": "cdc7a0e5976ccfee51a8fb3455565d3455500c0862a53af28f9dbbaeb1cbd051",
      "snapshot_text_derivation": "snapshot file decoded as UTF-8 with universal newlines (Path.read_text: CRLF and CR become LF); offsets are character indexes into that text",
      "snapshot_text_sha256": "ff7af49ebb47e0eaddc9962da4f67fa26af0b218693d07ea4dedaaf70ecca98b",
      "snapshot_text_length": 55303,
      "window_max_bytes": 9000,
      "window_overlap_bytes": 1200,
      "window_count": 8,
      "windows": [
        {
          "window_id": "S4-W01",
          "index": 1,
          "start": 0,
          "end": 8951,
          "text_sha256": "8039befc0bdbc47ec921c917e4ddfbeee3de63c64199b97f3b8faf1d7e830e2c",
          "outcome": "no_relevant_evidence",
          "validator_ok": true,
          "attempts": [
            {
              "model": "qwen3:14b",
              "duration_seconds": 13.870103299999755,
              "prompt_hash": "69a132d6691f29fc9440b8bcaa028917ec0caf63bfcc5ad1599bbaf4f6e1b1d4",
              "response_hash": "acd39fd2b77bee90cd5fb7d8c3049a647a8980beec429c8d6815ffe3f0cbfdf9",
              "validator_ok": true,
              "validator_reasons": []
            }
          ]
        },
        {
          "window_id": "S4-W02",
          "index": 2,
          "start": 7755,
          "end": 15836,
          "text_sha256": "3fa2131fc847cb65d88f990627179ab7b37336af7c754d36544b21fb7d652994",
          "outcome": "failed",
          "validator_ok": false,
          "attempts": [
            {
              "model": "qwen3:14b",
              "duration_seconds": 19.873869499999273,
              "prompt_hash": "84d0fa93a016b23b6327c82eab8c9778632f79ac018bc3945474025e9771ccd2",
              "response_hash": "a17a7745a604d5185202f3a0957bab0b5cab2e6d63f4c5f59b9f8a6d2978f61a",
              "validator_ok": false,
              "validator_reasons": [
                "schema: window outcome: 1 validation error for WindowOutcome\n  Value error, an evidence outcome needs a source and a curator_recommendation [type=value_error, input_value={'research_id': 'RQ-6d9c1...r_recommendation': None}, input_type=dict]\n    For further information visit https://errors.pydantic.dev/2.13/v/value_error"
              ]
            },
            {
              "model": "qwen3:14b",
              "duration_seconds": 19.17583889999878,
              "prompt_hash": "03f2f9085916efd91b2219717a58f3a51799deaf3e13ffc744dfb9c7cdfb362e",
              "response_hash": "2936b2645c2a34303375d0a2d84b1920ea5ab2cf1646d99c76fb309538f8664b",
              "validator_ok": false,
              "validator_reasons": [
                "source_id: omitted supplied source S4",
                "source_id: unknown source <missing>",
                "quote-full:S4: exact evidence is absent from the full snapshot"
              ]
            },
            {
              "model": "qwen3.8:27b",
              "duration_seconds": 60.06409310000163,
              "prompt_hash": "8629392822f4f29c25591f3da46a9ad4920c8395149fc97b7db96f632a996b12",
              "response_hash": "0965f858ac69a89de67b094cdad7ee9410987f69d896f7c72ad10dc6c3884fdf",
              "validator_ok": false,
              "validator_reasons": [
                "source_id: omitted supplied source S4",
                "source_id: unknown source <missing>"
              ]
            }
          ]
        },
        {
          "window_id": "S4-W03",
          "index": 3,
          "start": 14690,
          "end": 23608,
          "text_sha256": "41e2b824ed1a2f565b9e5fe25127dc6ed9281f01f872b76d1244009c9d1ff101",
          "outcome": "not_run",
          "validator_ok": null,
          "attempts": []
        },
        {
          "window_id": "S4-W04",
          "index": 4,
          "start": 22408,
          "end": 31361,
          "text_sha256": "ce43f2fe75ae551f85b3611e291f73003aeef5ad070fb1513e8d2ba2d8d554c2",
          "outcome": "not_run",
          "validator_ok": null,
          "attempts": []
        },
        {
          "window_id": "S4-W05",
          "index": 5,
          "start": 30161,
          "end": 38737,
          "text_sha256": "1a7b5c67aa18d42b562b5642fbaf397b0fbda5ea02903ce15b687044c00ecc50",
          "outcome": "not_run",
          "validator_ok": null,
          "attempts": []
        },
        {
          "window_id": "S4-W06",
          "index": 6,
          "start": 37537,
          "end": 46419,
          "text_sha256": "b2133a1f5e72c5b30e6da3537ec116412980436971cd6fb294d838a5744087f9",
          "outcome": "not_run",
          "validator_ok": null,
          "attempts": []
        },
        {
          "window_id": "S4-W07",
          "index": 7,
          "start": 45219,
          "end": 54211,
          "text_sha256": "cfc52a3713506e236aa1dc0d7eba780c839d4e563830e2ca775ebbccef394289",
          "outcome": "not_run",
          "validator_ok": null,
          "attempts": []
        },
        {
          "window_id": "S4-W08",
          "index": 8,
          "start": 53011,
          "end": 55303,
          "text_sha256": "9b84cf6860026891a8b8a88742dd203cfeaa0ecc13af4c6677ff668c4e274470",
          "outcome": "not_run",
          "validator_ok": null,
          "attempts": []
        }
      ]
    }
  ],
  "stage": "qwen_extract",
  "error_type": "QwenValidationError",
  "recovery": {
    "raw_note": "removed",
    "question": "queued",
    "complete": true,
    "secondary_failures": []
  }
}
```

## Retry

The research question was returned to `queued`. Re-run:

```bash
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-6d9c12f4 --candidate-list brain/00_Inbox/Scout_Candidates/RQ-6d9c12f4.md
```
