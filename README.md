# MarketPilot — A Modern Python Platform for Financial Asset Management

resolve an issue

MarketPilot is an open-source Python platform for quantitative research, portfolio construction, and automated asset management.
It enables quants and researchers to build resilient data pipelines, machine learning and reinforcement learning models, and policy-aware execution flows in a modular, production-ready environment.

**MarketPilot is the evolved version of Alpha-FusionNet** — a system providing the analytical core and intelligent financial modeling foundation. MarketPilot extends it with **Agentic Reasoning**, **Feedback Learning**, **Multi-tier Reflection (Micro/Meso/Macro)**, **Dynamic Risk Management**, and **Scenario-Based Analysis**, significantly enhancing transparency, interpretability, and decision accuracy in financial operations.

---

## Key Features

* **Transparency and Explainability:** Every decision is fully traceable from raw data to model output.
* **Agentic Reasoning:** Multiple specialized agents (analyst, researcher, trader, risk, compliance, fund) cooperate in a dynamic decision graph with real-time feedback.
* **Multi-tier Reflection:** Three layers of reasoning feedback (micro, meso, macro) ensure logical consistency, contradiction detection, and self-evaluation.
* **Adaptive Risk Management:** Integrates CMDP constraints with macro/micro context for dynamic exposure adjustment in volatile regimes.
* **Scenario-Based Analysis:** Simulates economic and market events to test portfolio resilience and response.
* **Policy-Aware Reinforcement Learning:** RL models trained under hard/soft CMDP constraints with multi-objective reward shaping for stability, risk, and returns.
* **Research-to-Operations Integration:** Unified batch (Airflow/CLI) and intraday (FastAPI) workflows for model serving and execution.
* **Governance and Compliance:** Versioned policy tracking (`policy.yaml`), decision logging, and transparent audit trails for supervisory teams.

---

## Features (Implemented & Planned)

| Category           | Description                                                                                   | Status          |
| ------------------ | --------------------------------------------------------------------------------------------- | --------------- |
| Data Layer         | Robust adapters (prices, news, filings, fundamentals, macro), QC, corporate actions, alignment | In Progress     |
| Feature Engineering| Indicators, microstructure, NLP sentiment/events, graph features, regime labeling             | In Progress     |
| Reasoning Graph    | Typed agent graph with logical guards and message passing                                     | Planned         |
| Multi-tier Reflection | Feedback logic across micro/meso/macro layers with latency budgets                         | Planned         |
| Reinforcement Learning | CMDP-based training, memory-driven learning, and policy exporter                           | Planned         |
| Backtesting & Evaluation | Realistic order fills, slippage modeling, attribution, and leakage validation          | Planned         |
| Dashboards & Analytics | Streamlit dashboards and PDF/HTML risk/performance reports                                 | In Design       |
| Automated Testing  | pytest-based unit/e2e tests for RL and reflection modules                                    | In Progress     |

---

## Roadmap

**Phase 1 — Data Layer & PanelRow Alignment**
Build resilient data ingestion, cleaning, and alignment pipelines to generate consistent and reliable PanelRows.

**Phase 2 — Multi-tier Reflection & Adaptive Risk Management**
Add three levels of reflection to control reasoning quality and enhance model risk awareness.

**Phase 3 — RL Integration with CMDP & Policy Exporter**
Implement constrained reinforcement learning with CMDP logic and automatic policy generation (`policy.yaml`).

**Phase 4 — Backtesting Engine & Risk Reporting**
Develop realistic backtesting with slippage, impact modeling, and detailed risk/performance analytics.

**Phase 5 — Analytical & Monitoring Dashboards**
Launch interactive dashboards for live monitoring of performance, reflection quality, and drift metrics.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Inspirations

* **FinRL** — Reinforcement Learning framework for portfolio optimization and algorithmic trading.
  🔗 [https://github.com/AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL)

* **FinRobot** — LLM-based agentic financial research and strategy automation platform.
  🔗 [https://github.com/AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot)

* **FinGPT** — Financial Large Language Model focusing on market data, reasoning, and macro analysis.
  🔗 [https://github.com/AI4Finance-Foundation/FinGPT](https://github.com/AI4Finance-Foundation/FinGPT)

* **TradingAgents** — Multi-agent trading framework integrating LLMs and RL for autonomous decision making.
  🔗 [https://github.com/TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)

---
