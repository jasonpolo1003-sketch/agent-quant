/* Quant Brain — Interactive Visual Agent Base & Roaming Co-Pilot Engine.
   Built to taste-skill data-terminal rules: no violet/indigo, no gradients, no emojis. */
"use strict";

(function initBaseBots(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.QBBots = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function buildBaseBots() {

  const STATIONS = [
    {
      id: "scout_desk",
      label: "Scout Desk",
      sub: "Agent Reach & Discovery",
      x: 16,
      y: 28,
      color: "#4a8ad6",
      stageKeys: ["dispatch", "discovery", "fetch", "research_run"],
      page: "activity",
      description: "Searches primary academic and practitioner sources, classifies credibility tiers, and saves immutable snapshots before any model sees them.",
    },
    {
      id: "validator_gate",
      label: "Validator Gate",
      sub: "Qwen 14B/27B + 5 Gates",
      x: 50,
      y: 22,
      color: "#d9a441",
      stageKeys: ["qwen_validation", "evidence_extraction"],
      page: "activity",
      description: "Runs local Qwen 14B (with one repair and 27B escalation) and checks 5 deterministic gates: schema, source-ID, polarity, invented-rule, and slop.",
    },
    {
      id: "library_rag",
      label: "Library & RAG",
      sub: "Curator & Embeddings",
      x: 84,
      y: 28,
      color: "#44a282",
      stageKeys: ["curation"],
      page: "learn",
      description: "Promotes verified claims into brain/01_Sources/ and embeds chunks with nomic-embed-text so retrieval is grounded.",
    },
    {
      id: "strategy_forge",
      label: "Strategy Forge",
      sub: "Frozen Rules & Hash",
      x: 22,
      y: 72,
      color: "#d9a441",
      stageKeys: ["strategy", "card"],
      page: "strategies",
      description: "Locks exact entry/exit rules and cost assumptions into a SHA-256 frozen Strategy Card before any backtest is allowed to run.",
    },
    {
      id: "backtest_pit",
      label: "Backtest Pit",
      sub: "In-Sample & Held-Out",
      x: 54,
      y: 74,
      color: "#4a8ad6",
      stageKeys: ["backtest", "data_refresh", "health_check"],
      page: "strategies",
      description: "Executes next-bar signals with trading costs against Buy & Hold and Random Entry benchmarks, logging every trial to the immutable ledger.",
    },
    {
      id: "review_tribunal",
      label: "Review Tribunal",
      sub: "Adversarial DSR Gate",
      x: 84,
      y: 72,
      color: "#e5566f",
      stageKeys: ["review", "agent_prompt"],
      page: "strategies",
      description: "Tries hard to disprove the backtest using Deflated Sharpe Ratio (DSR >= 0.95) across all trials. Rejects strategies that show no out-of-sample edge.",
    },
  ];

  const PATH_EDGES = [
    ["scout_desk", "validator_gate"],
    ["validator_gate", "library_rag"],
    ["library_rag", "strategy_forge"],
    ["strategy_forge", "backtest_pit"],
    ["backtest_pit", "review_tribunal"],
    ["validator_gate", "review_tribunal"],
  ];

  const BOTS = [
    {
      id: "scout",
      name: "Scout Bot",
      role: "research_scout",
      badge: "DSC-01",
      color: "#4a8ad6",
      homeStation: "scout_desk",
      defaultMood: "idle",
      bio: "Routes discovery through Agent Reach, checks source quality tiers, and snapshots upstream evidence.",
    },
    {
      id: "validator",
      name: "Gatekeeper Qwen",
      role: "qwen_validator",
      badge: "VAL-14B",
      color: "#d9a441",
      homeStation: "validator_gate",
      defaultMood: "thinking",
      bio: "Enforces strict extractive grounding. Escalates from 14B to 27B and fails closed if any quote or number is invented.",
    },
    {
      id: "curator",
      name: "Curator Bot",
      role: "knowledge_curator",
      badge: "RAG-02",
      color: "#44a282",
      homeStation: "library_rag",
      defaultMood: "happy",
      bio: "Guards brain/01_Sources/ and maintains semantic vector chunks for the NotebookLM-style Tutor.",
    },
    {
      id: "backtester",
      name: "Sim Engine Bot",
      role: "backtest_runner",
      badge: "SIM-04",
      color: "#4a8ad6",
      homeStation: "backtest_pit",
      defaultMood: "working",
      bio: "Runs two-phase backtests with next-bar execution and 5-10 bps slippage on verified Gate F datasets.",
    },
    {
      id: "reviewer",
      name: "Arbiter Bot",
      role: "adversarial_reviewer",
      badge: "REV-05",
      color: "#e5566f",
      homeStation: "review_tribunal",
      defaultMood: "alert",
      bio: "Audits every trial in the ledger and upholds Reject when out-of-sample DSR or random-entry gates fail.",
    },
  ];

  function stationById(stationId) {
    return STATIONS.find((s) => s.id === stationId) || STATIONS[0];
  }

  function mapStageToStation(stage, agentRole) {
    const s = String(stage || "").toLowerCase();
    const r = String(agentRole || "").toLowerCase();
    if (s.includes("qwen") || s.includes("valid") || s.includes("extract")) return "validator_gate";
    if (s.includes("curat") || r.includes("curator")) return "library_rag";
    if (s.includes("card") || s.includes("strategy")) return "strategy_forge";
    if (s.includes("backtest") || s.includes("data_refresh") || s.includes("health")) return "backtest_pit";
    if (s.includes("review")) return "review_tribunal";
    if (s.includes("discov") || s.includes("fetch") || s.includes("dispatch") || r.includes("scout")) return "scout_desk";
    return "scout_desk";
  }

  function mapEventToBotId(event) {
    if (!event) return "scout";
    const s = String(event.stage || "").toLowerCase();
    const r = String(event.agent_role || "").toLowerCase();
    if (s.includes("qwen") || s.includes("valid") || s.includes("extract")) return "validator";
    if (r.includes("curator") || s.includes("curat")) return "curator";
    if (s.includes("backtest") || s.includes("health") || s.includes("data_refresh") || r.includes("terminal")) return "backtester";
    if (s.includes("review") || r.includes("review")) return "reviewer";
    return "scout";
  }

  function mapStatusToMood(status) {
    const st = String(status || "").toLowerCase();
    if (st === "running" || st === "started") return "working";
    if (st === "completed" || st === "passed" || st === "accepted" || st === "done") return "happy";
    if (st === "failed" || st === "refused" || st === "invalid" || st === "rejected") return "alert";
    return "idle";
  }

  function deriveInitialBotStates(context = {}) {
    const counts = context.counts || {};
    const runs = Array.isArray(context.runs) ? context.runs : [];
    const lab = context.lab || {};
    const latestRun = runs[0] || null;
    const latestCard = (lab.cards || [])[0] || null;
    const latestReview = (lab.reviews || [])[0] || null;
    const backtests = lab.backtests || [];

    const states = {};
    for (const b of BOTS) {
      const home = stationById(b.homeStation);
      states[b.id] = {
        ...b,
        stationId: home.id,
        x: home.x,
        y: home.y,
        mood: b.defaultMood,
        speech: b.bio,
        detail: "Standing by at " + home.label,
        active: false,
      };
    }

    if (latestRun) {
      const runMood = mapStatusToMood(latestRun.status);
      states.scout.mood = runMood;
      states.scout.speech = `${latestRun.title || "Latest run"}: ${latestRun.outcome || latestRun.status}`;
      states.scout.detail = latestRun.reason
        ? `Stopped reason: ${latestRun.reason}`
        : `Completed ${latestRun.steps || 0} recorded events in ${latestRun.run_id}.`;

      const qwenPhase = (latestRun.phases || []).find((p) => p.stage === "qwen_validation");
      if (qwenPhase) {
        states.validator.mood = qwenPhase.failed > 0 ? "alert" : "happy";
        states.validator.speech = `Qwen Gate: ${qwenPhase.ok} passed, ${qwenPhase.failed} failed in ${latestRun.run_id}.`;
        states.validator.detail = qwenPhase.failed > 0
          ? "Caught ungrounded or schema-violating model output and enforced fail-closed rules."
          : "All model outputs cleared the 5 deterministic validation gates.";
      }
    } else {
      states.scout.speech = `${counts.sources || 0} curated sources and ${counts.research_questions || 0} research questions tracked.`;
    }

    states.curator.speech = `Indexing ${counts.sources || 7} verified sources and ${counts.notes || 0} brain notes.`;
    states.curator.detail = `Price datasets verified: ${counts.price_datasets || 0}. Ready for context retrieval.`;

    if (backtests.length > 0) {
      const heldOut = backtests.filter((bt) => bt.config && bt.config.phase === "held_out" && bt.config.kind === "rule");
      states.backtester.mood = "happy";
      states.backtester.speech = `${backtests.length} ledger rows recorded (${heldOut.length} held-out rule trials).`;
      states.backtester.detail = latestCard
        ? `Card ${latestCard.strategy_id} (${latestCard.status}): tested across SPY, QQQ, IWM with 5 and 10 bps costs.`
        : "Backtest ledger loaded with Buy & Hold and Random Entry baselines.";
    } else if (latestCard) {
      states.backtester.stationId = "strategy_forge";
      const forge = stationById("strategy_forge");
      states.backtester.x = forge.x;
      states.backtester.y = forge.y;
      states.backtester.speech = `Card ${latestCard.strategy_id} is ${latestCard.status}. Ready to simulate.`;
    }

    if (latestReview) {
      const isRejected = String(latestReview.verdict || "").toLowerCase().startsWith("reject");
      states.reviewer.mood = isRejected ? "alert" : "happy";
      states.reviewer.speech = `${latestReview.strategy_id || "Review"}: ${latestReview.verdict_text || latestReview.verdict}`;
      states.reviewer.detail = isRejected
        ? "Honest quant result: strategy failed out-of-sample DSR (0.896 < 0.950) and random-entry gates."
        : "Adversarial review recorded.";
    }

    return states;
  }

  function buildReplayStepsFromEvents(events = [], runSummary = {}) {
    if (!Array.isArray(events) || events.length === 0) {
      return [
        {
          botId: "scout",
          stationId: "scout_desk",
          mood: "working",
          speech: "Dispatching Research Scout to scan candidate sources...",
          stage: "discovery",
          status: "running",
        },
        {
          botId: "validator",
          stationId: "validator_gate",
          mood: "thinking",
          speech: "Running Qwen 14B/27B extraction and 5 deterministic validation gates...",
          stage: "qwen_validation",
          status: "running",
        },
        {
          botId: "curator",
          stationId: "library_rag",
          mood: "happy",
          speech: "Curating verified evidence into brain/01_Sources/ and RAG chunks...",
          stage: "curation",
          status: "completed",
        },
        {
          botId: "backtester",
          stationId: "strategy_forge",
          mood: "working",
          speech: "Freezing Strategy Card SC-0002 rules with SHA-256 hash...",
          stage: "strategy",
          status: "completed",
        },
        {
          botId: "backtester",
          stationId: "backtest_pit",
          mood: "working",
          speech: "Simulating 101 in-sample and 91 held-out trades with next-bar execution...",
          stage: "backtest",
          status: "completed",
        },
        {
          botId: "reviewer",
          stationId: "review_tribunal",
          mood: "alert",
          speech: "Adversarial Review: DSR 0.896 < 0.950. Verdict: REJECT (no edge shown).",
          stage: "review",
          status: "failed",
        },
      ];
    }

    return events.slice(0, 24).map((ev, idx) => {
      const botId = mapEventToBotId(ev);
      const stationId = mapStageToStation(ev.stage, ev.agent_role);
      const mood = mapStatusToMood(ev.status);
      const msg = ev.message || `${ev.agent_role} -> ${ev.event_type} (${ev.status})`;
      return {
        stepIndex: idx + 1,
        eventId: ev.event_id,
        botId,
        stationId,
        mood,
        speech: msg.length > 110 ? msg.slice(0, 109) + "…" : msg,
        stage: ev.stage || "run",
        status: ev.status || "running",
        timestamp: ev.created_at || "",
        runId: ev.run_id || runSummary.run_id || "",
      };
    });
  }

  function botAvatarSvg(styleMode = "droid", color = "#4a8ad6", mood = "idle") {
    const eyeColor = mood === "alert" ? "#e5566f" : mood === "happy" ? "#44a282" : mood === "working" ? "#d9a441" : "#ffffff";
    if (styleMode === "pixel") {
      return `<svg viewBox="0 0 32 32" width="28" height="28" class="bot-svg pixel" aria-hidden="true">
        <rect x="14" y="2" width="4" height="4" fill="${color}"/>
        <rect x="8" y="6" width="16" height="14" rx="2" fill="#131217" stroke="${color}" stroke-width="2"/>
        <rect x="11" y="10" width="4" height="4" fill="${eyeColor}"/>
        <rect x="17" y="10" width="4" height="4" fill="${eyeColor}"/>
        <rect x="12" y="16" width="8" height="2" fill="${color}"/>
        <rect x="10" y="21" width="12" height="7" fill="#212023" stroke="${color}" stroke-width="1.5"/>
      </svg>`;
    }
    if (styleMode === "geometric") {
      return `<svg viewBox="0 0 36 36" width="28" height="28" class="bot-svg geo" aria-hidden="true">
        <polygon points="18,3 31,11 31,25 18,33 5,25 5,11" fill="#131217" stroke="${color}" stroke-width="2"/>
        <circle cx="18" cy="18" r="7" fill="none" stroke="${color}" stroke-width="1.5"/>
        <circle cx="15" cy="16" r="2" fill="${eyeColor}"/>
        <circle cx="21" cy="16" r="2" fill="${eyeColor}"/>
        <path d="${mood === "alert" ? "M14 22 L22 22" : "M14 21 Q18 24 22 21"}" stroke="${eyeColor}" stroke-width="1.8" fill="none" stroke-linecap="round"/>
      </svg>`;
    }
    return `<svg viewBox="0 0 40 40" width="28" height="28" class="bot-svg droid" aria-hidden="true">
      <line x1="20" y1="4" x2="20" y2="9" stroke="${color}" stroke-width="2" stroke-linecap="round"/>
      <circle cx="20" cy="3.5" r="2.2" fill="${eyeColor}"/>
      <rect x="8" y="9" width="24" height="17" rx="6" fill="#131217" stroke="${color}" stroke-width="2"/>
      <rect x="11" y="12" width="18" height="9" rx="3" fill="#171719" stroke="#222224" stroke-width="1"/>
      <circle cx="15.5" cy="16.5" r="2.2" fill="${eyeColor}"/>
      <circle cx="24.5" cy="16.5" r="2.2" fill="${eyeColor}"/>
      <path d="${mood === "alert" ? "M16 23 L24 23" : mood === "happy" ? "M15 22 Q20 25 25 22" : "M16 22.5 L24 22.5"}" stroke="${color}" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M13 27 L27 27 L25 34 L15 34 Z" fill="#212023" stroke="${color}" stroke-width="1.5"/>
    </svg>`;
  }

  return {
    STATIONS,
    PATH_EDGES,
    BOTS,
    stationById,
    mapStageToStation,
    mapEventToBotId,
    mapStatusToMood,
    deriveInitialBotStates,
    buildReplayStepsFromEvents,
    botAvatarSvg,
  };
});
