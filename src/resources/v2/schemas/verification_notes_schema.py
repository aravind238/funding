from marshmallow import fields, Schema, post_dump
from marshmallow_enum import EnumField
from src.models import VerificationNotesStatus


class VerificationNotesSchema(Schema):
    """
    VerificationNotes Schema
    """

    id = fields.Int(dump_only=True)
    client_id = fields.Int(required=True)
    debtor_id = fields.Int(required=True)
    invoice_id = fields.Int(required=True)
    soa_id = fields.Int(required=True)
    verification_type_or_method = fields.Str(required=False)
    contact = fields.Str(required=False)
    notes = fields.Str(required=False, allow_none=True)
    status = EnumField(VerificationNotesStatus, required=False, allow_none=True)
    last_processed_at = fields.DateTime(required=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


    @post_dump(pass_many=True)
    def utc_to_est(self, data, many, **kwargs):
        from src.resources.v2.helpers.convert_datetime import utc_to_local

        if many and isinstance(data, list):
            for each_data in data:
                if "last_processed_at" in each_data and each_data["last_processed_at"]:
                    each_data["last_processed_at"] = utc_to_local(
                        dt=each_data["last_processed_at"]
                    )
                if "created_at" in each_data and each_data["created_at"]:
                    each_data["created_at"] = utc_to_local(dt=each_data["created_at"])
                if "updated_at" in each_data and each_data["updated_at"]:
                    each_data["updated_at"] = utc_to_local(dt=each_data["updated_at"])
        else:
            if "last_processed_at" in data and data["last_processed_at"]:
                data["last_processed_at"] = utc_to_local(dt=data["last_processed_at"])
            if "created_at" in data and data["created_at"]:
                data["created_at"] = utc_to_local(dt=data["created_at"])
            if "updated_at" in data and data["updated_at"]:
                data["updated_at"] = utc_to_local(dt=data["updated_at"])
        return data

    class Meta:
        ordered = True

class VerificationNotesRefSchema(VerificationNotesSchema):
    """
    VerificationNotesRefSchema
    """
    invoice_number = fields.Method("get_invoice_number", dump_only=True)
    vn_reference = fields.Method("get_vn_reference", dump_only=True)
    debtor_name = fields.Method("get_debtor_name", dump_only=True)
    debtor_ref_key = fields.Method("get_debtor_ref_key", dump_only=True)
    has_client_submitted = fields.Method("get_has_client_submitted", dump_only=True)
    request_type = fields.Method("get_request_type", dump_only=True)

    def get_invoice_number(self, verification_notes):
        return verification_notes.get_invoice_number()

    def get_vn_reference(self, verification_notes):
        return verification_notes.get_vn_reference()

    def get_debtor_name(self, verification_notes):
        return verification_notes.get_debtor_name()
        
    def get_debtor_ref_key(self, verification_notes):
        return verification_notes.get_debtor_ref_key()

    def get_has_client_submitted(self, verification_notes):
        has_client_submitted = False
        if verification_notes.has_client_submitted():
            has_client_submitted = True
        return has_client_submitted
    
    def get_request_type(self, verification_notes):
        return "verification_notes"

class VerificationNotesDashboardSchema(VerificationNotesRefSchema):
    """
    VerificationNotesDashboardSchema
    """
    client_name = fields.Method("get_client_name", dump_only=True)
    high_priority = fields.Method("get_high_priority", dump_only=True)
    payment_type = fields.Method("get_payment_type", dump_only=True)
    created_by = fields.Method("get_created_by", dump_only=True)

    def get_client_name(self, verification_notes):
        return verification_notes.get_client_name()
    
    # high_priority: dumpy variable for displaying in dashboard with soa/rr
    def get_high_priority(self, verification_notes):
        return False
    
    # payment_type: dumpy variable for displaying in dashboard with soa/rr
    def get_payment_type(self, verification_notes):
        return ""

    def get_created_by(self, verification_notes):
        request_created_by_principal = verification_notes.request_created_by_principal()
        request_created_by = (
            request_created_by_principal.user if request_created_by_principal else None
        )
        if not request_created_by:
            request_created_by_client = verification_notes.request_created_by_client()
            request_created_by = (
                request_created_by_client.user if request_created_by_client else None
            )
        return request_created_by
