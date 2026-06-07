#!/usr/bin/env python3
"""Score jobs in jobs_latest.json against search-config.json criteria.
Writes ranked top-N to scored_jobs.json and prints a summary.
Score (0-100): must-have skills 50, nice-to-have 25, location 15, recency 10.
Jobs containing any exclude term are dropped.
"""
import json, datetime, pathlib

HERE = pathlib.Path(__file__).resolve().parent
cfg  = json.loads((HERE/"search-config.json").read_text())
data = json.loads((HERE/"jobs_latest.json").read_text())
jobs = data.get("jobs", [])

must    = [s.lower() for s in cfg.get("must_have", [])]
nice    = [s.lower() for s in cfg.get("nice_to_have", [])]
exclude = [s.lower() for s in cfg.get("exclude", [])]
locs    = [s.lower() for s in cfg.get("locations", [])]
top_n   = int(cfg.get("top_n", 5))

def text_of(j):
    keys = ("title","description","city","state","country","employment_type")
    return " ".join(str(j.get(k) or "") for k in keys).lower()

scored = []
for j in jobs:
    t = text_of(j)
    if any(x in t for x in exclude):
        continue
    must_hits = [m for m in must if m in t]
    nice_hits = [n for n in nice if n in t]
    score = 0.0
    if must: score += 50 * (len(must_hits)/len(must))
    if nice: score += 25 * (len(nice_hits)/len(nice))
    if any(l in t for l in locs) or bool(j.get("is_remote")): score += 15
    try:
        posted = datetime.datetime.fromisoformat((j.get("posted_utc") or "").replace("Z","+00:00"))
        days = (datetime.datetime.now(datetime.timezone.utc) - posted).days
        score += max(0, 10 - days)
    except Exception:
        pass
    j2 = dict(j)
    j2["score"] = round(min(100, score), 1)
    j2["must_hits"] = must_hits
    j2["nice_hits"] = nice_hits
    scored.append(j2)

scored.sort(key=lambda x: x["score"], reverse=True)
top = scored[:top_n]
(HERE/"scored_jobs.json").write_text(json.dumps(
    {"scored_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "top": top}, indent=2))

print("Scored {} eligible jobs; top {}:".format(len(scored), len(top)))
for j in top:
    loc = "{} {}".format(j.get("city") or "", j.get("country") or "").strip()
    print("  {:5.1f}  {} @ {} ({}) {}".format(
        j["score"], j.get("title"), j.get("company"), loc, j.get("company_website") or ""))
