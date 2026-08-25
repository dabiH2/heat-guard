# Deploying the live demo

The live link is the submission's highest-value artefact. FortyGuard, `01-kickoff`
`[00:59:19]`: *"the judges won't be opening the GitHub repositories that often […] what
they will 100% open is your pitch, the live link."*

It must stay reachable until **16 September** — judging runs ~2.5 weeks past the 30 Aug
deadline.

---

## The app needs no API key. That is deliberate.

`app.py` forces `HEATGUARD_OFFLINE=1` unless `HEATGUARD_ONLINE=1` is explicitly set, so
the deployed instance serves entirely from the committed cache in `data/fixtures/api/`.

Three reasons, in order of how much they matter:

1. **A live app can be made to spend money.** Every uncached request costs 4,220 credits
   and there is no rate limit between a curious judge and the budget. Twelve sites and a
   few dates of idle clicking is tens of thousands of credits.
2. **The key expires 2026-09-21**, five days after judging ends. An app that depends on
   the API is an app that dies mid-judging.
3. **No key means no secret to leak** — nothing in the deployment config, nothing in a
   demo video frame. Keys in repos are an explicit disqualifier.

Everything the demo shows was captured live and committed. `data/fixtures/api/` is the
production data store, not a cache.

---

## Streamlit Community Cloud

1. Go to **share.streamlit.io** and sign in with GitHub **as `dabiH2`** (the account that
   owns the repo — not a different one, or it will not see it).
2. Authorise Streamlit for **private** repositories when prompted. `dabiH2/heat-guard` is
   private; without this it will not appear in the picker.
3. **New app** → *Deploy a public app from a repo*:
   - Repository: `dabiH2/heat-guard`
   - Branch: `main`
   - Main file path: `app.py`
4. **Advanced settings** → Python version **3.12**.
5. **Secrets: leave empty.** The app needs none. If you add a FortyGuard key it will still
   run offline, because the app opts in to online mode rather than out of it — but there
   is no reason to put one there.
6. Deploy. First build takes a few minutes while `requirements.txt` installs.

### Keeping it awake

Community Cloud sleeps an app after ~7 days idle and wakes it on the next request with a
cold start of 30–60 s. A judge hitting a sleeping app may read it as broken.

Cheapest mitigation: a free uptime monitor (UptimeRobot, cron-job.org) pinging the app URL
every 12 hours from now until 17 September. Set it up the day you deploy, not the week
judging starts.

---

## Verifying a deploy

Check these on the live URL, in order — each one catches a different failure:

- [ ] The page loads and the **"Serving from the cached fixture set"** banner is visible.
      If that banner is missing, the app is in online mode and can spend credits.
- [ ] **Decision** tab: pick `PHX-CHASE`, date `2025-07-15`, ask *"How many hours were
      they above the danger threshold?"* → a result appears with a stated layer.
      A `CacheMiss` here means the fixture set did not ship; check `data/fixtures/api/`
      is present in the repo and not gitignored.
- [ ] Change the question to *"Is this site chronically dangerous?"* → a **refusal**,
      not an answer. Refusals are a feature and this is the fastest way to see one.
- [ ] **The trap** tab renders the 17.0 h vs 0.0 h comparison.
- [ ] No API key appears anywhere in the page source.

## Running it locally

```bash
venv\Scripts\activate
streamlit run app.py
```

Offline by default, same as production. To let it hit the live API (developer machines
only, spends credits):

```bash
set HEATGUARD_ONLINE=1 && streamlit run app.py
```
