"""Shared fixtures. Everything here reads committed files — no network, no credits."""

import csv
import json
import os
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


@pytest.fixture(autouse=True)
def _isolate_mode_env():
    """Snapshot and restore the offline/online switches around every test.

    `app.py` sets `os.environ["HEATGUARD_OFFLINE"] = "1"` at import time, deliberately —
    the deployment must be offline by default. But `tests/test_app_runs.py` executes
    app.py in-process via AppTest, so that assignment leaked into the rest of the session
    and broke a tools test that needed online mode. The failure depended on test ORDER,
    which is the worst kind to debug.

    Restoring here fixes it in both directions and stops any future test that touches
    these variables from poisoning its neighbours.
    """
    saved = {k: os.environ.get(k) for k in ("HEATGUARD_OFFLINE", "HEATGUARD_ONLINE")}
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture(scope="session")
def site_rows() -> list[dict]:
    """config/sites.csv as a list of dicts — the built roster."""
    with (CONFIG / "sites.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="session")
def site_geojson() -> dict:
    return json.loads((CONFIG / "sites.geojson").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def site_source() -> dict:
    """config/sites_source.yaml — the human-authored input the artifacts derive from."""
    return yaml.safe_load((CONFIG / "sites_source.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def thresholds() -> dict:
    return yaml.safe_load((CONFIG / "thresholds.yaml").read_text(encoding="utf-8"))
