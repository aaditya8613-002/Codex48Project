import os
import tempfile
from pathlib import Path

# Must be set before the app is imported: tests use a throwaway SQLite file and no AI key.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp) / 'test.db'}"
os.environ["GEMINI_API_KEY"] = ""

import pytest  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.kit import load_kit  # noqa: E402
from app import models  # noqa: E402,F401

KIT = Path(__file__).resolve().parent.parent / "sample_kit" / "northwind.json"


@pytest.fixture()
def session():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture()
def org_id(session):
    return load_kit(session, KIT, embed=False)
