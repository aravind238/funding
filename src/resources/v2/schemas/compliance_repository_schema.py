from marshmallow import fields, Schema, post_dump
from marshmallow_enum import EnumField
from src.models import ComplianceRepositoryStatus


class ComplianceRepositorySchema(Schema):
    """
    ComplianceRepositorySchema
    """

    id = fields.Int(dump_only=True)
    client_id = fields.Int(required=True)
    document_type = fields.Str(required=False)
    period_end_date = fields.Date(required=False)
    frequency = fields.Str(required=False)
    status = EnumField(ComplianceRepositoryStatus, required=False)
    last_processed_at = fields.DateTime(required=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    request_type = fields.Method("get_request_type", dump_only=True)

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
    
    def get_request_type(self, compliance_repository):
        return "compliance_repository"

    class Meta:
        ordered = True

class ComplianceRepositoryRefSchema(ComplianceRepositorySchema):
    """
    ComplianceRepositoryRefSchema
    """
    cr_reference = fields.Method("get_cr_reference", dump_only=True)
    ref_client_no = fields.Method("get_ref_client_no", dump_only=True)
    client_name = fields.Method("get_client_name", dump_only=True)
    has_client_submitted = fields.Method(
        "get_has_client_submitted", dump_only=True
    )

    def get_cr_reference(self, compliance_repository):
        return compliance_repository.get_cr_reference()
    
    def get_ref_client_no(self, compliance_repository):
        ref_client_no = compliance_repository.client.ref_client_no if compliance_repository.client else None
        return ref_client_no

    def get_client_name(self, compliance_repository):
        return compliance_repository.get_client_name()
    
    def get_has_client_submitted(self, compliance_repository):
        has_client_submitted = False
        if compliance_repository.had_client_submitted():
            has_client_submitted = True
        return has_client_submitted

class ComplianceRepositoryDashboardSchema(ComplianceRepositoryRefSchema):
    """
    ComplianceRepositoryDashboardSchema
    """
    high_priority = fields.Method("get_high_priority", dump_only=True)
    payment_type = fields.Method("get_payment_type", dump_only=True)
    created_by = fields.Method("get_created_by", dump_only=True)
    
    # high_priority: dumpy variable for displaying in dashboard with soa/rr
    def get_high_priority(self, compliance_repository):
        return False
    
    # payment_type: dumpy variable for displaying in dashboard with soa/rr
    def get_payment_type(self, compliance_repository):
        return ""

    def get_created_by(self, compliance_repository):
        request_created_by_principal = compliance_repository.request_created_by_principal()
        request_created_by = (
            request_created_by_principal.user if request_created_by_principal else None
        )
        if not request_created_by:
            request_created_by_client = compliance_repository.request_created_by_client()
            request_created_by = (
                request_created_by_client.user if request_created_by_client else None
            )
        return request_created_by
        