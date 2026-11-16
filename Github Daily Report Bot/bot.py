"""Telegram bot that sends read-only GitHub activity reports."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, time as datetime_time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


LOGGER = logging.getLogger("github_daily_report_bot")
GITHUB_API_URL = "https://api.github.com"
TELEGRAM_API_URL = "https://api.telegram.org"
API_PAGE_SIZE = 100
MAX_API_PAGES = 10
MAX_TELEGRAM_MESSAGE_LENGTH = 3900


class ConfigurationError(ValueError):
    """Raised when required environment configuration is invalid."""


class GitHubAPIError(RuntimeError):
    """Raised when a GitHub API request fails."""


class TelegramAPIError(RuntimeError):
    """Raised when a Telegram Bot API request fails."""


@dataclass(frozen=True)
class Settings:
    github_token: str = field(repr=False)
    default_repo: str
    telegram_bot_token: str = field(repr=False)
    telegram_chat_id: int = field(repr=False)
    timezone: ZoneInfo
    standup_time: datetime_time
    lookback_hours: int
    llm_enabled: bool

    @classmethod
    def from_mapping(cls, values: dict[str, str]) -> Settings:
        github_token = values.get("GITHUB_TOKEN", "").strip()
        telegram_token = values.get("TELEGRAM_BOT_TOKEN", "").strip()
        repo = values.get("DEFAULT_REPO", "").strip()
        chat_id_text = values.get("TELEGRAM_CHAT_ID", "").strip()
        timezone_name = values.get("TIMEZONE", "").strip()
        standup_text = values.get("STANDUP_TIME", "").strip()
        lookback_text = values.get("LOOKBACK_HOURS", "").strip()

        if not github_token:
            raise ConfigurationError("GITHUB_TOKEN is required.")
        if not telegram_token:
            raise ConfigurationError("TELEGRAM_BOT_TOKEN is required.")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ConfigurationError("DEFAULT_REPO must use the owner/repository format.")
        if not re.fullmatch(r"-?\d+", chat_id_text) or int(chat_id_text) == 0:
            raise ConfigurationError("TELEGRAM_CHAT_ID must be a non-zero numeric chat ID.")
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", standup_text):
            raise ConfigurationError("STANDUP_TIME must use the 24-hour HH:MM format.")

        try:
            zone = ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError):
            raise ConfigurationError("TIMEZONE must be a valid IANA timezone.") from None

        try:
            standup = datetime_time.fromisoformat(standup_text)
        except ValueError:
            raise ConfigurationError("STANDUP_TIME must use the 24-hour HH:MM format.") from None

        try:
            lookback_hours = int(lookback_text)
        except ValueError:
            raise ConfigurationError("LOOKBACK_HOURS must be an integer from 1 to 720.") from None
        if not 1 <= lookback_hours <= 720:
            raise ConfigurationError("LOOKBACK_HOURS must be an integer from 1 to 720.")

        llm_enabled = parse_bool(values.get("LLM_ENABLED", "false"), "LLM_ENABLED")

        return cls(
            github_token=github_token,
            default_repo=repo,
            telegram_bot_token=telegram_token,
            telegram_chat_id=int(chat_id_text),
            timezone=zone,
            standup_time=standup,
            lookback_hours=lookback_hours,
            llm_enabled=llm_enabled,
        )


def parse_bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ConfigurationError(f"{name} must be true/false, 1/0, or yes/no.")


def read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
            raise ConfigurationError(f"Invalid .env entry on line {line_number}.")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_settings(env_path: Path | None = None) -> Settings:
    dotenv_values = read_dotenv(env_path or Path(__file__).with_name(".env"))
    merged = dict(dotenv_values)
    merged.update(os.environ)
    return Settings.from_mapping(merged)


def request_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: int = 40,
    error_type: type[RuntimeError] = RuntimeError,
) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers=headers, method="GET" if body is None else "POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read()
    except HTTPError as error:
        raise error_type(f"API request failed with HTTP {error.code}.") from None
    except TimeoutError:
        raise error_type("API request timed out.") from None
    except URLError as error:
        raise error_type(
            f"API request could not connect ({type(error.reason).__name__})."
        ) from None

    try:
        return json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise error_type("API returned an invalid JSON response.") from None


class GitHubClient:
    def __init__(self, token: str) -> None:
        self._headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-daily-report-bot",
        }

    def _get_pages(self, repo: str, endpoint: str, params: dict[str, str]) -> tuple[list[dict[str, Any]], bool]:
        safe_repo = quote(repo, safe="/")
        records: list[dict[str, Any]] = []
        truncated = False

        for page in range(1, MAX_API_PAGES + 1):
            query = urlencode({**params, "per_page": API_PAGE_SIZE, "page": page})
            url = f"{GITHUB_API_URL}/repos/{safe_repo}/{endpoint}?{query}"
            response = request_json(
                url,
                self._headers,
                timeout=30,
                error_type=GitHubAPIError,
            )
            if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
                raise GitHubAPIError("GitHub returned an unexpected response format.")
            records.extend(response)
            if len(response) < API_PAGE_SIZE:
                break
            if page == MAX_API_PAGES:
                truncated = True
        return records, truncated

    def fetch_report(
        self,
        repo: str,
        lookback_hours: int,
        generated_at: datetime | None = None,
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        since = generated_at.astimezone(timezone.utc) - timedelta(hours=lookback_hours)
        since_text = since.isoformat().replace("+00:00", "Z")
        until_text = generated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

        commits, commits_truncated = self._get_pages(
            repo,
            "commits",
            {"since": since_text, "until": until_text},
        )
        activities, activities_truncated = self._get_pages(
            repo,
            "issues",
            {"state": "all", "since": since_text},
        )

        pull_requests = [item for item in activities if "pull_request" in item]
        issues = [item for item in activities if "pull_request" not in item]
        return {
            "repo": repo,
            "generated_at": generated_at,
            "since": since,
            "commits": commits,
            "pull_requests": pull_requests,
            "issues": issues,
            "truncated": commits_truncated or activities_truncated,
        }


class TelegramClient:
    def __init__(self, token: str) -> None:
        self._token = token

    def call(self, method: str, payload: dict[str, Any]) -> Any:
        url = f"{TELEGRAM_API_URL}/bot{self._token}/{method}"
        response = request_json(
            url,
            {"Content-Type": "application/json"},
            payload=payload,
            timeout=40,
            error_type=TelegramAPIError,
        )
        if not isinstance(response, dict) or response.get("ok") is not True:
            raise TelegramAPIError(f"Telegram method {method} failed.")
        return response.get("result")

    def get_updates(self, offset: int | None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": 30, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        result = self.call("getUpdates", payload)
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise TelegramAPIError("Telegram returned an unexpected updates response.")
        return result

    def send_text(self, chat_id: int, text: str) -> None:
        for part in chunk_text(text):
            self.call("sendMessage", {"chat_id": chat_id, "text": part})


def chunk_text(text: str, max_length: int = MAX_TELEGRAM_MESSAGE_LENGTH) -> list[str]:
    if max_length < 4:
        raise ValueError("max_length must be at least 4.")

    chunks: list[str] = []
    current = ""
    for line in text.splitlines() or [""]:
        if len(line) > max_length:
            line = line[: max_length - 3] + "..."
        candidate = line if not current else f"{current}\n{line}"
        if len(candidate) > max_length:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current or not chunks:
        chunks.append(current)
    return chunks


def _display_name(item: dict[str, Any]) -> str:
    user = item.get("user")
    if isinstance(user, dict) and isinstance(user.get("login"), str):
        return user["login"]
    commit = item.get("commit")
    if isinstance(commit, dict):
        author = commit.get("author")
        if isinstance(author, dict) and isinstance(author.get("name"), str):
            return author["name"]
    return "unknown"


def _title(item: dict[str, Any]) -> str:
    commit = item.get("commit")
    title = commit.get("message") if isinstance(commit, dict) else item.get("title")
    if not isinstance(title, str):
        title = "(untitled)"
    return title.splitlines()[0].strip() or "(untitled)"


def _format_items(items: list[dict[str, Any]], kind: str) -> list[str]:
    lines: list[str] = []
    for item in items[:10]:
        actor = _display_name(item)
        title = _title(item)
        if kind == "commit":
            sha = item.get("sha")
            short_sha = sha[:7] if isinstance(sha, str) else "unknown"
            lines.append(f"- {short_sha} {title} ({actor})")
            continue

        number = item.get("number")
        number_text = f"#{number}" if isinstance(number, int) else "#?"
        state = item.get("state")
        state_text = state if isinstance(state, str) else "unknown"
        lines.append(f"- {number_text} [{state_text}] {title} ({actor})")
    if len(items) > 10:
        lines.append(f"- ...and {len(items) - 10} more")
    return lines


def format_report(report: dict[str, Any], display_timezone: ZoneInfo) -> str:
    generated_at = report["generated_at"].astimezone(display_timezone)
    since = report["since"].astimezone(display_timezone)
    commits = report["commits"]
    pull_requests = report["pull_requests"]
    issues = report["issues"]

    lines = [
        f"GitHub daily report: {report['repo']}",
        f"Period: {since:%Y-%m-%d %H:%M} to {generated_at:%Y-%m-%d %H:%M} ({display_timezone.key})",
        "",
        f"Commits: {len(commits)}",
        *_format_items(commits, "commit"),
        "",
        f"Pull requests updated: {len(pull_requests)}",
        *_format_items(pull_requests, "activity"),
        "",
        f"Issues updated: {len(issues)}",
        *_format_items(issues, "activity"),
    ]
    if not commits and not pull_requests and not issues:
        lines.extend(["", "No activity found in this period."])
    if report["truncated"]:
        lines.extend(["", "Note: results are capped at 1,000 records per GitHub endpoint."])
    return "\n".join(lines)


def send_report(settings: Settings, github: GitHubClient, telegram: TelegramClient) -> None:
    report = github.fetch_report(settings.default_repo, settings.lookback_hours)
    telegram.send_text(
        settings.telegram_chat_id,
        format_report(report, settings.timezone),
    )


def handle_message(
    message: dict[str, Any],
    settings: Settings,
    github: GitHubClient,
    telegram: TelegramClient,
) -> None:
    chat = message.get("chat")
    if not isinstance(chat, dict) or chat.get("id") != settings.telegram_chat_id:
        return

    text = message.get("text")
    if not isinstance(text, str) or not text.startswith("/"):
        return
    command = text.split(maxsplit=1)[0].split("@", maxsplit=1)[0].lower()

    if command in {"/start", "/help"}:
        telegram.send_text(
            settings.telegram_chat_id,
            "GitHub Daily Report Bot\nCommands:\n/report - generate a report now\n/help - show this help",
        )
    elif command == "/report":
        send_report(settings, github, telegram)
    else:
        telegram.send_text(settings.telegram_chat_id, "Unknown command. Use /help.")


def _process_update(
    update: dict[str, Any],
    settings: Settings,
    github: GitHubClient,
    telegram: TelegramClient,
) -> None:
    message = update.get("message")
    if not isinstance(message, dict):
        return

    chat = message.get("chat")
    if not isinstance(chat, dict) or chat.get("id") != settings.telegram_chat_id:
        return
    try:
        handle_message(message, settings, github, telegram)
    except (GitHubAPIError, TelegramAPIError) as error:
        LOGGER.error("Manual report/command failed: %s", error)
        try:
            telegram.send_text(
                settings.telegram_chat_id,
                "The request could not be completed. Check the bot logs for details.",
            )
        except TelegramAPIError as notify_error:
            LOGGER.error("Could not send failure notice: %s", notify_error)


def run_bot(settings: Settings) -> None:
    github = GitHubClient(settings.github_token)
    telegram = TelegramClient(settings.telegram_bot_token)
    offset: int | None = None
    last_sent_date = None

    if settings.llm_enabled:
        LOGGER.warning(
            "LLM_ENABLED is true, but no LLM provider is configured; reports will use deterministic summaries."
        )
    LOGGER.info(
        "Bot started for %s; daily report time is %s (%s).",
        settings.default_repo,
        settings.standup_time.strftime("%H:%M"),
        settings.timezone.key,
    )

    while True:
        try:
            updates = telegram.get_updates(offset)
            for update in updates:
                _process_update(update, settings, github, telegram)
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = max(offset or 0, update_id + 1)

            now = datetime.now(settings.timezone)
            current_time = (now.hour, now.minute)
            configured_time = (settings.standup_time.hour, settings.standup_time.minute)
            if current_time >= configured_time and last_sent_date != now.date():
                try:
                    send_report(settings, github, telegram)
                    last_sent_date = now.date()
                    LOGGER.info("Scheduled report sent.")
                except (GitHubAPIError, TelegramAPIError) as error:
                    LOGGER.error("Scheduled report failed and will be retried: %s", error)
        except TelegramAPIError as error:
            LOGGER.error("Telegram polling failed: %s", error)
            time.sleep(5)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        settings = load_settings()
    except ConfigurationError as error:
        LOGGER.error("Configuration error: %s", error)
        return 2

    try:
        run_bot(settings)
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
