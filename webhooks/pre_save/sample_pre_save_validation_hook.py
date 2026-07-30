# """
# LIMS-000: Sample pre-save validation webhook — reference example.
#
# Module:    Sample
# Type:      pre-save
# Trigger:   Before any Sample record is saved
# Author:    Claude Code (LIMS Consulting Analyst)
# Confluence: https://your-confluence.atlassian.net/wiki/spaces/LIMS/pages/example
# """
# from __future__ import annotations
#
# import re
# from typing import Any
#
# from sapio_saas_api.webhook import SapioWebhookHandler, WebhookContext
# from sapio_saas_api.exceptions import SapioWebhookException
#
# # Field name constants — prevents typos and aids refactoring
# FIELD_SAMPLE_ID = "SampleId"
# FIELD_BARCODE = "Barcode"
# FIELD_SAMPLE_TYPE = "SampleType"
# FIELD_CONTAINER_ID = "ContainerId"
# FIELD_VOLUME_ML = "VolumeMl"
#
# VALID_SAMPLE_TYPES = {"Blood", "Urine", "Tissue", "Plasma", "Serum", "Other"}
# BARCODE_PATTERN = re.compile(r"^[A-Z]{3}-\d{6}$")
#
#
# class SamplePreSaveValidationHook(SapioWebhookHandler):
#     """
#     Validates Sample records before they are persisted to Sapio.
#
#     Trigger: Pre-save on Sample data type
#
#     Inputs:
#         SampleId (String):    Unique lab identifier — required
#         Barcode (String):     Physical barcode label — required, format AAA-000000
#         SampleType (String):  Controlled vocabulary — required
#         ContainerId (Long):   Parent container record ID — required
#         VolumeMl (Double):    Volume in millilitres — optional, must be > 0 if present
#
#     Outputs:
#         No mutations — validation only. Raises SapioWebhookException to block
#         save on invalid data.
#
#     Business Rules:
#         1. SampleId must be present and non-empty
#         2. Barcode must match pattern AAA-000000
#         3. SampleType must be in the controlled vocabulary
#         4. ContainerId must reference an existing container
#         5. VolumeMl, if provided, must be a positive number
#
#     Raises:
#         SapioWebhookException: With a user-readable message describing the violation.
#     """
#
#     # ------------------------------------------------------------------ #
#     # Public entry point                                                   #
#     # ------------------------------------------------------------------ #
#
#     def run(self, context: WebhookContext) -> None:
#         """Execute pre-save validation.
#
#         Args:
#             context: Sapio webhook context providing record access and utilities.
#
#         Raises:
#             SapioWebhookException: If any validation rule is violated.
#         """
#         log = context.get_logger()
#         record = context.get_record()
#
#         log.info(
#             "Starting %s for record type=%s id=%s",
#             self.__class__.__name__,
#             record.get_record_type(),
#             record.get_record_id(),
#         )
#
#         try:
#             self._validate_required_fields(record)
#             self._validate_barcode_format(record)
#             self._validate_sample_type(record)
#             self._validate_volume(record)
#         except SapioWebhookException:
#             log.warning(
#                 "Validation failed for Sample record id=%s", record.get_record_id()
#             )
#             raise
#         except Exception as exc:
#             log.error("Unexpected error in %s: %s", self.__class__.__name__, exc)
#             raise SapioWebhookException(
#                 "An unexpected error occurred during sample validation. "
#                 "Please contact your LIMS administrator."
#             ) from exc
#
#         log.info("Sample validation passed for record id=%s", record.get_record_id())
#
#     # ------------------------------------------------------------------ #
#     # Private validators                                                   #
#     # ------------------------------------------------------------------ #
#
#     def _validate_required_fields(self, record: Any) -> None:
#         """Check all required fields are present and non-empty.
#
#         Args:
#             record: The Sapio Sample record.
#
#         Raises:
#             SapioWebhookException: If a required field is missing.
#         """
#         required = [FIELD_SAMPLE_ID, FIELD_BARCODE, FIELD_SAMPLE_TYPE, FIELD_CONTAINER_ID]
#         for field in required:
#             value = record.get_field_value(field)
#             if value is None or (isinstance(value, str) and not value.strip()):
#                 raise SapioWebhookException(
#                     f"'{field}' is required and cannot be empty."
#                 )
#
#     def _validate_barcode_format(self, record: Any) -> None:
#         """Validate barcode matches the lab format AAA-000000.
#
#         Args:
#             record: The Sapio Sample record.
#
#         Raises:
#             SapioWebhookException: If the barcode format is invalid.
#         """
#         barcode: str = record.get_field_value(FIELD_BARCODE)
#         if not BARCODE_PATTERN.match(barcode):
#             raise SapioWebhookException(
#                 f"Barcode '{barcode}' is invalid. "
#                 "Expected format: three uppercase letters, hyphen, six digits (e.g. BLD-001234)."
#             )
#
#     def _validate_sample_type(self, record: Any) -> None:
#         """Validate SampleType is in the controlled vocabulary.
#
#         Args:
#             record: The Sapio Sample record.
#
#         Raises:
#             SapioWebhookException: If the sample type is not recognised.
#         """
#         sample_type: str = record.get_field_value(FIELD_SAMPLE_TYPE)
#         if sample_type not in VALID_SAMPLE_TYPES:
#             valid_list = ", ".join(sorted(VALID_SAMPLE_TYPES))
#             raise SapioWebhookException(
#                 f"Sample type '{sample_type}' is not recognised. "
#                 f"Valid types are: {valid_list}."
#             )
#
#     def _validate_volume(self, record: Any) -> None:
#         """Validate VolumeMl is positive if provided.
#
#         Args:
#             record: The Sapio Sample record.
#
#         Raises:
#             SapioWebhookException: If VolumeMl is present but not a positive number.
#         """
#         volume = record.get_field_value(FIELD_VOLUME_ML)
#         if volume is None:
#             return  # optional field — not required
#         try:
#             volume_float = float(volume)
#         except (TypeError, ValueError):
#             raise SapioWebhookException(
#                 f"VolumeMl must be a number, got '{volume}'."
#             )
#         if volume_float <= 0:
#             raise SapioWebhookException(
#                 f"VolumeMl must be greater than zero, got {volume_float}."
#             )
