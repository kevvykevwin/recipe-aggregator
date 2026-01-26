import re
from typing import Optional
from googleapiclient.discovery import build

from backend.config import get_settings
from backend.models.schemas import VideoMetadata, VideoDetails

settings = get_settings()


def _get_youtube_client():
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_urls_from_text(text: str) -> list[str]:
    """Extract URLs from text (e.g., video description)."""
    url_pattern = r'https?://[^\s<>"\')\]]+|www\.[^\s<>"\')\]]+'
    urls = re.findall(url_pattern, text)
    return [u.rstrip(".,;:") for u in urls]


def get_playlist_videos(playlist_id: str) -> list[VideoMetadata]:
    """Fetch all videos from a YouTube playlist."""
    youtube = _get_youtube_client()
    videos = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item["snippet"]
            video_id = snippet["resourceId"]["videoId"]
            videos.append(
                VideoMetadata(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description"),
                    channel_name=snippet.get("channelTitle"),
                    published_at=snippet.get("publishedAt"),
                    thumbnail_url=snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url"),
                )
            )

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return videos


def get_video_details(video_id: str) -> Optional[VideoDetails]:
    """Fetch detailed information about a single video."""
    try:
        youtube = _get_youtube_client()
        request = youtube.videos().list(part="snippet", id=video_id)
        response = request.execute()

        items = response.get("items", [])
        if not items:
            return None
    except Exception as e:
        print(f"YouTube API error: {e}")
        return None

    snippet = items[0]["snippet"]
    description = snippet.get("description", "")

    return VideoDetails(
        video_id=video_id,
        title=snippet.get("title", ""),
        description=description,
        channel_name=snippet.get("channelTitle"),
        published_at=snippet.get("publishedAt"),
        thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url"),
        tags=snippet.get("tags", []),
        linked_urls=extract_urls_from_text(description),
    )
