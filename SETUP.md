# OpenClaw Job-Search Agent — Setup Reference

Host: &lt;your-server&gt; (Ubuntu 24.04). Gateway runs as systemd --user service (linger on).

## Components
- OpenClaw gateway: `systemctl --user status openclaw-gateway`
- Telegram bot @&lt;your_bot&gt;, owner chatId &lt;TELEGRAM_CHAT_ID&gt;
- Skills: gog (Gmail/Calendar), cold-email-writer
- gog auth: &lt;you@gmail.com&gt; (gmail+calendar)

## Secrets (chmod 600, injected into gateway env via drop-ins)
- ~/.config/gogcli/keyring.env      GOG_KEYRING_PASSWORD, GOG_ACCOUNT
- ~/.config/job-agent/secrets.env   RAPIDAPI_KEY, RAPIDAPI_HOST, HUNTER_API_KEY

## Pipeline (job-search/)
- search-config.json   queries/locations/skills/exclude/top_n  (EDIT to match profile)
- jsearch_jobs.py      fetch jobs from JSearch  -> jobs_latest.json
- scorer.py            score & rank top_n       -> scored_jobs.json
- hunter_lookup.py     recruiter emails via Hunter.io
- nightly-prompt.txt   instructions the agent runs each night
- run-nightly.sh       wrapper the timer executes
- outbox/<n>.json      drafted emails awaiting APPROVE/SKIP

## Schedule
- systemd timer: nightly-job-search.timer  @ 21:00 &lt;Your/Timezone&gt; (e.g. Asia/Colombo)
- Service:       nightly-job-search.service (runs run-nightly.sh)

## Go-live checklist
1. Subscribe to JSearch:  https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
2. Fill ../job-search-profile.md and edit search-config.json to match.
3. Test once:   systemctl --user start nightly-job-search.service
                journalctl --user -u nightly-job-search.service -n 50
4. Enable nightly:  systemctl --user enable --now nightly-job-search.timer
5. Approve outreach in Telegram: reply "APPROVE <n>" or "SKIP <n>".

## Manual test of pieces
  set -a; . ~/.config/job-agent/secrets.env; set +a
  python3 job-search/jsearch_jobs.py && python3 job-search/scorer.py
  python3 job-search/hunter_lookup.py <company-domain>
