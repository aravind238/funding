from marshmallow import fields, Schema, post_dump
from marshmallow_enum import EnumField
from src.models import DisclaimersName, DisclaimersType


class DisclaimersSchema(Schema):
    id = fields.Str(dump_only=True)
    name = EnumField(DisclaimersName, required=True)
    text = fields.Str(required=True)
    disclaimer_type = EnumField(DisclaimersType, required=False, allow_none=True)
    is_deleted = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @post_dump(pass_many=True)
    def utc_to_est(self, data, many, **kwargs):
        from src.resources.v2.helpers.convert_datetime import utc_to_local
        
        if many and isinstance(data, list):
            for each_data in data:
                if each_data["name"] == "Canada":
                    each_data["name"] = "Canada other than Quebec"

                if "created_at" in each_data:
                    each_data["created_at"] = utc_to_local(dt=each_data["created_at"])
                if "updated_at" in each_data:
                    each_data["updated_at"] = utc_to_local(dt=each_data["updated_at"])
        else:
            if data["name"] == "Canada":
                data["name"] = "Canada other than Quebec"
                
            if "created_at" in data:
                data["created_at"] = utc_to_local(dt=data["created_at"])
            if "updated_at" in data:
                data["updated_at"] = utc_to_local(dt=data["updated_at"])
        return data

    class Meta:
        ordered = True
        


class DisclaimerOnlySchema(Schema):
    id = fields.Str(dump_only=True)
    name = EnumField(DisclaimersName, required=True)
    text = fields.Str(required=True)
    # disclaimer_type = EnumField(DisclaimersType, required=False, allow_none=True)

    @post_dump(pass_many=True)
    def display_name(self, data, many, **kwargs):
        
        if many and isinstance(data, list):
            for each_data in data:
                if each_data["name"] == "Canada":
                    each_data["name"] = "Canada other than Quebec"
        else:
            if data["name"] == "Canada":
                data["name"] = "Canada other than Quebec"
        return data

        
    class Meta:
        ordered = True
        
