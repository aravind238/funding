from marshmallow import fields, Schema, post_dump
from marshmallow_enum import EnumField
from src.models import ClientSource

class ClientSchema(Schema):
    """
    Client Schema
    """

    id = fields.Int(dump_only=True)
    uuid = fields.Str(required=False)
    source = EnumField(ClientSource, required=True)
    name = fields.Str(required=True)
    ref_key = fields.Int(required=True)
    ref_client_no = fields.Str(required=False)
    ref_account_exec = fields.Str(required=False)
    lcra_client_accounts_id = fields.Str(required=False)
    lcra_client_accounts_number = fields.Str(required=False)
    lcra_control_account_organizations_id = fields.Str(required=False)
    is_active = fields.Bool(dump_only=True)
    default_disclaimer_id = fields.Str(required=False)
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
        
        
class ClientInfoSchema(ClientSchema):
    """
    Client Info Schema
    """
    control_account_name = fields.Method("get_control_account", dump_only=True)
    client_settings_id = fields.Method("get_client_settings_id", dump_only=True)

    def get_control_account(self, client):
        control_account_name = None
        clients_control_account = client.clients_control_account if client.clients_control_account else None
        if clients_control_account:
            control_account_name = clients_control_account[0].control_account.name
            
        return control_account_name

    def get_client_settings_id(self, client):
        client_settings_id = None
        client_settings = client.client_settings if client.client_settings else None
        if client_settings:
            client_settings_id = client_settings[0].id
            
        return client_settings_id

