"""
PopulateCvtChargeUnitPrice — On-save rule handler for the Charge data type.

On every save of the Charge (C_Charge) record, this handler:
  1. Queries the single CVT Configuration (C_CVTConfiguration) record.
  2. Reads its Price Per Item (C_PricePerItem) value.
  3. Writes that value into Unit Price (C_UnitPrice) on the Charge record
     being saved.

The save is failed (rolled back) if the CVT Configuration table does not
contain exactly one record.

Trigger: on-save rule (VELOX_RULE_ACTION) on the Charge data type.
Register in server.py:  config.register('/populate_cvt_charge_unit_price',
                                        PopulateCvtChargeUnitPrice)
Then, in the Sapio app, create an on-save rule on Charge whose webhook URL
points at  <server-url>/populate_cvt_charge_unit_price.
"""
from sapiopycommons.general.exceptions import SapioUserErrorException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from webhooks.commons.data_type_models import C_ChargeModel, C_CVTConfigurationModel


class PopulateCvtChargeUnitPrice(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        incoming = context.data_record_list or []

        # Keep only Charge records; ignore anything else the platform included
        # in the on-save context.
        charge_records = [r for r in incoming if r.data_type_name == C_ChargeModel.DATA_TYPE_NAME]
        if not charge_records:
            return SapioWebhookResult(True)

        # Look up the singleton CVT Configuration record. Fail the save if the
        # table has zero or multiple rows — both source fields would otherwise
        # be ambiguous.
        configs = self.rec_handler.query_all_models(C_CVTConfigurationModel)
        if len(configs) != 1:
            raise SapioUserErrorException(
                f"Expected exactly 1 {C_CVTConfigurationModel.DISPLAY_NAME} record, "
                f"but found {len(configs)}. Cannot populate Charge."
            )

        config = configs[0]
        price_per_item = config.get_C_PricePerItem_field()
        charge_in_account = config.get_C_ChargeInAccount_field()

        charges = self.inst_man.add_existing_records_of_type(charge_records, C_ChargeModel)
        for charge in charges:
            charge.set_C_UnitPrice_field(price_per_item)
            charge.set_C_CreditChargeProjectAward_field(charge_in_account)

        self.rec_man.store_and_commit()
        print(f"[PopulateCvtChargeUnitPrice] commit complete, updated {len(charges)} Charge(s)")
        return SapioWebhookResult(True)