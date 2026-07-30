# Worked Examples

Realistic, end-to-end plugins. Adapt the data types / field names to the actual
generated models in `webhooks/commons/data_type_models.py` (grep first).

---

## Example 1 — The canonical request: table toolbar → form → pick samples → create Request → navigate

Requirement: *"Create a table toolbar in Request and, on click, prompt the user
with a request form to fill the details, ask them to choose samples, then navigate
to the created request."*

Endpoint type: `TABLETOOLBAR` on the Request data type. Register as
`/create_request`. The Sapio admin adds a Table Toolbar button on Request pointing
at `<server-url>/create_request`.

```python
"""
CreateRequest — table toolbar on Request: collect request details via a form,
let the user pick Sample records, create the Request with those samples as
children, and navigate the user to the new Request.

Register in server.py:  config.register('/create_request', CreateRequest)
"""
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.pojo.webhook.WebhookDirective import FormDirective
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopycommons.callbacks.field_builder import FieldBuilder, AnyFieldInfo
from sapiopycommons.general.exceptions import SapioUserErrorException

from webhooks.commons.data_type_models import RequestModel, SampleModel

_author_ = "generated"


class CreateRequest(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        cu = self.callback
        fb = FieldBuilder()

        # 1. Collect the request details.
        form = cu.form_dialog("New Request", "Enter the request details:", [
            fb.string_field("RequestName", abstract_info=AnyFieldInfo(required=True)),
            fb.selection_list_field("Priority", static_values=["Low", "Medium", "High"],
                                    default_value="Medium"),
            fb.string_field("Description", num_lines=3),
        ])

        # 2. Let the user choose Sample records from the system.
        #    input_selection_dialog opens the search/scan/browse UI for the data type.
        samples = cu.input_selection_dialog(SampleModel, "Choose samples for this request:",
                                            multi_select=True)
        if not samples:
            raise SapioUserErrorException("At least one sample must be selected.")

        # 3. Create the Request record and attach the chosen samples as children.
        request = self.inst_man.add_new_record_of_type(RequestModel)
        request.set_field_value(RequestModel.C_REQUESTNAME__FIELD_NAME.field_name,
                                form["RequestName"])
        # ^ Verify the real field constants by grepping data_type_models.py for RequestModel.
        for sample in samples:
            request.add_child(sample)
        self.rec_man.store_and_commit()

        # 4. Navigate the user to the newly created Request.
        return SapioWebhookResult(True, directive=FormDirective(request.get_data_record()))
```

Notes:
- Replace `C_REQUESTNAME__FIELD_NAME` etc. with the actual field constants found in
  `RequestModel`. If the field doesn't exist, ask the user or fall back to a raw
  string and flag it.
- `input_selection_dialog` returns typed models when given a model class; those
  models can be passed straight to `add_child`.
- Cancelling any dialog raises `SapioUserCancelledException`, handled by the base as
  a clean no-op — no need to check for `None`.

---

## Example 2 — Selection-list field (dynamic dropdown values)

Requirement: *"Populate the Billable Account dropdown on a Request from a search."*
Endpoint type: `SELECTIONDATAFIELD`. Uses bare `AbstractWebhookHandler` and returns
`list_values`. This is exactly `webhooks/SelectionList/BillableAccount.py` — read
that file for the full working pattern. Shape:

```python
class BillableAccount(AbstractWebhookHandler):
    def run(self, context: SapioWebhookContext) -> SapioWebhookResult:
        request = context.data_record
        values = [...]   # build from a CustomReport query
        return SapioWebhookResult(passed=True, list_values=values)
```

---

## Example 3 — Form toolbar button: edit the current record, confirm, save

Endpoint type: `FORMTOOLBAR` / `ACTIONMENU`; `context.data_record` is the record.

```python
class MarkComplete(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        record = context.data_record
        if not self.callback.yes_no_dialog("Confirm", "Mark this request complete?"):
            return SapioWebhookResult(True)   # user said no
        model = self.inst_man.add_existing_record_of_type(record, RequestModel)
        model.set_field_value(RequestModel.C_STATUS__FIELD_NAME.field_name, "Complete")
        self.rec_man.store_and_commit()
        self.callback.toaster_popup("Request marked complete.", popup_type=PopupType.Success)
        return SapioWebhookResult(True, refresh_data=True)
```

---

## Example 4 — On-save validation rule (block a bad save)

Endpoint type: on-save rule (`VELOX_RULE_ACTION`); `context.data_record_list` holds
the records being saved. Return `False` (or raise) to fail the save.

```python
class ValidateSample(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        for record in context.data_record_list:
            volume = record.get_field_value("Volume")
            if volume is not None and volume < 0:
                raise SapioUserErrorException("Volume cannot be negative.")
        return SapioWebhookResult(True)
```

---

## Example 5 — ELN experiment toolbar: act on entries, write a file, navigate

Endpoint type: `EXPERIMENTENTRYTOOLBAR` / `NOTEBOOKEXPERIMENTMAINTOOLBAR`;
`context.eln_experiment`, `context.experiment_entry`. See
`kb/sapio-webhooks-tutorials/scripts/experimentrules/ExperimentToolbar.py` (writes a
PDF back to the client via `callback.write_file`) and
`kb/sapio-webhooks-tutorials/scripts/experimentlaunch/ScreeningSheetLaunch.py`
(creates an experiment from a template and navigates with `ElnExperimentDirective`).

```python
return SapioWebhookResult(True, directive=ElnExperimentDirective(
    context.eln_experiment.notebook_experiment_id))
```
