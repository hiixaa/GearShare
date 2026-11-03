"""Shared fixtures.

Phase 3: every test gets its OWN fresh temporary database (schema + seed +
indexes), so no test depends on what an earlier test did, and every Phase 1
and Phase 2 test now runs with the real database underneath.
"""

import shutil
from datetime import date
from pathlib import Path

import pytest

from gearshare import GearShare
from sql.setup_db import create_database
from storage import Storage

DATA_DIR = Path(__file__).parent.parent / "data"
TODAY = date(2026, 11, 3)


@pytest.fixture(scope="session")
def template_db(tmp_path_factory):
    """Built ONCE per test run; each test gets a copy (copying is much faster)."""
    path = tmp_path_factory.mktemp("template") / "gearshare.db"
    create_database(path, out=lambda *_: None)
    return path


@pytest.fixture
def db_path(template_db, tmp_path):
    """A fresh database file for this test only."""
    path = tmp_path / "gearshare.db"
    shutil.copy(template_db, path)
    return path


@pytest.fixture
def shop(db_path):
    """The starter shop, loaded from (and saving to) a fresh database."""
    storage = Storage(db_path)
    gs = GearShare(storage)
    gs.load_data()
    yield gs
    storage.close()


@pytest.fixture
def today():
    return TODAY
