#!/usr/bin/env python3
"""Fetch jobs from JSearch (RapidAPI) using search-config.json.
Each query may be a string (uses default country) or an object:
  {"q": "...", "country": "lk", "remote": true}
Writes normalized, de-duplicated jobs to jobs_latest.json.
Reads RAPIDAPI_KEY / RAPIDAPI_HOST from the environment.
Exits non-zero with JSEARCH_NOT_SUBSCRIBED if the key is not subscribed.
"""
import json, os, sys, time, datetime, pathlib, urllib.parse, urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
CFG  = HERE / "search-config.json"
OUT  = HERE / "jobs_latest.json"

KEY  = os.environ.get("RAPIDAPI_KEY")
HOST = os.environ.get("RAPIDAPI_HOST", "jsearch.p.rapidapi.com")
if not KEY:
    sys.exit("ERROR: RAPIDAPI_KEY not set in environment")

cfg = json.loads(CFG.read_text())
queries     = cfg.get("queries", [])
date_posted = cfg.get("date_posted", "week")
num_pages   = int(cfg.get("num_pages", 1))
def_country = cfg.get("country", "us")

def fetch(q, country, remote):
    params = {"query": q, "page": "1", "num_pages": str(num_pages),
              "date_posted": date_posted, "country": country}
    if remote:
        params["remote_jobs_only"] = "true"
    url = f"https://{HOST}/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"x-rapidapi-key": KEY,
                                               "x-rapidapi-host": HOST})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

seen = {}
for item in queries:
    if isinstance(item, dict):
        q = item.get("q") or item.get("query")
        country = item.get("country", def_country)
        remote = bool(item.get("remote", False))
    else:
        q, country, remote = item, def_country, False
    if not q:
        continue
    try:
        data = fetch(q, country, remote)
    except urllib.error.HTTPError as e:
        body = ""
        try: body = e.read().decode()
        except Exception: pass
        if e.code in (401, 403) or "not subscribed" in body.lower():
            sys.exit(f"JSEARCH_NOT_SUBSCRIBED: HTTP {e.code} {body[:200]} "
                     f"-- subscribe at rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch")
        print(f"WARN query failed: {q} [{country}]: HTTP {e.code} {body[:120]}", file=sys.stderr)
        continue
    except Exception as e:
        print(f"WARN query failed: {q} [{country}]: {e}", file=sys.stderr); continue
    for j in (data.get("data") or []):
        jid = j.get("job_id")
        if not jid or jid in seen:
            continue
        seen[jid] = {
            "job_id": jid,
            "title": j.get("job_title"),
            "company": j.get("employer_name"),
            "company_website": j.get("employer_website"),
            "employment_type": j.get("job_employment_type"),
            "city": j.get("job_city"), "state": j.get("job_state"),
            "country": j.get("job_country"), "is_remote": j.get("job_is_remote"),
            "posted_utc": j.get("job_posted_at_datetime_utc"),
            "publisher": j.get("job_publisher"),
            "apply_link": j.get("job_apply_link"),
            "description": (j.get("job_description") or "")[:4000],
            "query": q,
        }
    time.sleep(1)

jobs = list(seen.values())
OUT.write_text(json.dumps({"fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           "count": len(jobs), "jobs": jobs}, indent=2))
print(f"Fetched {len(jobs)} unique jobs across {len(queries)} queries -> {OUT}")
