"""
CreateRequest — Table toolbar button on the Request data type.

On click it:
  1. Prompts the user with a form to fill in the new request's details.
  2. Asks the user to choose Sample records from the system.
  3. Creates the Request record and attaches the chosen samples as children.
  4. Navigates the user to the newly created Request.

Trigger: TABLETOOLBAR on the Request data type.
Register in server.py:  config.register('/create_request', CreateRequest)
Then, in the Sapio app, add a Table Toolbar button on Request whose webhook URL
points at  <server-url>/create_request.
"""
import time

from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.pojo.webhook.WebhookDirective import FormDirective
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopycommons.callbacks.field_builder import FieldBuilder, AnyFieldInfo
from sapiopycommons.general.exceptions import SapioUserErrorException

from webhooks.commons.data_type_models import RequestModel, SampleModel

_author_ = "generated (sapio-webhook-plugin skill)"


class CreateRequest(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        cu = self.callback
        fb = FieldBuilder(RequestModel.DATA_TYPE_NAME)

        # 1. Collect the new request's details.
        #    Field keys mirror the real Request data fields so the values map back
        #    onto the record 1:1. All of these are STRING fields on Request.
        form = cu.form_dialog("New Request", "Enter the request details:", [
            fb.string_field(RequestModel.REQUESTNAME__FIELD_NAME.field_name,
                            display_name="Request Title",
                            abstract_info=AnyFieldInfo(required=True)),
            fb.string_field(RequestModel.REQUESTERNAME__FIELD_NAME.field_name,
                            display_name="Requester Name"),
            fb.string_field(RequestModel.REQUESTEREMAIL__FIELD_NAME.field_name,
                            display_name="Requester Email"),
            fb.string_field(RequestModel.REQUESTERORGANIZATION__FIELD_NAME.field_name,
                            display_name="Requester Organization"),
        ])

        # 2. Let the user choose Sample records from the system (search/scan/browse UI).
        samples = cu.input_selection_dialog(SampleModel, "Choose samples for this request:",
                                            multi_select=True)
        if not samples:
            # Friendly toaster + failed result; the record is never created.
            raise SapioUserErrorException("At least one sample must be selected.")

        # 3. Create the Request and attach the chosen samples as children.
        request = self.inst_man.add_new_record_of_type(RequestModel)
        request.set_field_value(RequestModel.REQUESTNAME__FIELD_NAME.field_name,
                                form[RequestModel.REQUESTNAME__FIELD_NAME.field_name])
        request.set_field_value(RequestModel.REQUESTERNAME__FIELD_NAME.field_name,
                                form.get(RequestModel.REQUESTERNAME__FIELD_NAME.field_name))
        request.set_field_value(RequestModel.REQUESTEREMAIL__FIELD_NAME.field_name,
                                form.get(RequestModel.REQUESTEREMAIL__FIELD_NAME.field_name))
        request.set_field_value(RequestModel.REQUESTERORGANIZATION__FIELD_NAME.field_name,
                                form.get(RequestModel.REQUESTERORGANIZATION__FIELD_NAME.field_name))
        # RequestDate is a DATE field (milliseconds since epoch).
        request.set_field_value(RequestModel.REQUESTDATE__FIELD_NAME.field_name,
                                int(time.time() * 1000))
        request.set_field_value(RequestModel.NUMBEROFSAMPLES__FIELD_NAME.field_name, len(samples))

        for sample in samples:
            request.add_child(sample)

        # Persist the new Request + relationships in one batched, transactional call.
        self.rec_man.store_and_commit()

        # 4. Navigate the user to the created Request.
        cu.toaster_popup(f"Request created with {len(samples)} sample(s).",
                         title="Request Created")
        return SapioWebhookResult(True, directive=FormDirective(request.get_data_record()))
