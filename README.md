# Twenty CRM Agent

AI agent that queries and manages [Twenty CRM](https://twenty.com) data via GraphQL, powered by [LangGraph](https://github.com/langchain-ai/langgraph) with Human-in-the-Loop.

Ask questions in natural language — the agent automatically discovers the GraphQL schema, builds queries, and returns structured results. Write operations (create, update, delete) require explicit user approval.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                        User                          │
│              (CLI Terminal or Web Chat)               │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│               LangGraph Agent (StateGraph)           │
│                                                      │
│  Claude via Anthropic API  ──or──  AWS Bedrock       │
└──────────┬─────────────────────────┬────────────────┘
           │                         │
     ┌─────▼─────┐           ┌──────▼───────┐
     │ Read Tools │           │ Write Tools  │
     │            │           │              │
     │ introspect │           │ mutate       │──► Human-in-the-Loop
     │ query      │           │ (create,     │   (approve / reject)
     └─────┬─────┘           │  update,     │
           │                  │  delete)     │
           │                  └──────┬───────┘
           │                         │
           ▼                         ▼
┌─────────────────────────────────────────────────────┐
│              Twenty CRM  ·  GraphQL API              │
│                    (localhost:3000)                   │
└─────────────────────────────────────────────────────┘
```

**Tools available to the agent:**

| Tool | Type | Description |
|------|------|-------------|
| `introspect_schema` | Read | Discovers GraphQL types, queries, and mutations |
| `query_graphql` | Read | Executes read-only GraphQL queries |
| `mutate_graphql` | Write | Executes mutations — **requires user approval** |

---

## Prerequisites

| Requirement | Minimum version | Purpose |
|-------------|-----------------|---------|
| [Docker](https://docs.docker.com/get-docker/) + Docker Compose | v20+ | Run Twenty CRM locally |
| [Python](https://python.org) | 3.11+ | Run the agent |
| API Key | — | **Anthropic API key** or **AWS Bedrock** access |

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/franco1215/twenty-crm-agent.git
cd twenty-crm-agent
```

### 2. Start Twenty CRM with Docker

```bash
# Generate an application secret
export APP_SECRET=$(openssl rand -base64 32)

# Start containers (Twenty + PostgreSQL + Redis)
docker compose -f docker-compose.twenty.yml up -d
```

> Wait ~60 seconds for the server to be ready. Check with:
> ```bash
> docker compose -f docker-compose.twenty.yml logs twenty-server --tail 5
> ```

### 3. Create a workspace and get your API Key

1. Open **http://localhost:3000** in your browser
2. Create your account and workspace (demo data is generated automatically)
3. Go to **Settings** → **APIs & Webhooks**
4. Click **Generate API Key** and **copy the key** (it's only shown once!)

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```env
# Required
TWENTY_API_KEY=your-twenty-api-key-here

# Option 1: Anthropic API (default)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Option 2: AWS Bedrock (uncomment and configure)
# LLM_PROVIDER=bedrock
# AWS_REGION=us-east-1
# BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20250929-v1:0
```

### 5. Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .venv\Scripts\activate     # Windows

pip install -e .
```

### 6. Run the agent

**CLI mode (terminal):**

```bash
python -m src.cli.main
```

**Web mode (browser):**

```bash
python -m src.web.server
# Open http://localhost:3001
```

---

## Example Questions

### Read operations (executed directly)

| Question | What the agent does |
|----------|---------------------|
| "List all companies" | Introspects schema → builds query → returns list |
| "How many open opportunities do we have?" | Filters opportunities by stage |
| "Who works at Acme Corp?" | Filters people by company |
| "What tasks are due this week?" | Filters tasks by date |
| "Show me details of opportunity X" | Single record query by ID or name |

### Write operations (asks for approval first)

| Question | What the agent does |
|----------|---------------------|
| "Create a company called Test Corp" | Builds mutation → **asks for approval** → executes |
| "Update the contact name to John" | Builds mutation → **asks for approval** → executes |
| "Delete the note with ID abc123" | Builds mutation → **asks for approval** → executes |

---

## Human-in-the-Loop

When the agent needs to create, update, or delete data, it **pauses and asks for your approval** before executing:

### CLI:

```
╭──────────────────────────────────────────────╮
│         Mutation Approval Required            │
│                                               │
│  Create company Test Corp                     │
│                                               │
│  mutation {                                   │
│    createCompany(data: { name: "Test Corp" }) │
│    { id name }                                │
│  }                                            │
│                                               │
│  Approve this operation? [yes/no]: █          │
╰──────────────────────────────────────────────╯
```

### Web:

A banner appears with **Approve** / **Reject** buttons.

Implemented using LangGraph's `interrupt()` mechanism with `MemorySaver` for checkpointing.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | LLM provider: `anthropic` or `bedrock` |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (required if provider=anthropic) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5-20250929` | Claude model to use |
| `AWS_REGION` | `us-east-1` | AWS region for Bedrock |
| `BEDROCK_MODEL_ID` | `anthropic.claude-sonnet-4-5-20250929-v1:0` | Bedrock model ID |
| `TWENTY_CRM_URL` | `http://localhost:3000` | Twenty CRM base URL |
| `TWENTY_API_KEY` | — | Twenty CRM API key (required) |
| `PORT` | `3001` | Web server port |

### Using AWS Bedrock

```env
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20250929-v1:0
# Uses default AWS credential chain (env vars, ~/.aws/credentials, IAM role)
```

---

## Project Structure

```
twenty-crm-agent/
├── src/
│   ├── config.py                # Environment variable configuration
│   ├── llm.py                   # LLM factory: ChatAnthropic or ChatBedrock
│   ├── graphql_client.py        # GraphQL client with introspection
│   ├── agent/
│   │   ├── graph.py             # LangGraph StateGraph with HITL
│   │   ├── tools.py             # Agent tools (introspect, query, mutate)
│   │   ├── prompts.py           # System prompt
│   │   └── state.py             # Graph state definition
│   ├── cli/
│   │   └── main.py              # CLI REPL with Rich
│   └── web/
│       ├── server.py            # FastAPI server
│       └── static/
│           ├── index.html       # Chat UI
│           ├── style.css        # Styles (dark theme)
│           └── app.js           # Chat logic + approval handling
├── tests/
│   └── test_graphql_client.py   # Integration tests
├── docker-compose.twenty.yml    # Twenty CRM Docker setup
├── langgraph.json               # LangGraph Studio/Cloud config
├── pyproject.toml               # Python dependencies
├── .env.example                 # Environment variable template
└── CLAUDE.md                    # Claude Code instructions
```

## Tech Stack

- **[LangGraph](https://github.com/langchain-ai/langgraph)** — Stateful agent framework with Human-in-the-Loop
- **[LangChain](https://github.com/langchain-ai/langchain)** — LLM abstraction (Anthropic + Bedrock)
- **[FastAPI](https://fastapi.tiangolo.com/)** — Async web server
- **[Rich](https://github.com/Textualize/rich)** — Formatted terminal output
- **[httpx](https://www.python-httpx.org/)** — Async HTTP client for GraphQL
- **[Twenty CRM](https://twenty.com/)** — Open-source CRM with GraphQL API

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Twenty CRM won't start | Make sure Docker is running: `docker info` |
| API key error | Confirm you copied the full key into `.env` |
| "Rate limit exceeded" | Twenty limits to 100 req/min — wait and retry |
| Port 3000 in use | Change the port in `docker-compose.twenty.yml` |
| Port 3001 in use | Change `PORT` in `.env` |
| Dependency install error | Confirm Python 3.11+: `python3 --version` |

---

## License

MIT
