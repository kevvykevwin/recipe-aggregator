# Recipe Aggregator

Extract and organize recipes from Instagram, YouTube, websites, images, and video files using AI.

## Features

- **Multi-source ingestion**: Instagram posts/reels, YouTube videos, recipe websites, images, video files
- **AI extraction**: Uses Claude to extract structured recipe data from any content
- **Image scanning**: Claude Vision extracts recipes from photos of recipe cards, screenshots
- **Video processing**: Whisper transcription + frame analysis for cooking videos
- **Bulk import**: CSV upload with automatic Instagram post fetching
- **Notion sync**: Export recipes to Notion (optional)

## Setup

### Prerequisites

- Python 3.11+
- ffmpeg (for video processing)

```bash
# macOS
brew install ffmpeg
```

### Installation

```bash
# Clone the repo
git clone <repo-url>
cd recipe-aggregator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required:
- `ANTHROPIC_API_KEY` - For Claude recipe extraction

Optional:
- `OPENAI_API_KEY` - For Whisper video transcription
- `YOUTUBE_API_KEY` - For YouTube video details
- `INSTAGRAM_USERNAME` - For Instagram post fetching
- `NOTION_TOKEN` - For Notion export

### Instagram Setup (if using Instagram features)

Instagram requires a one-time login to create a session:

```bash
python scripts/instagram_login.py
```

This handles 2FA and saves the session for reuse.

## Usage

### Start the server

```bash
uvicorn backend.main:app --reload
```

API available at http://localhost:8000

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/ingest/youtube` | Ingest from YouTube video or playlist |
| `POST /api/ingest/instagram` | Ingest from Instagram post/reel |
| `POST /api/ingest/url` | Ingest from recipe website |
| `POST /api/ingest/manual` | Ingest from pasted text |
| `POST /api/ingest/csv` | Bulk import from CSV file |
| `POST /api/ingest/video` | Ingest from uploaded video file |
| `GET /api/recipes` | List all recipes |
| `GET /api/recipes/{id}` | Get recipe details |

### CSV Import

```bash
# Direct upload
curl -X POST "http://localhost:8000/api/ingest/csv" -F "file=@recipes.csv"

# Batch processing with progress
python scripts/batch_ingest.py recipes.csv
```

CSV format:
```csv
url,caption,image_url
https://instagram.com/p/xyz,Optional caption,Optional image URL
```

- `url` (required): Source URL
- `caption` (optional): Recipe text - auto-fetched for Instagram URLs
- `image_url` (optional): Image to scan if caption is minimal

### Video Upload

```bash
curl -X POST "http://localhost:8000/api/ingest/video" -F "file=@cooking_video.mp4"
```

Supported formats: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`

## Project Structure

```
backend/
├── main.py              # FastAPI app
├── config.py            # Settings
├── models/
│   └── schemas.py       # Pydantic models
├── db/
│   ├── database.py      # SQLite setup
│   ├── models.py        # SQLAlchemy models
│   └── crud.py          # Database operations
├── routers/
│   ├── ingest.py        # Ingestion endpoints
│   └── recipes.py       # Recipe CRUD endpoints
├── services/
│   ├── extractor.py     # Claude AI extraction
│   ├── youtube.py       # YouTube API
│   ├── instagram.py     # Instagram scraping
│   ├── recipe_scraper.py# Website scraping
│   ├── video.py         # Video processing
│   └── transcription.py # YouTube transcripts
└── prompts/
    └── extraction.py    # Claude prompts

scripts/
├── instagram_login.py   # Instagram session setup
├── batch_ingest.py      # Batch CSV processing
└── ingest_youtube.py    # YouTube playlist import
```

## Recipe Categories

Recipes are auto-categorized:
- `breakfast`, `lunch`, `dinner`, `snack`
- `dessert`, `beverage`, `appetizer`, `side`
- `technique` (for cooking techniques)
- `other`

## Development

```bash
# Run tests
pytest -v

# Lint
ruff check . --fix

# Format
ruff format .
```

## License

MIT
