"""Repo Agent — LangGraph node factory.

Scans retrieved citation content for ``github.com/{owner}/{repo}`` patterns
and queries the public GitHub REST API to obtain repository metadata.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from app.agents.state import AgentState, RepoInfo

if TYPE_CHECKING:
    import httpx

logger = logging.getLogger(__name__)

# Matches github.com/owner/repo (not raw/blob/tree sub-paths).
_GITHUB_PATTERN = re.compile(
    r"github\.com/([A-Za-z0-9\-_.]+)/([A-Za-z0-9\-_.]+)",
)


def make_repo_enrich_node(http_client: httpx.AsyncClient):
    """Return an async LangGraph node that enriches state with GitHub repo metadata.

    Parameters
    ----------
    http_client:
        A shared ``httpx.AsyncClient`` instance.
    """

    async def repo_enrich(state: AgentState) -> dict:
        hits = state.get("retrieval_hits", [])
        if not hits:
            return {"github_repos": []}

        # Collect unique (owner, repo) pairs from all citation content.
        seen: set[tuple[str, str]] = set()
        for hit in hits:
            for match in _GITHUB_PATTERN.finditer(hit.content):
                owner, repo = match.group(1), match.group(2)
                # Filter out common false-positive suffixes.
                repo = repo.rstrip(".,;:)")
                seen.add((owner.lower(), repo.lower()))

        if not seen:
            logger.info("RepoAgent: no GitHub references found in %d hits", len(hits))
            return {"github_repos": []}

        repos: list[dict[str, Any]] = []
        for owner, repo in seen:
            try:
                resp = await http_client.get(
                    f"https://api.github.com/repos/{owner}/{repo}",
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
                if resp.status_code != 200:
                    logger.warning(
                        "RepoAgent: GitHub API %d for %s/%s", resp.status_code, owner, repo,
                    )
                    continue
                data = resp.json()
                info = RepoInfo(
                    owner=owner,
                    name=data.get("name", repo),
                    description=data.get("description") or "",
                    stars=data.get("stargazers_count", 0),
                    language=data.get("language") or "",
                    topics=data.get("topics", []),
                    html_url=data.get("html_url", f"https://github.com/{owner}/{repo}"),
                )
                repos.append(info.model_dump())
                logger.info("RepoAgent: found %s/%s (%d ★)", owner, repo, info.stars)
            except Exception:
                logger.exception("RepoAgent: error fetching %s/%s", owner, repo)

        return {"github_repos": repos}

    return repo_enrich
