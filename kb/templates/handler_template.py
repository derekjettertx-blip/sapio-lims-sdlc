"""
<PluginName> — <one-line description of what this plugin does>.

Trigger: <TABLETOOLBAR | FORMTOOLBAR | ACTIONMENU | on-save rule | ...> on <DataType>.
Register in server.py as:  config.register('/<endpoint_path>', <PluginName>)
"""
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.pojo.webhook.WebhookDirective import FormDirective
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopycommons.callbacks.field_builder import FieldBuilder, AnyFieldInfo
from sapiopycommons.general.exceptions import SapioUserErrorException

# Typed models generated from the Sapio schema. Import only what you use.
# from webhooks.commons.data_type_models import RequestModel, SampleModel

_author_ = "<your name>"


class PluginName(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        # 1. Read the trigger context (pick the attribute for your endpoint type).
        records = context.data_record_list        # TABLETOOLBAR / on-save
        # record = context.data_record            # FORMTOOLBAR / ACTIONMENU
        if not records:
            raise SapioUserErrorException("No records were selected.")

        # 2. Collect user input via a dialog.
        fb = FieldBuilder()
        form = self.callback.form_dialog("Title", "Please fill in the details:", [
            fb.string_field("Name", abstract_info=AnyFieldInfo(required=True)),
            fb.selection_list_field("Type", static_values=["A", "B", "C"]),
        ])
        # form is None-safe: a cancel raises SapioUserCancelledException (handled by base).

        # 3. Create / edit records.
        # new_model = self.inst_man.add_new_record_of_type(RequestModel)
        # new_model.set_field_value(RequestModel.SOME__FIELD_NAME.field_name, form["Name"])
        # self.rec_man.store_and_commit()

        # 4. Return, optionally navigating the user somewhere.
        # return SapioWebhookResult(True, directive=FormDirective(new_model.get_data_record()))
        return SapioWebhookResult(True)
