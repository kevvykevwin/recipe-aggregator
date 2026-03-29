from pathlib import Path

import pytest
from fastapi import HTTPException

from backend import main as app_main


@pytest.mark.asyncio
async def test_root_returns_controlled_error_when_frontend_is_missing(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(app_main, "FRONTEND_DIR", tmp_path / "missing-frontend")

    with pytest.raises(HTTPException) as exc_info:
        await app_main.root()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Frontend bundle is unavailable"
