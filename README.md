# Job Search AI Agent

An autonomous, self-hosted job-search agent built on **[OpenClaw](https://openclaw.ai)**.
Every night it searches for jobs matching your profile, scores them, finds recruiter
contacts, drafts personalized outreach emails (with your CV attached), and sends them to
you on **Telegram for one-tap approval** before anything is emailed via **Gmail**.

```
JSearch (RapidAPI) ──► score ──► Hunter.io (recruiter email) ──► cold-email draft
        └────────────────────────────────────────────────────────────┘
                                   │
                      Telegram: "APPROVE 1 / SKIP 1"
                                   │
                       gog → Gmail send (CV attached) ──► applications log
```

## What it does

1. **Fetch** jobs from JSearch (RapidAPI) using your configured queries (local + global remote).
2. **Score** each job 0–100 against your must-have / nice-to-have skills, location, and recency.
3. **Find recruiters** for the top matches via Hunter.io domain search.
4. **Draft** a unique, personalized outreach email per job (formal template, tailored to the posting).
5. **Ask you on Telegram** — one message per night listing the top candidates with `APPROVE n` / `SKIP n`.
6. **Send** approved emails from your Gmail with your **CV attached**, and log them.

It runs unattended via a **systemd user timer** and survives reboots (lingering enabled).

## Architecture

| Layer | Tech |
|-------|------|
| Agent runtime | OpenClaw gateway (systemd `--user` service) |
| Chat / approvals | Telegram bot |
| Email + Calendar | `gog` CLI (Google Workspace) with OAuth |
| Job data | JSearch (RapidAPI) |
| Recruiter emails | Hunter.io |
| Email drafting | OpenClaw `cold-email-writer` skill |
| Scheduling | systemd timer (`OnCalendar`, timezone-aware) |

## Prerequisites

- An always-on **Linux server** (tested on Ubuntu 24.04, x86_64) with **Node.js ≥ 22**.
- **Anthropic API key** (powers the agent).
- **Telegram bot token** (from [@BotFather](https://t.me/BotFather)).
- **Google Cloud OAuth client** (Desktop app) with Gmail API + Calendar API enabled,
  and your Gmail added as a **Test user** on the consent screen.
- **RapidAPI** account subscribed to [JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch).
- **Hunter.io** API key (free tier = 50 searches/mo).

## Repository layout

```
.
├── README.md
├── SETUP.md                      # quick host reference / go-live checklist
├── scripts/
│   ├── jsearch_jobs.py           # fetch + normalize jobs (per-query country/remote)
│   ├── scorer.py                 # score & rank top-N against your config
│   └── hunter_lookup.py          # recruiter/hiring emails via Hunter.io
├── nightly-prompt.txt            # the orchestration prompt the agent runs each night
├── run-nightly.sh                # wrapper the timer executes (openclaw agent ...)
├── systemd/
│   ├── nightly-job-search.service
│   ├── nightly-job-search.timer  # 21:00, timezone-aware
│   ├── gog-keyring.conf.example  # drop-in: inject gog keyring password into gateway
│   └── job-agent.conf.example    # drop-in: inject API keys into gateway
└── examples/
    ├── secrets.env.example
    ├── search-config.example.json
    ├── job-search-profile.example.md
    └── AGENTS-snippet.md          # approval-handling guidance for the agent
```

## Setup (summary)

> Full step-by-step lives in [`SETUP.md`](SETUP.md). High level:

### 1. Install OpenClaw
```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -   # Node 22
sudo apt-get install -y nodejs
sudo npm install -g openclaw
openclaw onboard --non-interactive --accept-risk \
  --auth-choice apiKey --anthropic-api-key "sk-ant-..." \
  --gateway-bind loopback --gateway-auth token --install-daemon \
  --skip-channels --skip-search --skip-ui
loginctl enable-linger "$USER"
systemctl --user enable --now openclaw-gateway
```

### 2. Telegram
```bash
openclaw channels add --channel telegram --token "<BOT_TOKEN>"
systemctl --user restart openclaw-gateway
# message the bot once, then:
openclaw pairing approve telegram <CODE>
```

### 3. Gmail via gog
```bash
openclaw skills install gog
openclaw skills install cold-email-writer
# install the gog binary (Linux): grab the latest release tarball
#   https://github.com/openclaw/gogcli/releases   ->  install gog to /usr/local/bin
gog auth keyring file                 # GOG_KEYRING_PASSWORD must be set
gog auth credentials /path/to/client_secret.json
# headless OAuth (remote person, different computer): single-process --manual flow
gog auth add you@gmail.com --services gmail,calendar --manual --timeout 30m
#   -> open the printed URL, approve, paste the redirect URL back into the same process
```

> **Headless OAuth note:** this gog build does **not** persist PKCE state between
> separate `--remote --step 1` / `--step 2` runs. Use either the **single-process
> `--manual`** flow (paste the redirect URL into the same running process) or the
> **listener + SSH tunnel** method when the browser is on the same machine that can
> reach the server. See `SETUP.md`.

### 4. Job APIs
```bash
# store keys in ~/.config/job-agent/secrets.env (see examples/secrets.env.example)
# subscribe your RapidAPI key to JSearch first
```

### 5. Wire secrets into the gateway
Drop-ins make the keys available to the agent's `exec` tool:
```bash
mkdir -p ~/.config/systemd/user/openclaw-gateway.service.d
cp systemd/gog-keyring.conf.example ~/.config/systemd/user/openclaw-gateway.service.d/gog-keyring.conf
cp systemd/job-agent.conf.example   ~/.config/systemd/user/openclaw-gateway.service.d/job-agent.conf
systemctl --user daemon-reload && systemctl --user restart openclaw-gateway
```

### 6. Profile, config, CV, and schedule
```bash
# copy examples into ~/.openclaw/workspace and edit for the candidate
cp examples/job-search-profile.example.md ~/.openclaw/workspace/job-search-profile.md
mkdir -p ~/.openclaw/workspace/job-search
cp examples/search-config.example.json    ~/.openclaw/workspace/job-search/search-config.json
cp scripts/*.py nightly-prompt.txt run-nightly.sh ~/.openclaw/workspace/job-search/
chmod +x ~/.openclaw/workspace/job-search/*.py ~/.openclaw/workspace/job-search/run-nightly.sh
# put the candidate's CV at ~/.openclaw/workspace/job-search/CV.pdf
# append examples/AGENTS-snippet.md to ~/.openclaw/workspace/AGENTS.md
cp systemd/nightly-job-search.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now nightly-job-search.timer
```

## Daily use

The agent messages you on Telegram each night with the top candidates. Reply:

- `APPROVE 1` → send that outreach email (CV attached) and log it
- `SKIP 1` → discard that draft

Manual controls:
```bash
systemctl --user list-timers nightly-job-search.timer   # next run
systemctl --user start nightly-job-search.service        # run now
journalctl --user -u nightly-job-search.service -n 50    # logs
```

## Security & privacy

- **No secrets are committed.** All keys/tokens live in `~/.config/...` on the server
  (`chmod 600`) and are git-ignored. The `gog` refresh token is stored in an encrypted
  keyring (`file` backend, protected by `GOG_KEYRING_PASSWORD`).
- The gateway binds to **loopback** with token auth.
- Outreach is **never** sent without your explicit `APPROVE`.

## Notes & gotchas

- **Google consent screen** in *Testing* mode issues refresh tokens that can expire
  after ~7 days. Publish to **Production** for hands-off 24/7 operation.
- **Hunter.io free tier** = 50 searches/month; keep `top_n` modest.
- Jobs from aggregators (e.g. job-board mirror domains) often have no real employer
  domain, so no recruiter email can be found — those are skipped.

## License

MIT — see [LICENSE](LICENSE).

---
*Built with [OpenClaw](https://openclaw.ai).*
