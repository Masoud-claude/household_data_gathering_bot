# 🇨🇦 Canadian Household Financial Data Bot

A production-ready Telegram bot that monitors **20+ trusted Canadian sources** and delivers curated, AI-summarised updates on household and personal finance trends — built for fintech startup founders.

---

## Features

| Feature | Description |
|---|---|
| **Automated Monitoring** | Polls RSS feeds from Statistics Canada, Bank of Canada, CMHC, Angus Reid, Fraser Institute, Financial Post, CBC, BNN, and more — every 6 hours |
| **Smart Filtering** | Keyword-based relevance filter keeps only Canadian household/consumer finance content |
| **AI Summaries** | Claude (`claude-sonnet-4-6`) distils each article into 3–5 founder-relevant bullet points |
| **Deduplication** | SQLite tracks all sent URLs — you will never see the same report twice |
| **Weekly Digest** | Auto-generated every Monday at 8 AM ET with a "Founder's Lens" strategic section |
| **Full Command Set** | `/latest`, `/search`, `/filter`, `/sources`, `/digest` |

---

## Tracked Topics

`#debt` `#housing` `#savings` `#inflation` `#income` `#credit` `#sentiment` `#tax` `#retirement` `#banking` `#generational` `#investment`

---

## Quick Start

### Prerequisites

- Python 3.11+
- A Telegram Bot Token (see below)
- An Anthropic API key (https://console.anthropic.com/)

### 1. Clone and install

```bash
git clone https://github.com/your-org/household-data-bot.git
cd household-data-bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in BOT_TOKEN and ANTHROPIC_API_KEY
```

### 3. Run

```bash
python main.py
```

On first startup, set `POLL_ON_STARTUP=true` in `.env` to immediately fetch articles.

---

## Getting a Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. *Canada Finance Updates*) and a username (must end in `bot`)
4. BotFather replies with your token — copy it into `.env` as `BOT_TOKEN`
5. Send `/start` to your new bot to register your chat for broadcasts

---

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome message + register for broadcasts |
| `/latest` | 5 most recent updates |
| `/search [keyword]` | Search cached updates (e.g. `/search mortgage`) |
| `/filter [tag]` | Filter by topic tag (e.g. `/filter #debt`) |
| `/sources` | Full list of monitored sources |
| `/digest` | On-demand weekly digest with Founder's Lens |

---

## Monitored Sources

### Government & Regulatory
- Statistics Canada (statcan.gc.ca)
- Bank of Canada (bankofcanada.ca)
- Canada Revenue Agency (canada.ca/cra)
- OSFI (osfi-bsif.gc.ca)
- Financial Consumer Agency of Canada (canada.ca/fcac)
- CMHC (cmhc-schl.gc.ca)

### Research & Non-Governmental
- Angus Reid Institute
- Nanos Research
- Canadian Centre for Policy Alternatives (CCPA)
- C.D. Howe Institute
- Broadbent Institute
- MNP Consumer Debt Index
- Equifax Canada
- CPA Canada
- Fraser Institute

### Media & Aggregators
- Financial Post
- Globe and Mail
- CBC News Business
- BNN Bloomberg Canada

---

## Adding New Sources

Edit `bot/sources.py` and append a new `Source` entry to the `SOURCES` list:

```python
Source(
    name="My New Source",
    category="Research",           # "Government" | "Research" | "Media"
    url="https://example.ca",
    feeds=[
        "https://example.ca/feed.rss",
    ],
    extra_keywords=["custom", "keywords"],
),
```

No other changes needed — the monitor, formatter, and scheduler pick it up automatically.

---

## Adding New Topic Tags

Edit the `TOPIC_TAGS` dict in `bot/sources.py`:

```python
"#newtag": ["keyword one", "keyword two", "another phrase"],
```

---

## Deployment

### Docker (recommended)

```bash
docker build -t canada-fin-bot .

docker run -d \
  --name canada-fin-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  canada-fin-bot

docker logs -f canada-fin-bot
```

### Docker Compose

```yaml
version: "3.9"
services:
  bot:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
```

```bash
docker compose up -d
```

### VPS with systemd

Create `/etc/systemd/system/canada-fin-bot.service`:

```ini
[Unit]
Description=Canadian Household Financial Data Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/household-data-bot
EnvironmentFile=/home/ubuntu/household-data-bot/.env
ExecStart=/home/ubuntu/household-data-bot/.venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now canada-fin-bot
sudo journalctl -u canada-fin-bot -f
```

### Railway.app

1. Fork this repo
2. New Project -> Deploy from GitHub Repo
3. Add env vars: `BOT_TOKEN`, `ANTHROPIC_API_KEY`
4. Add a Volume mount at `/app/data` for SQLite persistence
5. Railway auto-detects the Dockerfile and deploys

---

## Architecture

```
main.py
  └── Application (python-telegram-bot v20)
        ├── CommandHandlers  ← bot/commands.py
        ├── ErrorHandler     ← bot/commands.py
        └── AsyncIOScheduler ← bot/scheduler.py
              ├── poll_feeds_job (every 6h)
              │     └── monitor.py -> summarizer.py -> database.py
              └── weekly_digest_job (Monday 08:00 ET)
                    └── summarizer.py -> formatter.py -> broadcast
```

### File Structure

```
household_data_gathering_bot/
├── bot/
│   ├── __init__.py
│   ├── commands.py     # Telegram command handlers + broadcast helpers
│   ├── database.py     # SQLite data layer
│   ├── formatter.py    # HTML message formatting for Telegram
│   ├── monitor.py      # RSS polling and relevance filtering
│   ├── scheduler.py    # APScheduler job definitions
│   ├── sources.py      # Source definitions, keywords, topic tags
│   └── summarizer.py   # Claude API integration
├── data/               # SQLite DB + log files (gitignored)
├── main.py             # Entry point
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | Yes | - | Telegram Bot API token |
| `ANTHROPIC_API_KEY` | Yes | - | Anthropic Claude API key |
| `LOG_LEVEL` | No | `INFO` | DEBUG / INFO / WARNING / ERROR |
| `POLL_ON_STARTUP` | No | `false` | Run immediate poll on bot start |

---

## Cost Estimates

| Usage | Estimated Monthly Cost |
|---|---|
| Anthropic API (claude-sonnet-4-6, ~50 articles/day) | ~$2-5 USD |
| VPS hosting (2 GB RAM, 1 vCPU) | ~$5-10 USD |
| **Total** | **~$7-15 USD/month** |

---

## License

MIT
