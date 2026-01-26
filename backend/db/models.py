from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum

from backend.db.database import Base
from backend.models.schemas import SourcePlatform, RecipeCategory, RecipeStatus


class RecipeModel(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    ingredients = Column(JSON, default=list)
    instructions = Column(JSON, default=list)
    prep_time_minutes = Column(Integer, nullable=True)
    cook_time_minutes = Column(Integer, nullable=True)
    total_time_minutes = Column(Integer, nullable=True)
    servings = Column(String(100), nullable=True)
    category = Column(SQLEnum(RecipeCategory), default=RecipeCategory.OTHER)
    cuisine = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)
    macros = Column(JSON, nullable=True)
    image_url = Column(String(2000), nullable=True)
    source_platform = Column(SQLEnum(SourcePlatform), nullable=False)
    source_url = Column(String(2000), nullable=False)
    source_video_id = Column(String(50), nullable=True, index=True)
    transcript = Column(Text, nullable=True)
    status = Column(SQLEnum(RecipeStatus), default=RecipeStatus.EXTRACTED)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
