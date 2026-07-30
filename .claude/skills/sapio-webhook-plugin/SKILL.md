---
name: sapio-webhook-plugin
description: >-
  Generate a Sapio LIMS webhook plugin (toolbar button, action menu, on-save /
  ELN rule, selection-list field, scheduled task) from a plain-language
  requirement. Writes a CommonsWebhookHandler in webhooks/, wires it into
  server.py, and uses the sapiopylib / sapiopycommons APIs for dialogs
  (CallbackUtil forms, selections, confirmations), record creation
  (RecordModelManager), navigation (WebhookDirective), and typed data models
  from webhooks/commons/data_type_models.py. Use whenever the user asks to
  "create/add a Sapio plugin/webhook/toolbar button/action button/rule", e.g.
  "add a table toolbar in Request that prompts a form and navigates to the new
  record".
---

# Sapio Webhook Plugin Generator

Turn a plain-language requirement into a working Sapio webhook plugin: a Python
handler under `webhooks/`, registered in `server.py`, using the installed
`sapiopylib` + `sapiopycommons` APIs and the repo's typed record models.

A Sapio webhook is an HTTP endpoint the Sapio platform calls when a user clicks a
button, saves a record, launches an experiment, etc. Your handler receives a
`SapioWebhookContext`, does work (dialogs, record CRUD), and returns a
`SapioWebhookResult` that can carry a navigation directive.

## Workflow

Follow these steps for every request.

1. **Classify the trigger** → pick the endpoint type. This decides how the plugin
   is invoked in Sapio and what is on the context. See the table in
   `references/api-reference.md` §Endpoint types. Common cases:
   - "table toolbar button on X" → `TABLETOOLBAR`; `context.data_record_list`
     holds the selected rows of type X.
   - "form toolbar button" / "action menu on X" → `FORMTOOLBAR` / `ACTIONMENU`;
     `context.data_record` is the single record.
   - "when X is saved" → on-save rule (`VELOX_RULE_ACTION`); `context.data_record_list`.
   - "ELN entry button" / "experiment toolbar" → `EXPERIMENTENTRYTOOLBAR` /
     `NOTEBOOKEXPERIMENTMAINTOOLBAR`; `context.eln_experiment`, `context.experiment_entry`.
   - "selection list field values for X" → `SELECTIONDATAFIELD`; return
     `SapioWebhookResult(True, list_values=[...])` (see `BillableAccount.py`).
   - "scheduled task / nightly job" → `SCHEDULEDPLUGIN`.

2. **Resolve data types & fields.** Every data type the plugin touches (Request,
   Sample, etc.) should map to a generated model class in
   `webhooks/commons/data_type_models.py`. That file is huge (~2.9 MB) — never
   read it whole. Grep it for `class <Name>Model` and for the specific
   `*__FIELD_NAME` constants you need. Use those typed constants
   (`RequestModel.C_REQUESTEDFOR__FIELD_NAME.field_name`) instead of raw strings.
   If a needed data type/field is absent, tell the user and fall back to string
   field names, flagging the assumption.

3. **Design the interaction flow** from the requirement. Map each user-facing
   step to a `CallbackUtil` call (form, selection, confirm, message, file) and
   each data change to a `RecordModelManager` operation. See
   `references/api-reference.md` §CallbackUtil and §Records.

4. **Choose the ending directive** — where the user lands afterward. Navigate to
   a created/edited record with `FormDirective(record)` (single) or
   `TableDirective(records)` (many), or `DirectiveUtil.record_adaptive(records)`.
   ELN → `ElnExperimentDirective` / `ExperimentEntryDirective`. See §Directives.

5. **Write the handler** in the right subfolder of `webhooks/` (mirror existing
   layout: `webhooks/SelectionList/`, `webhooks/OnSave/`, or a new folder named
   for the endpoint type, e.g. `webhooks/TableToolbar/`). Start from
   `templates/handler_template.py`. Prefer `CommonsWebhookHandler` (override
   `execute`) — it wires up managers on `self` and turns exceptions into
   user-facing messages. Use bare `AbstractWebhookHandler` (override `run`) only
   for the simplest selection-list plugins or when avoiding the commons dep.

6. **Register the endpoint** in `server.py`: add the import and a
   `config.register('/snake_case_path', HandlerClass)` line next to the existing
   ones. Give the user the endpoint path so they can configure the button/rule
   in Sapio to point at `<server-url>/snake_case_path`.

7. **Report** what you created: files, endpoint path, and the manual Sapio-side
   configuration the user must do (create the toolbar button / rule and set its
   webhook URL to the registered path). You cannot configure the Sapio UI from
   code — always state this.

## Conventions (match the existing repo)

- Handlers subclass `CommonsWebhookHandler` and implement `execute(self, context)`.
  Managers are already on `self`: `self.rec_man`, `self.inst_man`, `self.dr_man`,
  `self.eln_man`, `self.callback` (a `CallbackUtil`), `self.directive`.
- Raise `SapioUserErrorException("message")` to abort with a friendly toaster and
  a failed result — don't return silent failures. Import from
  `sapiopycommons.general.exceptions`.
- Create records with `self.inst_man.add_new_record_of_type(SomeModel)`, set
  fields with the typed `set_*_field` methods or `set_field_value(FIELD.field_name, v)`,
  link with `parent.add_child(child)`, then persist with
  `self.rec_man.store_and_commit()` ONCE at the end.
- Every dialog can be cancelled — `CallbackUtil` raises `SapioUserCancelledException`,
  which `CommonsWebhookHandler` handles as a clean cancel. Don't wrap dialogs in
  broad `try/except` that swallows this.
- Use `FieldBuilder` to build form fields; `static_values=[...]` for fixed
  dropdowns via `selection_list_field`.
- **Extensions treated as children.** Some data types carry another type as a
  Sapio *extension* (its fields surface on the parent as `Ext.Field`, e.g.
  `Request` exposes `C_CVTRequest.*`). When a requirement says to create/attach
  an extension record, model it as a CHILD: create the extension type with
  `self.inst_man.add_new_record_of_type(ExtModel)` and link it with
  `parent.add_child(ext)` — do NOT try to set the `Ext.Field` columns on the
  parent. Example: `webhooks/TableToolbar/CreateCloneAndVectorRequest.py` creates
  a `C_CVTRequestModel` and adds it as a child of the `RequestModel`.
- Keep the `_author_` / class docstring style seen in existing scripts.

## References

- `references/api-reference.md` — full API surface: CallbackUtil (forms,
  selections, confirmations, files), FieldBuilder, RecordModelManager /
  DataRecordManager, SapioWebhookResult + directives, SapioWebhookContext
  attributes, endpoint types, exceptions.
- `references/examples.md` — worked end-to-end plugins, including the canonical
  "table toolbar → form → pick samples → create Request → navigate" example.
- `templates/handler_template.py` — starting skeleton for a new handler.
- Real in-repo examples: `webhooks/SelectionList/BillableAccount.py` (selection
  field), `kb/sapio-webhooks-tutorials/scripts/` (toolbar, launch, on-save
  patterns), `kb/sapio-webhooks-tutorials/7_webhook_server.py` (forms).
