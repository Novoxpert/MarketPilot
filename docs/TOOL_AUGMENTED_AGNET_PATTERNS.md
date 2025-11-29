# Tool-Augmented Agent Patterns

This guide presents modular strategies for building agentic systems that support trading workflows and asset management. Each pattern demonstrates how to combine LLM reasoning with tool-based execution to create intelligent, context-aware agents.

---

## 1. Function Invocation via Tool Registry

```python
if "context_pack" in tools:
    state.get("data.analysis", []).append(
        tools["context_pack"](
            symbol=state.get("data.symbol", {}),
        )
    )
```

**Description**  
- Checks if a tool (e.g. `context_pack`) is available.
- Invokes the tool with a trading symbol from state.
- Appends the result to a shared analysis buffer.

**Use Case**  
Retrieve a bundle of technical indicators (e.g., RSI, Bollinger Bands, moving averages) for a given equity or ETF before generating a trade signal.

---

## 2. Embedding-Based Context Retrieval

```python
query = state["messages"][-1].content

vectorstore = FAISS.load_local("vectorstore_index", OpenAIEmbeddings())
docs: list[Document] = vectorstore.similarity_search(query, k=3)

state["documents"] = [doc.page_content for doc in docs]
```

**Description**  
- Extracts the latest user query.
- Loads a vectorstore of embedded financial documents.
- Retrieves the top-k most relevant documents.
- Stores them in state for LLM access.

**Use Case**  
Search internal research memos, earnings transcripts, or macroeconomic reports to contextualize a portfolio manager’s question like “What’s the outlook for energy sector ETFs in Q1?”

---

## 3. LLM-Based Planning and Tool Selection

```python
llm = ChatOpenAI(model="gpt-4", temperature=0.2)

planning_prompt = [
    HumanMessage(content="Given the user query, generate a response using available tools."),
    *state["messages"]
]
response = llm(planning_prompt)
```

**Description**  
- Uses a low-temperature LLM to generate deterministic plans.
- Combines user input with prior messages.
- Delegates tool selection and response generation to the LLM.

**Use Case**  
Given a prompt like “What’s the risk-adjusted return of my portfolio this month?”, the LLM can decide to invoke tools for portfolio holdings, benchmark data, and volatility metrics.

---

## 4. Tool-Calling via LLM Function Schema

```python
response = llm.invoke_function_calling(
    messages=planning_prompt,
    tools=[tool_schema],
    tool_choice="auto"
)
```

**Description**  
- Uses structured function calling with tool schemas.
- LLM selects and invokes tools based on user intent.

**Use Case**  
Automatically trigger a `get_asset_correlation_matrix` tool when a user asks, “How correlated are my top 10 holdings?”

---

## 5. Multi-Tool Parallel Execution

```python
multi_tool_use.parallel({
    "tool_uses": [
        {"recipient_name": "search_web", "parameters": {"query": "US CPI forecast"}},
        {"recipient_name": "search_finance", "parameters": {"tickerSymbol": "SPY", "intent": "stock"}}
    ]
})
```

**Description**  
- Executes multiple tools in parallel.
- Aggregates macroeconomic and market data simultaneously.

**Use Case**  
Fetch inflation forecasts and current ETF prices in parallel to assess macro risk exposure across asset classes.

---

## 6. Agentic Planning with Intermediate State

```python
plan = llm([
    SystemMessage(content="You are a portfolio analysis agent."),
    HumanMessage(content="Evaluate my exposure to interest rate risk.")
])

for step in plan.steps:
    result = tools[step.tool](**step.args)
    state[step.name] = result
```

**Description**  
- LLM generates a multi-step plan.
- Each step is executed via tool calls.
- Results are stored in state for downstream use.

**Use Case**  
Plan might include: (1) retrieve bond holdings, (2) calculate duration and convexity, (3) simulate rate shock scenarios.

---

## 7. Self-Reflective Agent Loop

```python
while not state["done"]:
    thought = llm([
        SystemMessage(content="Reflect on next best action."),
        *state["messages"]
    ])
    action = parse_tool_call(thought)
    result = tools[action.name](**action.args)
    state.update(result)
```

**Description**  
- Implements a reflection-action loop.
- LLM iteratively determines next best action.
- Enables autonomous, adaptive workflows.

**Use Case**  
An agent continuously monitors market volatility, re-evaluates portfolio beta, and adjusts hedging strategies in real time.

---

## 8. Memory-Augmented Agent Behavior

```python
if "target_allocation" not in state:
    state["target_allocation"] = memory.get("user.target_allocation")

llm([
    SystemMessage(content="Use the user's target allocation to rebalance the portfolio."),
    HumanMessage(content="Should I rebalance this quarter?")
])
```

**Description**  
- Retrieves long-term memory (e.g., user preferences).
- Personalizes LLM behavior based on stored facts.

**Use Case**  
Use stored target allocations (e.g., 60/30/10 equity/bond/alt) to evaluate current drift and recommend rebalancing actions.

---

## Summary Table

| Pattern                     | Type     | Trading Example                                           | Asset Management Example                             |
|----------------------------|----------|-----------------------------------------------------------|-------------------------------------------------------|
| Tool Registry              | Function | Fetch indicators for a stock                              | Load asset metadata for NAV calculation               |
| Embedding Search           | Function | Retrieve similar analyst reports                          | Search internal memos on sector rotation strategies   |
| LLM Planning               | LLM      | Plan trade execution steps                                | Generate quarterly portfolio review plan              |
| Function Calling           | LLM      | Auto-call volatility estimator                            | Trigger asset classification tool                     |
| Parallel Execution         | Function | Fetch CPI + SPY price concurrently                        | Retrieve benchmark returns + client portfolio history |
| Stepwise Planning          | Hybrid   | Multi-step trade validation                               | Multi-step risk attribution analysis                  |
| Reflective Loop            | LLM      | Adaptive hedging based on market shifts                   | Iterative rebalancing based on drift thresholds       |
| Memory Integration         | Hybrid   | Use stored risk profile for trade sizing                  | Apply client mandates to asset selection              |