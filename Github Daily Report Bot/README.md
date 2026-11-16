# GitHub Daily Report Bot

Telegram bot that reads activity from one GitHub repository and sends a daily report to an allow-listed chat. It uses Python 3.11+ and `tzdata` for IANA timezone support on Windows.

## Configure

The project reads `.env` from its root directory. Existing environment variables take precedence over values in the file.

Required settings:

| Variable | Description |
| --- | --- |
| `GITHUB_TOKEN` | GitHub fine-grained token with read-only access to repository contents, issues, and pull requests. |
| `DEFAULT_REPO` | Repository in `owner/repository` format. |
| `TELEGRAM_BOT_TOKEN` | Token issued by BotFather. |
| `TELEGRAM_CHAT_ID` | Only chat ID allowed to use the bot and receive scheduled reports. |
| `TIMEZONE` | IANA timezone, for example `Asia/Ho_Chi_Minh`. |
| `STANDUP_TIME` | Daily send time in 24-hour `HH:MM` format. |
| `LOOKBACK_HOURS` | Activity period, from 1 to 720 hours. |
| `LLM_ENABLED` | Boolean flag. LLM summaries are not implemented; if true, the bot logs a warning and uses deterministic reports. |

Never commit `.env` or share its tokens. The bot does not print credentials.

## Run on Windows

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python bot.py
```

The process uses Telegram long polling, so it does not require a public inbound endpoint. Keep it running for scheduled reports. If the bot already has a webhook configured, remove it before starting long polling. A report is also available on demand with `/report`; `/start` and `/help` show the command list. If the process starts after the configured send time, it sends that day's scheduled report on startup.

## Test

```powershell
python -m unittest discover -s tests -v
```

Tests use mocks and do not call GitHub or Telegram. The GitHub API calls are read-only; Telegram messages are sent only when the bot is run and an authorized chat or scheduled send triggers them.
