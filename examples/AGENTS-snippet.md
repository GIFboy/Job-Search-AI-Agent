# Append this section to ~/.openclaw/workspace/AGENTS.md

## Job-search outreach approvals
When the user replies "APPROVE <n>" or "SKIP <n>" about nightly job outreach:
- Read $HOME/.openclaw/workspace/job-search/outbox/<n>.json
- APPROVE: send via `gog gmail send --to <to> --subject "<subject>" --body "<body>" --attach $HOME/.openclaw/workspace/job-search/CV.pdf`,
  then append a row to job-applications.md (date | title | company | score | to | Sent)
  and delete job-search/outbox/<n>.json
- SKIP: delete job-search/outbox/<n>.json and acknowledge briefly
- Never send an outreach email without an explicit APPROVE for that exact number.
