from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SourcePlatform(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    WEBSITE = "website"
    MANUAL = "manual"
    VIDEO_FILE = "video_file"


class RecipeCategory(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    DESSERT = "dessert"
    BEVERAGE = "beverage"
    APPETIZER = "appetizer"
    SIDE = "side"
    TECHNIQUE = "technique"
    OTHER = "other"


class RecipeStatus(str, Enum):
    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"
    FAILED = "failed"


class GroceryCategory(str, Enum):
    PRODUCE = "produce"
    MEAT = "meat"
    SEAFOOD = "seafood"
    DAIRY = "dairy"
    BAKERY = "bakery"
    FROZEN = "frozen"
    PANTRY = "pantry"
    SPICES = "spices"
    CONDIMENTS = "condiments"
    BEVERAGES = "beverages"
    OTHER = "other"


class Ingredient(BaseModel):
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    grocery_category: GroceryCategory = GroceryCategory.OTHER


class Macros(BaseModel):
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sodium_mg: Optional[float] = None


class VideoMetadata(BaseModel):
    video_id: str
    title: str
    description: Optional[str] = None
    channel_name: Optional[str] = None
    published_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = None


class VideoDetails(VideoMetadata):
    tags: list[str] = Field(default_factory=list)
    linked_urls: list[str] = Field(default_factory=list)


class ScrapedRecipe(BaseModel):
    title: str
    ingredients: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    total_time: Optional[int] = None
    servings: Optional[str] = None
    image_url: Optional[str] = None
    source_url: str


class RecipeBase(BaseModel):
    title: str
    description: Optional[str] = None
    ingredients: list[Ingredient] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    total_time_minutes: Optional[int] = None
    servings: Optional[str] = None
    category: RecipeCategory = RecipeCategory.OTHER
    cuisine: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    macros: Optional[Macros] = None
    image_url: Optional[str] = None


class RecipeCreate(RecipeBase):
    source_platform: SourcePlatform
    source_url: str
    source_video_id: Optional[str] = None
    transcript: Optional[str] = None
    status: RecipeStatus = RecipeStatus.EXTRACTED


class Recipe(RecipeBase):
    id: int
    source_platform: SourcePlatform
    source_url: str
    source_video_id: Optional[str] = None
    transcript: Optional[str] = None
    status: RecipeStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecipeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ingredients: Optional[list[Ingredient]] = None
    instructions: Optional[list[str]] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    total_time_minutes: Optional[int] = None
    servings: Optional[str] = None
    category: Optional[RecipeCategory] = None
    cuisine: Optional[str] = None
    tags: Optional[list[str]] = None
    macros: Optional[Macros] = None
    image_url: Optional[str] = None
    status: Optional[RecipeStatus] = None


class IngestYouTubeRequest(BaseModel):
    playlist_id: Optional[str] = None
    video_url: Optional[str] = None


class IngestURLRequest(BaseModel):
    url: str


class IngestInstagramRequest(BaseModel):
    url: str


class IngestManualRequest(BaseModel):
    caption: str
    source_url: str
    image_url: Optional[str] = None


class IngestResponse(BaseModel):
    success: bool
    message: str
    recipe_id: Optional[int] = None
    recipe_ids: Optional[list[int]] = None
