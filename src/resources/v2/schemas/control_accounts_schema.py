from marshmallow import fields, Schema, post_dump

class ControlAccountSchema(Schema):
    """
    ControlAccount Schema
    """

    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    currency = fields.Str(required=True)
    country = fields.Str(required=True)
    lcra_export_id = fields.Int(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)
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
        