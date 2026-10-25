"""Public GitHub repository inspection. Only names/links are presented in the UI."""
import os
import re
import requests

API_ROOT = "https://api.github.com"
TIMEOUT = 10
MAX_REPOS = 5
MAX_FILES_PER_REPO = 3
MAX_FILE_BYTES = 45000

LANGUAGE_SKILLS = {
    "Python": ["python"], "JavaScript": ["javascript"], "TypeScript": ["javascript", "react"],
    "HTML": ["html"], "CSS": ["css"], "SQL": ["sql", "postgresql"],
    "Jupyter Notebook": ["python", "data analysis"], "Java": [], "C": [], "C++": [],
    "Go": [], "Rust": [], "Shell": ["cloud"], "Dockerfile": ["cloud"], "HCL": ["cloud"],
}
FILE_MARKERS = {
    "pyproject.toml": ["python"], "requirements.txt": ["python"], "Pipfile": ["python"],
    "package.json": ["javascript"], "vite.config.js": ["javascript", "react"],
    "vite.config.ts": ["javascript", "react"], "next.config.js": ["javascript", "react"],
    "next.config.mjs": ["javascript", "react"], "manage.py": ["python"],
    "Dockerfile": ["cloud"], "docker-compose.yml": ["cloud"], "docker-compose.yaml": ["cloud"],
    "pytest.ini": ["testing"], "playwright.config.ts": ["testing"], "jest.config.js": ["testing"],
    "alembic.ini": ["sql"], "schema.sql": ["sql"], "requirements-dev.txt": ["python", "testing"],
    "tailwind.config.js": ["css"], "tailwind.config.ts": ["css"],
}


class GitHubServiceError(Exception):
    pass


def _headers():
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(url, params=None):
    try:
        response = requests.get(url, headers=_headers(), params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise GitHubServiceError("GitHub could not be reached. Check your connection and try again.") from exc
    if response.status_code == 404:
        raise GitHubServiceError("That public GitHub user or repository was not found.")
    if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
        raise GitHubServiceError("GitHub's API rate limit was reached. Configure an optional GitHub token or try later.")
    if response.status_code == 401:
        raise GitHubServiceError("The configured GitHub token was rejected. Check GITHUB_TOKEN.")
    if not response.ok:
        raise GitHubServiceError(f"GitHub API request failed (HTTP {response.status_code}).")
    return response.json()


def analyze_github_user(username):
    """Fetch public repositories and inspect a bounded sample of source filenames/content."""
    username = username.strip().removeprefix("@")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", username):
        raise GitHubServiceError("Enter a valid GitHub username (letters, numbers, or hyphens).")
    user = _get(f"{API_ROOT}/users/{username}")
    repos = _get(f"{API_ROOT}/users/{username}/repos", {"per_page": MAX_REPOS, "sort": "updated", "direction": "desc", "type": "owner"})
    repos = [r for r in repos if not r.get("fork")][:MAX_REPOS]
    evidence = {}
    repo_rows = []
    inspected_files = 0
    for repo in repos:
        repo_files = 0
        repo_rows.append({
            "name": repo.get("name", ""),
            "url": repo.get("html_url", ""),
            "language": repo.get("language") or "Not detected",
            "updated_at": (repo.get("updated_at") or "")[:10],
        })
        for skill in LANGUAGE_SKILLS.get(repo.get("language"), []):
            evidence.setdefault(skill, set()).add(f"repository language: {repo.get('language')}")
        try:
            tree = _get(f"{API_ROOT}/repos/{username}/{repo['name']}/git/trees/{repo['default_branch']}", {"recursive": "1"})
            tree_items = tree.get("tree", [])
        except GitHubServiceError:
            continue
        for node in tree_items:
            if node.get("type") != "blob":
                continue
            path = node.get("path", "")
            basename = path.rsplit("/", 1)[-1]
            for skill in FILE_MARKERS.get(basename, []):
                evidence.setdefault(skill, set()).add(f"repository file: {basename}")
            if repo_files >= MAX_FILES_PER_REPO:
                break
            if not path.lower().endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".sql", ".html", ".css")):
                continue
            if node.get("size", MAX_FILE_BYTES + 1) > MAX_FILE_BYTES:
                continue
            inspected_files += 1
            repo_files += 1
            # Only inspect a small source sample to derive skill hints. Never execute repo code.
            try:
                file_data = _get(f"{API_ROOT}/repos/{username}/{repo['name']}/contents/{path}")
                import base64
                content = base64.b64decode(file_data.get("content", "")).decode("utf-8", errors="ignore")[:MAX_FILE_BYTES]
            except (GitHubServiceError, ValueError):
                continue
            lower = content.lower()
            markers = {
                "python": [r"\bdef\s+\w+\s*\(", r"\bimport\s+(django|fastapi|pandas|numpy)"],
                "javascript": [r"\bconst\s+\w+\s*=", r"\bfunction\s+\w+\s*\(", r"\bexport\s+default\b"],
                "react": [r"from\s+['\"]react['\"]", r"\buse(state|effect|memo)\s*\("],
                "sql": [r"\bselect\b.+\bfrom\b", r"\bcreate\s+table\b"],
                "html": [r"<!doctype\s+html", r"<(main|section|form|article)\b"],
                "css": [r"\{[^{}]{0,160}:[^{}]{1,160};"],
                "testing": [r"\b(assert|describe|it|test)\s*\("],
                "security": [r"\b(jwt|oauth|csrf|bcrypt|argon2)\b"],
            }
            for skill, patterns in markers.items():
                if any(re.search(pattern, lower, re.DOTALL) for pattern in patterns):
                    evidence.setdefault(skill, set()).add(f"sampled source file: {basename}")
    labels = {
        "python": "Python", "javascript": "JavaScript", "react": "React", "html": "HTML",
        "css": "CSS", "sql": "SQL / data", "postgresql": "PostgreSQL", "testing": "Software testing",
        "security": "Application security", "cloud": "Cloud / deployment", "data analysis": "Data analysis",
    }
    inferred = [{"skill_id": skill, "skill": labels.get(skill, skill.title()), "evidence": sorted(list(sources))[:4]}
                for skill, sources in sorted(evidence.items())]
    return {
        "username": user.get("login", username),
        "profile_url": user.get("html_url", f"https://github.com/{username}"),
        "public_repos": user.get("public_repos", len(repo_rows)),
        "repositories": repo_rows,
        "inferred_skills": inferred,
        "note": "Repository metadata and a bounded sample of public source files were inspected. These are weak signals of demonstrated activity, not proof of authorship, proficiency, or contribution. Forks are excluded from the displayed list. No repository descriptions are displayed.",
    }
