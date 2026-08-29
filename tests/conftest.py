"""Shared fixtures. Everything here reads committed files — no network, no credits."""

import csv
import json
import os
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


MODE_VARS = ("HEATGUARD_OFFLINE", "HEATGUARD_ONLINE")


@pytest.fixture(scope="session")
def _pristine_mode_env() -> dict[str, str | None]:
    """The offline/online switches as they were before any test ran."""
    return {k: os.environ.get(k) for k in MODE_VARS}


@pytest.fixture(autouse=True)
def _isolate_mode_env(_pristine_mode_env):
    """Reset the offline/online switches to their session-start values after every test.

    `app.py` sets `os.environ["HEATGUARD_OFFLINE"] = "1"` at import, deliberately — the
    deployment must be offline by default. `tests/test_app_runs.py` executes app.py
    in-process via AppTest, so that assignment leaked into the whole session and broke a
    tools test that needed online mode. The failure depended on test ORDER, which is the
    worst kind to debug.

    Restoring to a SESSION-START baseline rather than to whatever was set when this
    fixture happened to run matters: `test_app_runs.py` sets its state in a
    module-scoped fixture, which executes *before* the function-scoped snapshot would.
    Snapshotting there captured the already-polluted value and faithfully restored the
    pollution — a fixture that looked like isolation and provided none.
    """
    try:
        yield
    finally:
        for key, value in _pristine_mode_env.items():
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
