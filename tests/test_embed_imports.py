import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_embed_app_exists():
    import embed

    assert embed.app is not None


def test_embed_app_registers_expected_routes():
    import embed

    paths = {route.path for route in embed.app.routes}
    assert "/health" in paths
    assert "/embed" in paths
    assert "/embed_sentences" in paths
    assert "/analyze" in paths
    assert "/memory" in paths


def test_embed_app_title():
    import embed

    assert embed.app.title == "Hawaiian Corpus Embedding Service"