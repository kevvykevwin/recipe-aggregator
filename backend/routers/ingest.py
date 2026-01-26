import csv
import io
import asyncio
import random
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db import crud
from backend.models.schemas import (
    IngestYouTubeRequest,
    IngestURLRequest,
    IngestInstagramRequest,
    IngestManualRequest,
    IngestResponse,
    SourcePlatform,
    RecipeStatus,
)
from backend.services.youtube import (
    extract_video_id,
    get_video_details,
    get_playlist_videos,
)
from backend.services.transcription import get_youtube_transcript
from backend.services.recipe_scraper import scrape_recipe_url
from backend.services.instagram import get_post_data, download_reel_video
from backend.services.extractor import extract_recipe

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


async def _process_youtube_video(
    video_id: str, db: AsyncSession
) -> tuple[bool, str, int | None]:
    """Process a single YouTube video and extract recipe."""
    # Check if already processed
    existing = await crud.get_recipe_by_video_id(db, video_id)
    if existing:
        return False, f"Video {video_id} already processed", existing.id

    # Get video details
    video_details = get_video_details(video_id)
    if not video_details:
        return False, f"Could not fetch video details for {video_id}", None

    # Get transcript
    transcript = get_youtube_transcript(video_id)

    # Build content for extraction
    content_parts = [f"Title: {video_details.title}"]
    if video_details.description:
        content_parts.append(f"Description: {video_details.description}")
    if transcript:
        content_parts.append(f"Transcript: {transcript}")

    # Try to scrape linked recipe URLs
    scraped_content = None
    for url in video_details.linked_urls:
        if any(
            domain in url.lower()
            for domain in ["recipe", "food", "cook", "kitchen", "allrecipes", "epicurious"]
        ):
            scraped = await scrape_recipe_url(url)
            if scraped:
                scraped_content = f"""
Scraped Recipe from {url}:
Title: {scraped.title}
Ingredients: {', '.join(scraped.ingredients)}
Instructions: {' '.join(scraped.instructions)}
"""
                content_parts.append(scraped_content)
                break

    full_content = "\n\n".join(content_parts)

    # Extract recipe using Claude
    recipe_data = await extract_recipe(
        content=full_content,
        source_platform=SourcePlatform.YOUTUBE,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        source_video_id=video_id,
        transcript=transcript,
        image_url=video_details.thumbnail_url,
    )

    if not recipe_data:
        return False, f"Failed to extract recipe from video {video_id}", None

    # If no ingredients or instructions, mark for review
    if not recipe_data.ingredients or not recipe_data.instructions:
        recipe_data.status = RecipeStatus.NEEDS_REVIEW

    # Save to database
    recipe = await crud.create_recipe(db, recipe_data)
    return True, f"Successfully extracted recipe: {recipe.title}", recipe.id


@router.post("/youtube", response_model=IngestResponse)
async def ingest_youtube(
    request: IngestYouTubeRequest, db: AsyncSession = Depends(get_db)
):
    """Ingest recipe(s) from YouTube video or playlist."""
    if not request.playlist_id and not request.video_url:
        raise HTTPException(
            status_code=400, detail="Either playlist_id or video_url is required"
        )

    if request.video_url:
        # Single video
        video_id = extract_video_id(request.video_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        success, message, recipe_id = await _process_youtube_video(video_id, db)
        return IngestResponse(success=success, message=message, recipe_id=recipe_id)

    # Playlist
    videos = get_playlist_videos(request.playlist_id)
    if not videos:
        raise HTTPException(
            status_code=404, detail="Playlist not found or contains no videos"
        )

    recipe_ids = []
    successes = 0
    failures = 0

    for video in videos:
        success, _, recipe_id = await _process_youtube_video(video.video_id, db)
        if success and recipe_id:
            recipe_ids.append(recipe_id)
            successes += 1
        else:
            failures += 1

    return IngestResponse(
        success=successes > 0,
        message=f"Processed {len(videos)} videos: {successes} extracted, {failures} failed/skipped",
        recipe_ids=recipe_ids,
    )


@router.post("/url", response_model=IngestResponse)
async def ingest_url(request: IngestURLRequest, db: AsyncSession = Depends(get_db)):
    """Ingest a recipe directly from a URL."""
    # Try to scrape the URL
    scraped = await scrape_recipe_url(request.url)

    if scraped:
        # Build content from scraped data
        content = f"""
Title: {scraped.title}
Ingredients: {chr(10).join(scraped.ingredients)}
Instructions: {chr(10).join(scraped.instructions)}
Prep Time: {scraped.prep_time} minutes
Cook Time: {scraped.cook_time} minutes
Total Time: {scraped.total_time} minutes
Servings: {scraped.servings}
"""
    else:
        # Fall back to just the URL for Claude to try
        content = f"Recipe URL: {request.url}"

    recipe_data = await extract_recipe(
        content=content,
        source_platform=SourcePlatform.WEBSITE,
        source_url=request.url,
        image_url=scraped.image_url if scraped else None,
    )

    if not recipe_data:
        raise HTTPException(status_code=500, detail="Failed to extract recipe from URL")

    recipe = await crud.create_recipe(db, recipe_data)
    return IngestResponse(
        success=True,
        message=f"Successfully extracted recipe: {recipe.title}",
        recipe_id=recipe.id,
    )


@router.post("/instagram", response_model=IngestResponse)
async def ingest_instagram(
    request: IngestInstagramRequest, db: AsyncSession = Depends(get_db)
):
    """Ingest a recipe from an Instagram post or reel."""
    post_data = get_post_data(request.url)

    if not post_data:
        raise HTTPException(
            status_code=400,
            detail="Could not fetch Instagram post. Make sure it's a public post/reel.",
        )

    if not post_data.caption:
        raise HTTPException(
            status_code=400,
            detail="Instagram post has no caption to extract recipe from.",
        )

    # Build content for extraction
    content = f"""
Instagram Recipe Post by @{post_data.owner_username}

Caption:
{post_data.caption}
"""

    recipe_data = await extract_recipe(
        content=content,
        source_platform=SourcePlatform.INSTAGRAM,
        source_url=post_data.post_url,
        image_url=post_data.image_url,
    )

    if not recipe_data:
        raise HTTPException(
            status_code=500, detail="Failed to extract recipe from Instagram post"
        )

    # Instagram captions often lack full details, mark for review
    if not recipe_data.ingredients or len(recipe_data.ingredients) < 3:
        recipe_data.status = RecipeStatus.NEEDS_REVIEW

    recipe = await crud.create_recipe(db, recipe_data)
    return IngestResponse(
        success=True,
        message=f"Successfully extracted recipe: {recipe.title}",
        recipe_id=recipe.id,
    )


@router.post("/manual", response_model=IngestResponse)
async def ingest_manual(
    request: IngestManualRequest, db: AsyncSession = Depends(get_db)
):
    """
    Ingest a recipe from manually provided caption/text.

    Use this when you copy-paste a caption from Instagram or other sources.
    """
    # Determine source platform from URL
    source_platform = SourcePlatform.MANUAL
    if "instagram.com" in request.source_url:
        source_platform = SourcePlatform.INSTAGRAM
    elif "youtube.com" in request.source_url or "youtu.be" in request.source_url:
        source_platform = SourcePlatform.YOUTUBE

    recipe_data = await extract_recipe(
        content=request.caption,
        source_platform=source_platform,
        source_url=request.source_url,
        image_url=request.image_url,
    )

    if not recipe_data:
        raise HTTPException(
            status_code=500, detail="Failed to extract recipe from provided text"
        )

    # Manual entries often lack full details
    if not recipe_data.ingredients or len(recipe_data.ingredients) < 3:
        recipe_data.status = RecipeStatus.NEEDS_REVIEW

    recipe = await crud.create_recipe(db, recipe_data)
    return IngestResponse(
        success=True,
        message=f"Successfully extracted recipe: {recipe.title}",
        recipe_id=recipe.id,
    )


@router.post("/csv", response_model=IngestResponse)
async def ingest_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk import recipes from a CSV file.

    CSV columns:
        url (required): Source URL
        caption (optional): Recipe text - auto-fetched for Instagram URLs if empty
        image_url (optional): Image URL - will be scanned if caption is minimal

    Behavior:
        - Instagram URLs with empty caption: auto-fetches post caption and image
        - If caption < 50 chars and image_url exists: scans image with vision
        - Image-only rows: uses Claude vision to extract recipe

    Examples:
        # Instagram URL (caption auto-fetched)
        url,caption
        https://instagram.com/p/xyz,

        # With caption provided
        url,caption
        https://instagram.com/p/xyz,"🍝 Recipe here..."
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handles BOM
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    # Validate columns - need url and either caption or image_url
    if "url" not in reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="CSV must have 'url' column"
        )

    has_caption = "caption" in reader.fieldnames
    has_image = "image_url" in reader.fieldnames

    if not has_caption and not has_image:
        raise HTTPException(
            status_code=400,
            detail="CSV must have either 'caption' or 'image_url' column"
        )

    recipe_ids = []
    successes = 0
    failures = 0

    for row in reader:
        url = row.get("url", "").strip()
        caption = row.get("caption", "").strip() if has_caption else ""
        image_url = row.get("image_url", "").strip() or None

        if not url:
            failures += 1
            continue

        # Determine source platform
        source_platform = SourcePlatform.MANUAL
        if "instagram.com" in url:
            source_platform = SourcePlatform.INSTAGRAM
        elif "youtube.com" in url or "youtu.be" in url:
            source_platform = SourcePlatform.YOUTUBE

        # Auto-fetch Instagram post data if caption is empty
        is_reel = False
        video_frames = None
        carousel_frames = None

        if source_platform == SourcePlatform.INSTAGRAM and not caption:
            try:
                post_data = get_post_data(url)
                if post_data:
                    caption = post_data.caption or ""
                    image_url = image_url or post_data.image_url
                    url = post_data.post_url  # normalized URL
                    is_reel = post_data.is_video

                    # For reels with minimal caption, process the video
                    if is_reel and len(caption) < 100 and post_data.video_url:
                        try:
                            from backend.services.video import extract_from_video
                            video_path = await download_reel_video(post_data.video_url)
                            if video_path:
                                video_data = extract_from_video(video_path, num_frames=4)
                                if video_data.transcript:
                                    caption = f"Video transcript:\n{video_data.transcript}\n\nCaption:\n{caption}"
                                video_frames = video_data.frames
                                video_path.unlink(missing_ok=True)  # cleanup
                        except Exception as e:
                            print(f"Reel video processing failed: {e}")

                    # For carousels with minimal caption, download and scan images
                    elif post_data.is_carousel and len(caption) < 100 and post_data.carousel_urls:
                        try:
                            import base64
                            import httpx
                            carousel_frames = []
                            # Get up to 4 carousel images
                            for img_url in post_data.carousel_urls[:4]:
                                async with httpx.AsyncClient(timeout=30.0) as client:
                                    resp = await client.get(img_url)
                                    if resp.status_code == 200:
                                        b64 = base64.b64encode(resp.content).decode("utf-8")
                                        carousel_frames.append(b64)
                            if carousel_frames:
                                caption = f"Extract recipe from these carousel images.\n\nCaption: {caption}" if caption else "Extract the recipe from these carousel images."
                        except Exception as e:
                            print(f"Carousel processing failed: {e}")

                # Rate limit: wait 8-15 seconds between Instagram fetches (longer to avoid blocks)
                await asyncio.sleep(random.uniform(8, 15))
            except Exception:
                pass  # Continue with empty caption, will try image scan

        # Combine video frames and carousel frames
        all_frames = video_frames or carousel_frames

        # Need either caption or image or frames
        if not caption and not image_url and not all_frames:
            failures += 1
            continue

        # Scan image if no caption provided (or caption is minimal)
        scan_image = image_url and len(caption) < 50 and not all_frames

        # If image-only, set placeholder content for prompt
        if not caption and image_url:
            caption = "Extract the recipe or cooking technique from this image."
        elif not caption and all_frames:
            caption = "Extract the recipe or cooking technique from these images."

        try:
            recipe_data = await extract_recipe(
                content=caption,
                source_platform=source_platform,
                source_url=url,
                image_url=image_url,
                scan_image=scan_image,
                video_frames=all_frames,
            )

            if recipe_data:
                if not recipe_data.ingredients or len(recipe_data.ingredients) < 3:
                    recipe_data.status = RecipeStatus.NEEDS_REVIEW
                recipe = await crud.create_recipe(db, recipe_data)
                recipe_ids.append(recipe.id)
                successes += 1
            else:
                failures += 1
        except Exception:
            failures += 1

    return IngestResponse(
        success=successes > 0,
        message=f"Processed {successes + failures} rows: {successes} extracted, {failures} failed",
        recipe_ids=recipe_ids,
    )


@router.post("/video", response_model=IngestResponse)
async def ingest_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract recipe from a video file.

    Combines audio transcription (Whisper) with key frame analysis (Claude vision)
    for comprehensive extraction.

    Supported formats: .mp4, .mov, .avi, .mkv, .webm
    """
    from backend.services.video import extract_from_video
    import tempfile
    from pathlib import Path

    allowed_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Extract transcript and frames
        video_data = extract_from_video(tmp_path, num_frames=5)

        # Build content for extraction
        content_parts = []
        if video_data.transcript:
            content_parts.append(f"Video transcript:\n{video_data.transcript}")
        else:
            content_parts.append("Extract the recipe or cooking technique from these video frames.")

        if video_data.duration_seconds:
            content_parts.append(f"Video duration: {int(video_data.duration_seconds)} seconds")

        full_content = "\n\n".join(content_parts)

        recipe_data = await extract_recipe(
            content=full_content,
            source_platform=SourcePlatform.VIDEO_FILE,
            source_url=f"file://{file.filename}",
            transcript=video_data.transcript,
            video_frames=video_data.frames if video_data.frames else None,
        )

        if not recipe_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to extract recipe from video"
            )

        if not recipe_data.ingredients or len(recipe_data.ingredients) < 3:
            recipe_data.status = RecipeStatus.NEEDS_REVIEW

        recipe = await crud.create_recipe(db, recipe_data)
        return IngestResponse(
            success=True,
            message=f"Successfully extracted recipe: {recipe.title}",
            recipe_id=recipe.id,
        )

    finally:
        # Clean up temp file
        tmp_path.unlink(missing_ok=True)
