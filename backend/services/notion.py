from typing import Optional
from notion_client import Client

from backend.config import get_settings
from backend.models.schemas import Recipe

settings = get_settings()

# Cuisine to emoji mapping
CUISINE_EMOJI = {
    "american": "🇺🇸",
    "americana": "🇺🇸",
    "chinese": "🇨🇳",
    "french": "🇫🇷",
    "italian": "🇮🇹",
    "japanese": "🇯🇵",
    "korean": "🇰🇷",
    "mexican": "🇲🇽",
    "thai": "🇹🇭",
    "indian": "🇮🇳",
    "vietnamese": "🇻🇳",
    "greek": "🇬🇷",
    "spanish": "🇪🇸",
    "mediterranean": "🌊",
    "middle eastern": "🧆",
}


def _get_client() -> Optional[Client]:
    """Get Notion client if configured."""
    if not settings.notion_token:
        return None
    return Client(auth=settings.notion_token)


def _get_cuisine_emoji(cuisine: str) -> str:
    """Get emoji for cuisine type."""
    if not cuisine:
        return "🍽️"
    cuisine_lower = cuisine.lower()
    for key, emoji in CUISINE_EMOJI.items():
        if key in cuisine_lower:
            return emoji
    return "🍽️"


def _get_recipe_emoji(title: str, category: str) -> str:
    """Get emoji for recipe based on title/category."""
    title_lower = title.lower()

    # Check title for common foods
    if any(x in title_lower for x in ["chicken", "poultry"]):
        return "🍗"
    if any(x in title_lower for x in ["beef", "steak"]):
        return "🥩"
    if any(x in title_lower for x in ["pork", "bacon"]):
        return "🥓"
    if any(x in title_lower for x in ["fish", "salmon", "tuna"]):
        return "🐟"
    if any(x in title_lower for x in ["shrimp", "prawn", "seafood"]):
        return "🦐"
    if any(x in title_lower for x in ["pasta", "spaghetti", "noodle"]):
        return "🍝"
    if any(x in title_lower for x in ["rice", "congee"]):
        return "🍚"
    if any(x in title_lower for x in ["soup", "stew"]):
        return "🍲"
    if any(x in title_lower for x in ["salad"]):
        return "🥗"
    if any(x in title_lower for x in ["sandwich", "burger"]):
        return "🍔"
    if any(x in title_lower for x in ["pizza"]):
        return "🍕"
    if any(x in title_lower for x in ["taco", "burrito"]):
        return "🌮"
    if any(x in title_lower for x in ["cake", "cookie", "dessert"]):
        return "🍰"
    if any(x in title_lower for x in ["bread"]):
        return "🍞"
    if any(x in title_lower for x in ["egg"]):
        return "🥚"
    if any(x in title_lower for x in ["tofu"]):
        return "🧈"

    # Default by category
    category_emoji = {
        "breakfast": "🍳",
        "lunch": "🥪",
        "dinner": "🍽️",
        "dessert": "🍰",
        "snack": "🍿",
        "beverage": "🥤",
        "appetizer": "🥟",
        "side": "🥬",
    }
    return category_emoji.get(category, "📄")


async def find_cuisine_page(cuisine: str) -> Optional[str]:
    """Find existing cuisine sub-page under the Cooking parent."""
    client = _get_client()
    if not client or not settings.notion_cooking_page_id:
        return None

    try:
        # Search for pages that match the cuisine
        response = client.blocks.children.list(
            block_id=settings.notion_cooking_page_id
        )

        cuisine_lower = cuisine.lower() if cuisine else ""

        for block in response.get("results", []):
            if block.get("type") == "child_page":
                page_title = block.get("child_page", {}).get("title", "").lower()
                # Check if cuisine matches (e.g., "italian" matches "Italian Cuisine")
                if cuisine_lower and cuisine_lower in page_title:
                    return block["id"]
                # Also check for "Random Cuisine" as fallback
                if "random" in page_title:
                    fallback_id = block["id"]

        # Return Random Cuisine as fallback if no match
        return fallback_id if 'fallback_id' in dir() else None

    except Exception as e:
        print(f"Error finding cuisine page: {e}")
        return None


async def create_cuisine_page(cuisine: str) -> Optional[str]:
    """Create a new cuisine sub-page under Cooking."""
    client = _get_client()
    if not client or not settings.notion_cooking_page_id:
        return None

    try:
        emoji = _get_cuisine_emoji(cuisine)
        title = f"{cuisine} Cuisine" if cuisine else "Other Recipes"

        response = client.pages.create(
            parent={"page_id": settings.notion_cooking_page_id},
            icon={"type": "emoji", "emoji": emoji},
            properties={
                "title": {"title": [{"text": {"content": title}}]}
            },
        )
        return response["id"]
    except Exception as e:
        print(f"Error creating cuisine page: {e}")
        return None


async def create_recipe_page(recipe: Recipe, parent_page_id: str) -> Optional[str]:
    """Create a recipe page under the cuisine page."""
    client = _get_client()
    if not client:
        return None

    try:
        emoji = _get_recipe_emoji(recipe.title, recipe.category)

        # Build page content blocks
        children = []

        # Ingredients section
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Ingredients"}}]
            }
        })

        for ing in recipe.ingredients:
            text = ing.name
            if ing.quantity:
                text = f"{ing.quantity} {ing.unit or ''} {ing.name}".strip()
            if ing.notes:
                text += f" ({ing.notes})"

            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            })

        # Instructions section
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Instructions"}}]
            }
        })

        for step in recipe.instructions:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": step}}]
                }
            })

        # Source link
        if recipe.source_url:
            children.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "Source: "}},
                        {
                            "type": "text",
                            "text": {"content": recipe.source_url, "link": {"url": recipe.source_url}}
                        }
                    ]
                }
            })

        # Create the page
        response = client.pages.create(
            parent={"page_id": parent_page_id},
            icon={"type": "emoji", "emoji": emoji},
            properties={
                "title": {"title": [{"text": {"content": recipe.title}}]}
            },
            children=children,
        )

        return response["id"]

    except Exception as e:
        print(f"Error creating recipe page: {e}")
        return None


async def export_recipe_to_notion(recipe: Recipe) -> Optional[str]:
    """
    Export a recipe to Notion.

    Finds or creates the appropriate cuisine page, then creates the recipe.
    Returns the Notion page ID if successful.
    """
    client = _get_client()
    if not client:
        print("Notion not configured")
        return None

    # Find or create cuisine page
    cuisine_page_id = await find_cuisine_page(recipe.cuisine)

    if not cuisine_page_id:
        # Try to create new cuisine page, or use Random Cuisine
        if recipe.cuisine:
            cuisine_page_id = await create_cuisine_page(recipe.cuisine)

        if not cuisine_page_id:
            # Fall back to finding/creating "Random Cuisine"
            cuisine_page_id = await find_cuisine_page("random")
            if not cuisine_page_id:
                cuisine_page_id = await create_cuisine_page("Random")

    if not cuisine_page_id:
        print("Could not find or create cuisine page")
        return None

    # Create recipe page
    return await create_recipe_page(recipe, cuisine_page_id)


def is_notion_configured() -> bool:
    """Check if Notion integration is configured."""
    return bool(settings.notion_token and settings.notion_cooking_page_id)
