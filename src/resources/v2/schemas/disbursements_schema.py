from marshmallow import fields, Schema, post_dump
from marshmallow_enum import EnumField
from src.models import PaymentMethod, DisbursementRefType


class DisbursementsSchema(Schema):
    """
    Disbursements Schema
    """

    id = fields.Int(dump_only=True)
    client_id = fields.Int(required=True)
    soa_id = fields.Int(required=False, allow_none=True)
    payee_id = fields.Int(required=True)    
    ref_type = EnumField(DisbursementRefType, required=True)
    ref_id = fields.Int(required=True)
    payment_method = EnumField(PaymentMethod, required=False)
    client_fee = fields.Number(required=False, allow_none=True)
    amount = fields.Number(required=True)
    third_party_fee = fields.Number(required=False)
    tp_ticket_number = fields.Str(required=False, allow_none=True)
    is_reviewed = fields.Bool(required=False)
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
        