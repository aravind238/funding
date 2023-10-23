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
from src.resources.v2.helpers import generate_pdf
from src.resources.v2.helpers.helper import principal_settings
from src.middleware.permissions import Permissions
from pathlib import Path
from src.resources.v2.helpers.convert_datetime import utc_to_local


class ReserveReleasePDF:
    def __init__(self, reserve_release, html_template="reserve_release.html"):
        self.reserve_release = reserve_release
        self.fee_to_principal = Decimal(0)
        self.fee_to_client = Decimal(0)
        self.column_list = []
        
        # html template name
        self.html_template = html_template

        # Current time
        self.current_time = utc_to_local(iso_format=False)
        self.date_time = self.current_time.strftime("%Y%m%d%H%M%S")
        
        # Submission time
        self.reserve_release_submitted_at = None
        self.principal_email = None

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

        self.reserve_release_approved_history_attribute = None
        self.reserve_release_created_by = None
        self.reserve_release_submitted_by = None
        self.reserve_release_approved_by = None
        self.reserve_release_completed_by = None

        self.client_client_fee = Decimal(0)
        self.client_third_party_fee = Decimal(0)
        self.client_amount = Decimal(0)
        self.client_reserve_release_disbursement_list = []

        self.miscellaneous_adjustment = Decimal(0)
        self.discount_fee = Decimal(0)

        self.payee_client_fee = Decimal(0)
        self.payee_third_party_fee = Decimal(0)
        self.payee_amount = Decimal(0)
        self.payee_reserve_release_disbursement_list = []

        self.has_action_required = False
        if self.reserve_release.had_action_required():
            self.has_action_required = True

        # add high_priority to fee_to_principal
        if self.reserve_release.high_priority:
            self.fee_to_principal += self.payment_info["high_priority"]

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

        self.run_func()

    def get_reserve_release_approvals_history(self):
        approvals_history = ApprovalsHistory.query.filter_by(
            reserve_release_id=self.reserve_release.id, is_deleted=False
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

        reserve_release_approved_history = None
        if self.reserve_release.status.value == "approved":
            # reserve release approved by AE
            reserve_release_approved_history = approvals_history_approved

        if self.reserve_release.status.value == "completed":
            # reserve release approved by BO
            reserve_release_approved_history = approvals_history_completed

        # when reserve_release is approved or completed(LC-1120)
        if (
            reserve_release_approved_history
            and reserve_release_approved_history.key in ["approved_at", "funded_at"]
        ):
            if isinstance(reserve_release_approved_history.attribute, str):
                self.reserve_release_approved_history_attribute = json.loads(
                    reserve_release_approved_history.attribute
                )
            else:
                self.reserve_release_approved_history_attribute = (
                    reserve_release_approved_history.attribute
                )

        if approvals_history_created:
            self.reserve_release_created_by = self.get_users_by_email(
                [approvals_history_created.user]
            )

        if approvals_history_submitted:
            self.principal_email = approvals_history_submitted.user
            self.reserve_release_submitted_by = self.get_users_by_email(
                [approvals_history_submitted.user]
            )
            self.reserve_release_submitted_at = utc_to_local(
                iso_format=False, dt=approvals_history_submitted.created_at.isoformat()
            )

        if approvals_history_approved:
            self.reserve_release_approved_by = self.get_users_by_email(
                [approvals_history_approved.user]
            )

        if approvals_history_completed:
            self.reserve_release_completed_by = self.get_users_by_email(
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

    @property
    def company_name(self):
        company_name = None
        return company_name

    @property
    def control_account_name(self):
        control_account_name = None
        clients_control_account = self.reserve_release.client.clients_control_account
        if clients_control_account:
            control_account_name = clients_control_account[0].control_account.name
        return control_account_name

    @property
    def reserve_release_disbursements(self):
        return Disbursements.query.join(ReserveReleaseDisbursements).filter(
            Disbursements.is_deleted == False,
            ReserveReleaseDisbursements.reserve_release_id == self.reserve_release.id,
            Client.id == Disbursements.client_id,
            ClientPayee.client_id == Client.id,
            ClientPayee.payee_id == Disbursements.payee_id,
        )

    def get_client_reserve_release_disbursements(self):
        client_reserve_release_disbursements = (
            self.reserve_release_disbursements.filter(
                ClientPayee.ref_type == "client",
            ).all()
        )

        self.column_list = [
            "id",
            "payment_method",
            "third_party_fee",
            "amount",
            "client_fee",
        ]

        client_payment_method = None
        if client_reserve_release_disbursements:
            for reserve_release_disbursement in client_reserve_release_disbursements:
                # for wire
                if reserve_release_disbursement.payment_method.value == "wire":
                    self.fee_to_principal += self.payment_info["wire"]
                    self.fee_to_client += Decimal(
                        reserve_release_disbursement.client_fee
                    )
                    client_payment_method = self.payment_desc["wire"]

                # for same day ach
                if reserve_release_disbursement.payment_method.value == "same_day_ach":
                    self.fee_to_principal += self.payment_info["same_day_ach"]
                    self.fee_to_client += Decimal(
                        reserve_release_disbursement.client_fee
                    )
                    client_payment_method = self.payment_desc["same_day_ach"]

                # for ach
                if (
                    reserve_release_disbursement.payment_method.value
                    == "direct_deposit"
                ):
                    client_payment_method = self.payment_desc["direct_deposit"]

                wire_fee_disbursement = (
                    reserve_release_disbursement.client_fee
                    if reserve_release_disbursement.client_fee
                    else Decimal(0)
                )
                # third_party_fee_disbursement = (
                #     Decimal(reserve_release_disbursement.third_party_fee)
                #     if reserve_release_disbursement.third_party_fee
                #     else Decimal(0)
                # )

                client_disbursement_amount = Decimal(wire_fee_disbursement)

                client_reserve_release_disbursement = self.obj_to_dict(
                    reserve_release_disbursement
                )

                client_reserve_release_disbursement["client_amount"] = Decimal(
                    client_reserve_release_disbursement.pop("amount")
                    - Decimal(client_disbursement_amount)
                )

                client_reserve_release_disbursement["client_fee"] = (
                    Decimal(client_reserve_release_disbursement.pop("client_fee"))
                    if reserve_release_disbursement.client_fee
                    else Decimal(0)
                )
                client_reserve_release_disbursement["third_party_fee"] = (
                    Decimal(
                        client_reserve_release_disbursement.pop("third_party_fee")
                    )
                    if reserve_release_disbursement.third_party_fee
                    else Decimal(0)
                )
                client_reserve_release_disbursement[
                    "payment_method"
                ] = client_payment_method

                self.client_reserve_release_disbursement_list.append(
                    client_reserve_release_disbursement
                )

                self.client_client_fee += client_reserve_release_disbursement[
                    "client_fee"
                ]
                # self.client_third_party_fee += client_reserve_release_disbursement[
                #     "third_party_fee"
                # ]
                self.client_amount += client_reserve_release_disbursement[
                    "client_amount"
                ]
                self.get_disbursements_payment_type.add(client_payment_method)

    def get_payee_reserve_release_disbursements(self):
        payee_reserve_release_disbursements = self.reserve_release_disbursements.filter(
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
        if payee_reserve_release_disbursements:
            for (
                payee_reserve_release_disbursement
            ) in payee_reserve_release_disbursements:
                # for wire
                if payee_reserve_release_disbursement.payment_method.value == "wire":
                    self.fee_to_principal += self.payment_info["wire"]
                    self.fee_to_principal += self.payment_info["tp"]
                    self.fee_to_client += Decimal(
                        payee_reserve_release_disbursement.client_fee
                    )
                    self.fee_to_client += Decimal(
                        payee_reserve_release_disbursement.third_party_fee
                    )
                    payee_payment_method = self.payment_desc["wire"]

                # for same day ach
                if (
                    payee_reserve_release_disbursement.payment_method.value
                    == "same_day_ach"
                ):
                    self.fee_to_principal += self.payment_info["same_day_ach"]
                    self.fee_to_principal += self.payment_info["tp"]
                    self.fee_to_client += Decimal(
                        payee_reserve_release_disbursement.client_fee
                    )
                    self.fee_to_client += Decimal(
                        payee_reserve_release_disbursement.third_party_fee
                    )
                    payee_payment_method = self.payment_desc["same_day_ach"]

                # for ach
                if (
                    payee_reserve_release_disbursement.payment_method.value
                    == "direct_deposit"
                ):
                    self.fee_to_principal += self.payment_info["tp"]
                    self.fee_to_client += Decimal(
                        payee_reserve_release_disbursement.third_party_fee
                    )
                    payee_payment_method = self.payment_desc["direct_deposit"]

                wire_fee_disbursements = (
                    Decimal(payee_reserve_release_disbursement.client_fee)
                    if payee_reserve_release_disbursement.client_fee
                    else Decimal(0)
                )
                third_party_fee_disbursements = (
                    Decimal(payee_reserve_release_disbursement.third_party_fee)
                    if payee_reserve_release_disbursement.third_party_fee
                    else Decimal(0)
                )
                payee_disbursement_amounts = Decimal(
                    wire_fee_disbursements + third_party_fee_disbursements
                )

                dict_data = self.obj_to_dict(payee_reserve_release_disbursement)

                dict_data["amount"] = Decimal(dict_data.pop("amount")) - Decimal(
                    payee_disbursement_amounts
                )
                dict_data["payment_method"] = payee_payment_method

                dict_data["client_fee"] = (
                    Decimal(dict_data.pop("client_fee"))
                    if payee_reserve_release_disbursement.client_fee
                    else Decimal(0)
                )
                dict_data["third_party_fee"] = (
                    Decimal(dict_data.pop("third_party_fee"))
                    if payee_reserve_release_disbursement.third_party_fee
                    else Decimal(0)
                )
                # payee_first_name = (
                #     payee_reserve_release_disbursement.payee.first_name
                #     if payee_reserve_release_disbursement.payee.first_name
                #     else ""
                # )
                # payee_last_name = (
                #     payee_reserve_release_disbursement.payee.last_name
                #     if payee_reserve_release_disbursement.payee.last_name
                #     else ""
                # )
                payee_account_nickname = (
                    payee_reserve_release_disbursement.payee.account_nickname
                    if payee_reserve_release_disbursement.payee.account_nickname
                    else ""
                )

                dict_data["payee_name"] = f"{payee_account_nickname}"

                dict_data["payee_is_new"] = (
                    payee_reserve_release_disbursement.payee.is_new
                    if payee_reserve_release_disbursement.payee.is_new
                    else False
                )

                self.payee_reserve_release_disbursement_list.append(dict_data)

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
        return self.payee_client_fee + self.client_client_fee

    @property
    def tp_fees(self):
        return self.payee_third_party_fee

    def cal_miscellaneous_adjustment(self):
        miscellaneous_adjustment = (
            self.reserve_release.miscellaneous_adjustment
            if self.reserve_release.miscellaneous_adjustment
            else Decimal(0)
        )
        self.miscellaneous_adjustment = Decimal(miscellaneous_adjustment)

    def cal_discount_fees(self):
        discount_fee = (
            self.reserve_release.discount_fee_adjustment
            if self.reserve_release.discount_fee_adjustment
            else Decimal(0)
        )
        self.discount_fee = Decimal(discount_fee)

    @property
    def advance_subtotal(self):
        total_charge_to_reserves = (
            self.reserve_release.advance_amount
            if self.reserve_release.advance_amount
            and self.reserve_release.advance_amount is not None
            else Decimal(0)
        )
        return Decimal(total_charge_to_reserves) - (
            self.miscellaneous_adjustment + self.discount_fee
        )
        
    @property
    def disbursement_amount(self):
        # fee_to_client = self.fee_to_client
        # if not self.fee_to_client:
        #     fee_to_client = self.tp_fees + self.wire_fees
        # return Decimal(self.reserve_release.disbursement_amount)
        return Decimal(self.advance_subtotal) - self.fee_to_client

    @property
    def outstanding_amount(self):
        client_payee_total_amount = self.client_amount + self.payee_amount
        return Decimal(self.advance_subtotal) - Decimal(
            client_payee_total_amount + self.fee_to_client
        )

    # @property
    # def disclaimer_text(self):
    #     get_selected_disclaimer = self.reserve_release.get_selected_disclaimer()
    #     get_disclaimer_text = None
        
    #     if (
    #         get_selected_disclaimer
    #         and isinstance(get_selected_disclaimer, list)
    #         and "text" in get_selected_disclaimer[0]
    #         and get_selected_disclaimer[0]["text"]
    #     ):
    #         get_disclaimer_text = get_selected_disclaimer[0]["text"]
        
    #     if (
    #         get_selected_disclaimer
    #         and isinstance(get_selected_disclaimer, dict)
    #         and "text" in get_selected_disclaimer
    #         and get_selected_disclaimer["text"]
    #     ):
    #         get_disclaimer_text = get_selected_disclaimer["text"]
    #     return get_disclaimer_text

    @property
    def client(self):
        get_client = self.reserve_release.client
        client = ClientSchema().dump(get_client).data
        if (
            self.reserve_release_approved_history_attribute
            and "client" in self.reserve_release_approved_history_attribute
            and self.reserve_release_approved_history_attribute["client"]
        ):
            client = self.reserve_release_approved_history_attribute["client"]

        return client

    def get_client_settings(self):
        client_settings = self.reserve_release.rr_client_settings()
        # # get client settings from approval history if reserve release approved
        # if (
        #     self.reserve_release_approved_history_attribute
        #     and "client_settings" in self.reserve_release_approved_history_attribute
        #     and self.reserve_release_approved_history_attribute["client_settings"]
        # ):
        #     client_settings = self.reserve_release_approved_history_attribute[
        #         "client_settings"
        #     ]
        # else:
        #     get_client_settings = ClientSettings.query.filter_by(
        #         client_id=self.client["id"], is_deleted=False
        #     ).first()
        #     if get_client_settings:
        #         client_settings_schema = ClientSettingsSchema()
        #         client_settings = client_settings_schema.dump(get_client_settings).data

        if client_settings:
            self.client_payment_info = {
                "wire": Decimal(client_settings["wire_fee"]),
                "same_day_ach": Decimal(client_settings["same_day_ach_fee"]),
                "high_priority": Decimal(client_settings["high_priority_fee"]),
                "tp": Decimal(client_settings["third_party_fee"]),
            }
            
            # add high_priority to fee_to_client
            if self.reserve_release.high_priority:
                self.fee_to_client += Decimal(self.client_payment_info["high_priority"])

    @property
    def reserve_release_supporting_documents(self):
        reserve_release_supporting_documents = SupportingDocuments.query.filter_by(
            reserve_release_id=self.reserve_release.id, is_deleted=False
        ).all()

        self.column_list = ["id", "soa_id", "url", "notes", "name", "tags", "ext"]
        reserve_release_supporting_document_list = []
        if reserve_release_supporting_documents:
            for (
                reserve_release_supporting_document
            ) in reserve_release_supporting_documents:
                ext = None
                if reserve_release_supporting_document.url:
                    ext = Path(reserve_release_supporting_document.url).suffix
                setattr(reserve_release_supporting_document, "ext", ext)

                reserve_release_supporting_document_list.append(
                    self.obj_to_dict(reserve_release_supporting_document)
                )
        return reserve_release_supporting_document_list

    @property
    def reserve_release_details(self):
        # if not self.fee_to_client:
        #     self.fee_to_client = self.tp_fees + self.wire_fees

        get_reserve_release = {
            "reserve_release": {
                "reserve_release_id": self.reserve_release.id,
                "ref_client_rr_id": f"{self.reserve_release.get_ref_client_rr_id()}",
                "client_id": self.reserve_release.client_id,
                "discount_fee_adjustment": self.reserve_release.discount_fee_adjustment,
                "reason_for_disc_fee_adj": self.reserve_release.reason_for_disc_fee_adj,
                "advance_subtotal": self.advance_subtotal,
                "miscellaneous_adjustment": self.reserve_release.miscellaneous_adjustment,
                "reason_miscellaneous_adj": self.reserve_release.reason_miscellaneous_adj,
                "advance_amount": "{0:,.2f}".format(
                    self.reserve_release.advance_amount
                ),
                "high_priority": self.reserve_release.high_priority,
                "status": self.reserve_release.status.value,
                "reference_number": self.reserve_release.reference_number,
                "has_action_required": self.has_action_required,
            },
            "client_reserve_release_disbursement": self.client_reserve_release_disbursement_list,
            # "client_client_fee": self.client_client_fee,
            # "client_third_party_fee": self.client_third_party_fee,
            "payee_reserve_release_disbursement": self.payee_reserve_release_disbursement_list,
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
            "total_fee_to_client": self.fee_to_client,
            # "disclaimer_text": self.disclaimer_text,
            "reserve_release_created_by": self.reserve_release_created_by,
            "reserve_release_submitted_by": self.reserve_release_submitted_by,
            "reserve_release_approved_by": self.reserve_release_approved_by,
            "reserve_release_completed_by": self.reserve_release_completed_by,
            "client": {
                "name": self.client["name"],
                "ref_client_no": self.client["ref_client_no"],
            },
            "company_name": self.company_name,
            "control_account_name": self.control_account_name,
            "current_time": self.current_time,
            "reserve_release_submitted_at": self.reserve_release_submitted_at,
            "principal_email": self.principal_email,
            "get_reserve_release_supporting_documents": self.reserve_release_supporting_documents,
            "supporting_doc_not_image_ext": self.supporting_doc_not_image_ext,
            "branding_logo_url": self.logo_url,
        }

        return get_reserve_release

    def run_func(self):
        self.get_reserve_release_approvals_history()
        self.get_client_settings()
        self.get_client_reserve_release_disbursements()
        self.get_payee_reserve_release_disbursements()
        self.cal_miscellaneous_adjustment()
        self.cal_discount_fees()

    @property
    def download_pdf(self):
        # Generate file name
        file_name = f"reserve_release_{self.date_time}"

        # Generating PDF
        html = render_template(
            self.html_template, data=self.reserve_release_details
        )
        
        pdf_url = generate_pdf(file_name=file_name, html=html)

        if isinstance(pdf_url, Response):
            return pdf_url

        # Generating zip
        memory_file = BytesIO()
        with ZipFile(memory_file, "w") as zip:
            pdf_download = requests.get(pdf_url)
            zip.writestr(f"{file_name}.pdf", pdf_download.content)
            # Downloading Documents
            if self.reserve_release_supporting_documents:
                for docs in self.reserve_release_supporting_documents:
                    r = requests.get(docs["url"])
                    # get url
                    get_url = docs["url"]
                    filename, file_extension = os.path.splitext(get_url)
                    zip.writestr(docs["name"] + str(file_extension), r.content)
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
