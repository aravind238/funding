from marshmallow import fields, Schema, validates, ValidationError, validates_schema, post_dump, pre_load
from marshmallow_enum import EnumField
from marshmallow.validate import Length, Range
from src.models import PayeeStatus, ClientPayeeStatus


class PayeeSchema(Schema):
    """
    Payee Schema
    """

    id = fields.Int(dump_only=True)
    first_name = fields.Str(required=False, allow_none=True)
    last_name = fields.Str(required=False, allow_none=True)
    account_nickname = fields.Str(required=False, allow_none=True)
    status = EnumField(PayeeStatus, required=False, allow_none=True)
    address_line_1 = fields.Str(required=False, allow_none=True)
    # address_line_2 = fields.Str(required=False, allow_none=True)
    city = fields.Str(required=False, allow_none=True)
    state_or_province = fields.Str(required=False, allow_none=True)
    country = fields.Str(required=False, allow_none=True)
    postal_code = fields.Str(required=False, allow_none=True)
    phone = fields.Str(required=False, allow_none=True, validate=Length(min=10, max=12, error="must be between 10 to 12 digits"))
    alt_phone = fields.Str(required=False, allow_none=True, validate=Length(min=10, max=12, error="must be between 10 to 12 digits"))
    email = fields.Email(required=False, allow_none=True)
    notes = fields.Str(required=False, allow_none=True)
    is_new = fields.Bool(dump_only=True)
    is_active = fields.Bool(required=False, allow_none=True)
    last_processed_at = fields.DateTime(required=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)

    @post_dump(pass_many=True)
    def utc_to_est(self, data, many, **kwargs):
        from src.resources.v2.helpers.convert_datetime import utc_to_local
        
        if many and isinstance(data, list):
            for each_data in data:
                if "last_processed_at" in each_data and each_data["last_processed_at"]:
                    each_data["last_processed_at"] = utc_to_local(dt=each_data["last_processed_at"])
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

    @pre_load
    def validate_mandatory_fields(self, data, **kwargs):
        """[* mandatory fields]

        Arguments:
            data {[phone]}

        Raises:
            ValidationError: [Raising validation errors]
        """

        # checking, if phone is str and empty then convert to null
        if (
            "phone" in data
            and not data["phone"]
            and isinstance(data["phone"], str)
        ):
            data["phone"] = None
        return data

        
    class Meta:
        ordered = True
        


class PayeeClientSchema(PayeeSchema):
    """
    Payee with client Schema
    """
    client_id = fields.Str(dump_only=True)
    client_name = fields.Str(dump_only=True)
    ref_type = EnumField(ClientPayeeStatus, dump_only=True)
    payment_status = fields.Str(dump_only=True)

class PayeeDashboardSchema(PayeeSchema):
    """
    Payee Dashboard Schema
    """
    client_id = fields.Method("get_client_id", dump_only=True)
    request_type = fields.Method("get_request_type", dump_only=True)
    created_by = fields.Method("get_created_by", dump_only=True)
    
    def get_client_id(self, payee):
        return payee.client_payee[0].client_id if payee.client_payee else None

    def get_request_type(self, payee):
        return "payee"
    
    def get_created_by(self, payee):
        request_created_by_principal = payee.request_created_by_principal()
        request_created_by = (
            request_created_by_principal.user if request_created_by_principal else None
        )
        if not request_created_by:
            request_created_by_client = payee.request_created_by_client()
            request_created_by = (
                request_created_by_client.user if request_created_by_client else None
            )
        
        return request_created_by