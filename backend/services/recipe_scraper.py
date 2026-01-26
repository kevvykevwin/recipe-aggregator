from typing import Optional
from recipe_scrapers import scrape_html
import httpx

from backend.models.schemas import ScrapedRecipe


async def scrape_recipe_url(url: str) -> Optional[ScrapedRecipe]:
    """
    Scrape a recipe from a URL using the recipe-scrapers library.

    Returns a ScrapedRecipe object or None if scraping fails.
    """
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        scraper = scrape_html(html, org_url=url)

        # Extract ingredients as list of strings
        ingredients = []
        try:
            ingredients = scraper.ingredients()
        except Exception:
            pass

        # Extract instructions - handle both list and string
        instructions = []
        try:
            instr = scraper.instructions()
            if isinstance(instr, str):
                instructions = [s.strip() for s in instr.split("\n") if s.strip()]
            else:
                instructions = instr
        except Exception:
            pass

        # Parse times
        prep_time = None
        cook_time = None
        total_time = None
        try:
            prep_time = scraper.prep_time()
        except Exception:
            pass
        try:
            cook_time = scraper.cook_time()
        except Exception:
            pass
        try:
            total_time = scraper.total_time()
        except Exception:
            pass

        # Get servings
        servings = None
        try:
            servings = str(scraper.yields())
        except Exception:
            pass

        # Get image
        image_url = None
        try:
            image_url = scraper.image()
        except Exception:
            pass

        # Get title
        title = "Untitled Recipe"
        try:
            title = scraper.title()
        except Exception:
            pass

        return ScrapedRecipe(
            title=title,
            ingredients=ingredients,
            instructions=instructions,
            prep_time=prep_time,
            cook_time=cook_time,
            total_time=total_time,
            servings=servings,
            image_url=image_url,
            source_url=url,
        )

    except Exception:
        return None
