import json
from typing import Optional
from anthropic import Anthropic

from backend.config import get_settings
from backend.models.schemas import (
    RecipeCreate,
    RecipeStatus,
    SourcePlatform,
    Ingredient,
    Macros,
    RecipeCategory,
    GroceryCategory,
)
from backend.prompts.extraction import EXTRACTION_SYSTEM_PROMPT, get_extraction_prompt

settings = get_settings()


def _get_client() -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)


def _parse_category(value: Optional[str]) -> RecipeCategory:
    if not value:
        return RecipeCategory.OTHER
    try:
        return RecipeCategory(value.lower())
    except ValueError:
        return RecipeCategory.OTHER


def _parse_grocery_category(value: Optional[str]) -> GroceryCategory:
    if not value:
        return GroceryCategory.OTHER
    try:
        return GroceryCategory(value.lower())
    except ValueError:
        return GroceryCategory.OTHER


def _parse_ingredients(data: object) -> list[Ingredient]:
    if isinstance(data, (str, dict)):
        data = [data]
    elif not isinstance(data, list):
        return []

    ingredients = []
    for item in data:
        if isinstance(item, str):
            ingredients.append(Ingredient(name=item))
        elif isinstance(item, dict):
            ingredients.append(
                Ingredient(
                    name=str(item.get("name") or "Unknown"),
                    quantity=item.get("quantity"),
                    unit=item.get("unit"),
                    notes=item.get("notes"),
                    grocery_category=_parse_grocery_category(
                        item.get("grocery_category")
                    ),
                )
            )
    return ingredients


def _parse_instructions(data: object) -> list[str]:
    if isinstance(data, str):
        return [line.strip() for line in data.splitlines() if line.strip()]
    if not isinstance(data, list):
        return []
    return [str(item).strip() for item in data if item is not None and str(item).strip()]


def _parse_macros(data: Optional[dict]) -> Optional[Macros]:
    if not isinstance(data, dict) or not data:
        return None
    # Check if all values are None
    if all(v is None for v in data.values()):
        return None
    return Macros(
        calories=data.get("calories"),
        protein_g=data.get("protein_g"),
        carbs_g=data.get("carbs_g"),
        fat_g=data.get("fat_g"),
        fiber_g=data.get("fiber_g"),
        sodium_mg=data.get("sodium_mg"),
    )


def _build_message_content(
    prompt: str,
    image_url: Optional[str] = None,
    base64_frames: Optional[list[str]] = None,
) -> list[dict] | str:
    """Build message content, optionally including images."""
    content_blocks = []

    # Add URL-based image if provided
    if image_url:
        content_blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "url",
                    "url": image_url,
                },
            }
        )

    # Add base64 frames (from video extraction)
    if base64_frames:
        for frame_b64 in base64_frames:
            content_blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": frame_b64,
                    },
                }
            )

    # If no images, just return the prompt as string
    if not content_blocks:
        return prompt

    # Add text prompt at the end
    content_blocks.append(
        {
            "type": "text",
            "text": prompt,
        }
    )

    return content_blocks


async def extract_recipe(
    content: str,
    source_platform: SourcePlatform,
    source_url: str,
    source_video_id: Optional[str] = None,
    transcript: Optional[str] = None,
    image_url: Optional[str] = None,
    scan_image: bool = False,
    video_frames: Optional[list[str]] = None,
) -> Optional[RecipeCreate]:
    """
    Send content to Claude for recipe extraction.

    Args:
        content: Text content (caption, transcript, etc.)
        source_platform: Where the recipe came from
        source_url: Original URL
        source_video_id: YouTube video ID if applicable
        transcript: Video transcript if available
        image_url: Image URL to store and optionally scan
        scan_image: If True, send the image to Claude for vision analysis
        video_frames: Base64-encoded frames extracted from video

    Returns a RecipeCreate object or None if extraction fails.
    """
    client = _get_client()
    prompt = get_extraction_prompt(content)

    # Build message with optional images/frames
    message_content = _build_message_content(
        prompt,
        image_url=image_url if scan_image else None,
        base64_frames=video_frames,
    )

    try:
        message = client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            system=[{"type": "text", "text": EXTRACTION_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": message_content}],
        )

        response_text = message.content[0].text

        # Try to parse JSON from response
        # Handle potential markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        data = json.loads(response_text.strip())

        # Determine status based on extraction quality
        status = RecipeStatus.EXTRACTED
        if not data.get("ingredients") or not data.get("instructions"):
            status = RecipeStatus.NEEDS_REVIEW

        return RecipeCreate(
            title=data.get("title", "Untitled Recipe"),
            description=data.get("description"),
            ingredients=_parse_ingredients(data.get("ingredients") or []),
            instructions=_parse_instructions(data.get("instructions")),
            prep_time_minutes=data.get("prep_time_minutes"),
            cook_time_minutes=data.get("cook_time_minutes"),
            total_time_minutes=data.get("total_time_minutes"),
            servings=data.get("servings"),
            category=_parse_category(data.get("category")),
            cuisine=data.get("cuisine"),
            tags=data.get("tags") or [],
            macros=_parse_macros(data.get("macros")),
            image_url=image_url or data.get("image_url"),
            source_platform=source_platform,
            source_url=source_url,
            source_video_id=source_video_id,
            transcript=transcript,
            status=status,
        )

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None
    except Exception as e:
        print(f"Extraction error: {type(e).__name__}: {e}")
        return None
