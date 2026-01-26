import re
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import instaloader
import httpx

from backend.config import get_settings

settings = get_settings()

SESSION_DIR = Path(__file__).parent.parent.parent / ".instagram_sessions"


@dataclass
class InstagramPostData:
    shortcode: str
    caption: Optional[str]
    owner_username: str
    is_video: bool
    video_url: Optional[str]
    image_url: Optional[str]
    post_url: str
    is_carousel: bool = False
    carousel_urls: list[str] = None  # URLs of all carousel images


def extract_shortcode(url: str) -> Optional[str]:
    """Extract shortcode from Instagram URL (post or reel)."""
    patterns = [
        r"instagram\.com/p/([A-Za-z0-9_-]+)",
        r"instagram\.com/reel/([A-Za-z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _get_session_file(username: str) -> Path:
    """Get path to session file for a username."""
    SESSION_DIR.mkdir(exist_ok=True)
    return SESSION_DIR / f"session-{username}"


def _get_loader() -> instaloader.Instaloader:
    """Get configured Instaloader instance with session persistence."""
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
    )

    username = settings.instagram_username
    if not username:
        return loader

    session_file = _get_session_file(username)

    # Try to load existing session
    if session_file.exists():
        try:
            loader.load_session_from_file(username, str(session_file))
            print(f"Loaded Instagram session for {username}")
            return loader
        except Exception as e:
            print(f"Failed to load session: {e}")

    # Fall back to login if we have password
    if settings.instagram_password:
        try:
            loader.login(username, settings.instagram_password)
            loader.save_session_to_file(str(session_file))
            print(f"Logged in and saved session for {username}")
        except Exception as e:
            print(f"Instagram login failed: {e}")

    return loader


def create_session(username: str, password: str) -> bool:
    """
    Create and save a new Instagram session.
    Call this once to set up the session file.
    """
    loader = instaloader.Instaloader()
    try:
        loader.login(username, password)
        session_file = _get_session_file(username)
        loader.save_session_to_file(str(session_file))
        print(f"Session saved to {session_file}")
        return True
    except Exception as e:
        print(f"Login failed: {e}")
        return False


def get_post_data(url: str) -> Optional[InstagramPostData]:
    """
    Fetch post/reel data from Instagram using Instaloader.
    Uses saved session if available.
    """
    shortcode = extract_shortcode(url)
    if not shortcode:
        return None

    try:
        loader = _get_loader()
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        # Check for carousel
        is_carousel = post.typename == "GraphSidecar"
        carousel_urls = []
        if is_carousel:
            try:
                for node in post.get_sidecar_nodes():
                    carousel_urls.append(node.display_url)
            except Exception:
                pass  # Fall back to single image

        return InstagramPostData(
            shortcode=shortcode,
            caption=post.caption,
            owner_username=post.owner_username,
            is_video=post.is_video,
            video_url=post.video_url if post.is_video else None,
            image_url=post.url,
            post_url=f"https://www.instagram.com/p/{shortcode}/",
            is_carousel=is_carousel,
            carousel_urls=carousel_urls if carousel_urls else None,
        )

    except Exception as e:
        print(f"Instagram fetch error: {e}")
        return None


async def download_reel_video(video_url: str) -> Optional[Path]:
    """
    Download Instagram reel video to a temp file.
    Returns path to the downloaded video or None if failed.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(video_url)
            response.raise_for_status()

            # Save to temp file
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp.write(response.content)
            tmp.close()
            return Path(tmp.name)
    except Exception as e:
        print(f"Failed to download reel: {e}")
        return None
