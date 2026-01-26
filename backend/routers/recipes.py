from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db import crud
from backend.models.schemas import Recipe, RecipeUpdate
from backend.services.notion import export_recipe_to_notion, is_notion_configured

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.get("", response_model=list[Recipe])
async def list_recipes(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all recipes with optional filtering."""
    return await crud.list_recipes(db, skip=skip, limit=limit, status=status)


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single recipe by ID."""
    recipe = await crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.patch("/{recipe_id}", response_model=Recipe)
async def update_recipe(
    recipe_id: int, recipe_update: RecipeUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a recipe."""
    recipe = await crud.update_recipe(db, recipe_id, recipe_update)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.delete("/{recipe_id}")
async def delete_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a recipe."""
    success = await crud.delete_recipe(db, recipe_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"message": "Recipe deleted successfully"}


@router.get("/notion/status")
async def notion_status():
    """Check if Notion integration is configured."""
    return {"configured": is_notion_configured()}


@router.post("/{recipe_id}/export/notion")
async def export_to_notion(recipe_id: int, db: AsyncSession = Depends(get_db)):
    """Export a single recipe to Notion."""
    if not is_notion_configured():
        raise HTTPException(
            status_code=400,
            detail="Notion not configured. Add NOTION_TOKEN and NOTION_COOKING_PAGE_ID to .env"
        )

    recipe = await crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    notion_page_id = await export_recipe_to_notion(recipe)

    if not notion_page_id:
        raise HTTPException(status_code=500, detail="Failed to export to Notion")

    return {
        "success": True,
        "message": f"Exported '{recipe.title}' to Notion",
        "notion_page_id": notion_page_id,
    }


@router.post("/export/notion/all")
async def export_all_to_notion(db: AsyncSession = Depends(get_db)):
    """Export all recipes to Notion."""
    if not is_notion_configured():
        raise HTTPException(
            status_code=400,
            detail="Notion not configured. Add NOTION_TOKEN and NOTION_COOKING_PAGE_ID to .env"
        )

    recipes = await crud.list_recipes(db)
    exported = 0
    failed = 0

    for recipe in recipes:
        notion_page_id = await export_recipe_to_notion(recipe)
        if notion_page_id:
            exported += 1
        else:
            failed += 1

    return {
        "success": exported > 0,
        "message": f"Exported {exported} recipes, {failed} failed",
        "exported": exported,
        "failed": failed,
    }
