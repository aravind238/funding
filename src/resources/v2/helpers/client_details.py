from decimal import Decimal
from flask import json
from src.resources.v2.helpers import custom_response
import os
import requests
from src.models import *
from src.resources.v2.schemas import *

client_debtor_schema = ClientDebtorSchema()
client_control_account_schema = ClientControlAccountsSchema()
control_account_schema = ControlAccountSchema()
debtor_schema = DebtorSchema()
payee_schema = PayeeSchema()
client_funds_schema = ClientFundSchema()
disclaimers_schema = DisclaimersSchema()
disclaimer_only_schema = DisclaimerOnlySchema()
client_settings_schema = ClientSettingsSchema()
debtor_limit_approvals_schema = DebtorLimitApprovalsSchema()


class ClientDetails:
    
    def __init__(self, client, request_type=None):
        self.client = client
        # request_type = SOA|reserve_release
        self.request_type = request_type

    @property
    def request_type_approved(self):
        request_approved = None
        if self.request_type and self.request_type.status.value == "approved":
            request_approved = "approved_at"

        if self.request_type and self.request_type.status.value == "completed":
            request_approved = "funded_at"

        request_type_approved = None
        request_approved_attribute = None
        if request_approved:
            if self.request_type.object_as_string().lower() == "soa":
                request_type_approved = (
                    ApprovalsHistory.query.filter_by(
                        soa_id=self.request_type.id, is_deleted=False
                    )
                    .filter(ApprovalsHistory.key == request_approved)
                    .order_by(ApprovalsHistory.id.desc())
                    .first()
                )

            if self.request_type.object_as_string().lower() == "reserve release":
                request_type_approved = (
                    ApprovalsHistory.query.filter_by(
                        reserve_release_id=self.request_type.id, is_deleted=False
                    )
                    .filter(ApprovalsHistory.key == request_approved)
                    .order_by(ApprovalsHistory.id.desc())
                    .first()
                )

        if request_type_approved and request_type_approved.key in [
            "approved_at",
            "funded_at",
        ]:
            if isinstance(request_type_approved.attribute, str):
                request_approved_attribute = json.loads(request_type_approved.attribute)
            else:
                request_approved_attribute = request_type_approved.attribute
        return request_approved_attribute

    @property
    def debtors(self):
        from src.resources.v2.controllers.debtors_controller import get_soa_by_debtor

        get_debtors = self.client.get_debtors()
        debtor_objects_dict = []
        for debtor in get_debtors:            
            can_edit_debtor = False
            credit_limit_requested = Decimal(0)
            credit_limit_approved = Decimal(0)

            # Debtors
            debtor_obj = debtor_schema.dump(debtor.Debtor).data

            # client debtors
            client_debtors_schema = client_debtor_schema.dump(debtor.ClientDebtor).data
            client_debtor_client_ref_no = client_debtors_schema["client_ref_no"]
            days_1_30 = client_debtors_schema["days_1_30"]
            days_31_60 = client_debtors_schema["days_31_60"]
            days_61_90 = client_debtors_schema["days_61_90"]
            days_91_120 = client_debtors_schema["days_91_120"]
            current_ar = client_debtors_schema["current_ar"]
            credit_limit = client_debtors_schema["credit_limit"]

            # debtor limit approvals
            debtor_limit_approvals = DebtorLimitApprovals.query.filter(
                DebtorLimitApprovals.debtor_id == debtor_obj["id"],
                DebtorLimitApprovals.deleted_at == None,
            ).order_by(DebtorLimitApprovals.id.desc()).first()            
            if debtor_limit_approvals:
                debtor_limit_approvals_data = debtor_limit_approvals_schema.dump(debtor_limit_approvals).data
                credit_limit_requested = debtor_limit_approvals_data["credit_limit_requested"]
                credit_limit_approved = debtor_limit_approvals_data["credit_limit_approved"]

            # checking, if debtor is not synced
            if debtor_obj and debtor_obj["source"] == "funding":
                get_debtors_soa = get_soa_by_debtor(
                    debtor_id=debtor_obj["id"], client_id=self.client.id
                )

                debtors_soa_status = []
                can_edit_debtor = True
                if len(get_debtors_soa["reference_ids"]) > 0:
                    [
                        debtors_soa_status.append(each_data["status"])
                        for each_data in get_debtors_soa["data"]
                        if each_data["status"] != "draft"
                    ]

                    if debtors_soa_status:
                        can_edit_debtor = False

            debtor_obj.update(
                {
                    "client_ref_no": client_debtor_client_ref_no,
                    "days_1_30": days_1_30,
                    "days_31_60": days_31_60,
                    "days_61_90": days_61_90,
                    "days_91_120": days_91_120,
                    "current_ar": current_ar,
                    "credit_limit": credit_limit,
                    "can_edit": can_edit_debtor,
                    "credit_limit_requested": credit_limit_requested,
                    "credit_limit_approved": credit_limit_approved,
                }
            )

            debtor_objects_dict.append(debtor_obj)
        return debtor_objects_dict

    @property
    def payees(self):
        get_payees = self.client.get_payees()
        payee_objects_dict = payee_schema.dump(get_payees, many=True).data

        payees_data = []
        if payee_objects_dict:
            for payee_obj in payee_objects_dict:
                # payee accounts
                payee_obj.update({"accounts": []})

            # sort payee list alphabetically (LC-1306)
            payees_data = sorted(payee_objects_dict, key=lambda inv: inv["account_nickname"])
        return payees_data

    @property
    def client_control_account(self):
        clients_control_account = self.client.clients_control_account
        control_account_details = []
        if (
            bool(clients_control_account)
            and clients_control_account[0].control_account.is_deleted == False
        ):
            control_account = clients_control_account[0].control_account
            control_account_details.append(
                control_account_schema.dump(control_account).data
            )
        return control_account_details

    @property
    def client_funds(self):
        client_funds = None
        if (
            self.request_type_approved
            and "client_funds" in self.request_type_approved
            and self.request_type_approved["client_funds"] is not None
        ):
            client_funds = self.request_type_approved["client_funds"]

        if (
            bool(self.client.client_funds)
            and self.client.client_funds[0].is_deleted == False
            and client_funds is None
        ):
            client_funds = client_funds_schema.dump(self.client.client_funds[0]).data
        return client_funds

    @property
    def client_settings(self):
        # for soa, client settings
        if (
            self.request_type 
            and self.request_type.object_as_string().lower() == "soa"
        ):
            client_settings = self.request_type.soa_client_settings()
        # for reserve release, client settings
        elif (
            self.request_type
            and self.request_type.object_as_string().lower() == "reserve release"
        ):
            client_settings = self.request_type.rr_client_settings()
        else:
            client_settings = {}
            
        # if (
        #     self.request_type_approved
        #     and "client_settings" in self.request_type_approved
        #     and self.request_type_approved["client_settings"]
        # ):
        #     client_settings = self.request_type_approved["client_settings"]
        
        if not client_settings:
            if (
                self.client.client_settings
                and self.client.client_settings[0].is_deleted == False
            ):
                # get client settings
                client_settings = (
                    client_settings_schema.dump(self.client.client_settings[0])
                    .data
                )
            else:
                # save client settings
                client_settings_obj = {
                    "client_id": self.client.id
                }
                add_client_settings = ClientSettings(client_settings_obj)
                add_client_settings.save()

                client_settings = (
                    client_settings_schema.dump(add_client_settings)
                    .data
                )
        
        return client_settings

    @property
    def client_accounts(self):
        client_accounts = []
        get_payees = self.client.get_client_payees()
        payee_objects_dict = payee_schema.dump(get_payees, many=True).data
        if payee_objects_dict:
            client_accounts = sorted(payee_objects_dict, key=lambda inv: inv["account_nickname"])
        return client_accounts

    @property
    def client_disclaimer(self):
        client_disclaimer = []

        disclaimer = Disclaimers.query.filter_by(
            id=self.client.default_disclaimer_id, 
            is_deleted=False
        ).first()
        
        if disclaimer:
            disclaimers_data = disclaimer_only_schema.dump(disclaimer).data
            disclaimers_data["client_id"] = self.client.id
            client_disclaimer.append(disclaimers_data)
        return client_disclaimer

    @property
    def get_details(self):
        return {
            "debtors": self.debtors,
            "payee": self.payees,
            "client_control_account": self.client_control_account,
            "client_accounts": self.client_accounts,
            "client_fund": self.client_funds,
            "client_disclaimer": self.client_disclaimer,
            "client_settings": self.client_settings,
        }


def third_party_sync_by_client(client=None):
    """
    third party sync based off client id
    """
    try:
        status_code = 404

        if client is None:
            return {"status_code": status_code, "msg": "Client not found"}

        url = (
            os.getenv("LC_THIRD_PARTY_API_URL")
            + f"v1/funding/sync/client/{client.lcra_client_accounts_id}"
        )

        # defining a headers dict for the parameters to be sent to the API
        headers = {
            "app-id": os.getenv("LC_THIRD_PARTY_APP_ID"),
            "app-secret": os.getenv("LC_THIRD_PARTY_APP_SECRET"),
        }

        # defining a params dict for the parameters to be sent to the API
        # params = {
        #     "lcra_account_number" : client.lcra_client_accounts_number,
        #     "lcra_account_id" : client.lcra_client_accounts_id,
        #     "cadence_client_key" : client.ref_client_no
        # }

        try:
            r = requests.get(url=url, headers=headers, timeout=8)

            # extracting data in json format
            data = r.json()
            status_code = r.status_code

        except requests.ConnectionError as e:
            data = {"msg": f"Connection Error: {e}"}
        except requests.HTTPError as e:
            data = {"msg": f"HTTP Error: {e}"}
        except requests.Timeout as e:
            data = {"msg": f"Timeout Error: {e}"}
        except Exception as e:
            data = {"msg": f"RequestException Error: {e}"}

        msg = data["msg"] if "msg" in data else "Something went wrong, Please try again"

        res_data = {"status_code": status_code, "msg": msg}

        return res_data

    except Exception as e:
        print(f"Exception: {e}")
        return custom_response({"status": "error", "msg": str(e)}, 404)
