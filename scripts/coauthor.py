
#!/usr/bin/env python3

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API = "https://api.github.com/users/{}"
TIMEOUT = 10
USER_AGENT = "coauthor-line-script"
EXIT_ERROR = 2

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")


class GitHubAPIError(Exception):
    """Raised when the GitHub API request fails."""


def fetch_user(username: str) -> dict[str, Any]:
    """Fetch a GitHub user profile."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = API.format(urllib.parse.quote(username, safe=""))
    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.load(response)

    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            message = f"GitHub user '{username}' was not found."
        elif exc.code == 401:
            message = "GitHub authentication failed. Check your token."
        elif exc.code == 403:
            message = (
                "GitHub API access forbidden or rate limit exceeded. "
                "Check your token and API limits."
            )
        else:
            message = f"GitHub API returned HTTP {exc.code}: {exc.reason}"

        raise GitHubAPIError(message) from exc

    except urllib.error.URLError as exc:
        raise GitHubAPIError(
            f"Network error while contacting GitHub: {exc.reason}"
        ) from exc

    except TimeoutError as exc:
        raise GitHubAPIError("GitHub API request timed out.") from exc

    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GitHubAPIError("GitHub returned invalid JSON.") from exc

    if not isinstance(data, dict):
        raise GitHubAPIError("Unexpected GitHub API response format.")

    if not isinstance(data.get("id"), int) or isinstance(data.get("id"), bool):
        raise GitHubAPIError("GitHub API response is missing a valid user ID.")

    if not isinstance(data.get("login"), str) or not data["login"]:
        raise GitHubAPIError("GitHub API response is missing a valid login.")

    return data


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print(f"Usage: {argv[0]} <github-username>")
        return 0 if len(argv) == 2 else 1

    username = argv[1].strip()

    if not USERNAME_PATTERN.fullmatch(username):
        print("error: invalid GitHub username", file=sys.stderr)
        return 1

    try:
        user = fetch_user(username)
    except GitHubAPIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    login = user["login"]
    display_name = user.get("name") or login
    display_name = " ".join(display_name.split())

    noreply_email = f"{user['id']}+{login}@users.noreply.github.com"
    print(f"Co-authored-by: {display_name} <{noreply_email}>")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))


