import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch

from bot import (
    ConfigurationError,
    GitHubClient,
    Settings,
    chunk_text,
    format_report,
    handle_message,
    parse_bool,
    read_dotenv,
)


class SettingsTests(unittest.TestCase):
    def test_settings_validate_and_parse_values(self):
        settings = Settings.from_mapping(
            {
                "GITHUB_TOKEN": "github-secret",
                "DEFAULT_REPO": "octo/example",
                "TELEGRAM_BOT_TOKEN": "telegram-secret",
                "TELEGRAM_CHAT_ID": "-100123",
                "TIMEZONE": "Asia/Ho_Chi_Minh",
                "STANDUP_TIME": "09:30",
                "LOOKBACK_HOURS": "24",
                "LLM_ENABLED": "false",
            }
        )

        self.assertEqual(settings.default_repo, "octo/example")
        self.assertEqual(settings.telegram_chat_id, -100123)
        self.assertEqual(settings.standup_time.strftime("%H:%M"), "09:30")
        self.assertEqual(settings.lookback_hours, 24)
        self.assertFalse(settings.llm_enabled)

    def test_invalid_repo_is_rejected(self):
        values = {
            "GITHUB_TOKEN": "token",
            "DEFAULT_REPO": "https://github.com/octo/example",
            "TELEGRAM_BOT_TOKEN": "token",
            "TELEGRAM_CHAT_ID": "123",
            "TIMEZONE": "UTC",
            "STANDUP_TIME": "09:00",
            "LOOKBACK_HOURS": "24",
            "LLM_ENABLED": "false",
        }

        with self.assertRaisesRegex(ConfigurationError, "owner/repository"):
            Settings.from_mapping(values)

    def test_boolean_parser_rejects_ambiguous_values(self):
        with self.assertRaisesRegex(ConfigurationError, "LLM_ENABLED"):
            parse_bool("sometimes", "LLM_ENABLED")

    def test_dotenv_parser_keeps_values_private_and_supports_equals(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "# sample\nTOKEN='value=with=equals'\nexport FLAG=true\n",
                encoding="utf-8",
            )
            self.assertEqual(
                read_dotenv(env_path),
                {"TOKEN": "value=with=equals", "FLAG": "true"},
            )


class ReportTests(unittest.TestCase):
    def test_fetch_report_splits_pull_requests_from_issues(self):
        client = GitHubClient("token")
        commits = [{"sha": "abcdef012345", "commit": {"message": "Fix report", "author": {"name": "Dev"}}}]
        activities = [
            {"number": 7, "title": "Feature", "state": "open", "pull_request": {}, "user": {"login": "dev"}},
            {"number": 8, "title": "Bug", "state": "closed", "user": {"login": "dev"}},
        ]
        with patch.object(client, "_get_pages", side_effect=[(commits, False), (activities, False)]):
            report = client.fetch_report(
                "octo/example",
                24,
                generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )

        self.assertEqual(len(report["commits"]), 1)
        self.assertEqual(len(report["pull_requests"]), 1)
        self.assertEqual(len(report["issues"]), 1)

    def test_format_report_includes_period_and_categories(self):
        report = {
            "repo": "octo/example",
            "generated_at": datetime(2026, 1, 2, 12, tzinfo=timezone.utc),
            "since": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
            "commits": [{"sha": "abcdef0", "commit": {"message": "Fix bug"}}],
            "pull_requests": [],
            "issues": [{"number": 4, "title": "Bug", "state": "open"}],
            "truncated": False,
        }

        output = format_report(report, ZoneInfo("UTC"))
        self.assertIn("Commits: 1", output)
        self.assertIn("Pull requests updated: 0", output)
        self.assertIn("Issues updated: 1", output)
        self.assertIn("abcdef0 Fix bug", output)

    def test_chunk_text_respects_telegram_limit(self):
        chunks = chunk_text("line\n" + ("x" * 25) + "\nend", max_length=12)

        self.assertTrue(chunks)
        self.assertTrue(all(len(chunk) <= 12 for chunk in chunks))
        self.assertIn("line", chunks[0])

    def test_commands_from_unapproved_chats_are_ignored(self):
        from unittest.mock import Mock

        settings = Settings.from_mapping(
            {
                "GITHUB_TOKEN": "github-secret",
                "DEFAULT_REPO": "octo/example",
                "TELEGRAM_BOT_TOKEN": "telegram-secret",
                "TELEGRAM_CHAT_ID": "123",
                "TIMEZONE": "UTC",
                "STANDUP_TIME": "09:30",
                "LOOKBACK_HOURS": "24",
                "LLM_ENABLED": "false",
            }
        )
        telegram = Mock()

        handle_message(
            {"chat": {"id": 456}, "text": "/help"},
            settings,
            GitHubClient("token"),
            telegram,
        )

        telegram.send_text.assert_not_called()


if __name__ == "__main__":
    unittest.main()
