from flask import (
    json,
    Response,
    render_template,
    make_response,
    send_file,
)
import os
from decimal import Decimal
from src.models import *
from src.resources.v2.schemas import *
from datetime import datetime as dt
from io import BytesIO
from zipfile import ZipFile
import requests
from src.resources.v2.helpers import (
    generate_pdf,
    CalculateClientbalances,
)
from src.resources.v2.helpers.helper import principal_settings
from src.middleware.permissions import Permissions
import mimetypes
from pathlib import Path
from src.resources.v2.helpers.convert_datetime import utc_to_local


class SOAPDF:
    def __init__(self, soa, html_template = "invoice_schedule.html"):
        self.soa = soa
        self.zero_list = [0, 0.00]
        self.fee_to_principal = Decimal(0)
        self.fee_to_client = Decimal(0)
        self.column_list = []

        # html template name
        self.html_template = html_template

        # Current time
        self.current_time = utc_to_local(iso_format=False)
        self.date_time = self.current_time.strftime("%Y%m%d%H%M%S")
        
        # Submission time
        self.soa_submitted_at = None
        self.principal_email = None

        if self.soa.ar_balance is None:
            self.soa.ar_balance = 0.00

        if self.soa.adjustment_from_ae is None:
            self.soa.adjustment_from_ae = Decimal(0)

        if self.soa.invoice_cash_reserve_release is None:
            self.soa.invoice_cash_reserve_release = Decimal(0)

        principal_fee_charged = principal_settings()
        # for fee to principal
        self.payment_info = {
            "wire": principal_fee_charged["wire_fee"],
            "cheque": principal_fee_charged["cheque_fee"],
            "same_day_ach": principal_fee_charged["same_day_ach_fee"],
            "high_priority": principal_fee_charged["high_priority_fee"],
            "tp": principal_fee_charged["third_party_fee"],
        }

        # for fee to client
        self.client_payment_info = {
            "wire": Decimal(0),
            # "cheque": Decimal(0),
            "same_day_ach": Decimal(0),
            "high_priority": Decimal(0),
            "tp": Decimal(0),
        }

        self.payment_desc = {
            "wire": "Wire",
            "cheque": "Cheque",
            "same_day_ach": "Same Day ACH",
            "direct_deposit": "ACH",
        }

        # sort for payment type(LC-1595)
        self.payment_type_sorting = ["Same Day ACH", "Wire", "ACH"]
        self.get_disbursements_payment_type = set()

        # add high_priority to fee_to_principal
        if self.soa.high_priority:
            self.fee_to_principal += self.payment_info["high_priority"]

        self.soa_created_by = None
        self.soa_submitted_by = None
        self.soa_approved_by = None
        self.soa_completed_by = None
        self.soa_approved_history_attribute = None

        self.invoices = []
        self.invoice_total_held = Decimal(0)
        self.cash_reserve_releases = Decimal(0)
        self.created_by = None
        self.submitted_by = None
        self.preview_debtor_limits = {}
        self.preview_invoice_aging_by_debtor = {}
        self.new_debtors = []

        self.discount_fees_percentage = Decimal(0)
        self.credit_insurance_total_percentage = Decimal(0)
        self.reserves_withheld_total_percentage = Decimal(0)

        self.discount_percentage = Decimal(0)
        self.credit_insurance_percentage = Decimal(0)
        self.reserves_withheld_percentage = Decimal(0)

        self.client_client_fee = Decimal(0)
        self.client_third_party_fee = Decimal(0)
        self.client_amount = Decimal(0)
        self.client_soa_disbursements = []

        self.payee_client_fee = Decimal(0)
        self.payee_third_party_fee = Decimal(0)
        self.payee_amount = Decimal(0)
        self.payee_soa_disbursements = []

        self.has_action_required = False
        if self.soa.had_action_required():
            self.has_action_required = True

        self.obj_to_dict = lambda table_obj: {
            column: getattr(table_obj, column) for column in self.column_list
        }
        
        self.supporting_doc_not_image_ext = [
            ".csv",
            ".docx",
            ".xls",
            ".xlsx",
            ".pdf",
            ".txt",
        ]
        
        # get branding logo url
        get_branding = Permissions.get_user_details()["business_branding"]
        self.logo_url = (
            get_branding["logo_url"]
            if get_branding and "logo_url" in get_branding
            else None
        )

        # get user role
        self.user_role = None

        # get 'show_info' and 'show_requests' permissions for hide/show
        self.show_info = []
        self.show_requests = []

        self.run_func()

    def get_soa_approvals_history(self):
        approvals_history = ApprovalsHistory.query.filter_by(
            soa_id=self.soa.id, is_deleted=False
        ).order_by(ApprovalsHistory.id.desc())

        approvals_history_created = approvals_history.filter(
            ApprovalsHistory.key == "created_at"
        ).first()
        approvals_history_submitted = approvals_history.filter(
            ApprovalsHistory.key == "submitted_at"
        ).first()
        approvals_history_approved = approvals_history.filter(
            ApprovalsHistory.key == "approved_at"
        ).first()
        approvals_history_completed = approvals_history.filter(
            ApprovalsHistory.key == "funded_at"
        ).first()

        soa_approved_history = None
        if self.soa.status.value == "approved":
            # soa approved by AE
            soa_approved_history = approvals_history_approved

        if self.soa.status.value == "completed":
            # soa approved by BO
            soa_approved_history = approvals_history_completed

        # when soa is approved or completed(LC-1120)
        if soa_approved_history and soa_approved_history.key in [
            "approved_at",
            "funded_at",
        ]:
            if isinstance(soa_approved_history.attribute, str):
                self.soa_approved_history_attribute = json.loads(
                    soa_approved_history.attribute
                )
            else:
                self.soa_approved_history_attribute = soa_approved_history.attribute

        if approvals_history_created:
            self.soa_created_by = self.get_users_by_email(
                [approvals_history_created.user]
            )

        if approvals_history_submitted:
            self.principal_email = approvals_history_submitted.user
            self.soa_submitted_by = self.get_users_by_email(
                [approvals_history_submitted.user]
            )
            self.soa_submitted_at = utc_to_local(
                iso_format=False, dt=approvals_history_submitted.created_at.isoformat()
            )

        if approvals_history_approved:
            self.soa_approved_by = self.get_users_by_email(
                [approvals_history_approved.user]
            )

        if approvals_history_completed:
            self.soa_completed_by = self.get_users_by_email(
                [approvals_history_completed.user]
            )

    def get_users_by_email(self, email=[]):
        user_details = Permissions.get_users_by_email(email)
        users = user_details["users"]
        if not users or len(users) < 1:
            return ""
        return ", ".join(
            [user["first_name"] + " " + user["last_name"] for user in users]
        )

    def get_show_info_permissions(self):
        # get show_info and show_requests from auth api
        get_user_role_permissions = Permissions.get_user_role_permissions()
        # show requests
        show_requests = get_user_role_permissions["show_requests"]
        self.show_requests = list(show_requests.keys()) if show_requests else []
        # show info
        show_info = get_user_role_permissions["show_info"]
        self.show_info = list(show_info.keys()) if show_info else []
        # user role
        get_user_role = get_user_role_permissions["user_role"]
        self.user_role = get_user_role.lower()

    @property
    def company_name(self):
        company_name = None
        return company_name

    @property
    def control_account_name(self):
        control_account_name = None
        clients_control_account = self.soa.client.clients_control_account
        if clients_control_account:
            control_account_name = clients_control_account[0].control_account.name
        return control_account_name

    # @property
    # def client(self):
    #     return self.soa.client

    @property
    def client(self):
        get_client = self.soa.client
        client = ClientSchema().dump(get_client).data
        if (
            self.soa_approved_history_attribute
            and "client" in self.soa_approved_history_attribute
            and self.soa_approved_history_attribute["client"]
        ):
            client = self.soa_approved_history_attribute["client"]
        
        return client

    def get_invoices(self):
        get_all_invoices = self.soa.get_all_invoices_details()

        # get client_debtors from soa approval history
        saved_client_debtors = (
            self.soa_approved_history_attribute["client_debtors"] if self.soa_approved_history_attribute 
            and "client_debtors" in self.soa_approved_history_attribute 
            and self.soa_approved_history_attribute["client_debtors"] else None
        )

        debtor_dict = {}
        if get_all_invoices:
            for invoice in get_all_invoices:
                dict_data = {
                    "amount": invoice["amount"],
                    "actions": invoice["actions"],
                    "debtor_name": invoice["debtor_name"],
                    "po_number": invoice["po_number"],
                    "terms": invoice["terms"],
                    "invoice_date": invoice["invoice_date"],
                    "invoice_number": invoice["invoice_number"],
                }

                # checking condition for new debtors for showing attention in pdf
                if invoice["debtor_source"] == "funding":
                    self.new_debtors.append(invoice["debtor_name"])

                # not to alert debtor limits if debtor is new
                if invoice["debtor_source"] != "funding":

                    # Preview Debt Collector #                
                    ## Preview of A/R by debtor ## (LC-31)
                    # COD1 => Invoice total by debtor in the SOA = summary of all invoices in this SOA (by debtor)
                    # COD2 => Preview of A/R by debtor = Current A/R (by debtor) + Invoices in this SOA (by debtor)
                    # COD3 => Over Limit detail flag:	
                    #  1. IF Preview of A/R < 0 Then display orange Message "Debtor Balance is negative!"
                    #  2. IF 0 < Preview of A/R < Debtor Limit Then display green message "OK"
                    #  3. IF Preview of A/R > Debtor Limit Then display red message "Over Limit"
                    # COD4 => Over Limit - general flag:
                    #  1. IF all debtors have COD3 = "OK" then display green message
                    #  2. IF one or more debtors have COD3 = "Over Limit" then display red message
                    if debtor_dict.get(invoice["debtor_name"]) is None:
                        # COD1
                        debtor_dict[invoice["debtor_name"]] = invoice["amount"]
                    else:
                        invoice_aging = debtor_dict.get(invoice["debtor_name"])
                        # COD1
                        debtor_dict[invoice["debtor_name"]] = Decimal(
                            invoice_aging
                        ) + Decimal(invoice["amount"])

                    # get current_ar and credit_limit from saved client_debtors if debtor_id == invoice["debtor"]
                    if saved_client_debtors:
                        for client_debtor in saved_client_debtors:
                            if client_debtor["debtor_id"] == invoice["debtor"]:
                                current_ar = Decimal(client_debtor["current_ar"])
                                credit_limit = Decimal(client_debtor["credit_limit"])
                                break
                    else:
                        current_ar = invoice["current_ar"]
                        credit_limit = invoice["credit_limit"]

                    for debtor, invoice_amount in debtor_dict.items():
                        # COD2
                        preview_of_ar = invoice_amount + current_ar
                        if (
                            preview_of_ar > credit_limit
                            and debtor == invoice["debtor_name"]
                        ):
                            # COD4
                            self.preview_debtor_limits[debtor] = [invoice_amount]

                # Preview of Invoice Aging by Debtor
                ## DEBTOR AGIING ##
                # current day - invoice date = age(invoice_days)
                # COInvAg4 => if age(invoice_days) > 90 Then summary of invoices in this SOA by debtor with days (current day - invoice date = age)
                # COD0 => Invoice aging in detail Alert:
                # 1. IF COInvAg4 > 0 THEN display red message "Alert!"
                # 2. IF COInvAg4 < 0 THEN display green message "OK"
                # CODInvAgingFLAG => Invoice aging by Debtor flag - General:
                # 1. IF there is a debtor with a COD0 = "Ok" THEN display green message "Debtors are in Good Standing"
                # 2. IF there is one or more debtor with COD0 = "Alert" Then display red message "DebtorName has “Amount” in invoices with more than 90 days"
                if invoice["invoice_days"] > 90:
                    if (
                        self.preview_invoice_aging_by_debtor.get(invoice["debtor_name"])
                        is None
                    ):
                        # COInvAg4
                        self.preview_invoice_aging_by_debtor[
                            invoice["debtor_name"]
                        ] = invoice["amount"]
                    else:
                        invoice_aging = self.preview_invoice_aging_by_debtor.get(
                            invoice["debtor_name"]
                        )
                        # COInvAg4
                        self.preview_invoice_aging_by_debtor[
                            invoice["debtor_name"]
                        ] = Decimal(invoice_aging) + Decimal(invoice["amount"])

                self.invoices.append(dict_data)

                # get invoice held in reserve
                if invoice["actions"] == "hold_in_reserves":
                    self.invoice_total_held += (
                        invoice["amount"]
                        if invoice["amount"] is not None
                        else Decimal(0)
                    )

                # calculate cash reserve release from invoices
                if invoice["is_release_from_reserve"] == True:
                    self.cash_reserve_releases += (
                        invoice["amount"]
                        if invoice["amount"] is not None
                        else Decimal(0)
                    )

                self.created_by = (
                    invoice["added_by"] if invoice["added_by"] is not None else None
                )
                self.submitted_by = (
                    invoice["verified_by"]
                    if invoice["verified_by"] is not None
                    else None
                )

    def client_funds(self):
        # get client funds from approval history if soa approved
        if (
            self.soa_approved_history_attribute
            and "client_funds" in self.soa_approved_history_attribute
            and self.soa_approved_history_attribute["client_funds"] is not None
        ):
            if (
                "discount_fees_percentage"
                in self.soa_approved_history_attribute["client_funds"]
                and self.soa_approved_history_attribute["client_funds"][
                    "discount_fees_percentage"
                ]
                is not None
            ):
                self.discount_fees_percentage = Decimal(
                    "%.2f"
                    % self.soa_approved_history_attribute["client_funds"][
                        "discount_fees_percentage"
                    ]
                )

            if (
                "credit_insurance_total_percentage"
                in self.soa_approved_history_attribute["client_funds"]
                and self.soa_approved_history_attribute["client_funds"][
                    "credit_insurance_total_percentage"
                ]
                is not None
            ):
                self.credit_insurance_total_percentage = Decimal(
                    "%.2f"
                    % self.soa_approved_history_attribute["client_funds"][
                        "credit_insurance_total_percentage"
                    ]
                )

            if (
                "reserves_withheld_percentage"
                in self.soa_approved_history_attribute["client_funds"]
                and self.soa_approved_history_attribute["client_funds"][
                    "reserves_withheld_percentage"
                ]
                is not None
            ):
                self.reserves_withheld_total_percentage = Decimal(
                    "%.2f"
                    % self.soa_approved_history_attribute["client_funds"][
                        "reserves_withheld_percentage"
                    ]
                )

        else:
            client_funds = ClientFund.query.filter_by(
                is_deleted=False, client_id=self.soa.client_id
            ).first()

            if client_funds and client_funds.discount_fees_percentage is not None:
                self.discount_fees_percentage = client_funds.discount_fees_percentage

            if (
                client_funds
                and client_funds.credit_insurance_total_percentage is not None
            ):
                self.credit_insurance_total_percentage = (
                    client_funds.credit_insurance_total_percentage
                )

            if client_funds and client_funds.reserves_withheld_percentage is not None:
                self.reserves_withheld_total_percentage = (
                    client_funds.reserves_withheld_percentage
                )

    def get_client_settings(self):
        client_settings = self.soa.soa_client_settings()
        # # get client settings from approval history if soa approved
        # if (
        #     self.soa_approved_history_attribute
        #     and "client_settings" in self.soa_approved_history_attribute
        #     and self.soa_approved_history_attribute["client_settings"]
        # ):
        #     client_settings = self.soa_approved_history_attribute["client_settings"]
        # else:
        #     get_client_settings = ClientSettings.query.filter_by(
        #         client_id=self.client["id"], is_deleted=False
        #     ).first()
        #     if get_client_settings:                
        #         client_settings_schema = ClientSettingsSchema()
        #         client_settings = client_settings_schema.dump(
        #             get_client_settings
        #         ).data
        
        if client_settings:
            self.client_payment_info = {
                "wire": Decimal(client_settings["wire_fee"]),
                "same_day_ach": Decimal(client_settings["same_day_ach_fee"]),
                "high_priority": Decimal(client_settings["high_priority_fee"]),
                "tp": Decimal(client_settings["third_party_fee"]),
            }
            
            # add high_priority to fee_to_client
            if self.soa.high_priority:
                self.fee_to_client += Decimal(self.client_payment_info["high_priority"])

    def cal_discount_percentage(self):
        if (
            (self.discount_fees_percentage != None)
            & (bool(self.discount_fees_percentage in self.zero_list) == False)
            & (bool(self.soa.invoice_total in self.zero_list) == False)
        ):
            discountPercentage = (
                Decimal(self.soa.invoice_total) * Decimal(self.discount_fees_percentage)
            ) / 100
            self.discount_percentage = Decimal("%.2f" % discountPercentage)

    def cal_credit_insurance_percentage(self):
        if (
            (self.credit_insurance_total_percentage != None)
            & (bool(self.credit_insurance_total_percentage in self.zero_list) == False)
            & (bool(self.soa.invoice_total in self.zero_list) == False)
        ):
            credit_insurance_percentage = (
                Decimal(self.soa.invoice_total)
                * Decimal(self.credit_insurance_total_percentage)
            ) / 100
            self.credit_insurance_percentage = Decimal(
                "%.2f" % credit_insurance_percentage
            )

    def cal_reserves_withheld_percentage(self):
        if (
            (self.reserves_withheld_total_percentage != None)
            & (bool(self.reserves_withheld_total_percentage in self.zero_list) == False)
            & (bool(self.soa.invoice_total in self.zero_list) == False)
        ):
            reserves_withheld_percentage = (
                Decimal(self.soa.invoice_total)
                * Decimal(self.reserves_withheld_total_percentage)
            ) / 100
            self.reserves_withheld_percentage = Decimal(
                "%.2f" % reserves_withheld_percentage
            )

    def cal_advance_amount(self):
        self.soa.advance_amount = (
            self.soa.invoice_total
            + self.soa.invoice_cash_reserve_release
            + self.soa.additional_cash_reserve_release
            + self.soa.adjustment_from_ae
            + self.soa.fee_adjustment
        ) - (
            self.soa.additional_cash_reserve_held
            + self.discount_percentage
            + self.invoice_total_held
            + self.reserves_withheld_percentage
        )

    def cal_subtotal_discount_fees(self):
        if self.soa.fee_adjustment < 0:
            self.subtotal_discount_fees = self.soa.discount_fees + abs(
                self.soa.fee_adjustment
            )
        else:
            self.subtotal_discount_fees = (
                self.soa.discount_fees - self.soa.fee_adjustment
            )

    @property
    def soa_disbursements(self):
        return Disbursements.query.filter(
            Disbursements.soa_id == self.soa.id,
            Disbursements.is_deleted == False,
            Client.id == Disbursements.client_id,
            ClientPayee.client_id == Client.id,
            ClientPayee.payee_id == Disbursements.payee_id,
        )

    def get_client_soa_disbursements(self):
        client_soa_disbursements_obj = self.soa_disbursements.filter(
            ClientPayee.ref_type == "client",
        ).all()

        self.column_list = [
            "id",
            "payment_method",
            "third_party_fee",
            "amount",
            "client_fee",
        ]

        client_payment_method = None
        if client_soa_disbursements_obj:
            for soa_disbursement in client_soa_disbursements_obj:
                # for wire
                if soa_disbursement.payment_method.value == "wire":
                    self.fee_to_principal += self.payment_info["wire"]
                    self.fee_to_client += Decimal(soa_disbursement.client_fee)
                    client_payment_method = self.payment_desc["wire"]
                    
                # for same day ach
                if soa_disbursement.payment_method.value == "same_day_ach":
                    self.fee_to_principal += self.payment_info["same_day_ach"]
                    self.fee_to_client += Decimal(soa_disbursement.client_fee)
                    client_payment_method = self.payment_desc["same_day_ach"]

                # for ach
                if soa_disbursement.payment_method.value == "direct_deposit":
                    client_payment_method = self.payment_desc["direct_deposit"]

                third_party_fee = (
                    Decimal(soa_disbursement.third_party_fee)
                    if soa_disbursement.third_party_fee
                    else Decimal(0)
                )
                client_fee = (
                    Decimal(soa_disbursement.client_fee)
                    if soa_disbursement.client_fee
                    else Decimal(0)
                )
                tp_wire_total = client_fee + third_party_fee

                client_soa_disbursement = self.obj_to_dict(soa_disbursement)

                client_soa_disbursement["client_amount"] = Decimal(
                    client_soa_disbursement.pop("amount") - Decimal(tp_wire_total)
                )

                client_soa_disbursement["client_fee"] = (
                    Decimal(client_soa_disbursement.pop("client_fee"))
                    if soa_disbursement.client_fee
                    else Decimal(0)
                )

                # client_soa_disbursement["third_party_fee"] = (
                #     Decimal(client_soa_disbursement.pop("third_party_fee"))
                #     if soa_disbursement.third_party_fee
                #     else Decimal(0)
                # )

                client_soa_disbursement["payment_method"] = client_payment_method

                self.client_soa_disbursements.append(client_soa_disbursement)

                self.client_client_fee += client_soa_disbursement["client_fee"]
                # self.client_third_party_fee += client_soa_disbursement[
                #     "third_party_fee"
                # ]
                self.client_amount += client_soa_disbursement["client_amount"]
                self.get_disbursements_payment_type.add(client_payment_method)

    def get_payee_soa_disbursements(self):
        payee_soa_disbursements_obj = self.soa_disbursements.filter(
            ClientPayee.ref_type == "payee",
        ).all()

        self.column_list = [
            "id",
            "payment_method",
            "client_fee",
            "amount",
            "third_party_fee",
            "tp_ticket_number",
        ]

        payee_payment_method = None
        if payee_soa_disbursements_obj:
            for payee_soa_disbursement in payee_soa_disbursements_obj:
                # for wire
                if payee_soa_disbursement.payment_method.value == "wire":
                    self.fee_to_principal += self.payment_info["wire"]
                    self.fee_to_principal += self.payment_info["tp"]
                    self.fee_to_client += Decimal(payee_soa_disbursement.client_fee)
                    self.fee_to_client += Decimal(payee_soa_disbursement.third_party_fee)
                    payee_payment_method = self.payment_desc["wire"]
                
                # for same day ach
                if payee_soa_disbursement.payment_method.value == "same_day_ach":
                    self.fee_to_principal += self.payment_info["same_day_ach"]
                    self.fee_to_principal += self.payment_info["tp"]
                    self.fee_to_client += Decimal(payee_soa_disbursement.client_fee)
                    self.fee_to_client += Decimal(payee_soa_disbursement.third_party_fee)
                    payee_payment_method = self.payment_desc["same_day_ach"]

                # for ach
                if payee_soa_disbursement.payment_method.value == "direct_deposit":
                    self.fee_to_principal += self.payment_info["tp"]
                    self.fee_to_client += Decimal(payee_soa_disbursement.third_party_fee)
                    payee_payment_method = self.payment_desc["direct_deposit"]

                # cal net amount
                third_party_fee = (
                    Decimal(payee_soa_disbursement.third_party_fee)
                    if payee_soa_disbursement.third_party_fee
                    else Decimal(0)
                )
                client_fee = (
                    Decimal(payee_soa_disbursement.client_fee)
                    if payee_soa_disbursement.client_fee
                    else Decimal(0)
                )
                tp_wire_total = client_fee + third_party_fee

                dict_data = self.obj_to_dict(payee_soa_disbursement)

                dict_data["amount"] = Decimal(
                    dict_data.pop("amount") - Decimal(tp_wire_total)
                )

                dict_data["payment_method"] = payee_payment_method

                dict_data["client_fee"] = (
                    Decimal(dict_data.pop("client_fee"))
                    if payee_soa_disbursement.client_fee
                    else Decimal(0)
                )

                dict_data["third_party_fee"] = (
                    Decimal(dict_data.pop("third_party_fee"))
                    if payee_soa_disbursement.third_party_fee
                    else Decimal(0)
                )
                # payee_first_name = (
                #     payee_soa_disbursement.payee.first_name
                #     if payee_soa_disbursement.payee.first_name
                #     else ""
                # )
                # payee_last_name = (
                #     payee_soa_disbursement.payee.last_name
                #     if payee_soa_disbursement.payee.last_name
                #     else ""
                # )

                payee_account_nickname = (
                    payee_soa_disbursement.payee.account_nickname
                    if payee_soa_disbursement.payee.account_nickname
                    else ""
                )

                dict_data["payee_name"] = f"{payee_account_nickname}"

                dict_data["payee_is_new"] = (
                    payee_soa_disbursement.payee.is_new
                    if payee_soa_disbursement.payee.is_new is not None
                    else False
                )

                self.payee_soa_disbursements.append(dict_data)

                self.payee_client_fee += dict_data["client_fee"]
                self.payee_third_party_fee += dict_data["third_party_fee"]
                self.payee_amount += dict_data["amount"]
                self.get_disbursements_payment_type.add(payee_payment_method)

    @property
    def payment_type(self):
        # sort for payment type(LC-1595)
        payment_type = [
            value
            for sort in self.payment_type_sorting
            for value in list(self.get_disbursements_payment_type)
            if value == sort
        ]
        return payment_type

    @property
    def wire_fees(self):
        # cal total fees of wire/same day ach/ach for client as payee and third party payee
        return self.payee_client_fee + self.client_client_fee

    @property
    def tp_fees(self):
        # cal total third party fees of wire/same day/ach for third party payee
        return self.payee_third_party_fee

    @property
    def disbursement_amount(self):
        return Decimal(self.soa.advance_amount) - self.fee_to_client

    @property
    def outstanding_amount(self):
        # total client as payee(amount) + third party as payee(amount)
        client_payee_total_amount = self.client_amount + self.payee_amount
        return Decimal(self.soa.advance_amount) - Decimal(
            client_payee_total_amount + self.fee_to_client
        )

    @property
    def miscellaneous_adjustment(self):
        return self.fee_to_client

    @property
    def disclaimer_text(self):
        get_selected_disclaimer = self.soa.get_selected_disclaimer()
        get_disclaimer_text = None
        
        if (
            get_selected_disclaimer
            and isinstance(get_selected_disclaimer, list)
            and "text" in get_selected_disclaimer[0]
            and get_selected_disclaimer[0]["text"]
        ):
            get_disclaimer_text = get_selected_disclaimer[0]["text"]
        
        if (
            get_selected_disclaimer
            and isinstance(get_selected_disclaimer, dict)
            and "text" in get_selected_disclaimer
            and get_selected_disclaimer["text"]
        ):
            get_disclaimer_text = get_selected_disclaimer["text"]
        return get_disclaimer_text

    @property
    def soa_supporting_documents(self):
        soa_supporting_documents = SupportingDocuments.query.filter_by(
            soa_id=self.soa.id, is_deleted=False
        ).all()

        self.column_list = ["id", "soa_id", "url", "notes", "name", "tags", "ext"]
        soa_supporting_document_list = []
        if soa_supporting_documents:
            for soa_supporting_document in soa_supporting_documents:
                ext = None                
                if soa_supporting_document.url:
                    # ext = mimetypes.guess_extension(
                    #     mimetypes.guess_type(soa_supporting_document.url)[0]
                    # )
                    ext = Path(soa_supporting_document.url).suffix
                setattr(soa_supporting_document, "ext", ext)

                soa_supporting_document_list.append(
                    self.obj_to_dict(soa_supporting_document)
                )
        return soa_supporting_document_list

    @property
    def soa_verification_notes(self):
        soa_verification_notes = self.soa.soa_verification_notes()

        verification_notes_list = []
        if soa_verification_notes:
            for verification_notes in soa_verification_notes:
                dict_data = {
                    "invoice_number": verification_notes["invoice_number"],
                    "debtor_name": verification_notes["debtor_name"],
                    "verification_type_or_method": verification_notes["verification_type_or_method"],
                    "contact": verification_notes["contact"],
                    "notes": verification_notes["notes"],
                }

                verification_notes_list.append(dict_data)

        return verification_notes_list

    @property
    def soa_invoice_supporting_documents(self):
        soa_invoice_supporting_documents = self.soa.soa_invoice_supporting_documents()

        invoice_supporting_documents_list = []
        if soa_invoice_supporting_documents:
            for invoice_supporting_documents in soa_invoice_supporting_documents:

                ext = None
                if "url" in invoice_supporting_documents and invoice_supporting_documents["url"]:
                    ext = Path(invoice_supporting_documents["url"]).suffix

                dict_data = {
                    "invoice_number": invoice_supporting_documents["invoice_number"],
                    "debtor_name": invoice_supporting_documents["debtor_name"],
                    "name": invoice_supporting_documents["name"],
                    "ext": ext,
                    "supporting_document_file": invoice_supporting_documents["url"],
                }

                invoice_supporting_documents_list.append(dict_data)

        return invoice_supporting_documents_list

    @property
    def cal_client_balances(self):
        calculate_client_balances = CalculateClientbalances(
            request_type=self.soa,
            invoice_total=self.soa.invoice_total,
            client_id=self.soa.client_id,
        )
        return calculate_client_balances.client_limit_flag

    @property
    def soa_details(self):
        soa_list = {}

        # soa
        get_soa = {
            "soa_id": self.soa.id,
            "ref_client_soa_id": f"{self.client['ref_client_no']}-SOAID{self.soa.soa_ref_id}",
            "client_id": self.soa.client_id,
            "status": self.soa.status.value,
            "reference_number": self.soa.reference_number,
            "has_action_required": self.has_action_required,
            "invoice_total": "{0:,.2f}".format(self.soa.invoice_total),
            "invoice_cash_reserve_release": self.soa.invoice_cash_reserve_release,
            "discount_fees": "{0:,.2f}".format(self.discount_percentage),
            "credit_insurance_total": "{0:,.2f}".format(
                self.credit_insurance_percentage
            ),
            "reserves_withheld": "{0:,.2f}".format(self.reserves_withheld_percentage),
            "additional_cash_reserve_held": self.soa.additional_cash_reserve_held,
            "miscellaneous_adjustment": self.soa.miscellaneous_adjustment,
            "reason_miscellaneous_adj": self.soa.reason_miscellaneous_adj,
            "fee_adjustment": self.soa.fee_adjustment,
            "reason_fee_adj": self.soa.reason_fee_adj,
            "additional_cash_reserve_release": self.soa.additional_cash_reserve_release,
            "ar_balance": Decimal(self.soa.ar_balance),
            "advance_amount": "{0:,.2f}".format(self.soa.advance_amount),
            "discount_percentage": "{:,g}".format(
                Decimal(self.discount_fees_percentage)
            ),
            "credit_insurance_percentage": format(
                self.credit_insurance_total_percentage
            ),
            "reserves_withheld_percentage": "{:,g}".format(
                Decimal(self.reserves_withheld_total_percentage)
            ),
            "high_priority": self.soa.high_priority,
            "notes": self.soa.notes,
            "soa_ref_id": self.soa.soa_ref_id,
            "uploaded_supporting_docs": self.soa.uploaded_supporting_docs,
            "verification_calls": self.soa.verification_calls,
            "verification_call_notes": self.soa.verification_call_notes,
            "debtor_approval_emails": self.soa.debtor_approval_emails,
            "estoppel_letters": self.soa.estoppel_letters,
            "email_verification": self.soa.email_verification,
            "po_verification": self.soa.po_verification,
            "proof_of_delivery": self.soa.proof_of_delivery
            # "notes": self.soa.notes
        }

        soa_list.update(
            {
                "company_name": self.company_name,
                "control_account_name": self.control_account_name,
                "client": {
                    "name": self.client["name"],
                    "ref_client_no": self.client["ref_client_no"],
                },
                "invoice": self.invoices,
                "invoice_total_held": Decimal(self.invoice_total_held),
                "cash_reserve_releases": Decimal(self.cash_reserve_releases),
                "created_by": self.created_by,
                "submitted_by": self.submitted_by,
                "current_time": self.current_time,
                "soa_submitted_at": self.soa_submitted_at,
                "principal_email": self.principal_email,
                "subtotal_discount_fees": (self.subtotal_discount_fees),
                "soa": get_soa,
                "adjustment_from_ae": Decimal(self.soa.adjustment_from_ae),
                "reason_adjustment_from_ae": self.soa.reason_adjustment_from_ae,
                "client_soa_disbursement": self.client_soa_disbursements,
                # "client_client_fee": self.client_client_fee,
                # "client_third_party_fee": self.client_third_party_fee,
                "payee_soa_disbursement": self.payee_soa_disbursements,
                # "payee_client_fee": self.payee_client_fee,
                # "payee_third_party_fee": "{0:,.2f}".format(
                #     self.payee_third_party_fee
                # ),
                "payment_type": self.payment_type,
                "wire_fees": self.wire_fees,
                "tp_fees": self.tp_fees,
                "disbursement_amount": "{0:,.2f}".format(self.disbursement_amount),
                "outstanding_amount": self.outstanding_amount,
                "client_payee_wire_amount": Decimal(0),
                "fee_to_principal": self.fee_to_principal,
                "miscellaneous_adjustment": self.miscellaneous_adjustment,
                "soa_created_by": self.soa_created_by,
                "soa_submitted_by": self.soa_submitted_by,
                "soa_approved_by": self.soa_approved_by,
                "soa_completed_by": self.soa_completed_by,
                "disclaimer_text": self.disclaimer_text,
                "soa_verification_notes": self.soa_verification_notes,
                "get_soa_supporting_documents": self.soa_supporting_documents,
                "soa_invoice_supporting_documents": self.soa_invoice_supporting_documents,
                "preview_client_balances": self.cal_client_balances,
                "preview_debtor_limits": self.preview_debtor_limits,
                "preview_invoice_aging_by_debtor": self.preview_invoice_aging_by_debtor,
                "new_debtors": self.new_debtors,
                "total_fee_to_client": self.fee_to_client,
                "supporting_doc_not_image_ext": self.supporting_doc_not_image_ext,
                "branding_logo_url": self.logo_url,
                "show_info": self.show_info,
                "show_requests": self.show_requests,
                "user_role": self.user_role,
            }
        )
        return soa_list

    def run_func(self):
        self.get_soa_approvals_history() # should always run first
        self.get_client_settings()
        self.get_invoices()
        self.client_funds()
        self.cal_discount_percentage()
        self.cal_credit_insurance_percentage()
        self.cal_reserves_withheld_percentage()
        self.cal_subtotal_discount_fees()
        self.get_client_soa_disbursements()
        self.get_payee_soa_disbursements()
        self.get_show_info_permissions()

    @property
    def download_pdf(self):
        # Generate file name
        file_name = f"soa_{self.date_time}"

        # Generating PDF
        html = render_template(self.html_template, data=self.soa_details)
        
        pdf_url = generate_pdf(file_name=file_name, html=html)

        if isinstance(pdf_url, Response):
            return pdf_url

        # Generating zip
        memory_file = BytesIO()
        with ZipFile(memory_file, "w") as zip:
            pdf_download = requests.get(pdf_url)
            zip.writestr(f"{file_name}.pdf", pdf_download.content)
            # Downloading Documents
            if self.soa_supporting_documents:
                for docs in self.soa_supporting_documents:
                    r = requests.get(docs["url"])
                    # get url
                    get_url = docs["url"]
                    filename, file_extension = os.path.splitext(get_url)
                    zip.writestr(docs["name"] + str(file_extension), r.content)
            if self.soa_invoice_supporting_documents:
                for invoice_supporting_documents in self.soa_invoice_supporting_documents:
                    r = requests.get(invoice_supporting_documents["supporting_document_file"])
                    # get url
                    get_url = invoice_supporting_documents["supporting_document_file"]
                    filename, file_extension = os.path.splitext(get_url)
                    zip.writestr(invoice_supporting_documents["name"] + str(file_extension), r.content)
        memory_file.seek(0)

        response = make_response(
            send_file(
                memory_file,
                attachment_filename=str(file_name) + ".zip",
                as_attachment=True,
            )
        )
        response.headers["Access-Control-Expose-Headers"] = "content-disposition"
        response.headers["Cache-Control"] = "public, max-age=0"
        return response
