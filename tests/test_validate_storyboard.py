import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_storyboard import validate  # noqa: E402

FIX = Path(__file__).parent / "fixtures" / "storyboard.valid.json"


def test_valid_fixture_passes():
    assert validate(json.loads(FIX.read_text())) == []


def test_missing_field_fails():
    data = json.loads(FIX.read_text())
    del data["hook"]
    assert validate(data)


def test_scene_cap():
    assert validate(json.loads(FIX.read_text()), max_scenes=1)
