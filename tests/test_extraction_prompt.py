import json

from backend.prompts.extraction import EXTRACTION_SYSTEM_PROMPT


def test_required_output_format_is_valid_json() -> None:
    start_marker = "REQUIRED OUTPUT FORMAT (JSON):"
    end_marker = "GUIDELINES:"
    prompt_body = EXTRACTION_SYSTEM_PROMPT.split(start_marker, 1)[1].split(end_marker, 1)[0]

    parsed = json.loads(prompt_body.strip())

    assert parsed["macros"] is None
