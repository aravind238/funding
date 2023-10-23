from marshmallow import fields, Schema, post_dump
from marshmallow_enum import EnumField
from src.models import GenericRequestCategoryStatus, GenericRequestStatus


class GenericRequestSchema(Schema):
    """
    GenericRequestSchema
    """

    id = fields.Int(dump_only=True)
    client_id = fields.Int(required=True)
    category = EnumField(GenericRequestCategoryStatus, required=False, allow_none=True)
    status = EnumField(GenericRequestStatus, required=False, allow_none=True)
    notes = fields.Str(required=False, allow_none=True)
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
    
    def get_request_type(self, generic_request):
        return "generic_request"

    class Meta:
        ordered = True

class GenericRequestRefSchema(GenericRequestSchema):
    """
    GenericRequestRefSchema
    """
    gn_reference = fields.Method("get_gn_reference", dump_only=True)
    ref_client_no = fields.Method("get_ref_client_no", dump_only=True)

    def get_gn_reference(self, generic_request):
        return generic_request.get_gn_reference()
    
    def get_ref_client_no(self, generic_request):
        ref_client_no = generic_request.client.ref_client_no if generic_request.client else None
        return ref_client_no

class GenericRequestDashboardSchema(GenericRequestRefSchema):
    """
    GenericRequestDashboardSchema
    """
    client_name = fields.Method("get_client_name", dump_only=True)
    high_priority = fields.Method("get_high_priority", dump_only=True)
    payment_type = fields.Method("get_payment_type", dump_only=True)
    created_by = fields.Method("get_created_by", dump_only=True)

    def get_client_name(self, generic_request):
        return generic_request.get_client_name()
    
    # high_priority: dumpy variable for displaying in dashboard with soa/rr
    def get_high_priority(self, generic_request):
        return False
    
    # payment_type: dumpy variable for displaying in dashboard with soa/rr
    def get_payment_type(self, generic_request):
        return ""

    def get_created_by(self, generic_request):
        request_created_by_principal = generic_request.request_created_by_principal()
        request_created_by = (
            request_created_by_principal.user if request_created_by_principal else None
        )
        return request_created_by
