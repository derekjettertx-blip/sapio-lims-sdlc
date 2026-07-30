from sapiopycommons.customreport.auto_pagers import CustomReportDictAutoPager
from sapiopycommons.customreport.custom_report_builder import CustomReportBuilder
from sapiopycommons.customreport.term_builder import TermBuilder
from sapiopylib.rest.User import SapioUser
from sapiopylib.rest.WebhookService import AbstractWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult

from webhooks.commons.data_type_models import (
    C_DepartmentUserMappingModel,
    C_UserSupervisorMappingModel,
)


class RequestedForUser(AbstractWebhookHandler):
    """
    Selection list plugin for the "Requested For" field on a Request.

    Returns the set of usernames the current user is allowed to request on behalf
    of, based on their role in the mapping tables:
      * Supervisor      -> their own name + every user they supervise
                           (rows in C_UserSupervisorMapping where C_Supervisor == me).
      * Department head -> their own name + every member of the department(s) they
                           head (C_DepartmentUserMapping rows for me flagged
                           C_IsDepartmentHead, then all users in those departments).
      * Everyone else   -> only their own name.

    A user can be both a supervisor and a department head; in that case the two
    sets are unioned.
    """

    def run(self, context: SapioWebhookContext) -> SapioWebhookResult:
        user: SapioUser = context.user
        current_user: str = user.username

        # Always allow selecting yourself.
        names: set[str] = set()
        if current_user:
            names.add(current_user)

        # --- Supervisor: add everyone this user supervises ---------------------
        supervisee_term = TermBuilder(C_UserSupervisorMappingModel).is_term(
            C_UserSupervisorMappingModel.C_SUPERVISOR__FIELD_NAME.field_name, current_user)
        names.update(self._collect_column(
            context, C_UserSupervisorMappingModel,
            C_UserSupervisorMappingModel.C_USER__FIELD_NAME, supervisee_term))

        # --- Department head: add every member of departments this user heads --
        head_term = TermBuilder.and_terms(
            TermBuilder(C_DepartmentUserMappingModel).is_term(
                C_DepartmentUserMappingModel.C_USER__FIELD_NAME.field_name, current_user),
            TermBuilder(C_DepartmentUserMappingModel).is_term(
                C_DepartmentUserMappingModel.C_ISDEPARTMENTHEAD__FIELD_NAME.field_name, True))
        headed_departments = self._collect_column(
            context, C_DepartmentUserMappingModel,
            C_DepartmentUserMappingModel.C_DEPARTMENT__FIELD_NAME, head_term)

        for department in headed_departments:
            member_term = TermBuilder(C_DepartmentUserMappingModel).is_term(
                C_DepartmentUserMappingModel.C_DEPARTMENT__FIELD_NAME.field_name, department)
            names.update(self._collect_column(
                context, C_DepartmentUserMappingModel,
                C_DepartmentUserMappingModel.C_USER__FIELD_NAME, member_term))

        return SapioWebhookResult(passed=True, list_values=sorted(names))

    @staticmethod
    def _collect_column(context: SapioWebhookContext, model, column, root_term) -> set[str]:
        """
        Run a custom report against `model` filtered by `root_term` and return the
        distinct non-empty string values of `column`.
        """
        builder = CustomReportBuilder(model)
        builder.set_root_term(root_term)
        builder.add_column(column)
        report_criteria = builder.build_report_criteria()

        values: set[str] = set()
        for row in CustomReportDictAutoPager(context.user, report_criteria):
            value = row.get(column.field_name)
            if value:
                values.add(value)
        return values
