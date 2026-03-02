import asyncio
import base64
import json
import os
import re
import secrets
import signal
import time
from collections import deque
from pathlib import Path

from starlette.applications import Starlette
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
)
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates

def _get_nanobot_config():
    """Lazy import to avoid crashes if nanobot isn't fully initialized."""
    from nanobot.config.loader import convert_keys, convert_to_camel, load_config, save_config
    from nanobot.config.schema import Config
    return convert_keys, convert_to_camel, load_config, save_config, Config

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
SECRET_FIELDS = {"api_key", "apiKey", "token", "app_secret", "appSecret", "encrypt_key", "encryptKey", "verification_token", "verificationToken"}

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_urlsafe(16)
    print(f"Generated admin password: {ADMIN_PASSWORD}")

# --- Optional env var seeding into config on first boot ---
ENV_CONFIG_MAP = {
    # Providers
    "NANOBOT_OPENROUTER_API_KEY": ("providers", "openrouter", "api_key"),
    "NANOBOT_ANTHROPIC_API_KEY": ("providers", "anthropic", "api_key"),
    "NANOBOT_OPENAI_API_KEY": ("providers", "openai", "api_key"),
    "NANOBOT_DEEPSEEK_API_KEY": ("providers", "deepseek", "api_key"),
    "NANOBOT_GROQ_API_KEY": ("providers", "groq", "api_key"),
    "NANOBOT_GEMINI_API_KEY": ("providers", "gemini", "api_key"),
    "NANOBOT_ZHIPU_API_KEY": ("providers", "zhipu", "api_key"),
    # Agent defaults
    "NANOBOT_MODEL": ("agents", "defaults", "model"),
    "NANOBOT_PROVIDER": ("agents", "defaults", "provider"),
    "NANOBOT_MAX_TOKENS": ("agents", "defaults", "max_tokens"),
    "NANOBOT_TEMPERATURE": ("agents", "defaults", "temperature"),
    "NANOBOT_MAX_TOOL_ITERATIONS": ("agents", "defaults", "max_tool_iterations"),
    # Tools
    "NANOBOT_BRAVE_SEARCH_API_KEY": ("tools", "web", "search", "api_key"),
    # Channels - Telegram
    "NANOBOT_TELEGRAM_ENABLED": ("channels", "telegram", "enabled"),
    "NANOBOT_TELEGRAM_TOKEN": ("channels", "telegram", "token"),
    # Channels - Discord
    "NANOBOT_DISCORD_ENABLED": ("channels", "discord", "enabled"),
    "NANOBOT_DISCORD_TOKEN": ("channels", "discord", "token"),
    # Channels - Slack
    "NANOBOT_SLACK_ENABLED": ("channels", "slack", "enabled"),
    "NANOBOT_SLACK_BOT_TOKEN": ("channels", "slack", "token"),
    "NANOBOT_SLACK_APP_TOKEN": ("channels", "slack", "app_token"),
    # Channels - WhatsApp
    "NANOBOT_WHATSAPP_ENABLED": ("channels", "whatsapp", "enabled"),
    # Channels - Feishu
    "NANOBOT_FEISHU_ENABLED": ("channels", "feishu", "enabled"),
    "NANOBOT_FEISHU_APP_ID": ("channels", "feishu", "app_id"),
    "NANOBOT_FEISHU_APP_SECRET": ("channels", "feishu", "app_secret"),
}

NUMERIC_FIELDS = {"max_tokens", "temperature", "max_tool_iterations"}
BOOLEAN_FIELDS = {"enabled"}


def seed_config_from_env():
    """Seed nanobot config.json from environment variables on first boot."""
    config_path = Path.home() / ".nanobot" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text())
        except (json.JSONDecodeError, OSError):
            existing = {}
    else:
        existing = {}

    changed = False
    for env_var, path in ENV_CONFIG_MAP.items():
        value = os.environ.get(env_var)
        if not value:
            continue

        # Convert types
        field_name = path[-1]
        if field_name in BOOLEAN_FIELDS:
            value = value.lower() in ("true", "1", "yes")
        elif field_name in NUMERIC_FIELDS:
            try:
                value = float(value) if "." in str(value) else int(value)
            except ValueError:
                continue

        # Navigate/create nested dict
        obj = existing
        for key in path[:-1]:
            if key not in obj:
                obj[key] = {}
            obj = obj[key]

        # Only set if not already configured
        if path[-1] not in obj or not obj[path[-1]]:
            obj[path[-1]] = value
            changed = True

    if changed:
        config_path.write_text(json.dumps(existing, indent=2))
        print("Config seeded from environment variables")


seed_config_from_env()


class BasicAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn):
        if "Authorization" not in conn.headers:
            return None

        auth = conn.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != "basic":
                return None
            decoded = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError):
            raise AuthenticationError("Invalid credentials")

        username, _, password = decoded.partition(":")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            return AuthCredentials(["authenticated"]), SimpleUser(username)

        raise AuthenticationError("Invalid credentials")


def require_auth(request: Request):
    if not request.user.is_authenticated:
        return PlainTextResponse(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="nanobot"'},
        )
    return None


class GatewayManager:
    def __init__(self):
        self.process: asyncio.subprocess.Process | None = None
        self.state = "stopped"
        self.logs: deque[str] = deque(maxlen=500)
        self.start_time: float | None = None
        self.restart_count = 0
        self._read_tasks: list[asyncio.Task] = []

    async def start(self):
        if self.process and self.process.returncode is None:
            return
        self.state = "starting"
        try:
            self.process = await asyncio.create_subprocess_exec(
                "nanobot", "gateway",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.state = "running"
            self.start_time = time.time()
            task = asyncio.create_task(self._read_output())
            self._read_tasks.append(task)
        except Exception as e:
            self.state = "error"
            self.logs.append(f"Failed to start gateway: {e}")

    async def stop(self):
        if not self.process or self.process.returncode is not None:
            self.state = "stopped"
            return
        self.state = "stopping"
        self.process.terminate()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=10)
        except asyncio.TimeoutError:
            self.process.kill()
            await self.process.wait()
        self.state = "stopped"
        self.start_time = None

    async def restart(self):
        await self.stop()
        self.restart_count += 1
        await self.start()

    async def _read_output(self):
        try:
            while self.process and self.process.stdout:
                line = await self.process.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                cleaned = ANSI_ESCAPE.sub("", decoded)
                self.logs.append(cleaned)
        except asyncio.CancelledError:
            return
        if self.process and self.process.returncode is not None and self.state == "running":
            self.state = "error"
            self.logs.append(f"Gateway exited with code {self.process.returncode}")

    def get_status(self) -> dict:
        pid = None
        if self.process and self.process.returncode is None:
            pid = self.process.pid
        uptime = None
        if self.start_time and self.state == "running":
            uptime = int(time.time() - self.start_time)
        return {
            "state": self.state,
            "pid": pid,
            "uptime": uptime,
            "restart_count": self.restart_count,
        }


gateway = GatewayManager()
config_lock = asyncio.Lock()


def mask_secrets(data, _path=""):
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k in SECRET_FIELDS and isinstance(v, str) and v:
                result[k] = v[:8] + "***" if len(v) > 8 else "***"
            else:
                result[k] = mask_secrets(v, f"{_path}.{k}")
        return result
    if isinstance(data, list):
        return [mask_secrets(item, _path) for item in data]
    return data


def _collect_secret_values(data, field_name):
    values = []
    if isinstance(data, dict):
        for k, v in data.items():
            if k == field_name and isinstance(v, str):
                values.append(v)
            else:
                values.extend(_collect_secret_values(v, field_name))
    elif isinstance(data, list):
        for item in data:
            values.extend(_collect_secret_values(item, field_name))
    return values


def merge_secrets(new_data, existing_data):
    if isinstance(new_data, dict) and isinstance(existing_data, dict):
        result = {}
        for k, v in new_data.items():
            if k in SECRET_FIELDS and isinstance(v, str) and (v.endswith("***") or v == ""):
                result[k] = existing_data.get(k, "")
            else:
                result[k] = merge_secrets(v, existing_data.get(k, {}))
        return result
    return new_data


async def homepage(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    return templates.TemplateResponse(request, "index.html")


async def health(request: Request):
    return JSONResponse({"status": "ok", "gateway": gateway.state})


async def api_config_get(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    convert_keys, convert_to_camel, load_config, save_config, Config = _get_nanobot_config()
    config = load_config()
    data = convert_to_camel(config.model_dump())
    return JSONResponse(mask_secrets(data))


async def api_config_put(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    try:
        convert_keys, convert_to_camel, load_config, save_config, Config = _get_nanobot_config()
        restart = body.pop("_restartGateway", False)

        async with config_lock:
            existing_config = load_config()
            existing_data = convert_to_camel(existing_config.model_dump())

            merged = merge_secrets(body, existing_data)
            snake_data = convert_keys(merged)

            try:
                new_config = Config.model_validate(snake_data)
            except Exception as e:
                err_msg = str(e)
                for field in SECRET_FIELDS:
                    for val in _collect_secret_values(snake_data, field):
                        if val and len(val) > 3:
                            err_msg = err_msg.replace(val, "***")
                return JSONResponse({"error": f"Validation error: {err_msg}"}, status_code=400)

            save_config(new_config)

        if restart:
            asyncio.create_task(gateway.restart())

        return JSONResponse({"ok": True, "restarting": restart})
    except Exception as e:
        print(f"Config save error: {type(e).__name__}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_status(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    convert_keys, convert_to_camel, load_config, save_config, Config = _get_nanobot_config()
    config = load_config()
    data = config.model_dump()

    providers = {}
    for name, prov in data["providers"].items():
        providers[name] = {"configured": bool(prov.get("api_key"))}

    channels = {}
    for name, chan in data["channels"].items():
        channels[name] = {"enabled": chan.get("enabled", False)}

    cron_dir = Path.home() / ".nanobot" / "cron"
    cron_jobs = []
    if cron_dir.exists():
        for f in cron_dir.glob("*.json"):
            try:
                cron_jobs.append(json.loads(f.read_text()))
            except Exception:
                pass

    return JSONResponse({
        "gateway": gateway.get_status(),
        "providers": providers,
        "channels": channels,
        "cron": {"count": len(cron_jobs), "jobs": cron_jobs},
    })


async def api_logs(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    return JSONResponse({"lines": list(gateway.logs)})


async def api_gateway_start(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    asyncio.create_task(gateway.start())
    return JSONResponse({"ok": True})


async def api_gateway_stop(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    asyncio.create_task(gateway.stop())
    return JSONResponse({"ok": True})


async def api_gateway_restart(request: Request):
    auth_err = require_auth(request)
    if auth_err:
        return auth_err
    asyncio.create_task(gateway.restart())
    return JSONResponse({"ok": True})


async def auto_start_gateway():
    try:
        _, _, load_config, _, _ = _get_nanobot_config()
        config = load_config()
        if not config.get_api_key():
            return
    except Exception:
        return
    asyncio.create_task(gateway.start())



routes = [
    Route("/", homepage),
    Route("/health", health),
    Route("/api/config", api_config_get, methods=["GET"]),
    Route("/api/config", api_config_put, methods=["PUT"]),
    Route("/api/status", api_status),
    Route("/api/logs", api_logs),
    Route("/api/gateway/start", api_gateway_start, methods=["POST"]),
    Route("/api/gateway/stop", api_gateway_stop, methods=["POST"]),
    Route("/api/gateway/restart", api_gateway_restart, methods=["POST"]),
]

app = Starlette(
    routes=routes,
    middleware=[Middleware(AuthenticationMiddleware, backend=BasicAuthBackend())],
    on_startup=[auto_start_gateway],
    on_shutdown=[gateway.stop],
)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info", loop="asyncio")
    server = uvicorn.Server(config)

    def handle_signal():
        loop.create_task(gateway.stop())
        server.should_exit = True

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    loop.run_until_complete(server.serve())
