from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import RecipeModel
from backend.models.schemas import RecipeCreate, RecipeUpdate, Recipe, Ingredient


def _serialize_ingredients(ingredients: list[Ingredient]) -> list[dict]:
    return [ing.model_dump() for ing in ingredients]


def _deserialize_ingredients(data: list[dict]) -> list[Ingredient]:
    return [Ingredient(**ing) for ing in data]


async def create_recipe(db: AsyncSession, recipe: RecipeCreate) -> Recipe:
    db_recipe = RecipeModel(
        title=recipe.title,
        description=recipe.description,
        ingredients=_serialize_ingredients(recipe.ingredients),
        instructions=recipe.instructions,
        prep_time_minutes=recipe.prep_time_minutes,
        cook_time_minutes=recipe.cook_time_minutes,
        total_time_minutes=recipe.total_time_minutes,
        servings=recipe.servings,
        category=recipe.category,
        cuisine=recipe.cuisine,
        tags=recipe.tags,
        macros=recipe.macros.model_dump() if recipe.macros else None,
        image_url=recipe.image_url,
        source_platform=recipe.source_platform,
        source_url=recipe.source_url,
        source_video_id=recipe.source_video_id,
        transcript=recipe.transcript,
        status=recipe.status,
    )
    db.add(db_recipe)
    await db.commit()
    await db.refresh(db_recipe)
    return _model_to_schema(db_recipe)


async def get_recipe(db: AsyncSession, recipe_id: int) -> Optional[Recipe]:
    result = await db.execute(select(RecipeModel).where(RecipeModel.id == recipe_id))
    db_recipe = result.scalar_one_or_none()
    if db_recipe:
        return _model_to_schema(db_recipe)
    return None


async def get_recipe_by_video_id(db: AsyncSession, video_id: str) -> Optional[Recipe]:
    result = await db.execute(
        select(RecipeModel).where(RecipeModel.source_video_id == video_id)
    )
    db_recipe = result.scalar_one_or_none()
    if db_recipe:
        return _model_to_schema(db_recipe)
    return None


async def list_recipes(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
) -> list[Recipe]:
    query = select(RecipeModel)
    if status:
        query = query.where(RecipeModel.status == status)
    query = query.offset(skip).limit(limit).order_by(RecipeModel.created_at.desc())
    result = await db.execute(query)
    db_recipes = result.scalars().all()
    return [_model_to_schema(r) for r in db_recipes]


async def update_recipe(
    db: AsyncSession, recipe_id: int, recipe_update: RecipeUpdate
) -> Optional[Recipe]:
    result = await db.execute(select(RecipeModel).where(RecipeModel.id == recipe_id))
    db_recipe = result.scalar_one_or_none()
    if not db_recipe:
        return None

    update_data = recipe_update.model_dump(exclude_unset=True)

    if "ingredients" in update_data and update_data["ingredients"] is not None:
        update_data["ingredients"] = _serialize_ingredients(update_data["ingredients"])

    if "macros" in update_data and update_data["macros"] is not None:
        update_data["macros"] = update_data["macros"].model_dump()

    for field, value in update_data.items():
        setattr(db_recipe, field, value)

    await db.commit()
    await db.refresh(db_recipe)
    return _model_to_schema(db_recipe)


async def delete_recipe(db: AsyncSession, recipe_id: int) -> bool:
    result = await db.execute(select(RecipeModel).where(RecipeModel.id == recipe_id))
    db_recipe = result.scalar_one_or_none()
    if not db_recipe:
        return False
    await db.delete(db_recipe)
    await db.commit()
    return True


def _model_to_schema(db_recipe: RecipeModel) -> Recipe:
    from backend.models.schemas import Macros

    return Recipe(
        id=db_recipe.id,
        title=db_recipe.title,
        description=db_recipe.description,
        ingredients=_deserialize_ingredients(db_recipe.ingredients or []),
        instructions=db_recipe.instructions or [],
        prep_time_minutes=db_recipe.prep_time_minutes,
        cook_time_minutes=db_recipe.cook_time_minutes,
        total_time_minutes=db_recipe.total_time_minutes,
        servings=db_recipe.servings,
        category=db_recipe.category,
        cuisine=db_recipe.cuisine,
        tags=db_recipe.tags or [],
        macros=Macros(**db_recipe.macros) if db_recipe.macros else None,
        image_url=db_recipe.image_url,
        source_platform=db_recipe.source_platform,
        source_url=db_recipe.source_url,
        source_video_id=db_recipe.source_video_id,
        transcript=db_recipe.transcript,
        status=db_recipe.status,
        created_at=db_recipe.created_at,
        updated_at=db_recipe.updated_at,
    )
