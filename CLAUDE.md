# CLAUDE.md

Sapio LIMS webhook server for Stowers Institute. A Flask app (served by Waitress) that Sapio calls
over HTTP when a user clicks a toolbar button, saves a record, or opens a selection-list field.
Each handler receives a `SapioWebhookContext`, does work via `sapiopylib` / `sapiopycommons`, and
returns a `SapioWebhookResult`.

Active branch: `StowersImplementation`.

## Before writing or modifying a handler

**Read `.claude/skills/sapio-webhook-plugin/SKILL.md` first.** It is the canonical source for
trigger types, handler conventions (record creation, dialogs, error handling, extensions-as-
children, when to `store_and_commit`), and the end-to-end generation workflow. Don't reconstruct
those rules from surrounding code — some existing handlers predate them.

Supporting material:

| File | What it gives you |
|---|---|
| `kb/references/api-reference.md` | API surface — context attributes, managers on `self`, result/directive types, endpoint types |
| `kb/references/examples.md` | Worked end-to-end plugins |
| `kb/templates/handler_template.py` | Skeleton for a new handler |

## Commands

The virtualenv lives in the **parent** directory, not in this repo: `../.venv` (Python 3.14.3).

```bash
../.venv/Scripts/python.exe server.py            # Waitress on 0.0.0.0:8090
../.venv/Scripts/python.exe -c "import server"    # sanity check — prints "** Registration Completed **"
../.venv/Scripts/python.exe -m py_compile <file>  # syntax check an edited handler
```

Setup — includes `ruff`, which the edit hook's lint step needs:

```bash
python -m pip install -r requirements.txt
```

Environment variables:

- `SapioWebhooksDebug=True` — run the Flask dev server instead of Waitress.
- `SapioWebhooksInsecure=True` — disables Sapio cert verification. Local dev tenants only;
  **never** set this on a deployed server.

To let Sapio reach your machine, tunnel the port and set the tunnel URL as the webhook base
endpoint in the Sapio app:

```bash
cloudflared tunnel --url http://localhost:8090
```

Health check: `GET /ping` → `Alive!`. The repo README renders at `/`.

## Layout

| Path | Purpose |
|---|---|
| `server.py` | Entry point — imports and registers every endpoint. `grep config.register server.py` for the current list |
| `webhooks/<TriggerType>/` | Handlers, grouped by how Sapio invokes them |
| `webhooks/commons/data_type_models.py` | Generated typed record models — see gotchas |
| `kb/` | API reference, examples, template, `openapi.yaml`, `relationship.md` |
| `.claude/skills/` | `sapio-webhook-plugin`, `lucid-model-reconcile` |
| `.claude/hooks/check_python.py` | Runs after every edit — syntax, lint, and import checks. Blocks on failure |

## Gotchas

**`webhooks/commons/data_type_models.py` is ~62k lines (~2.9 MB). Never read it whole.** Grep for
`class <Name>Model` or the specific `*__FIELD_NAME` constant you need, or read with an
offset/limit. Use the typed constants
(`RequestModel.C_REQUESTEDFOR__FIELD_NAME.field_name`) rather than raw strings.

**The generated models are stale against the live tenant.** A field present in the dump does not
prove it exists in the tenant, and a field missing from the dump may exist. See the comment at
`webhooks/table_toolbar/create_samples_and_request_from_dna_parts.py:19-26`. When a set on a
picklist field fails, the platform's error says nothing about which values are legal — query the
tenant's real definitions through `self.dt_man.get_field_definition_list(...)` and
`self.list_man.get_picklist(...)` instead of trusting the dump. `_validate_picklist_value` in that
same file is the working example to copy.

**Registration is manual and easy to forget.** A new handler needs *both* an import and a
`config.register('/path', Handler)` line in `server.py`. `python -c "import server"` catches a
broken import but will not tell you a handler went unregistered.

**The Sapio-side button or rule cannot be created from code.** After adding an endpoint, someone
must configure the toolbar button / on-save rule by hand in the Sapio app and point it at
`<server-url>/<path>`. Always say this explicitly when reporting a new endpoint — the work isn't
finished without it.

**No debug `print()` in committed handlers.** Use `self.callback.display_info(...)` for
user-visible progress or `self.logger` for server-side logging.

**On-save handlers receive mixed record types.** Filter `context.data_record_list` by
`data_type_name` before wrapping into models — the platform includes records beyond the one that
triggered the rule.
