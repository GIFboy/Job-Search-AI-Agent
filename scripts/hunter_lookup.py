#!/usr/bin/env python3
"""Find likely recruiter/hiring emails for a company domain via Hunter.io.
Usage: hunter_lookup.py <domain>
Reads HUNTER_API_KEY from environment. Prints JSON with ranked candidates.
"""
import json, os, sys, urllib.parse, urllib.request

key = os.environ.get("HUNTER_API_KEY")
if not key: sys.exit("ERROR: HUNTER_API_KEY not set in environment")
if len(sys.argv) < 2: sys.exit("usage: hunter_lookup.py <domain>")
domain = sys.argv[1].replace("https://","").replace("http://","").strip("/").split("/")[0]

url = "https://api.hunter.io/v2/domain-search?" + urllib.parse.urlencode(
        {"domain": domain, "api_key": key, "limit": "10"})
with urllib.request.urlopen(url, timeout=30) as r:
    d = json.loads(r.read().decode())

emails = (d.get("data") or {}).get("emails", []) or []
def rank(e):
    dep = ((e.get("department") or "")+" "+(e.get("position") or "")).lower()
    s = 0
    for kw,w in [("recruit",5),("talent",5),("hiring",5),("hr",4),
                 ("human resources",4),("people",3),("founder",2),("ceo",2)]:
        if kw in dep: s += w
    return s
emails.sort(key=rank, reverse=True)
out = [{"email":e.get("value"),"first":e.get("first_name"),"last":e.get("last_name"),
        "position":e.get("position"),"department":e.get("department"),
        "confidence":e.get("confidence"),"type":e.get("type")} for e in emails[:5]]
print(json.dumps({"domain":domain,
                  "organization":(d.get("data") or {}).get("organization"),
                  "candidates":out}, indent=2))
