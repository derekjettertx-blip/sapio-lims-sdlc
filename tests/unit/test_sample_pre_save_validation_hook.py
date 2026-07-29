"""
Unit tests for SamplePreSaveValidationHook — reference example.

Ticket:    LIMS-000
Coverage:  happy path, required fields, barcode format, sample type,
           volume validation, unexpected error handling
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from sapio_saas_api.exceptions import SapioWebhookException
except ImportError:
    # Fallback for environments without the Sapio SDK installed
    class SapioWebhookException(Exception):  # type: ignore[no-redef]
        pass

from webhooks.pre_save.sample_pre_save_validation_hook import (
    SamplePreSaveValidationHook,
    FIELD_SAMPLE_ID,
    FIELD_BARCODE,
    FIELD_SAMPLE_TYPE,
    FIELD_CONTAINER_ID,
    FIELD_VOLUME_ML,
)


# ====================================================================== #
# Shared fixtures                                                         #
# ====================================================================== #

VALID_FIELDS: dict[str, object] = {
    FIELD_SAMPLE_ID: "S-2024-001",
    FIELD_BARCODE: "BLD-001234",
    FIELD_SAMPLE_TYPE: "Blood",
    FIELD_CONTAINER_ID: 9001,
    FIELD_VOLUME_ML: 5.0,
}


@pytest.fixture
def context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_logger.return_value = MagicMock()
    return ctx


@pytest.fixture
def valid_record() -> MagicMock:
    rec = MagicMock()
    rec.get_record_type.return_value = "Sample"
    rec.get_record_id.return_value = 1001
    rec.get_field_value.side_effect = lambda f: VALID_FIELDS.get(f)
    return rec


# ====================================================================== #
# Happy path                                                              #
# ====================================================================== #

class TestHappyPath:
    def test_valid_sample_passes_without_exception(self, context, valid_record):
        context.get_record.return_value = valid_record
        SamplePreSaveValidationHook().run(context)  # must not raise

    def test_volume_none_is_allowed(self, context, valid_record):
        """VolumeMl is optional — None must not raise."""
        fields = {**VALID_FIELDS, FIELD_VOLUME_ML: None}
        valid_record.get_field_value.side_effect = lambda f: fields.get(f)
        context.get_record.return_value = valid_record
        SamplePreSaveValidationHook().run(context)


# ====================================================================== #
# Required fields                                                         #
# ====================================================================== #

class TestRequiredFields:
    @pytest.mark.parametrize("missing_field", [
        FIELD_SAMPLE_ID, FIELD_BARCODE, FIELD_SAMPLE_TYPE, FIELD_CONTAINER_ID
    ])
    def test_missing_required_field_raises(self, context, missing_field):
        fields = {k: v for k, v in VALID_FIELDS.items() if k != missing_field}
        rec = MagicMock()
        rec.get_record_type.return_value = "Sample"
        rec.get_record_id.return_value = 1002
        rec.get_field_value.side_effect = lambda f: fields.get(f)
        context.get_record.return_value = rec

        with pytest.raises(SapioWebhookException, match=missing_field):
            SamplePreSaveValidationHook().run(context)

    def test_empty_string_sample_id_raises(self, context, valid_record):
        fields = {**VALID_FIELDS, FIELD_SAMPLE_ID: "   "}
        valid_record.get_field_value.side_effect = lambda f: fields.get(f)
        context.get_record.return_value = valid_record

        with pytest.raises(SapioWebhookException, match=FIELD_SAMPLE_ID):
            SamplePreSaveValidationHook().run(context)


# ====================================================================== #
# Barcode format                                                          #
# ====================================================================== #

class TestBarcodeFormat:
    @pytest.mark.parametrize("bad_barcode", [
        "bld-001234",   # lowercase
        "BLD001234",    # missing hyphen
        "BL-001234",    # only 2 letters
        "BLD-12345",    # only 5 digits
        "BLD-1234567",  # 7 digits
        "",
        "INVALID",
    ])
    def test_invalid_barcode_raises(self, context, valid_record, bad_barcode):
        fields = {**VALID_FIELDS, FIELD_BARCODE: bad_barcode}
        valid_record.get_field_value.side_effect = lambda f: fields.get(f)
        context.get_record.return_value = valid_record

        with pytest.raises(SapioWebhookException, match="arcode"):
            SamplePreSaveValidationHook().run(context)

    @pytest.mark.parametrize("good_barcode", [
        "BLD-001234", "URI-999999", "TIS-000001", "AAA-123456"
    ])
    def test_valid_barcode_passes(self, context, valid_record, good_barcode):
        fields = {**VALID_FIELDS, FIELD_BARCODE: good_barcode}
        valid_record.get_field_value.side_effect = lambda f: fields.get(f)
        context.get_record.return_value = valid_record
        SamplePreSaveValidationHook().run(context)  # must not raise


# ====================================================================== #
# Sample type vocabulary                                                  #
# ====================================================================== #

class TestSampleType:
    @pytest.mark.parametrize("bad_type", ["blood", "WHOLE_BLOOD", "Sputum", "", "Unknown"])
    def test_invalid_sample_type_raises(self, context, valid_record, bad_type):
        fields = {**VALID_FIELDS, FIELD_SAMPLE_TYPE: bad_type}
        valid_record.get_field_value.side_effect = lambda f: fields.get(f)
        context.get_record.return_value = valid_record

        with pytest.raises(SapioWebhookException, match="not recognised"):
            SamplePreSaveValidationHook().run(context)

    @pytest.mark.parametrize("valid_type", ["Blood", "Urine", "Tissue", "Plasma", "Serum", "Other"])
    def test_all_valid_types_pass(self, context, valid_record, valid_type):
        fields = {**VALID_FIELDS, FIELD_SAMPLE_TYPE: valid_type}
        valid_record.get_field_value.side_effect = lambda f: fields.get(f)
        context.get_record.return_value = valid_record
        SamplePreSaveValidationHook().run(context)


# ====================================================================== #
# Volume validation                                                       #
# ====================================================================== #

class TestVolumeValidation:
    @pytest.mark.parametrize("bad_volume", [0, -1.5, -0.001])
    def test_non_positive_volume_raises(self, context, valid_record, bad_volume):
        fields = {**VALID_FIELDS, FIELD_VOLUME_ML: bad_volume}
        valid_record.get_field_value.side_effect = lambda f: fields.get(f)
        context.get_record.return_value = valid_record

        with pytest.raises(SapioWebhookException, match="greater than zero"):
            SamplePreSaveValidationHook().run(context)

    def test_non_numeric_volume_raises(self, context, valid_record):
        fields = {**VALID_FIELDS, FIELD_VOLUME_ML: "lots"}
        valid_record.get_field_value.side_effect = lambda f: fields.get(f)
        context.get_record.return_value = valid_record

        with pytest.raises(SapioWebhookException, match="number"):
            SamplePreSaveValidationHook().run(context)


# ====================================================================== #
# Error handling                                                          #
# ====================================================================== #

class TestErrorHandling:
    def test_unexpected_error_is_wrapped_in_webhook_exception(self, context, valid_record):
        valid_record.get_field_value.side_effect = RuntimeError("SDK crash")
        context.get_record.return_value = valid_record

        with pytest.raises(SapioWebhookException, match="unexpected error"):
            SamplePreSaveValidationHook().run(context)

    def test_sapio_exception_propagates_unchanged(self, context, valid_record):
        """SapioWebhookException from a validator must not be double-wrapped."""
        fields = {**VALID_FIELDS, FIELD_SAMPLE_ID: None}
        valid_record.get_field_value.side_effect = lambda f: fields.get(f)
        context.get_record.return_value = valid_record

        with pytest.raises(SapioWebhookException, match=FIELD_SAMPLE_ID):
            SamplePreSaveValidationHook().run(context)
