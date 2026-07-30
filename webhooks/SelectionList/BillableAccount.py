from sapiopycommons.customreport.auto_pagers import CustomReportDictAutoPager
from sapiopycommons.customreport.custom_report_builder import CustomReportBuilder
from sapiopycommons.customreport.term_builder import TermBuilder
from sapiopycommons.general.custom_report_util import CustomReportUtil
from sapiopylib.rest.WebhookService import AbstractWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.RecordModelManager import RecordModelManager

from webhooks.commons.data_type_models import RequestModel, C_DepartmentUserMappingModel, C_BillableAccountModel, C_ChargeProjectModel


class BillableAccount(AbstractWebhookHandler):
    def run(self, context: SapioWebhookContext) -> SapioWebhookResult:
        user = context.user
        rec_man = RecordModelManager(user)
        request = context.data_record
        requester = request.get_field_value(RequestModel.C_REQUESTEDFOR__FIELD_NAME.field_name)
        billable_account_list = []
        builder = CustomReportBuilder(C_BillableAccountModel)
        user_term = TermBuilder(C_DepartmentUserMappingModel).is_term(
        C_DepartmentUserMappingModel.C_USER__FIELD_NAME.field_name, requester)
        report = CustomReportUtil.get_system_report_criteria(user, "Billable Account search")
        root_term = report.root_term
        joins = report.join_list

        # Combine the requester term with the system report's root term.
        combined_term = TermBuilder.and_terms(user_term, root_term)
        builder.set_root_term(combined_term)
        # # Add the system report's joins to the builder so the combined term resolves.
        builder.join_list.extend(joins or [])
        builder.add_column(C_BillableAccountModel.C_PROJECTANDAWARD__FIELD_NAME)

        report_criteria = builder.build_report_criteria()

        for row in CustomReportDictAutoPager(user, report_criteria):
            value = row.get(C_BillableAccountModel.C_PROJECTANDAWARD__FIELD_NAME.field_name)
            if value and value not in billable_account_list:
                billable_account_list.append(value)
        return SapioWebhookResult(passed=True, list_values=billable_account_list)
