"""
CreateCloneAndVectorRequest — Table toolbar button on the DNA Part data type.

On click (with one or more DNA Parts selected) it:
  1. Creates a new Request record.
  2. Creates a CVT Request (C_CVTRequest) record and attaches it to the Request
     as a CHILD. In Sapio C_CVTRequest is modelled as an *extension* of Request,
     but per requirements it is treated here as a child record (see the
     "Extensions treated as children" convention in the sapio-webhook-plugin
     skill).
  3. Loads the Sample children of the selected DNA Parts and attaches those
     samples to the Request as children.
  4. Attaches each selected DNA Part to the CVT Request as a child.
  5. Navigates the user to the newly created Request form.

Trigger: TABLETOOLBAR on the DNAPart data type — context.data_record_list holds
the selected DNA Part rows.
Register in server.py:  config.register('/create_clone_and_vector_request', CreateCloneAndVectorRequest)
Then, in the Sapio app, add a Table Toolbar button named "Create Clone and Vector
Request" on DNA Part whose webhook URL points at
  <server-url>/create_clone_and_vector_request.
"""
import time

from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.pojo.webhook.WebhookDirective import FormDirective
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopycommons.callbacks.field_builder import FieldBuilder, AnyFieldInfo
from sapiopycommons.general.exceptions import SapioUserErrorException

from webhooks.commons.data_type_models import DNAPartModel, RequestModel, SampleModel, C_CVTRequestModel

_author_ = "generated (sapio-webhook-plugin skill)"


class CreateCloneAndVectorRequest(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        cu = self.callback

        # 1. Resolve the selected DNA Part rows from the table toolbar context.
        selected_records = context.data_record_list
        if not selected_records:
            raise SapioUserErrorException("Select one or more DNA Parts before creating a request.")
        dna_parts = self.inst_man.add_existing_records_of_type(selected_records, DNAPartModel)

        # 2. Prompt a form for the new request's details.
        #    - Request Name: free-text the user enters.
        #    - Requested For: a selection populated from the system user list.
        #    - Request Type: prefilled as "CVT" and locked (not editable).
        fb = FieldBuilder(RequestModel.DATA_TYPE_NAME)
        form = cu.form_dialog("Create Clone and Vector Request", "Enter the request details:", [
            fb.string_field(RequestModel.REQUESTNAME__FIELD_NAME.field_name,
                            display_name="Request Name",
                            abstract_info=AnyFieldInfo(required=True)),
            fb.selection_list_field(RequestModel.C_REQUESTEDFOR__FIELD_NAME.field_name,
                                    display_name="Requested For", user_list=True,
                                    abstract_info=AnyFieldInfo(required=True)),
            fb.string_field(RequestModel.C_REQUESTTYPE__FIELD_NAME.field_name,
                            display_name="Request Type", default_value="CVT",
                            abstract_info=AnyFieldInfo(editable=False)),
        ])

        # 3. Load the Sample children of every selected DNA Part in one batched call,
        #    then flatten (de-duplicating by record id so a shared sample is added once).
        self.rel_man.load_children_of_type(dna_parts, SampleModel)
        samples: list[SampleModel] = []
        seen_sample_ids: set = set()
        for dna_part in dna_parts:
            for sample in dna_part.get_children_of_type(SampleModel):
                if sample.record_id not in seen_sample_ids:
                    seen_sample_ids.add(sample.record_id)
                    samples.append(sample)

        # 4. Create the Request, applying the values entered on the form.
        request = self.inst_man.add_new_record_of_type(RequestModel)
        request.set_field_value(RequestModel.REQUESTNAME__FIELD_NAME.field_name,
                                form[RequestModel.REQUESTNAME__FIELD_NAME.field_name])
        request.set_field_value(RequestModel.C_REQUESTEDFOR__FIELD_NAME.field_name,
                                form[RequestModel.C_REQUESTEDFOR__FIELD_NAME.field_name])
        # Request Type is fixed to CVT for this button.
        request.set_field_value(RequestModel.C_REQUESTTYPE__FIELD_NAME.field_name, "CVT")
        request.set_field_value(RequestModel.NUMBEROFSAMPLES__FIELD_NAME.field_name, len(samples))

        # 5. Create the CVT Request and attach it to the Request as a CHILD
        #    (extension-treated-as-child convention).
        cvt_request = self.inst_man.add_new_record_of_type(C_CVTRequestModel)
        cvt_request.set_field_value(C_CVTRequestModel.C_NOOFSAMPLES__FIELD_NAME.field_name, len(samples))
        request.add_child(cvt_request)

        # 6. Attach the DNA Parts' samples to the Request as children.
        for sample in samples:
            request.add_child(sample)

        # 7. Attach each selected DNA Part to the CVT Request as a child.
        for dna_part in dna_parts:
            cvt_request.add_parent(dna_part)

        # Persist the new Request, CVT Request, and all relationships in one
        # batched, transactional call.
        self.rec_man.store_and_commit()

        # 7. Navigate the user to the created Request form.
        cu.toaster_popup(
            f"Request created with a CVT Request, {len(dna_parts)} DNA Part(s) and {len(samples)} sample(s).",
            title="Clone and Vector Request Created")
        return SapioWebhookResult(True, directive=FormDirective(request.get_data_record()))
