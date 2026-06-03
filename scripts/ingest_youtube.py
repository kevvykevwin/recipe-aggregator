#!/usr/bin/env python3
"""CLI script for ingesting recipes from YouTube videos or playlists."""

# ruff: noqa: E402

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from backend.db.database import AsyncSessionLocal, init_db
from backend.db import crud
from backend.models.schemas import SourcePlatform, RecipeStatus
from backend.services.youtube import (
    extract_video_id,
    get_video_details,
    get_playlist_videos,
)
from backend.services.transcription import get_youtube_transcript
from backend.services.recipe_scraper import scrape_recipe_url
from backend.services.extractor import extract_recipe


async def process_video(video_id: str, db) -> tuple[str, str | None]:
    """
    Process a single video.

    Returns: (status, recipe_title)
    status: 'extracted', 'needs_review', 'skipped', 'failed'
    """
    # Check if already processed
    existing = await crud.get_recipe_by_video_id(db, video_id)
    if existing:
        return "skipped", existing.title

    # Get video details
    video_details = get_video_details(video_id)
    if not video_details:
        return "failed", None

    print(f"  Processing: {video_details.title}")

    # Get transcript
    transcript = get_youtube_transcript(video_id)
    if transcript:
        print(f"    ✓ Got transcript ({len(transcript)} chars)")
    else:
        print("    ✗ No transcript available")

    # Build content for extraction
    content_parts = [f"Title: {video_details.title}"]
    if video_details.description:
        content_parts.append(f"Description: {video_details.description}")
    if transcript:
        content_parts.append(f"Transcript: {transcript}")

    # Try to scrape linked recipe URLs
    for url in video_details.linked_urls:
        if any(
            domain in url.lower()
            for domain in [
                "recipe",
                "food",
                "cook",
                "kitchen",
                "allrecipes",
                "epicurious",
            ]
        ):
            print(f"    → Scraping linked URL: {url[:60]}...")
            scraped = await scrape_recipe_url(url)
            if scraped:
                scraped_content = f"""
Scraped Recipe from {url}:
Title: {scraped.title}
Ingredients: {', '.join(scraped.ingredients)}
Instructions: {' '.join(scraped.instructions)}
"""
                content_parts.append(scraped_content)
                print(f"    ✓ Scraped recipe: {scraped.title}")
                break

    full_content = "\n\n".join(content_parts)

    # Extract recipe using Claude
    print("    → Extracting recipe with Claude...")
    recipe_data = await extract_recipe(
        content=full_content,
        source_platform=SourcePlatform.YOUTUBE,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        source_video_id=video_id,
        transcript=transcript,
        image_url=video_details.thumbnail_url,
    )

    if not recipe_data:
        print("    ✗ Failed to extract recipe")
        return "failed", None

    # Determine status
    if not recipe_data.ingredients or not recipe_data.instructions:
        recipe_data.status = RecipeStatus.NEEDS_REVIEW

    # Save to database
    recipe = await crud.create_recipe(db, recipe_data)
    status = "needs_review" if recipe.status == RecipeStatus.NEEDS_REVIEW else "extracted"
    print(f"    ✓ Saved: {recipe.title} (ID: {recipe.id}, Status: {status})")

    return status, recipe.title


async def main():
    parser = argparse.ArgumentParser(
        description="Ingest recipes from YouTube videos or playlists"
    )
    parser.add_argument("--video", "-v", help="YouTube video URL to process")
    parser.add_argument("--playlist", "-p", help="YouTube playlist ID to process")

    args = parser.parse_args()

    if not args.video and not args.playlist:
        parser.error("Either --video or --playlist is required")

    # Initialize database
    await init_db()

    async with AsyncSessionLocal() as db:
        if args.video:
            # Single video
            video_id = extract_video_id(args.video)
            if not video_id:
                print(f"Error: Invalid YouTube URL: {args.video}")
                sys.exit(1)

            print(f"\nProcessing video: {video_id}")
            status, title = await process_video(video_id, db)

            print(f"\nResult: {status}")
            if title:
                print(f"Recipe: {title}")

        else:
            # Playlist
            print(f"\nFetching playlist: {args.playlist}")
            videos = get_playlist_videos(args.playlist)

            if not videos:
                print("Error: Playlist not found or contains no videos")
                sys.exit(1)

            print(f"Found {len(videos)} videos\n")

            stats = {"extracted": 0, "needs_review": 0, "skipped": 0, "failed": 0}

            for i, video in enumerate(videos, 1):
                print(f"[{i}/{len(videos)}] {video.video_id}")
                status, _ = await process_video(video.video_id, db)
                stats[status] += 1

            print("\n" + "=" * 50)
            print("Summary:")
            print(f"  Extracted:    {stats['extracted']}")
            print(f"  Need Review:  {stats['needs_review']}")
            print(f"  Skipped:      {stats['skipped']}")
            print(f"  Failed:       {stats['failed']}")
            print(f"  Total:        {len(videos)}")


if __name__ == "__main__":
    asyncio.run(main())
