from sapiopycommons.callbacks.callback_util import FieldModifier
from sapiopycommons.general.exceptions import SapioUserErrorException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler

from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxPickListFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult

from webhooks.commons.data_type_models import DNAPartModel, RequestModel, SampleModel

# CVT: C_RequestType is fixed to this value for every Request this handler creates.
REQUEST_TYPE_CVT = "CVT"
REQUEST_TYPE_FIELD_NAME = "C_RequestType"

# Sample Type is fixed to this value for every Sample this handler creates.
SAMPLE_TYPE_CVT = "CVT"
SAMPLE_TYPE_FIELD_NAME = "ExemplarSampleType"

# These four Request fields aren't in the current data_type_models.py dump (confirmed stale/out
# of date with the tenant per user); field names are used as given.
REQUIRED_REQUEST_FIELDS = [
    "C_RequestedFor",
    "C_ScientificProjects",
    "C_BillableAccount",
    "C_Department",
]


class CreateSamplesAndRequestFromDnaParts(CommonsWebhookHandler):
    """
    DNA Part table toolbar button.

    For every selected DNA Part: creates a new Sample (Sample Type fixed to CVT)
    and links the DNA Part as that Sample's parent. Creates a single new Request
    (C_RequestType fixed to CVT), collects the remaining required Request fields
    from the user via a form dialog built from the Request's own fields, links
    every new Sample as a child of that Request, and navigates the user to the
    created Request.
    """

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        dna_part_records = context.data_record_list
        if not dna_part_records:
            raise SapioUserErrorException("Select at least one DNA Part record before running this action.")
        self.callback.display_info(f"Selected {len(dna_part_records)} DNA Part record(s).")

        dna_parts = self.rec_handler.wrap_models(dna_part_records, DNAPartModel)
        self.callback.display_info(f"Wrapped {len(dna_parts)} DNA Part model(s).")

        request = self.rec_handler.add_model(RequestModel)
        self._validate_picklist_value(RequestModel.DATA_TYPE_NAME, REQUEST_TYPE_FIELD_NAME, REQUEST_TYPE_CVT)
        request.set_C_RequestType_field(REQUEST_TYPE_CVT)
        self.callback.display_info("Created new Request model and set C_RequestType.")

        self.callback.set_record_form_dialog(
            "New Request",
            "Enter the required details for the new Request.",
            REQUIRED_REQUEST_FIELDS,
            request,
            default_modifier=FieldModifier(required=True, editable=True),
        )
        self.callback.display_info("Record form dialog completed.")
        self._validate_required_fields(request)
        self.callback.display_info("Required Request fields validated.")

        samples = self.rec_handler.add_models(SampleModel, len(dna_parts))
        self.callback.display_info(f"Created {len(samples)} Sample model(s).")
        self._validate_picklist_value(SampleModel.DATA_TYPE_NAME, SAMPLE_TYPE_FIELD_NAME, SAMPLE_TYPE_CVT)
        for dna_part, sample in zip(dna_parts, samples):
            sample.set_ExemplarSampleType_field(SAMPLE_TYPE_CVT)
            sample.add_parent(dna_part)
            sample.add_parent(request)
        self.callback.display_info("Set Sample Type and linked DNA Part and Request parents to each Sample.")

        self.rec_man.store_and_commit()
        self.callback.display_info(f"Stored and committed all records: Sample == {sample} Request == {request}")

        return SapioWebhookResult(True, directive=self.directive.record_form(request))

    def _validate_picklist_value(self, data_type_name: str, field_name: str, value: str) -> None:
        """
        Look up the tenant's actual picklist entries for a field and raise a clear error naming
        the valid options if `value` isn't one of them. data_type_models.py is confirmed stale
        against the tenant, so a "Failed to set field" error on a picklist field is otherwise
        opaque about what values are actually accepted.
        """
        field_defs = self.dt_man.get_field_definition_list(data_type_name) or []
        field_def = next((f for f in field_defs if f.data_field_name == field_name), None)
        if field_def is None:
            self.callback.display_warning(
                f"Could not find field '{field_name}' on data type '{data_type_name}' to validate against."
            )
            return
        if not isinstance(field_def, VeloxPickListFieldDefinition):
            return

        picklist = self.list_man.get_picklist(field_def.pick_list_name)
        entries = picklist.entry_list if picklist else None
        self.callback.display_info(
            f"Picklist '{field_def.pick_list_name}' for field '{field_name}' has entries: {entries}"
        )
        if entries is not None and value not in entries:
            raise SapioUserErrorException(
                f"'{value}' is not a valid value for field '{field_name}' "
                f"(picklist '{field_def.pick_list_name}'). Valid values are: {', '.join(entries)}"
            )

    def _validate_required_fields(self, request: RequestModel) -> None:
        missing = [name for name in REQUIRED_REQUEST_FIELDS if not request.get_field_value(name)]
        if missing:
            raise SapioUserErrorException(
                f"The following required Request fields were left blank: {', '.join(missing)}"
            )
