from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


def get_youtube_transcript(video_id: str) -> Optional[str]:
    """
    Fetch the transcript for a YouTube video.

    Returns the full transcript as a single string, or None if unavailable.
    """
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "en-US", "en-GB"]
        )

        # Combine all transcript segments into a single string
        full_transcript = " ".join(segment["text"] for segment in transcript_list)
        return full_transcript

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return None
    except Exception:
        # Handle any other unexpected errors
        return None
