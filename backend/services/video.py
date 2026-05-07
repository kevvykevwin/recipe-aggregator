import base64
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from openai import OpenAI
from moviepy.editor import VideoFileClip

from backend.config import get_settings

settings = get_settings()


@dataclass
class VideoExtraction:
    transcript: Optional[str]
    frames: list[str]  # base64 encoded images
    duration_seconds: float


def _get_openai_client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def _extract_audio_and_transcribe(video_path: Path) -> Optional[str]:
    """Extract audio from video and transcribe with Whisper."""
    if not settings.openai_api_key:
        return None

    client = _get_openai_client()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as audio_file:
        try:
            clip = VideoFileClip(str(video_path))
            clip.audio.write_audiofile(
                audio_file.name,
                codec="mp3",
                verbose=False,
                logger=None,
            )
            clip.close()

            with open(audio_file.name, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text",
                )
            return transcription
        except Exception:
            return None


def _extract_key_frames(video_path: Path, num_frames: int = 5) -> list[str]:
    """Extract evenly spaced frames from video as base64 JPEG."""
    frames = []

    try:
        clip = VideoFileClip(str(video_path))
        duration = clip.duration

        # Get frames at evenly spaced intervals
        timestamps = [duration * i / (num_frames + 1) for i in range(1, num_frames + 1)]

        for ts in timestamps:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as frame_file:
                frame = clip.get_frame(ts)
                # moviepy returns numpy array, save as image
                import numpy as np
                from PIL import Image

                img = Image.fromarray(np.uint8(frame))
                img.save(frame_file.name, "JPEG", quality=85)

                with open(frame_file.name, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    frames.append(b64)

        clip.close()
    except Exception:
        pass

    return frames


def extract_from_video(video_path: str | Path, num_frames: int = 5) -> VideoExtraction:
    """
    Extract transcript and key frames from a video file.

    Args:
        video_path: Path to the video file
        num_frames: Number of frames to extract (evenly spaced)

    Returns:
        VideoExtraction with transcript and base64-encoded frames
    """
    path = Path(video_path)

    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Get duration
    try:
        clip = VideoFileClip(str(path))
        duration = clip.duration
        clip.close()
    except Exception:
        duration = 0.0

    transcript = _extract_audio_and_transcribe(path)
    frames = _extract_key_frames(path, num_frames)

    return VideoExtraction(
        transcript=transcript,
        frames=frames,
        duration_seconds=duration,
    )
