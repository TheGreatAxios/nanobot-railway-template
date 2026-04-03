# nanobot Railway Template

One-click deploy [nanobot](https://github.com/HKUDS/nanobot) on [Railway](https://railway.app) with a web-based config UI and status dashboard.

This template has been refreshed against the current upstream nanobot package and docs as of April 3, 2026. The latest tagged release in `HKUDS/nanobot` is `v0.1.4.post6` from March 27, 2026.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/nanobot-3?referralCode=ayyhbt&utm_medium=integration&utm_source=template&utm_campaign=generic)

## Getting Started

1. Click the **Deploy on Railway** button above
2. Click **Configure Variables** → Set `ADMIN_PASSWORD` to a secure password (12+ characters)
3. Click **Deploy**
4. Once deployed, go to **Settings** → **TCP Proxy** → **Generate** → enter port `8080`
5. Go to the generated URL once the container restarts — login with username `admin` and your password
6. Set up your LLM provider (e.g., OpenRouter, Anthropic, etc.)
7. In Telegram, message [@BotFather](https://t.me/BotFather) to create a bot and get your token
8. Add the Telegram token to the Setup UI, restart the gateway, and boom — you're live

## What you get

- **Web Config UI** — configure providers, channels, tools, and agent defaults from your browser
- **Status Dashboard** — monitor gateway state, uptime, provider/channel status, and live logs
- **Gateway Management** — start, stop, and restart the nanobot gateway from the UI
- **Basic Auth** — password-protected admin panel
- **Persistent Storage** — config and data survive container restarts via Railway volume
- **Env Var Seeding** — optionally pre-configure nanobot via Railway environment variables

## Quick Start

### Deploy to Railway

See the [Getting Started](#getting-started) section above for the step-by-step guide

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
| `NANOBOT_CUSTOM_API_KEY` | API key for a custom OpenAI-compatible endpoint |
| `NANOBOT_CUSTOM_API_BASE` | Base URL for a custom OpenAI-compatible endpoint |
| `NANOBOT_AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `NANOBOT_AZURE_OPENAI_API_BASE` | Azure OpenAI deployment endpoint |
| `NANOBOT_OPENROUTER_API_KEY` | OpenRouter API key (recommended, access to all models) |
| `NANOBOT_ANTHROPIC_API_KEY` | Anthropic API key |
| `NANOBOT_OPENAI_API_KEY` | OpenAI API key |
| `NANOBOT_DEEPSEEK_API_KEY` | DeepSeek API key |
| `NANOBOT_GROQ_API_KEY` | Groq API key (also enables voice transcription) |
| `NANOBOT_GEMINI_API_KEY` | Google Gemini API key |
| `NANOBOT_ZHIPU_API_KEY` | Zhipu GLM API key |
| `NANOBOT_ZAI_API_KEY` | Current Zhipu/ZAI API key name |
| `NANOBOT_DASHSCOPE_API_KEY` | DashScope / Qwen API key |
| `NANOBOT_MOONSHOT_API_KEY` | Moonshot API key |
| `NANOBOT_MINIMAX_API_KEY` | MiniMax API key |
| `NANOBOT_MISTRAL_API_KEY` | Mistral API key |
| `NANOBOT_STEPFUN_API_KEY` | Step Fun API key |
| `NANOBOT_AIHUBMIX_API_KEY` | AiHubMix API key |
| `NANOBOT_SILICONFLOW_API_KEY` | SiliconFlow API key |
| `NANOBOT_VOLCENGINE_API_KEY` | VolcEngine API key |
| `NANOBOT_BYTEPLUS_API_KEY` | BytePlus API key |
| `NANOBOT_OLLAMA_API_BASE` | Ollama base URL |
| `NANOBOT_VLLM_API_BASE` | vLLM base URL |
| `NANOBOT_OVMS_API_BASE` | OVMS base URL |

### Agent Defaults

| Variable | Default | Description |
|---|---|---|
| `NANOBOT_MODEL` | `anthropic/claude-opus-4-5` | Default model |
| `NANOBOT_PROVIDER` | *(auto-detected)* | Default provider name |
| `NANOBOT_MAX_TOKENS` | `8192` | Max tokens per response |
| `NANOBOT_TEMPERATURE` | `0.1` | Sampling temperature |
| `NANOBOT_MAX_TOOL_ITERATIONS` | `200` | Max tool call iterations |
| `NANOBOT_CONTEXT_WINDOW_TOKENS` | `65536` | Context window budget |
| `NANOBOT_MAX_TOOL_RESULT_CHARS` | `16000` | Max chars retained from a tool result |
| `NANOBOT_REASONING_EFFORT` | *(unset)* | Optional reasoning mode (`low`, `medium`, `high`) |
| `NANOBOT_TIMEZONE` | `UTC` | Agent timezone (IANA name) |

### Tools

| Variable | Description |
|---|---|
| `NANOBOT_BRAVE_SEARCH_API_KEY` | Brave Search API key for web search |
| `NANOBOT_WEB_SEARCH_PROVIDER` | Search provider (`brave`, `tavily`, `duckduckgo`, `searxng`, `jina`) |
| `NANOBOT_WEB_SEARCH_BASE_URL` | Base URL for self-hosted SearXNG |

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

Custom, Azure OpenAI, Anthropic, OpenAI, OpenRouter, DeepSeek, Groq, Gemini, Zhipu, DashScope, Moonshot, MiniMax, Mistral, Step Fun, AiHubMix, SiliconFlow, VolcEngine, BytePlus, vLLM, Ollama, OVMS

## Supported Channels

This image now installs the current optional upstream channel extras for Discord, WeCom, WeChat/Weixin, and Matrix in addition to the base package channels. The UI still focuses on the most common channels: Telegram, Discord, Slack, WhatsApp, and Feishu/Lark.

## License & Disclaimer

MIT License — see [LICENSE](LICENSE).

**Use at your own risk.** This template is unaudited. All actions, inputs, and outputs are 100% your responsibility. The bot and template authors assume no liability for any consequences resulting from usage.

[Railway Template →](https://railway.com/deploy/nanobot-3?referralCode=ayyhbt&utm_medium=integration&utm_source=template&utm_campaign=generic)
