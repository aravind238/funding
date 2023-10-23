from marshmallow import fields, Schema, post_dump
from marshmallow_enum import EnumField


class InvoiceSupportingDocumentsSchema(Schema):
    """
    InvoiceSupportingDocuments Schema
    """

    id = fields.Int(dump_only=True)
    client_id = fields.Int(required=True)
    debtor_id = fields.Int(required=True)
    invoice_id = fields.Int(required=True)
    soa_id = fields.Int(required=True)
    url = fields.Str(required=False)
    notes = fields.Str(required=False, allow_none=True)
    name = fields.Str(required=False)
    user = fields.Str(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


    @post_dump(pass_many=True)
    def utc_to_est(self, data, many, **kwargs):
        from src.resources.v2.helpers.convert_datetime import utc_to_local

        if many and isinstance(data, list):
            for each_data in data:
                if "created_at" in each_data and each_data["created_at"]:
                    each_data["created_at"] = utc_to_local(dt=each_data["created_at"])
                if "updated_at" in each_data and each_data["updated_at"]:
                    each_data["updated_at"] = utc_to_local(dt=each_data["updated_at"])
        else:
            if "created_at" in data and data["created_at"]:
                data["created_at"] = utc_to_local(dt=data["created_at"])
            if "updated_at" in data and data["updated_at"]:
                data["updated_at"] = utc_to_local(dt=data["updated_at"])
        return data

    class Meta:
        ordered = True

class InvoiceSupportingDocumentsRefSchema(InvoiceSupportingDocumentsSchema):
    """
    InvoiceSupportingDocumentsRefSchema
    """
    invoice_number = fields.Method("get_invoice_number", dump_only=True)
    debtor_name = fields.Method("get_debtor_name", dump_only=True)
    client_name = fields.Method("get_client_name", dump_only=True)
    debtor_ref_key = fields.Method("get_debtor_ref_key", dump_only=True)
    request_type = fields.Method("get_request_type", dump_only=True)

    def get_invoice_number(self, invoice_supporting_documents):
        return invoice_supporting_documents.get_invoice_number()

    def get_debtor_name(self, invoice_supporting_documents):
        return invoice_supporting_documents.get_debtor_name()

    def get_client_name(self, invoice_supporting_documents):
        return invoice_supporting_documents.get_client_name()
        
    def get_debtor_ref_key(self, invoice_supporting_documents):
        return invoice_supporting_documents.get_debtor_ref_key()
    
    def get_request_type(self, invoice_supporting_documents):
        return "invoice_supporting_documents"
