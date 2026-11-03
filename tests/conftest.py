"""Shared fixtures. Every test gets its own freshly loaded shop, so no test
depends on what an earlier test did."""

from datetime import date
from pathlib import Path

import pytest

from gearshare import GearShare

DATA_DIR = Path(__file__).parent.parent / "data"
TODAY = date(2026, 11, 3)


@pytest.fixture
def shop():
    gs = GearShare()
    gs.load_data(DATA_DIR)
    return gs


@pytest.fixture
def today():
    return TODAY
