# Sapio Webhook API Reference

Condensed from `sapiopylib` (2026.6.x) and `sapiopycommons` (37.x) as installed in
this project. Signatures are accurate to those versions; grep the installed
packages if you need something not listed.

---

## Handler base classes

### `CommonsWebhookHandler` (preferred)
`from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler`

Override **`execute`**, not `run`. `run` is implemented by the base and wires up
managers on `self` before calling `execute`, then translates exceptions into
user-facing displays.

```python
class MyHandler(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        ...
        return SapioWebhookResult(True)
```

Available on `self` inside `execute`:
- `self.context`, `self.user`, `self.logger`
- Data managers: `self.dr_man` (DataRecordManager), `self.dt_man`, `self.eln_man`,
  `self.acc_man`, `self.report_man`, `self.messenger`
- Record models: `self.rec_man` (RecordModelManager), `self.inst_man` (instance),
  `self.rel_man` (relationship), `self.an_man` (ancestor)
- Helpers: `self.rec_handler`, `self.callback` (CallbackUtil), `self.directive`
  (DirectiveUtil), `self.exp_handler`
- Endpoint predicates: `self.is_main_toolbar()`, `self.is_table_toolbar()`,
  `self.is_eln_rule()`, `self.is_on_save_rule()`, `self.is_custom()`,
  `self.can_send_client_callback()`
- If `execute` returns `None`, the base raises `SapioException`.

### `AbstractWebhookHandler` (minimal)
`from sapiopylib.rest.WebhookService import AbstractWebhookHandler`

Override **`run`**. No managers wired up; any exception collapses to a generic
`SapioWebhookResult(False, "Error occurred...")`. Build managers yourself:
`RecordModelManager(context.user)`, `DataMgmtServer.get_client_callback(context.user)`.
Use for the simplest selection-list plugins (see `BillableAccount.py`).

---

## Server registration (`server.py`)

```python
from sapiopylib.rest.WebhookService import WebhookConfiguration, WebhookServerFactory
config = WebhookConfiguration(verify_sapio_cert=True, debug=True, client_timeout_seconds=1200)
config.register('/my_endpoint', MyHandler)          # POST-only route
app = WebhookServerFactory.configure_flask_app(app=None, config=config)
```
The Sapio-side button/rule must be configured (in the Sapio app, not code) to call
`<server-url>/my_endpoint`.

---

## SapioWebhookContext (what the platform sends you)

`from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext`

| Attribute | Type | When populated |
|---|---|---|
| `user` | `SapioUser` | always |
| `data_record` | `DataRecord \| None` | form/action toolbars; auto-filled if list has exactly 1 |
| `data_record_list` | `list[DataRecord] \| None` | table toolbar, on-save rule |
| `data_type_name` | `str \| None` | type in context |
| `data_field_name` / `data_field_name_list` | `str` / `list[str]` | field-scoped plugins |
| `eln_experiment` | `ElnExperiment \| None` | ELN contexts |
| `experiment_entry` / `experiment_entry_list` | entry / list | ELN entry contexts |
| `data_record_manager` | `DataRecordManager` | always |
| `eln_manager` | `ElnManager` | always |
| `field_map` / `field_map_list` | dict / list[dict] | selection-list & temp-type plugins |
| `selected_field_map_index_list` | `list[int]` | user's selected rows |
| `context_data` | `str` | extra data passed from client/other plugin |
| `end_point_type` | `WebhookEndpointType` | always — the trigger type |

Wrap raw `DataRecord`s into typed models:
`models = context.inst_man...` → use `inst_man.add_existing_records_of_type(context.data_record_list, RequestModel)`.

---

## Endpoint types (`WebhookEndpointType`)

`ACTIONMENU`, `FORMTOOLBAR`, `TABLETOOLBAR`, `TEMP_DATA_FORM_TOOLBAR`,
`TEMP_DATA_TABLE_TOOLBAR`, `VELOX_RULE_ACTION` (on-save), `VELOXELNRULEACTION`,
`NOTEBOOKEXPERIMENTMAINTOOLBAR`, `EXPERIMENTENTRYTOOLBAR`, `SELECTIONDATAFIELD`
(selection-list field), `ACTIONDATAFIELD`, `SCHEDULEDPLUGIN`,
`NOTEBOOKEXPERIMENTGRABBER`, `REPORTTOOLBAR`, `CUSTOM`.

---

## SapioWebhookResult (what you return)

`from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult`

```python
SapioWebhookResult(
    passed: bool,
    display_text: str | None = None,          # deprecated; prefer CallbackUtil messages
    list_values: list[str] | None = None,     # selection-list field return values
    directive: AbstractWebhookDirective | None = None,   # where to navigate next
    refresh_data: bool = False,
    refresh_notebook_experiment: bool = False,
    eln_entry_refresh_list: list[ExperimentEntry] | None = None,
    commit_message: str | None = None,
)
```
Common returns:
```python
return SapioWebhookResult(True)                                   # success, no nav
return SapioWebhookResult(True, directive=FormDirective(record))  # navigate to record
return SapioWebhookResult(True, list_values=values)               # selection field
return SapioWebhookResult(False, "why it failed")                 # failure (rolls back on-save)
```

---

## Directives (navigation)

`from sapiopylib.rest.pojo.webhook.WebhookDirective import (FormDirective, TableDirective,
CustomReportDirective, ElnExperimentDirective, ExperimentEntryDirective, HomePageDirective)`

| Directive | Constructor | Navigates to |
|---|---|---|
| `FormDirective` | `FormDirective(record: DataRecord, layout_name=None)` | one record's form |
| `TableDirective` | `TableDirective(records: list[DataRecord], layout_name=None)` | many records (table) |
| `ElnExperimentDirective` | `ElnExperimentDirective(eln_experiment_id: int)` | an ELN experiment |
| `ExperimentEntryDirective` | `ExperimentEntryDirective(exp_id: int, entry_id: int)` | an ELN entry |
| `CustomReportDirective` | `CustomReportDirective(report)` | a report search UI |
| `HomePageDirective` | `HomePageDirective()` | home page |

`FormDirective`/`TableDirective` need a `DataRecord`, not a record model — get it
from a model via `model.get_data_record()` (or `model.backing_record`).

`DirectiveUtil` (also `self.directive` in CommonsWebhookHandler) accepts flexible
record types:
```python
from sapiopycommons.general.directive_util import DirectiveUtil
DirectiveUtil.record_form(record)                 # -> FormDirective
DirectiveUtil.record_table(records)               # -> TableDirective
DirectiveUtil.record_adaptive(records)            # form if 1, table if many
DirectiveUtil.eln_experiment(context.eln_experiment)
DirectiveUtil.eln_entry(context.eln_experiment, context.experiment_entry)
```

---

## CallbackUtil — user dialogs

`from sapiopycommons.callbacks.callback_util import CallbackUtil, BlankResultHandling`
In CommonsWebhookHandler use `self.callback`; else `CallbackUtil(context)`.
Any dialog raises `SapioUserCancelledException` on cancel.

**Messages**
```python
cu.display_info(msg); cu.display_warning(msg); cu.display_error(msg)
cu.toaster_popup(message, title="", popup_type=PopupType.Info)   # Info/Success/Warning/Error
```

**Confirmations / options**
```python
cu.ok_cancel_dialog(title, msg, default_ok=True) -> bool
cu.yes_no_dialog(title, msg, default_yes=True) -> bool
cu.option_dialog(title, msg, options: list[str], default_option=0, user_can_cancel=False) -> str
```

**Pick from strings**
```python
cu.list_dialog(title, options: list[str], multi_select=False, preselected_values=None) -> list[str]
```

**Single-field input** (build field with FieldBuilder)
```python
cu.input_dialog(title, msg, field) -> FieldValue
```

**Multi-field form** (returns dict field_name -> value)
```python
cu.form_dialog(title, msg, fields: list[field], values: dict = None,
               column_positions: dict[str, tuple[int,int]] = None) -> dict
```

**Table (multi-row)** — `values` is a list of row dicts or an int (# of blank rows)
```python
cu.table_dialog(title, msg, fields, values) -> list[dict]
```

**Record selection** (choose from records you already have / from the system)
```python
cu.record_selection_dialog(msg, fields, records: list[SapioRecord], multi_select=True,
                           preselected_records=None) -> list[SapioRecord]
cu.input_selection_dialog(wrapper_type, msg, multi_select=True, allow_creation=False,
                          custom_search=None, record_whitelist=None) -> list[model]
```

**Record-backed form/table** (fields resolved from a real data type; can create records)
```python
cu.record_form_dialog(title, msg, fields, record) -> dict
cu.set_record_form_dialog(title, msg, fields, record) -> None      # writes back into record
cu.create_record_form_dialog(title, msg, fields, WrapperType) -> model  # new record from input
cu.record_table_dialog(title, msg, fields, records) -> list[dict]
```

**Files**
```python
name, data = cu.request_file(title, exts=["csv"])   # from client -> (name, bytes)
files = cu.request_files(title, exts=None)           # {name: bytes}
cu.write_file(file_name, file_data)                  # download to client
cu.write_zip_file(zip_name, {name: data})
```

**E-signature**
```python
cu.esign_dialog(title, msg, show_comment=True) -> ESigningResponsePojo  # .authenticated
```

---

## FieldBuilder — build dialog fields

`from sapiopycommons.callbacks.field_builder import FieldBuilder, AnyFieldInfo`

```python
fb = FieldBuilder()                          # or FieldBuilder("Sample")
fb.string_field(name, default_value=None, max_length=100, num_lines=1)
fb.boolean_field(name, default_value=False)
fb.int_field(name, default_value=None, min_value=..., max_value=...)
fb.double_field(name, default_value=None, precision=1)
fb.date_field(name, default_value=None)      # value = ms since epoch
fb.selection_list_field(name, static_values=["A","B"], multi_select=False, default_value=None)
fb.selection_list_field(name, pick_list_name="MyPickList")      # from configured pick list
fb.enum_field(name, options=[...])           # returns the selected index
```
Per-field appearance via `abstract_info=AnyFieldInfo(required=True, editable=True,
visible=True, description="...")`. The `name` is also the display name unless
`display_name=` is given. This `name` is the key in the returned dict.

---

## Records — create, edit, commit

### RecordModelManager (preferred — batched, transactional)
`from sapiopylib.rest.utils.recordmodel.RecordModelManager import RecordModelManager`

```python
inst = self.inst_man            # rec_man.instance_manager
sample = inst.add_new_record_of_type(SampleModel)            # typed
sample.set_field_value(SampleModel.SAMPLEID__FIELD_NAME.field_name, "S-001")
# or use generated setters: sample.set_SampleId_field("S-001")
child = inst.add_new_record_of_type(AliquotModel)
sample.add_child(child)                                       # queue relationship
self.rec_man.store_and_commit()                              # one batched call; assigns real IDs
```
Other instance methods: `add_new_record(dt_name)`,
`add_new_records_of_type(n, WrapperType)`, `add_existing_record(data_record)`,
`add_existing_records_of_type(records, WrapperType)`. Get the backing `DataRecord`
for a directive with `model.get_data_record()`. Discard with `self.rec_man.rollback()`.

### DataRecordManager (immediate, per-call requests)
`self.dr_man` / `context.data_record_manager`
```python
rec = dr.add_data_record("Sample")
rec.set_field_value("SampleId", "S-001"); dr.commit_data_records([rec])
dr.add_data_records_with_data("Sample", [{"SampleId": "S-1"}, {"SampleId": "S-2"}])
dr.create_children_fields_for_record(parent, "Aliquot", [{"Volume": 50}])
```
Prefer RecordModelManager when creating linked graphs (it batches).

---

## Typed data models

`from webhooks.commons.data_type_models import RequestModel, SampleModel, ...`

Each generated class exposes:
- `DATA_TYPE_NAME`, `DISPLAY_NAME`
- `FOO__FIELD_NAME` constants (`WrapperField`) — use `.field_name` for the raw name
- `get_Foo_field()` / `set_Foo_field(value)` typed accessors
- generic `get_field_value(name)` / `set_field_value(name, value)`

The file is ~2.9 MB — grep it, never read whole:
`grep -n "class RequestModel" webhooks/commons/data_type_models.py`, then read that
class block for field constants.

---

## Exceptions

`from sapiopycommons.general.exceptions import (SapioUserErrorException,
SapioCriticalErrorException, SapioException, MessageDisplayType)`

- `SapioUserErrorException("msg")` → friendly toaster warning + failed result. Use
  for validation / expected errors.
- `SapioCriticalErrorException("msg", display_type=MessageDisplayType.OK_DIALOG,
  title="...")` → modal error dialog.
- `SapioException(...)` or any other exception → generic "unexpected error" shown to
  user, full traceback logged. Use only for bugs.
- `SapioUserCancelledException` → raised by cancelled dialogs; handled as clean
  cancel (rolls back on-save transactions). Don't swallow it.
Only `CommonsWebhookHandler` renders these to the user.
