from marshmallow import fields, Schema, post_dump
from marshmallow_enum import EnumField
from src.models import ReserveReleaseStatus
from src.middleware.permissions import Permissions


# ReserveRelease Schema
class ReserveReleaseSchema(Schema):
    id = fields.Int(dump_only=True)
    client_id = fields.Int(required=True)
    ref_id = fields.Int(required=False, allow_none=True)
    reference_number = fields.Str(required=False, allow_none=True)
    advance_amount = fields.Number(required=False, allow_none=True, default=0)
    discount_fee_adjustment = fields.Number(required=False, allow_none=True, default=0)
    reason_for_disc_fee_adj = fields.Str(required=False, allow_none=True)
    miscellaneous_adjustment = fields.Number(required=False, allow_none=True, default=0)
    reason_miscellaneous_adj = fields.Str(required=False, allow_none=True)
    disbursement_amount = fields.Number(required=False, allow_none=True, default=0)
    disclaimer_id = fields.Int(required=False, allow_none=True)
    status = EnumField(ReserveReleaseStatus, required=False, allow_none=True)
    high_priority = fields.Bool(required=False, allow_none=True)
    last_processed_at = fields.DateTime(required=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)
    ref_client_rr_id = fields.Method(
        "get_ref_client_rr_id", dump_only=True
    )
    has_action_required = fields.Method(
        "get_rr_has_action_required", dump_only=True
    )
    has_client_submitted = fields.Method(
        "get_has_client_submitted", dump_only=True
    )
    payment_type = fields.Method(
        "get_payment_type", dump_only=True
    )
    
    def get_ref_client_rr_id(self, reserve_release):
        return reserve_release.get_ref_client_rr_id()
    
    def get_rr_has_action_required(self, reserve_release):
        rr_has_action_required = False
        if reserve_release.had_action_required():
            rr_has_action_required = True
        return rr_has_action_required
    
    def get_has_client_submitted(self, reserve_release):
        has_client_submitted = False
        if reserve_release.had_client_submitted():
            has_client_submitted = True
        return has_client_submitted

    def get_payment_type(self, reserve_release):                
        payment_method_dict = {"same_day_ach": "S", "wire": "W", "direct_deposit": "A"}
        payment_status_dict = {"In-System": "I", "Out-of-System": "O"}
        payment_string = ""
        payment_type = None
        payment_type_dict = {}

        disbursements_payment_type = reserve_release.get_disbursements_payment_type()
        if disbursements_payment_type:
            # Only show payment status indicator for AE/BO LC-2342
            # get user role
            user_role = Permissions.get_user_role_permissions()["user_role"]

            # principal
            if user_role == Permissions.principal:
                payment_type_list = []
                payment_type = [
                    v
                    for k, v in payment_method_dict.items()
                    for disbursement in disbursements_payment_type
                    if disbursement and disbursement[0].value == k
                ]
                [payment_type_list.append(payment_type_value) for payment_type_value in payment_type if payment_type_value not in payment_type_list]
                payment_type = ", ".join(payment_type_list)

            
            # AE/BO
            if user_role in [Permissions.ae, Permissions.bo]:
                for k, v in payment_method_dict.items():
                    for disbursement in disbursements_payment_type:
                        payment_method, payment_status = disbursement
                        
                        # checking, payment method
                        if payment_method and payment_method.value == k:
                            if v in payment_type_dict and payment_type_dict[v]:
                                if not payment_status:
                                    pass
                                else:
                                    payment_type_dict[v].append(payment_status_dict[payment_status])
                            else:
                                if payment_status:
                                    payment_type_dict[v] = [payment_status_dict[payment_status]]
                                else:
                                    payment_type_dict[v] = ""

                if payment_type_dict:
                    for p_method, p_status in payment_type_dict.items():
                        joined_payment_status = ",".join(p_status)
                        payment_string = payment_string + p_method + "(" + joined_payment_status + "), "
                        
                payment_type = payment_string.strip(", ")
                
        if not payment_type:
            payment_type = ""
        return payment_type

    @post_dump(pass_many=True)
    def utc_to_est(self, data, many):
        from src.resources.v2.helpers.convert_datetime import utc_to_local
        
        if many and isinstance(data, list):
            for each_data in data:
                if each_data["last_processed_at"]:
                    each_data["last_processed_at"] = utc_to_local(dt=each_data["last_processed_at"])
                if "created_at" in each_data:
                    each_data["created_at"] = utc_to_local(dt=each_data["created_at"])
                if "updated_at" in each_data:
                    each_data["updated_at"] = utc_to_local(dt=each_data["updated_at"])
        else:
            if data["last_processed_at"]:
                data["last_processed_at"] = utc_to_local(dt=data["last_processed_at"])
            if "created_at" in data:
                data["created_at"] = utc_to_local(dt=data["created_at"])
            if "updated_at" in data:
                data["updated_at"] = utc_to_local(dt=data["updated_at"])
        return data

    class Meta:
        ordered = True
        
        
# ReserveRelease Resource Schema
class ReserveReleaseResourseSchema(ReserveReleaseSchema):
    client_name = fields.Method("get_client_name", dump_only=True)
    ref_client_no = fields.Method("get_ref_client_no", dump_only=True)

    def get_client_name(self, reserve_release):
        client_name = reserve_release.client.name if reserve_release.client else None
        return client_name

    def get_ref_client_no(self, reserve_release):
        ref_client_no = (
            reserve_release.client.ref_client_no if reserve_release.client else None
        )
        return ref_client_no


# ReserveRelease Dashboard Schema
class ReserveReleaseDashboardSchema(ReserveReleaseResourseSchema):
    request_link = fields.Method("get_request_link", dump_only=True)
    request_type = fields.Method("get_request_type", dump_only=True)
    created_by = fields.Method("get_created_by", dump_only=True)

    def get_request_link(self, reserve_release):
        request_link = []
        reserve_release_id = reserve_release.id if reserve_release else None

        view_details = f"get-reserve-release-details/{reserve_release_id}"
        process = f"reserve-release/{reserve_release_id}"

        request_link.append({"view_details": view_details, "process": process})
        return request_link

    def get_request_type(self, reserve_release):
        return "reserve_release"

    def get_created_by(self, reserve_release):
        request_created_by_principal = reserve_release.request_created_by_principal()
        request_created_by = (
            request_created_by_principal.user if request_created_by_principal else None
        )
        if not request_created_by:
            request_created_by_client = reserve_release.request_created_by_client()
            request_created_by = (
                request_created_by_client.user if request_created_by_client else None
            )
        return request_created_by

# ReserveRelease Client Schema
class ReserveReleaseClientSchema(ReserveReleaseResourseSchema):
    control_account = fields.Method("get_control_account", dump_only=True)

    def get_control_account(self, reserve_release):
        control_account_name = None
        clients_control_account = reserve_release.client.clients_control_account if reserve_release.client else None
        if clients_control_account:
            control_account_name = clients_control_account[0].control_account.name
        return control_account_name
