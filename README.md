# 4writersBOT

Automated academic writing assistant that integrates with the [4writers.com](https://4writers.com) freelance marketplace. The system monitors available orders, auto-collects those matching your criteria, and runs them through a multi-agent AI pipeline that autonomously produces publication-ready academic essays.

Built with a Telegram bot interface for real-time notifications and order management.

## Architecture

The core engine is a **LangGraph state machine** with 7 specialized agents (bots) connected through conditional edges and feedback loops:

```
Bot 1 (Requirements) → Bot 2 (Writer) → Bot 3 (Citations) →
Bot 4 (Word Count) ↔ Bot 2 (expand/shorten) →
Bot 5 (Quality) ↔ Bot 2 (revise) + Bot 3 (reinsert) →
Bot 6 (AI Detection) → Humanizer ↔ Bot 6 (recheck) →
Bot 5b (Post-Humanization Quality) → Bot 7 (References) → END
```

### Agent Pipeline

| # | Agent | Role | Model |
|---|-------|------|-------|
| 1 | **Requirements Analyzer** | Parses order description + attached PDF/DOCX files, extracts structured requirements (topic, type, structure, citation style, keywords) | Fast (Haiku) |
| 2 | **Writer** | Generates academic text in 6 modes: `initial`, `expand`, `shorten`, `shorten_humanized`, `revise`, `fix_humanized` — implements Strategy pattern | Smart (Sonnet) |
| 3 | **Citation Integrator** | Searches academic papers via Semantic Scholar + OpenAlex, filters by relevance (LLM-verified), inserts APA in-text citations | Fast (Haiku) |
| 4 | **Word Count Checker** | Validates word count against target (pages x 300), triggers expand/shorten loops | Code-based |
| 5 | **Quality Checker** | LLM-based evaluation against 8 academic writing rules with extended thinking enabled | Smart (Sonnet) |
| 6 | **AI Detector** | Checks AI percentage via ZeroGPT; routes to humanizer if above threshold | ZeroGPT API |
| 7 | **References Generator** | Formats APA reference list from verified sources | Code-based |

Additionally:
- **Humanizer** — Uses Undetectable AI API for full-document or sentence-level humanization
- **Post-Humanization Quality Checker (5b)** — Re-validates text integrity after humanization

### Workflow Loops

- **Word Count Loop**: Bot 4 ↔ Bot 2 — expands or shortens text until within target range (max 50 iterations)
- **Quality Loop**: Bot 5 → Bot 2 → Bot 5 — revises text until all 8 rules pass (max 50 iterations)
- **AI Detection Loop**: Bot 6 → Humanizer → Bot 6 — humanizes until AI score ≤ 5% (max 20 iterations)

## Quality Rules

The quality checker enforces these academic writing standards:

1. **Assignment Completion** — Every question in the prompt must be answered with substantive depth
2. **Introduction** — No announcement phrases ("This essay will..."), no dictionary definitions, thesis at the end
3. **Thesis Statement** — Must follow ISO formula (Idea + Support + Order), no announcement form
4. **Citation Placement** — Citations forbidden in introduction, conclusion, and first/last sentences of body paragraphs
5. **Body Paragraph Structure** — Topic sentence → supporting sentences with citations → concluding sentence (5-6 sentences min)
6. **Conclusion** — No citations, no new information, restates thesis, summarizes body
7. **Academic Language** — No contractions, third person only, no rhetorical questions, no informal openers
8. **Citation Accuracy** — Every citation verified against the actual source abstract

## Academic Paper Search

Two-tier search with fallback:

1. **Semantic Scholar API** (primary) — searches by generated keywords, sorted by citation count, year ≥ 2020
2. **OpenAlex API** (fallback) — activates when Semantic Scholar fails or returns insufficient results

Papers are filtered by:
- Must have abstract (> 50 characters)
- Publication year ≥ 2020
- LLM-verified relevance to the essay topic

## Citation Styles

Supports four major styles with dedicated prompt templates:

- **APA** — `(Author, Year)` in-text, alphabetical reference list
- **MLA** — `(Author page)` in-text, Works Cited
- **Chicago** — Footnotes/endnotes or author-date
- **Harvard** — `(Author, Year)` with distinct reference formatting

## Telegram Bot Interface

### Commands & Menu

Persistent reply keyboard with 6 sections:

| Button | Function |
|--------|----------|
| Active Orders | View orders currently being processed |
| Completed | View finished orders |
| Late Orders | Track overdue deadlines |
| Revisions | Orders requiring revision |
| Statistics | Workflow stats (total/completed/failed, words generated, avg AI score) |
| Settings | Toggle auto-collection, configure order criteria |

### Order Actions

Each order card provides inline buttons:
- **View** — Full order description
- **Files** — List attached documents
- **Take** — Accept order on 4writers.com
- **Process with AI** — Trigger the full writing pipeline

### Auto-Collection

Configurable filters for automatic order acceptance:
- Price range (min/max)
- Page count (min/max)
- Order types (Essay, Research Paper, etc.)
- Academic levels (College, High School, University)
- Subjects (Nursing, History, etc.)
- Minimum deadline (hours)

### Real-Time Notifications

Background monitor polls the 4writers API every 5 seconds and sends Telegram notifications for:
- New available orders
- Removed orders
- Newly active orders

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| Bot Framework | aiogram 3.15 |
| AI Orchestration | LangGraph 0.2 |
| LLM Integration | LangChain + OpenRouter (OpenAI-compatible gateway) |
| Academic Search | Semantic Scholar API, OpenAlex API |
| AI Detection | ZeroGPT API |
| Humanization | Undetectable AI API |
| Document Parsing | PyPDF2, python-docx |
| HTTP Client | httpx |
| Database | SQLite |
| Marketplace API | py4writers |
| Containerization | Docker + Docker Compose |
| Package Manager | Poetry |

### LLM Models (via OpenRouter)

Any OpenRouter-compatible model can be used. Default configuration:

| Role | Default Model | Purpose |
|------|---------------|---------|
| Fast | `anthropic/claude-haiku-4.5` | Requirements analysis, citation integration |
| Smart | `anthropic/claude-sonnet-4.5` | Writing, quality checking (with extended thinking) |
| Writer | `anthropic/claude-sonnet-4.5` | Academic text generation |

Easily swappable to GPT-4o, Gemini, Llama, Mistral, or any other model on OpenRouter.

## Project Structure

```
4writersBOT/
├── src/
│   ├── __main__.py                 # Entry point: bot initialization + monitoring
│   ├── config.py                   # Environment configuration
│   ├── store.py                    # User credentials store
│   ├── checkpoint_manager.py       # LangGraph state persistence
│   │
│   ├── agents/                     # AI pipeline agents
│   │   ├── base_agent.py           # Base classes (BaseAgent → PromptBasedAgent → ValidationAgent)
│   │   ├── requirements_analyzer.py
│   │   ├── writer.py
│   │   ├── writer_modes.py         # Strategy pattern: 6 writing modes
│   │   ├── citation_integrator.py
│   │   ├── researcher.py           # Search query generation
│   │   ├── word_count_checker.py
│   │   ├── quality_checker.py
│   │   ├── quality_checker_post_humanization.py
│   │   ├── ai_detector.py
│   │   ├── humanizer.py
│   │   └── references_generator.py
│   │
│   ├── workflows/
│   │   ├── order_workflow.py       # LangGraph state machine definition
│   │   └── state.py                # OrderWorkflowState (35+ fields)
│   │
│   ├── handlers/                   # Telegram bot handlers
│   │   ├── start.py                # /start command
│   │   ├── menu.py                 # Inline keyboard callbacks
│   │   ├── menu_message.py         # Reply keyboard message handlers
│   │   ├── order_handlers.py       # Order view/take/process actions
│   │   └── settings_handlers.py    # FSM-based settings configuration
│   │
│   ├── keyboards/                  # Telegram keyboard layouts
│   │   ├── menu.py                 # Main menu + settings keyboards
│   │   └── order.py                # Order action keyboards
│   │
│   ├── services/
│   │   ├── api_service.py          # py4writers API wrapper
│   │   ├── order_service.py        # Order business logic
│   │   ├── order_monitor.py        # Background polling + notifications
│   │   ├── auto_collector.py       # Auto-accept matching orders
│   │   ├── user_service.py         # User data access
│   │   ├── prompt_manager.py       # Prompt loading + caching
│   │   └── mock_startup.py         # Mock notifications for testing
│   │
│   ├── utils/
│   │   ├── llm_service.py          # OpenRouter LLM integration
│   │   ├── semantic_scholar.py     # Semantic Scholar + OpenAlex search
│   │   ├── openalex.py             # OpenAlex direct client
│   │   ├── zerogpt.py              # ZeroGPT AI detection client
│   │   ├── undetectable_ai.py      # Undetectable AI humanization client
│   │   ├── file_parser.py          # PDF/DOCX content extraction
│   │   ├── prompt_loader.py        # Prompt file resolution
│   │   ├── prompt_selector.py      # Assignment type → prompt mapping
│   │   ├── json_parser.py          # Robust JSON extraction from LLM output
│   │   ├── text_analysis.py        # Text metrics and analysis
│   │   ├── text_converter.py       # Format conversion utilities
│   │   ├── time_parser.py          # Deadline time parsing
│   │   ├── api_helper.py           # HTTP utilities
│   │   └── mock_data.py            # Test fixtures
│   │
│   ├── formatters/
│   │   └── message_formatters.py   # Telegram message formatting
│   │
│   └── db/
│       └── database.py             # SQLite: users, orders, workflows, stages, stats
│
├── prompts/
│   ├── assignment_types/
│   │   └── essay/                  # Essay-specific prompts
│   │       ├── writer_prompt.txt
│   │       ├── writer_expand_prompt.txt
│   │       ├── writer_shorten_prompt.txt
│   │       ├── writer_shorten_humanized_prompt.txt
│   │       ├── writer_revise_prompt.txt
│   │       ├── writer_fix_humanized_prompt.txt
│   │       └── quality_checker_prompt.txt
│   ├── citation_styles/
│   │   ├── apa_instructions.txt
│   │   ├── mla_instructions.txt
│   │   ├── chicago_instructions.txt
│   │   └── harvard_instructions.txt
│   └── shared/                     # Shared across assignment types
│       ├── requirements_extractor_prompt.txt
│       ├── citation_integrator_prompt.txt
│       ├── quality_checker_post_humanization_prompt.txt
│       ├── paper_relevance_check_prompt.txt
│       └── citation_placement_fix_instructions.txt
│
├── data/
│   └── bot.db                      # SQLite database
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── poetry.lock
├── .env.example
├── .gitignore
└── .dockerignore
```

## Database Schema

SQLite with 5 tables:

- **`user_settings`** — Auto-collection toggle, max concurrent orders
- **`order_criteria`** — Filter rules (price, pages, types, levels, subjects, deadline)
- **`workflows`** — Execution records (status, final text, word count, AI score)
- **`workflow_stages`** — Per-stage logs (input/output data, timing, errors)
- **`workflow_stats`** — Aggregated metrics per user

## Setup

### Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenRouter API Key ([openrouter.ai](https://openrouter.ai))
- 4writers.com account credentials

### Installation

```bash
git clone https://github.com/soca1m/4writersBOT.git
cd 4writersBOT
poetry install
```

### Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram Bot API token |
| `OPENROUTER_API_KEY` | OpenRouter gateway key for LLM access |

Optional variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MOCK_API` | `false` | Use mock data for testing |
| `FAST_MODEL` | `anthropic/claude-haiku-4.5` | Model for simple tasks |
| `SMART_MODEL` | `anthropic/claude-sonnet-4.5` | Model for writing/quality |
| `WRITER_MODEL` | `anthropic/claude-sonnet-4.5` | Model for text generation |
| `ANALYZER_MODEL` | `anthropic/claude-haiku-4.5` | Model for analysis |
| `UNDETECTABLE_API_KEY` | — | Undetectable AI API key (for humanization) |
| `TAVILY_API_KEY` | — | Tavily search API key (optional) |

### Running

```bash
poetry run python -m src
```

### Docker

```bash
docker compose up -d
```

The Docker setup includes:
- Persistent SQLite volume (`./data:/app/data`)
- Checkpoint persistence (`./checkpoints.db:/app/checkpoints.db`)
- Automatic restart on failure
- Log rotation (10MB max, 3 files)

## Testing

Run the full workflow test:

```bash
poetry run python test_full_workflow.py
```

Use mock mode for development without real API calls:

```env
USE_MOCK_API=true
```

## Author

**soca1m** — [socalmy2003@gmail.com](mailto:socalmy2003@gmail.com)

## License

This project is proprietary software. All rights reserved.
