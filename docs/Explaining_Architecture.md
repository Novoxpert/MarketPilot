# **Architecture Overview**

This document describes the overall architecture of the project, the major components in `src/`, the configuration-driven architecture (Agents, Tools, Graphs), and the execution flow when running the CLI or the workflow engine.

![Architecture Overview](assets/folder_structure.png)

---

# **1. High-Level System Architecture**

The system implements an **Agentic Workflow Framework** built on:

* **LangGraph** for graph-based workflow composition
* **Dynamic loading** of Agents, Tools, and Pipelines from **YAML config files**
* A **CLI interface** for running agents interactively, invoking targets, and visualizing graphs
* A modular structure that cleanly separates:

  * Agent logic
  * Tool logic
  * Workflow/graph definitions
  * Configuration models
  * Backend utilities (config loaders, registries)
  * Integration points (data, ML models, feature store, etc.)

The architecture emphasizes **extensibility**: New agents, new tools, and new workflows can be added **without modifying source code**, simply by updating configuration files.

---

# **2. Repository Structure (Important Folders)**

```
.
├── configs/               # YAML configuration system
├── src/agentic/           # Agent, tool, graph, pipeline runtime
├── src/cli/               # CLI entrypoints + subcommands
├── docs/                  # Documentation
├── tests/                 # Unit tests
```

---

# **3. Configurations**

The system relies heavily on YAML-driven configuration. There are three main config types:

```
configs/agents/      → Defines agents and their parameters
configs/tools/       → Defines tools, their handler classes, and inputs/outputs
configs/graphs/      → Defines a LangGraph workflow and its nodes
config.yml           → Global project-level configuration
```

### **3.1 Agent Configuration Example**

**configs/agents/analyst.yml**

```yaml
id: analyst_agent
type: llm
class_path: agentic.agents.analyst.AnalystAgent
model: gpt-4.1
description: "Analyzes market data and produces insights."
tools:
  - market_price_fetcher
  - opportunity_scorer
params:
  temperature: 0.0
  system_prompt: |
    You are a market analyst focusing on trend and pattern detection.
```

### **3.2 Tool Configuration Example**

**configs/tools/market_price_fetcher.yml**

```yaml
id: market_price_fetcher
class_path: agentic.tools.market_price_fetcher.MarketPriceFetcher
description: "Fetches current market prices from APIs or datasets."
inputs:
  - symbol
outputs:
  - price
params:
  data_source: "yahoo-finance"
```

### **3.3 Graph Definition Example**

**configs/graphs/trading_intelligence_workflow.yml**

```yaml
id: trading_intelligence_workflow
description: "End-to-end trading decision workflow."
nodes:
  - id: load_data
    agent: data_loader
  - id: analyze
    agent: analyst
  - id: assess_risk
    agent: risk_assessment
  - id: execute
    agent: trader
edges:
  - from: load_data
    to: analyze
  - from: analyze
    to: assess_risk
  - from: assess_risk
    to: execute
```

---

# **4. Internal Architecture (src/agentic)**

```
src/agentic/
├── agent_manager.py         # Dynamically loads agents from config
├── agent_protocol.py        # Protocol/base interface for all agents
├── agents/                  # Concrete agent implementations
├── agent_types.py           # Enum / registry of agent types
├── config_models.py         # Pydantic models for configs
├── graph_builder.py         # Builds LangGraph workflows from YAML
├── node_registry.py         # Registry for mapping ids → agent instances
├── pipeline_runner.py       # Executes a graph or sequential pipeline
├── tool_protocol.py         # Base class/interface for all tools
└── tools/                   # Concrete tool implementations
```

### **4.1 Agents**

Each agent is a class that implements the `AgentProtocol`.

Example:

`src/agentic/agents/analyst.py`

```python
class AnalystAgent(LLMAgent):
    def run(self, state):
        # interpret query and produce analysis using model + tools
        ...
```

Supporting files:

* **llm_agent.py** – generic LLM-powered agent
* **planner_agent.py** – step-planning agent
* **tool_agent.py** – agent that delegates to a tool
* **retrieval_agent.py** – RAG-centric agent
* **summary_agent.py** – summarization agent
* **arithmetic_agent.py** – utility/math agent
* **state.py** – extensible state object passed around workflow steps

### **4.2 Tools**

Tools encapsulate programmatic operations and follow a `ToolProtocol`.

Examples:

* `context_pack.py`
* `market_price_fetcher.py`
* `portfolio_monitor.py`
* `opportunity_scorer.py`

### **4.3 Workflow Builder**

`graph_builder.py` parses a graph YAML and builds a LangGraph instance by:

1. Loading agent configs
2. Resolving node → agent mapping
3. Connecting nodes based on `edges:`
4. Returning a runnable workflow used by the CLI or API

### **4.4 Pipeline Runner**

`pipeline_runner.py` executes:

* A graph workflow
* Or a simple list of agents (pipeline mode)

---

# **5. CLI Architecture**

```
src/cli/
├── main.py                  # Entry point
├── commands/
│   ├── config.py            # Print / validate configs
│   ├── list_targets.py      # List available agents/tools/graphs
│   ├── run_agent.py         # Run a single agent interactively
│   ├── run_target.py        # Run an agent OR graph from config
│   └── visualize_graph.py   # Exports graph visualization
```

### **Example Commands**

```
marketpilot list targets
marketpilot run agent analyst
marketpilot run target trading_intelligence_workflow
marketpilot visualize graph trading_intelligence_workflow
```

---

# **6. Execution Flow**

Below is the full process when a user runs a graph, e.g.:

```
marketpilot run target trading_intelligence_workflow
```

### **Step 1 — CLI Parses Command**

`run_target.py` identifies whether the target is:

* an agent
* a tool
* or a graph

Because `trading_intelligence_workflow.yml` exists under `configs/graphs`, the CLI treats it as a workflow.

---

### **Step 2 — Config Loader Reads YAML**

`utils/config_loader.py` loads:

* Global `config.yml`
* Graph definition file
* All referenced agent configs
* All referenced tool configs

---

### **Step 3 — Agent Manager Instantiates Agents**

`agent_manager.py`:

* Reads `class_path`
* Dynamically `importlib.import_module(...)`
* Injects parameters, tools, LLM clients, etc.

Example:

```python
AnalystAgent = load_class("agentic.agents.analyst.AnalystAgent")
analyst = AnalystAgent(**params, tools=[...])
```

---

### **Step 4 — Tools Instantiated**

`tool_protocol.py` provides a base for tool execution.

Example:

```python
MarketPriceFetcher = load_class("agentic.tools.market_price_fetcher.MarketPriceFetcher")
```

Injected into agents based on YAML.

---

### **Step 5 — Graph Builder Constructs LangGraph**

`graph_builder.py`:

* Creates nodes for each agent
* Connects nodes as defined in the YAML `edges`
* Produces a runnable LangGraph workflow object

---

### **Step 6 — Pipeline Runner Executes Workflow**

`pipeline_runner.py` takes a graph instance and:

* Initializes the workflow state
* Executes node by node following the graph dependencies
* Passes outputs between agents
* Writes logs to `logs/` if enabled

---

### **Step 7 — Output Returned to User**

CLI prints:

* Final workflow output
* Optional intermediate logs
* Any errors encountered

---

# **7. Extending the System**

### **To add a new agent**

1. Implement a class in `src/agentic/agents/`
2. Add a YAML in `configs/agents/`
3. Reference it in a graph or use via CLI

### **To add a new tool**

1. Implement class in `src/agentic/tools/`
2. Add YAML to `configs/tools/`
3. Add tool id to agent config

### **To add a new workflow**

1. Create YAML in `configs/graphs/`
2. Run:

```
marketpilot visualize graph NEW_WORKFLOW
marketpilot run target NEW_WORKFLOW
```

---

# **8. Testing**

Tests live in:

```
tests/
├── test_analyst_agent.py
└── test_config_util.py
```

They validate:

* Agent functionality
* Config loading and validation
* Tool behavior
* End-to-end sanity checks

---

# **9. Summary**

This system is a **modular, configuration-driven agent orchestration framework**. Adding new capabilities requires **no changes** to the core runtime—everything loads dynamically from config files. The architecture cleanly separates concerns:

* YAML configs define behavior
* Agent/Tool classes implement logic
* Graph builder orchestrates workflows
* CLI provides user interaction

This makes the platform highly extensible, maintainable, and suitable for production-grade agent pipelines.