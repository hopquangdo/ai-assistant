# dqh-ai-core

A thin, reusable layer on the LangChain / LangGraph ecosystem. Task-agnostic:
you give it any LangChain tools, it runs the loop. Every factory returns a stock
LangChain type, so callers keep the full LCEL surface (`|`, `.stream`,
`.with_structured_output`, …).

Distribution `dqh-ai-core`, imported under the `dqh` namespace as `dqh.ai_core`.
Install the provider adapters you need as extras:
`pip install dqh-ai-core[anthropic]` / `dqh-ai-core[openai]`.

## Layout

| Module | Contents |
|---|---|
| `dqh.ai_core.config` | env + settings — `Settings` / `get_settings`, `DEFAULT_MODEL` |
| `dqh.ai_core.llm` | chat-model factory — `get_chat_model` |
| `dqh.ai_core.agents` | LangGraph ReAct wrapper (`Agent`) + deterministic `ToolExecutor` |
| `dqh.ai_core.tools` | tool-authoring helpers (content blocks; re-exports `@tool` etc.) |
| `dqh.ai_core.observability` | token/cost tracking — `Usage`, `UsageTracker` |

Everything is also re-exported from the top-level `dqh.ai_core` namespace.

## What's inside

| Symbol | Use |
|---|---|
| `Agent.create(tools, model=, system=)` | LangGraph ReAct agent. `.run(user_content)` / `.stream(...)`. `user_content` may be a string or a list of content blocks (text + images). |
| `ToolExecutor` / `ToolCall` / `ToolResult` | Deterministic, auditable execution of tools **without** an LLM — for replaying plans or scripted workflow steps. |
| `get_chat_model(...)` | Model factory (`init_chat_model` under the hood). Accepts a `"provider:name"` string, a `BaseChatModel` (pass-through), or `None` / `settings=` to build from `LLM_*` config. `Agent.create(tools)` with no `model=` uses the `None` path. |
| `get_settings()` | Cached `pydantic-settings` `Settings`; reads the environment and the nearest `.env` walking up from cwd. Subclass `Settings` in your app to add fields. |
| `tool`, `BaseTool`, `StructuredTool` | Re-exported from `langchain_core` for authoring tools. |
| `text_block(...)`, `image_block(b64, mime)` | Build multimodal content blocks; return `([image_block(...)], artifact)` from a tool declared `response_format="content_and_artifact"`. |

## Example

```python
from dqh.ai_core import Agent

agent = Agent.create(my_tools, model="anthropic:claude-sonnet-5", system="You sort files.")
messages = agent.run("Organize the images in ./inbox")
```

Or drive it from a `.env` (no explicit `model=`):

```dotenv
LLM_API_KEY=sk-or-...
LLM_MODEL_NAME=google/gemini-2.5-flash          # bare name -> sent as openai:<name>
LLM_BASE_URL=https://openrouter.ai/api/v1       # any OpenAI-compatible endpoint
```

```python
agent = Agent.create(my_tools, system="You sort files.")   # model pulled from the env
```

`get_chat_model()` (the `model=None` path) **requires** all three of `LLM_API_KEY` /
`LLM_MODEL_NAME` / `LLM_BASE_URL` (this project always goes through an OpenAI-compatible
gateway); a missing one raises. `LLM_MODEL_NAME` also accepts `"provider:name"` to force a
provider. `OPENROUTER_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` are accepted as
aliases for `LLM_API_KEY`. Depends only on LangChain packages — nothing here knows about
the filesystem or any specific task. See the `filesystem-tools` package for a ready-made
tool set.
