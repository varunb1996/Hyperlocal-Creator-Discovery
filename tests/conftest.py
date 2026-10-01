"""The creator workbook is private (not in the repo). Without it, data-dependent tests skip with a reason
instead of erroring, so CI still runs the synthetic and API-boot tests. Locally, with the file, all run."""
from pathlib import Path

import pytest

from normalize import CREATORS_XLSX

HAS_DATA = Path(CREATORS_XLSX).exists()

# Fixtures that load the workbook.
DATA_FIXTURES = {"pool", "cafes", "vocab", "mappings", "validated", "rows", "seeded", "ctx"}


def pytest_collection_modifyitems(config, items):
    if HAS_DATA:
        return
    skip = pytest.mark.skip(reason="creator workbook not present (private data; see README > Data)")
    for item in items:
        if DATA_FIXTURES & set(getattr(item, "fixturenames", ())) or item.get_closest_marker("needs_data"):
            item.add_marker(skip)
