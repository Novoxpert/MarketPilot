# Using the “System Prompts & Models of AI Tools” Repository

This document explains what the [x1xhlol/system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) repository is, why you might want to use it, and how to integrate and leverage its contents in your own AI / agent-engineering projects.

## What Is This Repository?

- It’s a **community-curated collection** of system prompts, internal tool definitions, and model configurations for many AI tools and agents. :contentReference[oaicite:0]{index=0}  
- Covers a wide variety of AI assistants / coding agents, such as FULL v0, Cursor, Lovable, Same.dev, Replit, Trae, vs. many others. :contentReference[oaicite:1]{index=1}  
- Provides **insights into system instruction structure**, tool ecosystems, and prompt-engineering patterns. :contentReference[oaicite:2]{index=2}  
- Licensed under **GPL-3.0**, so be sure to check compatibility with your project’s license. :contentReference[oaicite:3]{index=3}  
- It also comes with a **security notice**, especially for startups: exposing system prompts can be a risk. :contentReference[oaicite:4]{index=4}  

## Why Use It?

Here are some reasons you might want to integrate parts of this repository into your project:

- **Prompt Engineering**: Use real-world system prompt templates to bootstrap your own agent or assistant.
- **Tool Definition**: Adopt or adapt tool definitions (APIs, capabilities) that other agents use.
- **Learning & Research**: Study how established AI tools define their system instructions, memory, tool usage, and role.
- **Transparency & Security**: Use it for security analysis or build your own “system prompt leak” checks.
- **Rapid Prototyping**: Use these as blueprints or configs when building your own LLM-based agents.

## How to Integrate

### 1. Explore Its Structure

The repo is organized such that each AI tool / agent has its own folder. ([DeepWiki][1])
For example:

| Directory       | What It Contains                                                                |
| --------------- | ------------------------------------------------------------------------------- |
| `Qoder/`        | System prompt (`prompt.txt`), tool definitions, planning logic. ([DeepWiki][1]) |
| `Same.dev/`     | Schema for internal tools (`tools.json`), guidelines. ([DeepWiki][1])           |
| `VSCode Agent/` | System prompt, editing / context-gathering strategies. ([DeepWiki][1])          |
| …               | Other agents like Lovable, Trae, Leap.new, Kiro, etc.                           |

### 2. Use Prompts & Tool Definitions

Depending on your needs:

* **System Prompt**: Open the `.txt` or `.md` in the agent folder, and copy or adapt the instructions for your LLM system role.
* **Tool Schema**: If there are `.json` or `.yaml` files defining tools, you can reuse these definitions in your agent logic.
* **Example Interactions / Guidelines**: Some folders might include `.md` `.txt` or `.json` that show how to use / invoke the tools.

### 3. Integrate Into Your Application / Agent

Here’s a rough Python example using a generic OpenAI-like client + agent:

```python
from your_llm_client import LLMClient

# Load system prompt from the repo:
with open("external/system-prompts/Qoder/prompt.txt", "r") as f:
    system_prompt = f.read()

client = LLMClient(api_key="…")

# Build a message / context
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Generate a to-do list for my coding project."},
]

response = client.chat(messages)
print("Agent response:", response)
```

If you also want to use *tools* from the repository:

* Parse the `.json` definitions to build a registry of tools.
* Implement wrappers / adapters in your code to call those tools.

## Risks & Best Practices

* **License risk**: Since it’s GPL-3.0, be careful if your own project is proprietary — linking or embedding GPL content may impose obligations.
* **Security risk**: System prompts can contain sensitive logic or “agent identities.” If you're building a private or commercial system, vet carefully. ([GitHub][2])
* **Maintainability**: If you heavily adapt the prompts, consider keeping a “diff” or documentation on how you modified them — so you can rebase / merge future updates more easily.
* **Attribution**: If you reuse the content in a public-facing way, consider giving credit to the original repository.

## Useful Links

* Repository: **x1xhlol / system-prompts-and-models-of-ai-tools** ([GitHub][2])
* Project overview and motivation by the author ([Jimmy Song][3])
* GitMCP documentation (for integrating as a “Model Context Protocol (MCP)” service) ([gitmcp.io][4])


[1]: https://deepwiki.com/x1xhlol/system-prompts-and-models-of-ai-tools/1.1-repository-structure-and-organization?utm_source=chatgpt.com "Repository Structure and Organization | x1xhlol/system-prompts-and-models-of-ai-tools | DeepWiki"
[2]: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools?utm_source=chatgpt.com "GitHub - x1xhlol/system-prompts-and-models-of-ai-tools: FULL Augment Code, Claude Code, Cluely, CodeBuddy, Comet, Cursor, Devin AI, Junie, Kiro, Leap.new, Lovable, Manus Agent Tools, NotionAI, Orchids.app, Perplexity, Poke, Qoder, Replit, Same.dev, Trae, Traycer AI, VSCode Agent, Warp.dev, Windsurf, Xcode, Z.ai Code, dia & v0. (And other Open Sourced) System Prompts, Internal Tools & AI Models"
[3]: https://jimmysong.io/en/ai/system-prompts-and-models-of-ai-tools/?utm_source=chatgpt.com "System Prompts and Models of AI Tools - A community-curated collection of system prompts and AI tool examples for prompt …"
[4]: https://gitmcp.io/x1xhlol/system-prompts-and-models-of-ai-tools?utm_source=chatgpt.com "GitMCP"
