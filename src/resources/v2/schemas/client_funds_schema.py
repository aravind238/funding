from marshmallow import fields, Schema, post_dump


class ClientFundSchema(Schema):
    """
    Client fund Schema
    """

    id = fields.Int(dump_only=True)
    client_id = fields.Number(required=False)
    ar_balance = fields.Number(required=False)
    funding_balance = fields.Number(required=False)
    reserve_balance = fields.Number(required=False)
    credit_commitee = fields.Number(required=False)
    purchage_sales_agreement = fields.Number(required=False)
    discount_fees_percentage = fields.Number(required=False)
    credit_insurance_total_percentage = fields.Number(required=False)
    reserves_withheld_percentage = fields.Number(required=False)
    current_limit = fields.Number(required=False)
    loan_limit = fields.Number(required=False)
    cash_reserves = fields.Number(required=False)
    escrow_reserves = fields.Number(required=False)
    total_reserves = fields.Number(required=False)
    adjusted_reserves = fields.Number(required=False)
    required_reserves = fields.Number(required=False)
    additional_reserves_required = fields.Number(required=False)
    ineligible_value = fields.Number(required=False)
    accrued_invoice_fees = fields.Number(required=False)
    available_for_release = fields.Number(required=False)
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
        