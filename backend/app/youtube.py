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
        "description": channel.get("snippet", {}).get("description", ""),
        "custom_url": channel.get("snippet", {}).get("customUrl"),
        "country": channel.get("snippet", {}).get("country"),
        "published_at": channel.get("snippet", {}).get("publishedAt"),
        "followers": int(stats.get("subscriberCount", 0)),
        "subscriber_count_hidden": bool(stats.get("hiddenSubscriberCount", False)),
        "total_views": int(stats.get("viewCount", 0)),
        "avg_views": 0,
        "total_likes": 0,
        "total_comments": 0,
        "engagement_rate": 0,
        "total_posts": int(stats.get("videoCount", 0)),
        "sampled_videos": 0,
    }


def search_public_channels(query: str, page_token: str | None = None, limit: int = 24) -> dict:
    """Search YouTube channels and fetch their current, public channel statistics."""
    if not YOUTUBE_API_KEY:
        raise YouTubeAPIError("YouTube discovery is not configured; set YOUTUBE_API_KEY on the backend")
    query = query.strip()
    if len(query) < 2:
        raise YouTubeAPIError("Enter at least two characters to search YouTube")

    with httpx.Client(timeout=httpx.Timeout(YOUTUBE_API_TIMEOUT_SECONDS)) as client:
        search = _request(client, "search", {
            "part": "snippet",
            "type": "channel",
            "q": query[:160],
            "maxResults": max(1, min(limit, 50)),
            **({"pageToken": page_token} if page_token else {}),
        })
        search_items = search.get("items", [])
        channel_ids = [item.get("id", {}).get("channelId") for item in search_items]
        channel_ids = [channel_id for channel_id in channel_ids if channel_id]
        channels = _request(client, "channels", {
            "part": "snippet,statistics",
            "id": ",".join(channel_ids),
            "maxResults": len(channel_ids) or 1,
        }).get("items", []) if channel_ids else []

    by_id = {channel["id"]: channel for channel in channels}
    results = []
    for item in search_items:
        channel_id = item.get("id", {}).get("channelId")
        channel = by_id.get(channel_id)
        if not channel:
            continue
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})
        thumbnails = snippet.get("thumbnails", {})
        thumb = thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}
        results.append({
            "channel_id": channel_id,
            "title": snippet.get("title") or item.get("snippet", {}).get("title") or "YouTube creator",
            "description": snippet.get("description") or "",
            "custom_url": snippet.get("customUrl"),
            "country": snippet.get("country"),
            "published_at": snippet.get("publishedAt"),
            "thumbnail_url": thumb.get("url"),
            "subscriber_count": int(stats["subscriberCount"]) if stats.get("subscriberCount") is not None else None,
            "subscriber_count_hidden": bool(stats.get("hiddenSubscriberCount", False)),
            "total_views": int(stats["viewCount"]) if stats.get("viewCount") is not None else None,
            "video_count": int(stats["videoCount"]) if stats.get("videoCount") is not None else None,
            "channel_url": f"https://www.youtube.com/channel/{channel_id}",
        })
    return {
        "query": query,
        "results": results,
        "next_page_token": search.get("nextPageToken"),
        "result_count": len(results),
        "data_source": "YouTube Data API v3",
    }
