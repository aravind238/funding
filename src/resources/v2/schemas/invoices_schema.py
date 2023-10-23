from marshmallow import fields, Schema, validates, ValidationError, validates_schema, post_dump
from marshmallow_enum import EnumField
from src.models import InvoiceStatus, InvoiceActions
from datetime import datetime, date
from decimal import Decimal


class InvoiceSchema(Schema):
    """
    Invoice Schema
    """

    id = fields.Int(dump_only=True)
    client_id = fields.Int(required=True)
    soa_id = fields.Int(required=True)
    debtor = fields.Int(required=True)
    invoice_number = fields.Str(required=True)
    invoice_date = fields.Date(required=True)
    amount = fields.Number(required=True)
    po_number = fields.Str(required=False, allow_none=True)
    notes = fields.Str(required=False, allow_none=True)
    added_by = fields.Str(required=False)
    verified_by = fields.Str(required=False)
    status = EnumField(InvoiceStatus, required=False, allow_none=True)
    terms = fields.Int(required=True)
    is_credit_insured = fields.Bool(required=False)
    actions = EnumField(InvoiceActions, required=False)
    is_release_from_reserve = fields.Bool(required=False, allow_none=True)
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

    # validation for amount
    @validates_schema
    def validate_amount(self, data):
        if "amount" in data:
            if isinstance(data["amount"], float) or isinstance(data["amount"], Decimal):
                # convert amount type to str
                invoice_amount = str(data["amount"])
                # split amount
                invoice_amount_before, invoice_amount_after = invoice_amount.split(".")

                if len(invoice_amount_before) > 8:
                    raise ValidationError(
                        "Amount must be less than $100 million(100,000,000).", "amount"
                    )
            else:
                raise ValidationError("Only numbers are allowed.", "amount")
        else:
            raise ValidationError("Amount is required.", "amount")

    # validation for invoice_date
    @validates("invoice_date")
    def validate_invoice_date(self, data):
        from src.resources.v2.helpers.convert_datetime import current_date
        today = current_date()
        if data > today:
            raise ValidationError(f"invoice_date cannot be greater than current date({today}).")

        
    class Meta:
        ordered = True
        

class InvoiceDebtorSchema(InvoiceSchema):
    debtor_name = fields.Method("get_debtor_name", dump_only=True)
    client_name = fields.Method("get_client_name", dump_only=True)
    soa_ref_id = fields.Method("get_soa_ref_id", dump_only=True)

    def get_debtor_name(self, invoice):
        debtor_name = invoice.debtors.name if invoice.debtors else None
        return debtor_name

    def get_client_name(self, invoice):
        client_name = invoice.client.name if invoice.client else None
        return client_name

    def get_soa_ref_id(self, invoice):
        soa_ref_id = invoice.soa.soa_ref_id if invoice.soa else None
        return soa_ref_id


class InvoiceClientDebtorSchema(InvoiceDebtorSchema):
    current_ar = fields.Number(dump_only=True)
    credit_limit = fields.Number(dump_only=True)
    invoice_days = fields.Date(dump_only=True)


class InvoiceAEReadOnlySchema(Schema):
    """
    Invoice AE Read Only Schema
    """

    id = fields.Int(dump_only=True)
    client_id = fields.Int(required=True)
    soa_id = fields.Int(required=True)
    debtor = fields.Int(required=True)
    invoice_number = fields.Str(required=True)
    invoice_date = fields.Date(required=True)
    amount = fields.Number(required=True)
    po_number = fields.Str(required=False, allow_none=True)
    notes = fields.Str(required=False, allow_none=True)
    status = EnumField(InvoiceStatus, required=False, allow_none=True)
    terms = fields.Int(required=True)
    is_credit_insured = fields.Bool(required=False)
    actions = EnumField(InvoiceActions, required=False)
    is_release_from_reserve = fields.Bool(required=False, allow_none=True)
    is_deleted = fields.Bool(dump_only=True)
