# CLAUDE.md — Sapio LIMS Multi-Agent Orchestration System
# Version: 1.0

## System Overview

This is a **multi-agent orchestration system** for building Sapio LIMS
custom Python webhooks. One Coordinator Agent routes work to six specialist
sub-agents, each owning one phase of the SDLC.

You (Claude Code) operate AS the Coordinator Agent by default.
When the Coordinator invokes a sub-agent, you load that agent's `.md` file
and execute in that agent's persona until the sub-agent task completes,
then return to Coordinator mode.

```
User
  └─► Coordinator Agent          ← .claude/agents/coordinator.md
        ├─► Requirements Analyst  ← .claude/agents/requirements-analyst.md
        ├─► Webhook Designer      ← .claude/agents/webhook-designer.md
        ├─► Scaffold Engineer     ← .claude/agents/scaffold-engineer.md
        ├─► Code Reviewer         ← .claude/agents/code-reviewer.md
        ├─► Test Engineer         ← .claude/agents/test-engineer.md
        └─► UAT Packager          ← .claude/agents/uat-packager.md

Shared state: context/{TICKET-ID}.json
Protocol:     .claude/agents/shared-context.md
```

---

## Entry Point Rule

**Every request in this project routes through the Coordinator — there is no
direct path to a specialist agent.** This applies whether the request is:

- an explicit slash command (`/analyse-ticket LIMS-42`, `/run-pipeline
  LIMS-42`, ...) — each of the `.claude/commands/*.md` files is a thin
  delegator that loads `.claude/agents/coordinator.md` and hands off to it;
- raw natural language ("analyse LIMS-42", "what does this ticket need");
- or a prompt using the `TicketID:` / `Agent:` / `Skip Agents:` tags
  documented in `.claude/agents/coordinator.md`.

In every case: read `.claude/agents/coordinator.md` in full first and adopt
the Coordinator persona for the turn, before deciding which sub-agent(s) to
invoke. Do not shortcut this by mapping a tag or intent directly onto a
specialist's protocol — the specialist docs under `.claude/agents/` are only
ever reached *through* the Coordinator's Orchestration Protocol (Step 0
blocked-check, Prerequisites Table, shared-context read/write), never
independently.

---

## Quick Start

```bash
# Full pipeline from scratch
/run-pipeline LIMS-42

# Single phase
/analyse-ticket LIMS-42
/design-webhook LIMS-42
/scaffold-webhook LIMS-42
/review-webhook LIMS-42
/generate-tests LIMS-42
/prepare-uat LIMS-42

# Status check
/status LIMS-42

# Other pipeline state commands
/reset LIMS-42
/context LIMS-42
/skip-to LIMS-42 uat
```

All of the above are real, working commands under `.claude/commands/` — each
one loads `.claude/agents/coordinator.md` and executes the matching section
of its Orchestration Protocol / Pipeline State Commands table.

---

## MCP Servers

```json
{
  "mcpServers": {
    "atlassian": {
      "type": "url",
      "url": "https://mcp.atlassian.com/v1/mcp",
      "name": "atlassian-rovo"
    },
    "github": {
      "type": "url",
      "url": "https://github.com/mcp",
      "name": "github-mcp"
    },
    "microsoft365": {
      "type": "url",
      "url": "https://microsoft365.mcp.claude.com/mcp",
      "name": "m365-mcp"
    }
  }
}
```

**SCM: GitHub + Bitbucket (parallel).** GitHub is reached via `github-mcp` above.
Bitbucket has no equivalent hosted MCP — agents (`coordinator`, `scaffold-engineer`,
`code-reviewer`, `uat-packager`) that need Bitbucket access call the REST API
directly at `https://api.bitbucket.org/2.0` using `BITBUCKET_WORKSPACE` /
`BITBUCKET_REPO_SLUG` / `BITBUCKET_USERNAME` / `BITBUCKET_APP_PASSWORD` from `.env`.
Every SCM-facing step (branch create, PR/PR-equivalent, release/tag) must be
performed against **both** remotes when Bitbucket credentials are present.

---

## Agent Files

| File | Agent | Phase |
|------|-------|-------|
| `.claude/agents/coordinator.md` | Coordinator | Orchestration |
| `.claude/agents/requirements-analyst.md` | Requirements Analyst | Phase 1 |
| `.claude/agents/webhook-designer.md` | Webhook Designer | Phase 2 |
| `.claude/agents/scaffold-engineer.md` | Scaffold Engineer | Phase 3 |
| `.claude/agents/code-reviewer.md` | Code Reviewer | Phase 4 |
| `.claude/agents/test-engineer.md` | Test Engineer | Phase 5 |
| `.claude/agents/uat-packager.md` | UAT Packager | Phase 6 |
| `.claude/agents/shared-context.md` | Protocol | All phases |

Each phase also has a thin delegator command under `.claude/commands/`
(`analyse-ticket.md`, `design-webhook.md`, `scaffold-webhook.md`,
`review-webhook.md`, `generate-tests.md`, `prepare-uat.md`) plus five
pipeline-state commands (`run-pipeline.md`, `status.md`, `reset.md`,
`context.md`, `skip-to.md`) — all of them load coordinator.md rather than
containing their own protocol logic (see Entry Point Rule above).

---

## Environment Variables

Real values are never hardcoded in this file or any committed file — they live
in `.env` (git-ignored). See `.env.example` for the full template.

| Variable | Purpose |
|---|---|
| `SAPIO_URL` | Sapio LIMS tenant base URL |
| `SAPIO_USERNAME` / `SAPIO_PASSWORD` | Sapio API credentials |
| `ATLASSIAN_URL` | Jira/Confluence Cloud site base URL |
| `ATLASSIAN_EMAIL` / `ATLASSIAN_API_TOKEN` | Atlassian API token auth (Jira + Confluence) |
| `JIRA_PROJECT_KEY` | Jira project key for ticket routing |
| `CONFLUENCE_SPACE_KEY` | Confluence space key for design/UAT docs |
| `GITHUB_REPO` / `GITHUB_TOKEN` | GitHub repo slug + token (primary SCM) |
| `BITBUCKET_WORKSPACE` / `BITBUCKET_REPO_SLUG` / `BITBUCKET_USERNAME` / `BITBUCKET_APP_PASSWORD` | Bitbucket auth (secondary SCM, mirrored in parallel with GitHub) |
| `LUCID_API_TOKEN` | Lucid REST API token — required to fetch non-public Lucidchart diagrams |

---

## Coding Standards (enforced by Code Reviewer Agent)

- Python 3.11+ with strict mypy
- ruff linter, line length 100
- pytest with ≥ 80% coverage
- Google-style docstrings
- `context.get_logger()` — never `print()`
- Field access via `get_field_value()` — never dict access
- All post-save / event hooks must be idempotent
- No hardcoded credentials — use env vars

---

## Jira Field Mappings

| Custom field | Meaning |
|---|---|
| `customfield_10100` | Sapio Module |
| `customfield_10101` | Webhook Type hint |
| `customfield_10102` | Target Environment |

Workflow: `Backlog → In Analysis → In Development → In Review → In Testing → UAT Ready → Done`

---

## Confluence Layout

```
LIMS/
├── Architecture/
│   ├── Module-Specs/     ← per-module field docs + Lucidchart embeds
│   └── Data-Dictionary   ← canonical field name reference
├── Webhook-Designs/      ← one page per ticket (created by Webhook Designer)
│   └── Completed/        ← archived after UAT sign-off
└── UAT/                  ← UAT test scripts (created by UAT Packager)
```
