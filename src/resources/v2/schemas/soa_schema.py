# from src.models import SOAResourseSchema
from marshmallow import fields, Schema, post_dump
from marshmallow_enum import EnumField
from src.models import SOAStatus
from src.middleware.permissions import Permissions

class SOASchema(Schema):
    """
    SOA Schema
    """

    id = fields.Int(dump_only=True)
    client_id = fields.Int(required=True)
    soa_ref_id = fields.Int(required=False, allow_none=True)
    reference_number = fields.Str(required=False, allow_none=True)
    status = EnumField(SOAStatus, required=False, allow_none=True)
    uploaded_supporting_docs = fields.Bool(required=False, allow_none=True)
    verification_calls = fields.Bool(required=False, allow_none=True)
    verification_call_notes = fields.Bool(required=False, allow_none=True)
    debtor_approval_emails = fields.Bool(required=False, allow_none=True)
    estoppel_letters = fields.Bool(required=False, allow_none=True)
    email_verification = fields.Bool(required=False, allow_none=True)
    po_verification = fields.Bool(required=False, allow_none=True)
    proof_of_delivery = fields.Bool(required=False, allow_none=True)
    notes = fields.Str(required=False, allow_none=True)
    invoice_total = fields.Number(required=False)
    invoice_cash_reserve_release = fields.Number(required=False)
    disclaimer_id = fields.Int(required=False, allow_none=True)
    discount_fees = fields.Number(required=False)
    credit_insurance_total = fields.Number(required=False)
    reserves_withheld = fields.Number(required=False)
    additional_cash_reserve_held = fields.Number(required=False)
    miscellaneous_adjustment = fields.Number(required=False)
    reason_miscellaneous_adj = fields.Str(required=False, allow_none=True)
    fee_adjustment = fields.Number(required=False)
    reason_fee_adj = fields.Str(required=False, allow_none=True)
    additional_cash_reserve_release = fields.Number(required=False)
    advance_amount = fields.Number(required=False)
    high_priority = fields.Bool(required=False, allow_none=True)
    ar_balance = fields.Number(required=False)
    additional_notes = fields.Str(required=False, allow_none=True)
    adjustment_from_ae = fields.Number(required=False)
    reason_adjustment_from_ae = fields.Str(required=False, allow_none=True)
    subtotal_discount_fees = fields.Number(required=False)
    total_fees_to_client = fields.Number(required=False)
    total_third_party_fees = fields.Number(required=False)
    disbursement_amount = fields.Number(required=False)
    last_processed_at = fields.DateTime(required=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)
    client_number_soa_id_number = fields.Method(
        "get_client_number_soa_id_number", dump_only=True
    )
    has_action_required = fields.Method(
        "get_soa_has_action_required", dump_only=True
    )
    has_client_submitted = fields.Method(
        "get_has_client_submitted", dump_only=True
    )
    payment_type = fields.Method(
        "get_payment_type", dump_only=True
    )
    
    def get_client_number_soa_id_number(self, soa):
        ref_client_no = soa.client.ref_client_no if soa.client else None
        client_number_soa_id_number = f"{ref_client_no}-SOAID{soa.soa_ref_id}"
        return client_number_soa_id_number

    def get_soa_has_action_required(self, soa):
        soa_has_action_required = False
        if soa.had_action_required():
            soa_has_action_required = True
        return soa_has_action_required

    def get_has_client_submitted(self, soa):
        has_client_submitted = False
        if soa.had_client_submitted():
            has_client_submitted = True
        return has_client_submitted

    def get_payment_type(self, soa):        
        payment_method_dict = {"same_day_ach": "S", "wire": "W", "direct_deposit": "A"}
        payment_status_dict = {"In-System": "I", "Out-of-System": "O"}
        payment_string = ""
        payment_type = None
        payment_type_dict = {}

        disbursements_payment_type = soa.get_disbursements_payment_type()
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
        

# SOA Resource Schema
class SOAResourseSchema(SOASchema):
    client_name = fields.Method("get_client_name", dump_only=True)
    ref_client_no = fields.Method("get_ref_client_no", dump_only=True)

    def get_client_name(self, soa):
        client_name = soa.client.name if soa.client else None
        return client_name

    def get_ref_client_no(self, soa):
        ref_client_no = soa.client.ref_client_no if soa.client else None
        return ref_client_no


# SOA Dashboard Schema
class SOADashboardSchema(SOAResourseSchema):
    request_link = fields.Method("get_request_link", dump_only=True)
    request_type = fields.Method("get_request_type", dump_only=True)
    created_by = fields.Method("get_created_by", dump_only=True)

    def get_request_link(self, soa):
        request_link = []
        soa_id = soa.id if soa else None

        view_details = f"get-soa-details/{soa_id}"
        process = f"soa/{soa_id}"

        request_link.append({"view_details": view_details, "process": process})
        return request_link

    def get_request_type(self, soa):
        return "soa"

    def get_created_by(self, soa):
        request_created_by_principal = soa.request_created_by_principal()
        request_created_by = (
            request_created_by_principal.user if request_created_by_principal else None
        )
        if not request_created_by:
            request_created_by_client = soa.request_created_by_client()
            request_created_by = (
                request_created_by_client.user if request_created_by_client else None
            )
        
        return request_created_by

# SOA Client Schema
class SOAclientSchema(SOAResourseSchema):
    control_account = fields.Method("get_control_account", dump_only=True)

    def get_control_account(self, soa):
        control_account_name = None
        clients_control_account = soa.client.clients_control_account if soa.client else None
        if clients_control_account:
            control_account_name = clients_control_account[0].control_account.name
        return control_account_name
