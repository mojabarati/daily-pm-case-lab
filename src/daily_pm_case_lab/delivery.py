from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import Manifest


@dataclass(frozen=True)
class GitHubIssueDelivery:
    repository: str

    def deliver(self, case_path: Path, manifest: Manifest) -> str:
        if not os.environ.get("GITHUB_TOKEN") and not os.environ.get("GH_TOKEN"):
            raise RuntimeError("GITHUB_TOKEN or GH_TOKEN is required for GitHub Issue delivery")
        relative = case_path.as_posix()
        title = f"Daily PM Case: {manifest.company} — {manifest.case_title}"
        body = (
            f"A new Daily PM Case Lab exercise is ready.\n\n"
            f"- Company: {manifest.company}\n"
            f"- Category: {manifest.category}\n"
            f"- Difficulty: {manifest.difficulty}\n"
            f"- Quality score: {manifest.quality_score}/100\n"
            f"- Start spoiler-free: [{relative}/01-challenge.md]"
            f"(https://github.com/{self.repository}/blob/main/{relative}/01-challenge.md)\n"
        )
        completed = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                self.repository,
                "--title",
                title,
                "--body",
                body,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"GitHub Issue delivery failed with exit {completed.returncode}")
        output = completed.stdout.strip().splitlines()
        if not output or not output[-1].startswith("https://github.com/"):
            raise RuntimeError("GitHub Issue delivery returned no issue URL")
        return output[-1]
