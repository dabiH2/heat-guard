# Vendored third-party code

## `vendor/fortyguard/` — FortyGuard Temperature API quickstart client

| | |
|---|---|
| Upstream | https://github.com/FortyGuard-Tech/temperature-api-quickstart |
| Pinned commit | `f6de12d241810e3d45f39da4079db08ffeca6fc3` (2026-08-04) |
| Licence | MIT — see `LICENSE-fortyguard-quickstart` |
| Copyright | © 2026 FortyGuard, Inc. |
| Vendored | 2026-08-20, unmodified |

`__init__.py`, `client.py`, `exceptions.py`, `samples.py` — copied byte-for-byte. **Do not
edit these files.** All HeatGuard behaviour lives in `src/heatguard/tools.py`, which wraps
them. If upstream changes, re-vendor and re-run the tests rather than patching in place.

### Why vendored rather than a submodule or a pip install

- The upstream repo ships **no** `pyproject.toml` or `setup.py`, so `pip install git+…`
  cannot work.
- A submodule would make `git clone` alone produce a broken checkout for a judge, and the
  submission requires a judge-accessible repo that runs.
- The upstream repo is ~32 MB, almost all of it notebook-embedded imagery and sample data.
  The client itself is four files and 25 KB.
- Pinning to a SHA means upstream cannot change under the demo mid-hackathon.

CLAUDE.md: *"The quickstart repo ships a Python client that already does auth and
submit-then-poll. Wrap it. Do not rebuild it."*

---

## `data/fixtures/vendor_samples/` — upstream sample responses

Three response captures from the same repo, kept as **offline fixtures** so `tools.py` and
`router.py` can be tested against real API response shapes with **zero credits and no API
key**. They are San José, not Phoenix — they pin the *schema*, not our data.

| File | What it pins |
|---|---|
| `env_params_…_2024-07-15.json` | `/v1/env_params` — 24 hourly values, `heat_index_celsius`, local-time `metadata.timestamps` |
| `heatmap_…_exceedance.json` | `/v1/heatmap` `analytic_type="exceedance"` — per-tile `properties.value` in **hours**, `stats_data.units == "hour"` |
| `heatmap_…_persistence.json` | same shape, longest continuous run instead of a total |

These are the reason `docs/api-notes.md` could be filled in before a single credit was
spent.
