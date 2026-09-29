"""Read public YouTube channel data and normalize it for creator metrics."""

import re
from urllib.parse import urlparse

import httpx

from app.config import YOUTUBE_API_KEY, YOUTUBE_API_TIMEOUT_SECONDS

API_ROOT = "https://www.googleapis.com/youtube/v3"
CHANNEL_ID_PATTERN = re.compile(r"^UC[a-zA-Z0-9_-]{22}$")


class YouTubeAPIError(Exception):
    """A safe, user-facing failure while reading YouTube public data."""


def _channel_lookup(account_username: str, profile_url: str | None) -> dict[str, str]:
    candidate = (profile_url or "").strip() or account_username.strip()
    if candidate.startswith("http"):
        parsed = urlparse(candidate)
        if parsed.hostname not in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            raise YouTubeAPIError("YouTube profile URL must use youtube.com")
        path = parsed.path.strip("/")
        channel_match = re.match(r"^channel/(UC[a-zA-Z0-9_-]{22})$", path)
        if channel_match:
            return {"id": channel_match.group(1)}
        handle_match = re.match(r"^(@[^/]+)", path)
        if handle_match:
            return {"forHandle": handle_match.group(1)}
        custom_match = re.match(r"^(?:user|c)/([^/]+)", path)
        if custom_match:
            return {"forUsername": custom_match.group(1)}
        raise YouTubeAPIError("Use a YouTube channel URL or @handle URL")

    candidate = candidate.removeprefix("@").strip()
    if CHANNEL_ID_PATTERN.fullmatch(candidate):
        return {"id": candidate}
    if not candidate:
        raise YouTubeAPIError("Add a YouTube channel ID or @handle to this account")
    return {"forHandle": f"@{candidate}"}


def _request(client: httpx.Client, resource: str, params: dict) -> dict:
    try:
        response = client.get(f"{API_ROOT}/{resource}", params={**params, "key": YOUTUBE_API_KEY})
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise YouTubeAPIError("YouTube API request timed out") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            raise YouTubeAPIError("YouTube API rejected the key or daily quota was exceeded") from exc
        if exc.response.status_code == 404:
            raise YouTubeAPIError("YouTube channel was not found") from exc
        raise YouTubeAPIError(f"YouTube API returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise YouTubeAPIError("Could not connect to the YouTube API") from exc
    try:
        return response.json()
    except ValueError as exc:
        raise YouTubeAPIError("YouTube API returned an invalid response") from exc


def fetch_channel_metrics(account_username: str, profile_url: str | None = None) -> dict:
    """Fetch only raw, public channel statistics (no computed engagement metrics)."""
    if not YOUTUBE_API_KEY:
        raise YouTubeAPIError("YouTube sync is not configured; set YOUTUBE_API_KEY on the backend")

    timeout = httpx.Timeout(YOUTUBE_API_TIMEOUT_SECONDS)
    with httpx.Client(timeout=timeout) as client:
        channels = _request(client, "channels", {
            "part": "snippet,statistics",
            **_channel_lookup(account_username, profile_url),
            "maxResults": 1,
        }).get("items", [])
        if not channels:
            raise YouTubeAPIError("No public YouTube channel matched this account")

        channel = channels[0]
        stats = channel.get("statistics", {})

    return {
        "channel_id": channel["id"],
        "title": channel.get("snippet", {}).get("title"),
        "followers": int(stats.get("subscriberCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "avg_views": 0,
        "total_likes": 0,
        "total_comments": 0,
        "engagement_rate": 0,
        "total_posts": int(stats.get("videoCount", 0)),
        "sampled_videos": 0,
    }
