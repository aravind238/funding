from marshmallow import fields, Schema, post_dump


class ReasonsSchema(Schema):
    """
    Reasons Schema
    """

    id = fields.Int(dump_only=True)
    soa_id = fields.Int(required=False, allow_none=True)
    reserve_release_id = fields.Int(required=False, allow_none=True)
    payee_id = fields.Int(required=False, allow_none=True)
    debtor_limit_approvals_id = fields.Int(required=False, allow_none=True)
    generic_request_id = fields.Int(required=False, allow_none=True)
    compliance_repository_id = fields.Int(required=False, allow_none=True)
    lack_of_collateral = fields.Bool(required=False, allow_none=True)
    unacceptable_collateral = fields.Bool(required=False, allow_none=True)
    invoice_discrepancy = fields.Bool(required=False, allow_none=True)
    no_assignment_stamp = fields.Bool(required=False, allow_none=True)
    pre_billing = fields.Bool(required=False, allow_none=True)
    client_over_limit = fields.Bool(required=False, allow_none=True)
    confirmation_issue = fields.Bool(required=False, allow_none=True)
    others = fields.Bool(required=False, allow_none=True)
    notes = fields.Str(required=False, allow_none=True)
    status = fields.Str(required=False, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)
        
    @post_dump(pass_many=True)
    def utc_to_est(self, data, many, **kwargs):
        from src.resources.v2.helpers.convert_datetime import utc_to_local
        
        if many and isinstance(data, list):
            for each_data in data:
                if "created_at" in each_data:
                    each_data["created_at"] = utc_to_local(dt=each_data["created_at"])
                if "updated_at" in each_data:
                    each_data["updated_at"] = utc_to_local(dt=each_data["updated_at"])
        else:
            if "created_at" in data:
                data["created_at"] = utc_to_local(dt=data["created_at"])
            if "updated_at" in data:
                data["updated_at"] = utc_to_local(dt=data["updated_at"])
        return data
        
    class Meta:
        ordered = True
        