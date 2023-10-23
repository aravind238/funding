from flask import request
import simplejson as json
from src.models import *
from src.resources.v2.schemas import *
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from src.resources.v2.helpers import custom_response
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import or_, and_
from src.resources.v2.helpers.convert_datetime import utc_to_local

soa_schema = SOASchema()
comments_schema = CommentsSchema()
payee_schema = PayeeSchema()
soa_reasons_schema = ReasonsSchema()
disbursements_schema = DisbursementsSchema()
client_schema = ClientSchema()
client_funds_schema = ClientFundSchema()
supporting_documents_schema = SupportingDocumentsSchema()
debtor_schema = DebtorSchema()
client_debtor_schema = ClientDebtorSchema()
participants_schema = ParticipantSchema()
client_settings_schema = ClientSettingsSchema()


class SOADetails:
    
    def __init__(self, soa):
        self.soa = soa
        self.soa_dict = soa_schema.dump(self.soa).data
        self.invoices = []
        self.invoices_debtor_ids = []
        self.soa_submitted_by = {"added_at": None, "user": None}
        self.soa_submitted_by_principal = {"added_at": None, "user": None}
        self.soa_approved_by = {"added_at": None, "user": None}
        self.activity_log = []
        self.submission_activity = []
        self.soa_created_by = None
        self.soa_approved_history = None
        self.soa_approved_history_attribute = None
        self.saved_client = None
        self.saved_client_funds = None
        self.saved_debtors = None
        self.saved_client_debtors = None
        self.saved_participants = None
        self.saved_client_settings = None
        self.soa_invoice_ids = []
        self.has_invoice_debtors = False
        self.has_invoice_approved = False

        self.get_soa_approvals_history()

    @property
    def cal_fee_to_client(self):
        # cal fee to client (lc-1683)
        cal_disbursement_total_fees = self.soa.cal_disbursement_total_fees()
        return cal_disbursement_total_fees

    @property
    def soa_disbursements(self):
        soa_disbursement_objects = Disbursements.query.filter_by(
            soa_id=self.soa.id, is_deleted=False
        )
        soa_disbursement_dict = disbursements_schema.dump(
            soa_disbursement_objects, many=True
        ).data
        for get_soa_disbursement in soa_disbursement_dict:
            # ToDo: Need to be removed from frontend also
            get_soa_disbursement.update({"payee_account": []})
            get_soa_disbursement.update({"payee": []})
            # ToDo: Need to be removed from frontend also
            get_soa_disbursement.update({"client_account_details": []})

            # calculate net amount
            third_party_fee = (
                Decimal(get_soa_disbursement["third_party_fee"])
                if get_soa_disbursement["third_party_fee"] != None
                else Decimal(0)
            )
            client_fee = (
                Decimal(get_soa_disbursement["client_fee"])
                if get_soa_disbursement["client_fee"] != None
                else Decimal(0)
            )
            tp_wire_total = client_fee + third_party_fee
            amount = (
                Decimal(get_soa_disbursement["amount"])
                if get_soa_disbursement["amount"] != None
                else Decimal(0)
            )
            cal_net_amount = amount - tp_wire_total

            net_amount = Decimal("%.2f" % cal_net_amount)

            get_soa_disbursement.update({"net_amount": net_amount})

            if get_soa_disbursement["payee_id"] is not None:
                # get payee
                payee = Payee.query.filter(
                    Payee.id == get_soa_disbursement["payee_id"]
                )
                if self.soa.status.value != "completed":
                    payee = payee.filter(
                        Payee.is_deleted == False
                    )
                payee_object = payee_schema.dump(payee, many=True).data

                # ToDo: Need to be removed from frontend also 'payee_account'
                get_soa_disbursement.update(
                    {"payee_account": [], "payee": payee_object}
                )
                # get client payee
                client_payee = ClientPayee.query.filter(
                    ClientPayee.payee_id == get_soa_disbursement["payee_id"],
                    ClientPayee.client_id == get_soa_disbursement["client_id"],
                )
                if self.soa.status.value != "completed":
                    client_payee = client_payee.filter(
                        ClientPayee.is_deleted == False
                    )
                client_payee = client_payee.first()
                if client_payee:
                    get_soa_disbursement["ref_type"] = client_payee.ref_type.value
                    get_soa_disbursement["payment_status"] = client_payee.payment_status

            if get_soa_disbursement["payee_id"] is None:
                get_soa_disbursement.update({"client_account_details": []})

        return soa_disbursement_dict

    @property
    def client_accounts(self):
        # ToDo: Need to be removed from frontend also
        client_account_objects_dict = []
        return client_account_objects_dict

    @property
    def soa_comments(self):
        soa_comment_objects = Comments.query.filter_by(
            soa_id=self.soa.id, is_deleted=False
        )
        soa_comment_objects_dict = comments_schema.dump(
            soa_comment_objects, many=True
        ).data
        return soa_comment_objects_dict

    @property
    def soa_supporting_documents(self):
        soa_supporting_documents_objects = SupportingDocuments.query.filter_by(
            soa_id=self.soa.id, is_deleted=False
        )
        soa_supporting_documents_objects_dict = supporting_documents_schema.dump(
            soa_supporting_documents_objects, many=True
        ).data
        return soa_supporting_documents_objects_dict

    @property
    def soa_reasons(self):
        reason_objects = (
            ApprovalsHistory.query.filter(
                ApprovalsHistory.soa_id == self.soa.id,
                or_(
                    ApprovalsHistory.key == "rejected_at",
                    ApprovalsHistory.key == "action_required",
                ),
                ApprovalsHistory.is_deleted == False,
            )
            .order_by(ApprovalsHistory.id.desc())
            .all()
        )

        soa_reasons = []
        if reason_objects:
            for soa_reason in reason_objects:
                attribute = soa_reason.attribute

                each_reason = {
                    "id": attribute["id"] if "id" in attribute else None,
                    "user": soa_reason.user,
                    "soa_id": soa_reason.soa_id,
                    "reserve_release_id": soa_reason.reserve_release_id,
                    "lack_of_collateral": attribute["lack_of_collateral"]
                    if "lack_of_collateral" in attribute
                    else False,
                    "unacceptable_collateral": attribute["unacceptable_collateral"]
                    if "unacceptable_collateral" in attribute
                    else False,
                    "invoice_discrepancy": attribute["invoice_discrepancy"]
                    if "invoice_discrepancy" in attribute
                    else False,
                    "no_assignment_stamp": attribute["no_assignment_stamp"]
                    if "no_assignment_stamp" in attribute
                    else False,
                    "pre_billing": attribute["pre_billing"]
                    if "pre_billing" in attribute
                    else False,
                    "client_over_limit": attribute["client_over_limit"]
                    if "client_over_limit" in attribute
                    else False,
                    "confirmation_issue": attribute["confirmation_issue"]
                    if "confirmation_issue" in attribute
                    else False,
                    "others": attribute["others"] if "others" in attribute else False,
                    "notes": attribute["notes"] if "notes" in attribute else None,
                    "status": attribute["status"] if "status" in attribute else None,
                    "created_at": utc_to_local(dt=soa_reason.created_at.isoformat()),
                    "updated_at": utc_to_local(dt=soa_reason.updated_at.isoformat()),
                    "is_deleted": attribute["is_deleted"]
                    if "is_deleted" in attribute
                    else None,
                }
                soa_reasons.append(each_reason)
        return soa_reasons

    @property
    def client(self):
        if self.saved_client:
            client_details = self.saved_client
        else:
            client_details = client_schema.dump(self.soa.client).data
        return client_details

    @property
    def client_funds(self):
        if self.saved_client_funds:
            get_client_funds = self.saved_client_funds
        else:
            get_client_funds = client_funds_schema.dump(
                self.soa.client.client_funds[0]
            ).data
        return get_client_funds

    @property
    def client_settings(self):
        get_client_settings = self.soa.soa_client_settings()
        # if self.saved_client_settings:
        #   get_client_settings = self.saved_client_settings
        # else:
        #   if self.soa.client.client_settings:
        #     get_client_settings = client_settings_schema.dump(
        #       self.soa.client.client_settings[0]
        #     ).data
        return get_client_settings

    @property
    def business_settings_disclaimer(self):
        business_settings = self.soa.get_business_settings_disclaimer()
        return (
            business_settings[0]["text"]
            if business_settings
            and isinstance(business_settings, list)
            and "text" in business_settings[0]
            else None
        )

    @property
    def payees(self):
        payee_objects = self.soa.client.get_payees()
        payee_objects_dict = payee_schema.dump(payee_objects, many=True).data
        for pay in payee_objects_dict:
            # ToDo: Need to be removed from frontend also
            pay.update({"accounts": []})
        return payee_objects_dict

    @property
    def get_invoices(self):
        get_invoice = self.soa.get_all_invoices_details()

        if get_invoice:
            for each_invoice in get_invoice:
                debtor_name = None
                debtor_id = None
                potential_duplicated_debtor = False
                current_ar = float(0)
                credit_limit = float(0)

                # checking to stop multiple loops, if debtor is deleted from debtor/client debtor table
                if each_invoice["id"] not in self.soa_invoice_ids:
                    if each_invoice["debtor"]:
                        self.has_invoice_debtors = True

                    has_client_debtor = False
                    # checking for most recent client debtor based off client id and debtor id, is deleted or not
                    if each_invoice["debtor_is_deleted"] == False:
                        has_client_debtor = ClientDebtor.query.filter(
                            ClientDebtor.is_deleted == False,
                            ClientDebtor.client_id == self.soa.client_id,
                            ClientDebtor.debtor_id == each_invoice["debtor"],
                        ).first()

                    # get debtors and client debtors from db, if invoice's are approved and soa not approved
                    if (
                        (each_invoice["status"] == "approved")
                        and (not self.saved_debtors)
                        and (not self.saved_client_debtors)
                    ):
                        if "debtor" in each_invoice:
                            debtor_id = each_invoice["debtor"]
                        if "debtor_name" in each_invoice:
                            debtor_name = each_invoice["debtor_name"]
                        if "current_ar" in each_invoice:
                            current_ar = each_invoice["current_ar"]
                        if "credit_limit" in each_invoice:
                            credit_limit = each_invoice["credit_limit"]
                        self.has_invoice_approved = True
                    # get debtors and client debtors from db which are not deleted
                    elif each_invoice["debtor_is_deleted"] == False and bool(
                        has_client_debtor
                    ):
                        debtor_id = each_invoice["debtor"]
                        debtor_name = each_invoice["debtor_name"]
                        current_ar = has_client_debtor.current_ar
                        credit_limit = has_client_debtor.credit_limit

                    # get saved debtors from approval history
                    if self.saved_debtors:
                        get_saved_debtor = [
                            debtor
                            for debtor in self.saved_debtors
                            if debtor["id"] == each_invoice["debtor"]
                        ]
                        if get_saved_debtor:
                            debtor_name = get_saved_debtor[0]["name"]

                    # get saved client debtors from approval history
                    if self.saved_client_debtors:
                        get_saved_client_debtor = [
                            client_debtor
                            for client_debtor in self.saved_client_debtors
                            if client_debtor["debtor_id"] == each_invoice["debtor"]
                            and client_debtor["client_id"] == each_invoice["client_id"]
                        ]

                        if get_saved_client_debtor:
                            current_ar = get_saved_client_debtor[0]["current_ar"]
                            credit_limit = get_saved_client_debtor[0]["credit_limit"]

                    get_debtor = Debtor.query.filter(
                        Debtor.is_deleted == False,
                        Debtor.name == debtor_name,
                        Debtor.id != debtor_id,
                    ).count()
                    if get_debtor:
                        potential_duplicated_debtor = True

                    # get invoices of soa from invoice table
                    inv = {
                        "id": each_invoice["id"],
                        "client_id": each_invoice["client_id"],
                        "soa_id": each_invoice["soa_id"],
                        "debtor": debtor_id,
                        "invoice_number": each_invoice["invoice_number"],
                        "invoice_date": each_invoice["invoice_date"],
                        "amount": each_invoice["amount"],
                        "po_number": each_invoice["po_number"],
                        "notes": each_invoice["notes"],
                        "added_by": each_invoice["added_by"],
                        "verified_by": each_invoice["verified_by"],
                        "status": each_invoice["status"],
                        "terms": each_invoice["terms"],
                        "is_credit_insured": each_invoice["is_credit_insured"],
                        "actions": each_invoice["actions"],
                        "is_release_from_reserve": each_invoice[
                            "is_release_from_reserve"
                        ],
                        "created_at": utc_to_local(dt=each_invoice["created_at"]),
                        "updated_at": utc_to_local(dt=each_invoice["updated_at"]),
                        "is_deleted": each_invoice["is_deleted"],
                        "current_ar": current_ar,
                        "credit_limit": credit_limit,
                        "debtor_name": debtor_name,
                        "potential_duplicated_debtor": potential_duplicated_debtor,
                        "invoice_days": each_invoice["invoice_days"],
                    }
                    self.invoices.append(inv)
                    self.soa_invoice_ids.append(each_invoice["id"])
                    # Get debtor id that is not deleted from debtor/client debtor table
                    if debtor_id:
                        self.invoices_debtor_ids.append(debtor_id)

            return self.invoices

    @property
    def control_account_name(self):
        clients_control_account = self.soa.client.clients_control_account
        control_account_name = None
        if clients_control_account is not None:
            control_account_name = clients_control_account[0].control_account.name
        return control_account_name

    def get_soa_approvals_history(self):
        approvals_history = ApprovalsHistory.query.filter_by(soa_id=self.soa.id)

        soa_approvals_history_logs = approvals_history.all()

        if soa_approvals_history_logs:
            submitted_by_client = 0
            submitted_by_principal = 0
            is_request_approved = False
            for each_history in soa_approvals_history_logs:
                history_status = None
                if each_history.key == "action_required":
                    history_status = "AE Action Required to Principal"

                if each_history.key == "action_required_by_client":
                    history_status = "Principal Action Required to Client"

                if each_history.key == "approved_at":
                    history_status = "Approved by AE"
                    is_request_approved = True

                if (
                    self.soa.status.value == "client_draft"
                    or self.soa.status.value == "draft"
                ) and (
                    each_history.key == "client_created_at"
                    or each_history.key == "created_at"
                ):
                    history_status = "Created by"

                if each_history.key == "client_submission_at":
                    history_status = "Submitted by Client"
                    submitted_by_client += 1

                if each_history.key == "funded_at":
                    history_status = "Completed by BO"

                if each_history.key == "submitted_at":
                    history_status = "Submitted by Principal"
                    submitted_by_principal += 1

                if each_history.key == "principal_rejection_at":
                    history_status = "Rejected by Principal"

                if each_history.key == "rejected_at":
                    history_status = "Rejected by AE"

                if each_history.key == "reviewed_at":
                    history_status = "Submitted for approval by AE"

                if each_history.key == "updated_at":
                    history_status = "Updated by AE"

                if (
                    submitted_by_client > 1
                    and each_history.key == "client_submission_at"
                ):
                    history_status = "Resubmitted by Client"

                if submitted_by_principal > 1 and each_history.key == "submitted_at":
                    history_status = "Resubmitted by Principal"

                # if soa request completed by AE
                if each_history.key == "funded_at" and not is_request_approved:
                    history_status = "Completed by AE"

                # submission activity
                if history_status and each_history.key in [
                    "client_created_at",
                    "created_at",
                    "client_submission_at",
                    "submitted_at",
                    "approved_at",
                    "funded_at",
                ]:
                    # not to add resubmitted request
                    if history_status not in [
                        "Resubmitted by Client",
                        "Resubmitted by Principal",
                    ]:
                        self.submission_activity.append(
                            {
                                "added_at": utc_to_local(
                                    dt=each_history.created_at.isoformat()
                                ),
                                "description": history_status,
                                "user": each_history.user,
                            }
                        )

                # activity log
                if (
                    each_history.key == "client_created_at"
                    or each_history.key == "created_at"
                ):
                    history_status = "Created by"
                    self.soa_created_by = each_history.user

                if history_status:
                    self.activity_log.append(
                        {
                            "added_at": utc_to_local(
                                dt=each_history.created_at.isoformat()
                            ),
                            "description": history_status,
                            "user": each_history.user,
                        }
                    )

                if (
                    each_history.key == "client_submission_at"
                    or each_history.key == "submitted_at"
                ):
                    # request submitted by client/principal for soa step-2
                    if (
                        submitted_by_client == 1
                        and submitted_by_principal == 0
                        or submitted_by_client == 0
                        and submitted_by_principal == 1
                    ):
                        self.soa_submitted_by = {
                            "added_at": utc_to_local(
                                dt=each_history.created_at.isoformat()
                            ),
                            "user": each_history.user,
                        }

                    # latest request submitted by principal for view details(process button)
                    if submitted_by_principal >= 1:
                        self.soa_submitted_by_principal = {
                            "added_at": utc_to_local(
                                dt=each_history.created_at.isoformat()
                            ),
                            "user": each_history.user,
                        }

        # Need documents approval history for documents activity logs LC-2313
        documents_approval_history = approvals_history.join(SOA).filter(
            ApprovalsHistory.key.in_(
                [
                    "bo_uploaded_document_at", 
                    "bo_deleted_document_at"
                ]
            ),
            SOA.status == "completed"
        ).all()

        if documents_approval_history:
            for each_document_history in documents_approval_history:
                document_history_status = None

                if each_document_history.key == "bo_uploaded_document_at":
                    document_history_status = "File uploaded by BO"

                if each_document_history.key == "bo_deleted_document_at":
                    document_history_status = "File deleted by BO"

                # activity log
                if document_history_status:
                    self.activity_log.append(
                        {   
                            "added_at": utc_to_local(
                                dt=each_document_history.created_at.isoformat()
                            ),
                            "description": document_history_status,
                            "user": each_document_history.user,
                        }
                    )

        # Need approvals history in desc for latest info
        approvals_history = approvals_history.order_by(ApprovalsHistory.id.desc())

        # request approved by ae
        request_approved = approvals_history.filter(
            ApprovalsHistory.key == "approved_at", ApprovalsHistory.is_deleted == False
        ).first()

        if request_approved:
            # Needed latest request approved by AE for BO view details(process button)
            self.soa_approved_by = {
                "added_at": utc_to_local(dt=request_approved.created_at.isoformat()),
                "user": request_approved.user,
            }

        # request completed by bo
        request_completed = approvals_history.filter(
            ApprovalsHistory.key == "funded_at", ApprovalsHistory.is_deleted == False
        ).first()

        if self.soa.status.value == "approved":
            self.soa_approved_history = request_approved

        if self.soa.status.value == "completed":
            self.soa_approved_history = request_completed

        # when soa is approved or completed(LC-1120)
        if self.soa_approved_history and self.soa_approved_history.key in [
            "approved_at",
            "funded_at",
        ]:
            if isinstance(self.soa_approved_history.attribute, str):
                self.soa_approved_history_attribute = json.loads(
                    self.soa_approved_history.attribute
                )
            else:
                self.soa_approved_history_attribute = (
                    self.soa_approved_history.attribute
                )

            # get saved client
            if (
                self.soa_approved_history_attribute
                and "client" in self.soa_approved_history_attribute
                and self.soa_approved_history_attribute["client"] is not None
            ):
                self.saved_client = self.soa_approved_history_attribute["client"]

            # get saved client funds
            if (
                self.soa_approved_history_attribute
                and "client_funds" in self.soa_approved_history_attribute
                and self.soa_approved_history_attribute["client_funds"] is not None
            ):
                self.saved_client_funds = self.soa_approved_history_attribute[
                    "client_funds"
                ]

            # get saved debtors
            if (
                self.soa_approved_history_attribute
                and "debtors" in self.soa_approved_history_attribute
                and self.soa_approved_history_attribute["debtors"] is not None
            ):
                self.saved_debtors = self.soa_approved_history_attribute["debtors"]

            # get saved client debtors
            if (
                self.soa_approved_history_attribute
                and "client_debtors" in self.soa_approved_history_attribute
                and self.soa_approved_history_attribute["client_debtors"] is not None
            ):
                self.saved_client_debtors = self.soa_approved_history_attribute[
                    "client_debtors"
                ]

            # get saved participants
            if (
                self.soa_approved_history_attribute
                and "participants" in self.soa_approved_history_attribute
                and self.soa_approved_history_attribute["participants"] is not None
            ):
                self.saved_participants = self.soa_approved_history_attribute[
                    "participants"
                ]

            # get saved client settings
            if (
                self.soa_approved_history_attribute
                and "client_settings" in self.soa_approved_history_attribute
                and self.soa_approved_history_attribute["client_settings"]
            ):
                self.saved_client_settings = self.soa_approved_history_attribute[
                    "client_settings"
                ]

    @property
    def debtors(self):
        debtor_dict = []
        if self.saved_debtors:
            debtor_dict = self.saved_debtors
        else:
            if (not self.invoices_debtor_ids) and (not self.has_invoice_debtors):
                self.get_invoices

            if self.invoices_debtor_ids:
                for invoice_debtor_id in self.invoices_debtor_ids:
                    if self.has_invoice_approved and (not self.saved_debtors):
                        get_debtor = Debtor.query.filter(
                            Debtor.id == invoice_debtor_id
                        ).first()
                    else:
                        get_debtor = Debtor.query.filter(
                            Debtor.is_deleted == False, Debtor.id == invoice_debtor_id
                        ).first()
                    debtor = debtor_schema.dump(get_debtor).data
                    if debtor not in debtor_dict:
                        debtor_dict.append(debtor)
        return debtor_dict

    @property
    def client_debtors(self):
        if self.saved_client_debtors:
            client_debtor_dict = self.saved_client_debtors
        else:
            if (not self.invoices_debtor_ids) and (not self.has_invoice_debtors):
                self.get_invoices

            if self.has_invoice_approved and (not self.saved_client_debtors):
                get_client_debtor = ClientDebtor.query.filter(
                    ClientDebtor.client_id == self.soa.client_id,
                    ClientDebtor.debtor_id.in_(self.invoices_debtor_ids),
                )
            else:
                get_client_debtor = ClientDebtor.query.filter(
                    ClientDebtor.is_deleted == False,
                    ClientDebtor.client_id == self.soa.client_id,
                    ClientDebtor.debtor_id.in_(self.invoices_debtor_ids),
                )
            client_debtor_dict = client_debtor_schema.dump(
                get_client_debtor, many=True
            ).data
        return client_debtor_dict

    @property
    def participants(self):
        if self.saved_participants:
            participants_dict = self.saved_participants
        else:
            participants_obj = (
                Participant.query.join(ClientParticipant, Client)
                .filter(
                    Participant.id == ClientParticipant.participant_id,
                    Participant.is_deleted == False,
                    ClientParticipant.client_id == Client.id,
                    Client.id == self.soa.client_id,
                )
                .all()
            )

            participants_dict = participants_schema.dump(
                participants_obj, many=True
            ).data
        return participants_dict

    def get(self):
        self.soa_dict.update(
            {
                "total_fee_to_client": self.cal_fee_to_client["total_fee_to_client"],
                "soa_disbursement": self.soa_disbursements,
                "invoice": self.get_invoices,
                "client_account": self.client_accounts,
                "soa_comments": self.soa_comments,
                "payee": self.payees,
                "soa_reason": self.soa_reasons,
                "ref_client_details": {
                    "name": self.client["name"],
                    "ref_client_no": self.client["ref_client_no"],
                },
                "soa_submitted_by": self.soa_submitted_by,
                "soa_submitted_by_principal": self.soa_submitted_by_principal,
                "soa_approved": self.soa_approved_by,
                "soa_attachments": self.soa_supporting_documents,
                "debtor": self.debtors,
                "preview_debt_collector": [],
                "client_debtor": self.client_debtors,
                "control_account": self.control_account_name,
                "created_by": self.soa_created_by,
                "participants": self.participants,
                "client_funds": self.client_funds,
                "client_settings": self.client_settings,
                "business_settings_disclaimer": self.business_settings_disclaimer,
                "activity_log": self.activity_log,
                "submission_activity": self.submission_activity,
            }
        )
        return self.soa_dict
