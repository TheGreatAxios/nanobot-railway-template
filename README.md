# nanobot Railway Template

One-click deploy [nanobot](https://github.com/HKUDS/nanobot) on [Railway](https://railway.app) with a web-based config UI and status dashboard.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template/nanobot)

## What you get

- **Web Config UI** — configure providers, channels, tools, and agent defaults from your browser
- **Status Dashboard** — monitor gateway state, uptime, provider/channel status, and live logs
- **Gateway Management** — start, stop, and restart the nanobot gateway from the UI
- **Basic Auth** — password-protected admin panel
- **Persistent Storage** — config and data survive container restarts via Railway volume
- **Env Var Seeding** — optionally pre-configure nanobot via Railway environment variables

## Quick Start

### Deploy to Railway

1. Click the "Deploy on Railway" button above
2. Set the `ADMIN_PASSWORD` environment variable (or a random one will be generated and printed to logs)
3. Attach a volume mounted at `/data`
4. Optionally set any of the environment variables below to pre-configure nanobot
5. Open your app URL — you'll be prompted for credentials (default username: `admin`)
6. Once setup is complete, remove the public endpoint from your Railway service

### Run Locally with Docker

```bash
docker build -t nanobot .
docker run --rm -it -p 8080:8080 -e PORT=8080 -e ADMIN_PASSWORD=changeme -v nanobot-data:/data nanobot
```

Open `http://localhost:8080` and log in with `admin` / `changeme`.

## Environment Variables

All nanobot-specific variables are **optional**. If set, they seed the config on first boot (existing config values are not overwritten).

### Web UI

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | Web server port |
| `ADMIN_USERNAME` | `admin` | Basic auth username |
| `ADMIN_PASSWORD` | *(generated)* | Basic auth password. If unset, a random password is generated and printed to stdout |

### Provider API Keys

| Variable | Description |
|---|---|
| `NANOBOT_OPENROUTER_API_KEY` | OpenRouter API key (recommended, access to all models) |
| `NANOBOT_ANTHROPIC_API_KEY` | Anthropic API key |
| `NANOBOT_OPENAI_API_KEY` | OpenAI API key |
| `NANOBOT_DEEPSEEK_API_KEY` | DeepSeek API key |
| `NANOBOT_GROQ_API_KEY` | Groq API key (also enables voice transcription) |
| `NANOBOT_GEMINI_API_KEY` | Google Gemini API key |
| `NANOBOT_ZHIPU_API_KEY` | Zhipu GLM API key |

### Agent Defaults

| Variable | Default | Description |
|---|---|---|
| `NANOBOT_MODEL` | `anthropic/claude-opus-4-5` | Default model |
| `NANOBOT_PROVIDER` | *(auto-detected)* | Default provider name |
| `NANOBOT_MAX_TOKENS` | `8192` | Max tokens per response |
| `NANOBOT_TEMPERATURE` | `0.7` | Sampling temperature |
| `NANOBOT_MAX_TOOL_ITERATIONS` | `20` | Max tool call iterations |

### Tools

| Variable | Description |
|---|---|
| `NANOBOT_BRAVE_SEARCH_API_KEY` | Brave Search API key for web search |

### Channels

| Variable | Description |
|---|---|
| `NANOBOT_TELEGRAM_ENABLED` | Enable Telegram (`true`/`false`) |
| `NANOBOT_TELEGRAM_TOKEN` | Telegram bot token from @BotFather |
| `NANOBOT_DISCORD_ENABLED` | Enable Discord (`true`/`false`) |
| `NANOBOT_DISCORD_TOKEN` | Discord bot token |
| `NANOBOT_SLACK_ENABLED` | Enable Slack (`true`/`false`) |
| `NANOBOT_SLACK_BOT_TOKEN` | Slack bot token (`xoxb-...`) |
| `NANOBOT_SLACK_APP_TOKEN` | Slack app-level token (`xapp-...`) |
| `NANOBOT_WHATSAPP_ENABLED` | Enable WhatsApp (`true`/`false`) |
| `NANOBOT_FEISHU_ENABLED` | Enable Feishu/Lark (`true`/`false`) |
| `NANOBOT_FEISHU_APP_ID` | Feishu App ID |
| `NANOBOT_FEISHU_APP_SECRET` | Feishu App Secret |

## Architecture

```
Railway Container
├── Python Web Server (Starlette + uvicorn)
│   ├── / — Config editor + status dashboard
│   ├── /health — Health check (no auth)
│   └── /api/* — Config, status, logs, gateway control
└── nanobot gateway — managed as async subprocess
```

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | Yes | Web UI |
| `GET` | `/health` | No | Health check |
| `GET` | `/api/config` | Yes | Get config (secrets masked) |
| `PUT` | `/api/config` | Yes | Save config |
| `GET` | `/api/status` | Yes | Gateway, provider, channel status |
| `GET` | `/api/logs` | Yes | Recent gateway log lines |
| `POST` | `/api/gateway/start` | Yes | Start gateway |
| `POST` | `/api/gateway/stop` | Yes | Stop gateway |
| `POST` | `/api/gateway/restart` | Yes | Restart gateway |

## Supported Providers

Anthropic, OpenAI, OpenRouter, DeepSeek, Groq, Gemini, Zhipu, vLLM

## Supported Channels

Telegram, Discord, Slack, WhatsApp (via bridge), Feishu/Lark
