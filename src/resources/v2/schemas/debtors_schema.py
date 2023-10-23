from marshmallow import fields, Schema, post_dump
from marshmallow_enum import EnumField
from marshmallow.validate import Length, Range
from src.models import DebtorSource


class DebtorSchema(Schema):
    """
    Debtor Schema
    """

    id = fields.Int(dump_only=True)
    source = EnumField(DebtorSource, required=False, allow_none=True)
    name = fields.Str(required=True)
    ref_key = fields.Str(required=False)
    ref_debtor_no = fields.Str(required=False, allow_none=True)
    uuid = fields.Str(required=False)
    address_1 = fields.Str(required=False, allow_none=True)
    address_2 = fields.Str(required=False, allow_none=True)
    state = fields.Str(required=False, allow_none=True)
    city = fields.Str(required=False, allow_none=True)
    postal_code = fields.Str(required=False, allow_none=True)
    country = fields.Str(required=False, allow_none=True)
    phone = fields.Str(required=False, allow_none=True)
    email = fields.Email(required=False, allow_none=True)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)
    is_new = fields.Method(
        "is_debtor_new", dump_only=True
    )
    address = fields.Method(
        "get_address", dump_only=True
    )
    
    def is_debtor_new(self, debtor):
        is_new = False
        if debtor.source and debtor.source.value == "funding":
            is_new = True
        return is_new
        
    def get_address(self, debtor):
        address_concat = ""
        if debtor.address_1:
            address_concat = debtor.address_1
        if debtor.address_2:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.address_2
        if debtor.city:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.city
        if debtor.state:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.state
        if debtor.country:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.country
        if debtor.postal_code:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.postal_code
        return address_concat
        
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
        

class DebtorClientSchema(DebtorSchema):
    """
    Debtor Client Schema
    """

    client_name = fields.Str(required=True)
    credit_limit = fields.Number(required=True)
    current_ar = fields.Number(required=True)
    default_term_value = fields.Int(required=False, allow_none=True)
    days_1_30 = fields.Str(required=False, allow_none=True)
    days_31_60 = fields.Str(required=False, allow_none=True)
    days_61_90 = fields.Str(required=False, allow_none=True)
    days_91_120 = fields.Str(required=False, allow_none=True)


class DebtorLimitsSchema(DebtorClientSchema):
    """
    Debtor Client Schema
    """

    client_id = fields.Int(required=True)


class DuplicateDebtorsSchema(Schema):
    """
    Duplicate Debtors Schema
    """
    id = fields.Int(dump_only=True)
    source = EnumField(DebtorSource, required=False, allow_none=True)
    name = fields.Str(required=True)
    ref_key = fields.Int(required=False)
    ref_debtor_no = fields.Str(required=False, allow_none=True)
    address = fields.Method(
        "get_address", dump_only=True
    )
    client_name = fields.Str(dump_only=True)
    
    def get_address(self, debtor):
        address_concat = ""
        if debtor.address_1:
            address_concat = debtor.address_1
        if debtor.address_2:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.address_2
        if debtor.city:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.city
        if debtor.state:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.state
        if debtor.country:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.country
        if debtor.postal_code:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.postal_code
        return address_concat
                
    class Meta:
        ordered = True
