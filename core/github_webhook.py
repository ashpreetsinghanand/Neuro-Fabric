"""
GitHub webhook handler for Neuro-Fabric.

Receives PR merge events on the dev branch and triggers
documentation regeneration for affected tables/schemas.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # "owner/repo"
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


def is_configured() -> bool:
    """Check if GitHub integration is configured."""
    return bool(GITHUB_TOKEN and GITHUB_REPO)


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    if not GITHUB_WEBHOOK_SECRET:
        return True  # Skip verification if no secret configured
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def get_pr_files(pr_number: int) -> list[dict]:
    """Get files changed in a PR."""
    if not is_configured():
        return []
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/files"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
    return []


async def get_recent_prs(state: str = "closed", per_page: int = 10) -> list[dict]:
    """Get recent PRs from the configured repo."""
    if not is_configured():
        return []
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    params = {"state": state, "per_page": per_page, "sort": "updated", "direction": "desc"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code == 200:
            return [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "merged": pr.get("merged_at") is not None,
                    "author": pr["user"]["login"],
                    "updated_at": pr["updated_at"],
                    "url": pr["html_url"],
                    "base_branch": pr["base"]["ref"],
                }
                for pr in resp.json()
            ]
    return []


async def get_file_content(path: str, ref: str = "main") -> dict:
    """Get a file's content from GitHub."""
    if not is_configured():
        return {"error": "GitHub not configured"}
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    params = {"ref": ref}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code == 200:
            data = resp.json()
            import base64
            content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
            return {"path": path, "content": content, "sha": data.get("sha", ""), "size": data.get("size", 0)}
    return {"error": f"File not found: {path}"}


def parse_webhook_payload(payload: dict) -> dict[str, Any]:
    """
    Parse GitHub webhook payload for PR merge events.
    Returns info about what changed and whether doc regeneration is needed.
    """
    action = payload.get("action", "")
    pr = payload.get("pull_request", {})
    merged = pr.get("merged", False)
    base_branch = pr.get("base", {}).get("ref", "")

    result = {
        "action": action,
        "pr_number": pr.get("number"),
        "title": pr.get("title", ""),
        "merged": merged,
        "base_branch": base_branch,
        "should_regenerate": False,
        "changed_files": [],
    }

    # Only trigger on PR merge to dev branch
    if action == "closed" and merged and base_branch == "dev":
        result["should_regenerate"] = True
        logger.info(
            "PR #%s merged to dev: '%s' - will trigger doc regeneration",
            result["pr_number"], result["title"]
        )

    return result


async def handle_webhook(payload: dict) -> dict:
    """
    Full webhook handler: parse, determine action, and respond.
    If a PR is merged to dev, returns instructions for doc regeneration.
    """
    parsed = parse_webhook_payload(payload)

    if parsed["should_regenerate"]:
        # Get the files changed in this PR
        files = await get_pr_files(parsed["pr_number"])
        changed = [
            {"filename": f["filename"], "status": f["status"], "changes": f.get("changes", 0)}
            for f in files
        ]
        parsed["changed_files"] = changed

        # Determine which SQL/schema files changed
        schema_files = [f for f in changed if f["filename"].endswith((".sql", ".py"))]
        parsed["schema_changes"] = len(schema_files)
        parsed["message"] = (
            f"PR #{parsed['pr_number']} merged to dev. "
            f"{len(changed)} files changed ({len(schema_files)} schema-related). "
            "Documentation regeneration triggered."
        )
    else:
        parsed["message"] = f"PR event '{parsed['action']}' - no action needed."

    return parsed
