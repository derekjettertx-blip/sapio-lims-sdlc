from sapiopylib.rest.DataMgmtService import DataMgmtServer
from sapiopylib.rest.WebhookService import AbstractWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult

from webhooks.commons.data_type_models import RequestModel, C_DepartmentUserMappingModel, C_BillableAccountModel, C_ChargeProjectModel


class BillableAccountCopy(AbstractWebhookHandler):
    def run(self, context: SapioWebhookContext) -> SapioWebhookResult:
        user = context.user
        dr_man = DataMgmtServer.get_data_record_manager(user)
        request = context.data_record
        requester = request.get_field_value(RequestModel.C_REQUESTEDFOR__FIELD_NAME.field_name)
        billable_account_list = []

        # 1. Get the department(s) from Department User Mapping by matching requester with the user.
        mappings = dr_man.query_data_records(
            C_DepartmentUserMappingModel.DATA_TYPE_NAME,
            C_DepartmentUserMappingModel.C_USER__FIELD_NAME.field_name,
            [requester]).result_list
        departments = list({
            dept for m in mappings
            if (dept := m.get_field_value(C_DepartmentUserMappingModel.C_SLDEPARTMENT__FIELD_NAME.field_name))
        })

        # 2. Get the charge projects linked to those department(s).
        charge_projects = dr_man.query_data_records(
            C_ChargeProjectModel.DATA_TYPE_NAME,
            C_ChargeProjectModel.C_SLDEPARTMENT__FIELD_NAME.field_name,
            departments).result_list
        charge_project_ids = [cp.record_id for cp in charge_projects]


        # 3. Get the billable accounts linked to those charge projects.
        billable_accounts = dr_man.query_data_records(
            C_BillableAccountModel.DATA_TYPE_NAME,
            C_BillableAccountModel.C_SLCHARGEPROJECT__FIELD_NAME.field_name,
            charge_project_ids).result_list

        # 4. Keep only active accounts and collect the Project/Award value.
        for account in billable_accounts:
            if not account.get_field_value(C_BillableAccountModel.C_ISACTIVE__FIELD_NAME.field_name):
                continue
            value = account.get_field_value(C_BillableAccountModel.C_PROJECTANDAWARD__FIELD_NAME.field_name)
            if value and value not in billable_account_list:
                billable_account_list.append(value)

        return SapioWebhookResult(passed=True, list_values=billable_account_list)
