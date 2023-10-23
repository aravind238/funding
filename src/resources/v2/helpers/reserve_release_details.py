import simplejson as json
from src.models import *
from src.resources.v2.schemas import *
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from decimal import Decimal
from sqlalchemy import or_, and_
from src.resources.v2.helpers.convert_datetime import utc_to_local

reserve_release_schema = ReserveReleaseSchema()
comments_schema = CommentsSchema()
payee_schema = PayeeSchema()
reasons_schema = ReasonsSchema()
disbursements_schema = DisbursementsSchema()
client_schema = ClientSchema()
supporting_documents_schema = SupportingDocumentsSchema()
reserve_release_disbursements_schema = ReserveReleaseDisbursementsSchema()
approvals_history_schema = ApprovalsHistorySchema()
client_funds_schema = ClientFundSchema()
client_settings_schema = ClientSettingsSchema()


class ReserveReleaseDetails:
    
    def __init__(self, reserve_release):
        self.reserve_release = reserve_release
        self.reserve_release_dict = reserve_release_schema.dump(
            self.reserve_release
        ).data
        self.rr_submitted_by_principal = {"added_at": None, "user": None}
        self.rr_approved_by = {"added_at": None, "user": None}
        self.activity_log = []
        self.submission_activity = []
        self.reserve_release_created_by = None
        self.reserve_release_approved_history = None
        self.reserve_release_approved_history_attribute = None
        self.saved_client = None
        self.saved_client_funds = None
        self.saved_client_settings = None

        self.get_rr_approvals_history()

    def get_rr_approvals_history(self):
        approvals_history = ApprovalsHistory.query.filter_by(
            reserve_release_id=self.reserve_release.id
        )

        rr_approvals_history_logs = approvals_history.all()

        if rr_approvals_history_logs:
            submitted_by_client = 0
            submitted_by_principal = 0
            for each_history in rr_approvals_history_logs:
                history_status = None
                if each_history.key == "action_required":
                    history_status = "AE Action Required to Principal"

                if each_history.key == "action_required_by_client":
                    history_status = "Principal Action Required to Client"

                if each_history.key == "approved_at":
                    history_status = "Approved by AE"

                if (
                    (
                        self.reserve_release.status.value == "client_draft"
                        or self.reserve_release.status.value == "draft"
                    )
                    and (
                        each_history.key == "client_created_at"
                        or each_history.key == "created_at"
                    )
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

                if (
                    submitted_by_principal > 1 
                    and each_history.key == "submitted_at"
                ):
                    history_status = "Resubmitted by Principal"

                if (
                    submitted_by_principal > 1 
                    and each_history.key == "submitted_at"
                ):
                    history_status = "Resubmitted by Principal"

                # submission activity
                if (
                    history_status
                    and each_history.key in [
                        "client_created_at",
                        "created_at",
                        "client_submission_at",
                        "submitted_at",
                        "approved_at",
                        "funded_at",
                    ]
                ):
                    # not to add resubmitted request
                    if (
                        history_status not in [
                            "Resubmitted by Client", 
                            "Resubmitted by Principal"
                        ]
                    ):
                        self.submission_activity.append(
                            {
                            "added_at": utc_to_local(dt=each_history.created_at.isoformat()),
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
                    self.reserve_release_created_by = each_history.user

                if history_status:
                    self.activity_log.append(
                        {
                            "added_at": utc_to_local(dt=each_history.created_at.isoformat()),
                            "description": history_status,
                            "user": each_history.user,
                        }
                    )

                if (
                    each_history.key == "client_submission_at"
                    or each_history.key == "submitted_at"
                ):                
                    # latest request submitted by principal for view details(process button)
                    if (
                        submitted_by_principal >= 1
                    ):
                        self.rr_submitted_by_principal = {
                            "added_at": utc_to_local(dt=each_history.created_at.isoformat()),
                            "user": each_history.user,
                        }

        # Need documents approval history for documents activity logs LC-2313
        documents_approval_history = approvals_history.join(ReserveRelease).filter(
            ApprovalsHistory.key.in_(
                [
                    "bo_uploaded_document_at", 
                    "bo_deleted_document_at"
                ]
            ),
            ReserveRelease.status == "completed"
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

        approvals_history = approvals_history.order_by(ApprovalsHistory.id.desc())
        
        # request approved by ae
        request_approved = approvals_history.filter(
            ApprovalsHistory.key == "approved_at", 
            ApprovalsHistory.is_deleted == False
        ).first()

        if request_approved:
            # Needed latest request approved by AE for BO view details(process button)
            self.rr_approved_by = {
                "added_at": utc_to_local(dt=request_approved.created_at.isoformat()),
                "user": request_approved.user,
            }

        # request completed by bo
        request_completed = approvals_history.filter(
            ApprovalsHistory.key == "funded_at", 
            ApprovalsHistory.is_deleted == False
        ).first()

        if self.reserve_release.status.value == "approved":
            self.reserve_release_approved_history = request_approved

        if self.reserve_release.status.value == "completed":
            self.reserve_release_approved_history = request_completed

        # when reserve_release is approved or completed(LC-1120)
        if (
            self.reserve_release_approved_history
            and self.reserve_release_approved_history.key
            in ["approved_at", "funded_at"]
        ):
            if isinstance(self.reserve_release_approved_history.attribute, str):
                self.reserve_release_approved_history_attribute = json.loads(
                    self.reserve_release_approved_history.attribute
                )
            else:
                self.reserve_release_approved_history_attribute = (
                    self.reserve_release_approved_history.attribute
                )

        # saved client
        if (
            self.reserve_release_approved_history_attribute
            and "client" in self.reserve_release_approved_history_attribute
            and self.reserve_release_approved_history_attribute["client"] is not None
        ):
            self.saved_client = self.reserve_release_approved_history_attribute[
                "client"
            ]

        # saved client funds
        if (
            self.reserve_release_approved_history_attribute
            and "client_funds" in self.reserve_release_approved_history_attribute
            and self.reserve_release_approved_history_attribute["client_funds"]
        ):
            self.saved_client_funds = self.reserve_release_approved_history_attribute[
                "client_funds"
            ]

        # saved client settings
        if (
            self.reserve_release_approved_history_attribute
            and "client_settings" in self.reserve_release_approved_history_attribute
            and self.reserve_release_approved_history_attribute["client_settings"]
        ):
            self.saved_client_settings = self.reserve_release_approved_history_attribute[
                "client_settings"
            ]
        

    @property
    def reserve_release_disburesments(self):
        disbursement_objects = (
            Disbursements.query.join(ReserveReleaseDisbursements)
            .filter(
                Disbursements.is_deleted == False,
                ReserveReleaseDisbursements.reserve_release_id
                == self.reserve_release.id,
            )
            .all()
        )
        disbursement_dict = disbursements_schema.dump(
            disbursement_objects, many=True
        ).data

        for get_disbursement in disbursement_dict:
            # ToDo: Need to be removed from frontend also
            get_disbursement.update({"payee_account": []})
            get_disbursement.update({"payee": []})
            # ToDo: Need to be removed from frontend also
            get_disbursement.update({"client_account_details": []})

            # cal net amount
            third_party_fee = (
                Decimal(get_disbursement["third_party_fee"])
                if get_disbursement["third_party_fee"] != None
                else Decimal(0)
            )
            client_fee = (
                Decimal(get_disbursement["client_fee"])
                if get_disbursement["client_fee"] != None
                else Decimal(0)
            )
            tp_wire_total = client_fee + third_party_fee
            amount = (
                Decimal(get_disbursement["amount"])
                if get_disbursement["amount"] != None
                else Decimal(0)
            )
            cal_net_amount = amount - tp_wire_total

            net_amount = Decimal("%.2f" % cal_net_amount)

            get_disbursement.update({"net_amount": net_amount})

            if get_disbursement["payee_id"] is not None:

                # get payee
                payee = Payee.query.filter(
                    Payee.id == get_disbursement["payee_id"]
                )
                if self.reserve_release.status.value != "completed":
                    payee = payee.filter(
                        Payee.is_deleted == False
                    )
                payee_object = payee_schema.dump(payee, many=True).data
                
                # get client payee
                client_payee = ClientPayee.query.filter(
                    ClientPayee.payee_id == get_disbursement["payee_id"],
                    ClientPayee.client_id == get_disbursement["client_id"],
                )
                if self.reserve_release.status.value != "completed":
                    client_payee = client_payee.filter(
                        ClientPayee.is_deleted == False
                    )
                client_payee = client_payee.first()
                if client_payee:
                    get_disbursement["ref_type"] = client_payee.ref_type.value
                    get_disbursement["payment_status"] = client_payee.payment_status

                # ToDo: Need to be removed from frontend also
                get_disbursement.update({"payee_account": []})
                get_disbursement.update({"payee": payee_object})

            if get_disbursement["payee_id"] is None:
                # ToDo: Need to be removed from frontend also
                get_disbursement.update({"client_account_details": []})

        return disbursement_dict

    @property
    def client_accounts(self):
        # ToDo: Need to be removed from frontend also
        return []

    @property
    def payees(self):
        payee_objects = self.reserve_release.client.get_payees()
        payee_objects_dict = payee_schema.dump(payee_objects, many=True).data

        for pay in payee_objects_dict:
            # ToDo: Need to be removed from frontend also
            pay.update({"accounts": []})
        return payee_objects_dict

    @property
    def reserve_release_reasons(self):
        reason_objects = (
            ApprovalsHistory.query.filter(
                ApprovalsHistory.reserve_release_id == self.reserve_release.id,
                or_(
                    ApprovalsHistory.key == "rejected_at",
                    ApprovalsHistory.key == "action_required",
                ),
                ApprovalsHistory.is_deleted == False,
            )
            .order_by(ApprovalsHistory.id.desc())
            .all()
        )

        rr_reasons = []
        if reason_objects:
            for rr_reason in reason_objects:
                attribute = rr_reason.attribute

                each_reason = {
                    "id": attribute["id"] if "id" in attribute else None,
                    "user": rr_reason.user,
                    "soa_id": rr_reason.soa_id,
                    "reserve_release_id": rr_reason.reserve_release_id,
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
                    "created_at": utc_to_local(dt=attribute["created_at"])
                    if "created_at" in attribute
                    else None,
                    "updated_at": utc_to_local(dt=attribute["updated_at"])
                    if "updated_at" in attribute
                    else None,
                    "is_deleted": attribute["is_deleted"]
                    if "is_deleted" in attribute
                    else None,
                }
                rr_reasons.append(each_reason)
        return rr_reasons

    @property
    def reserve_release_comments(self):
        comment_objects = Comments.query.filter_by(
            reserve_release_id=self.reserve_release.id, is_deleted=False
        )
        comment_objects_dict = comments_schema.dump(comment_objects, many=True).data
        return comment_objects_dict

    @property
    def reserve_release_supporting_documents(self):
        supporting_documents_objects = SupportingDocuments.query.filter_by(
            reserve_release_id=self.reserve_release.id, is_deleted=False
        )
        supporting_documents_objects_dict = supporting_documents_schema.dump(
            supporting_documents_objects, many=True
        ).data
        return supporting_documents_objects_dict

    @property
    def control_account_name(self):
        clients_control_account_list = (
            self.reserve_release.client.clients_control_account
        )
        control_account_name = None
        if clients_control_account_list:
            control_account_name = clients_control_account_list[0].control_account.name
        return control_account_name

    @property
    def client(self):
        if self.saved_client:
            client_details = self.saved_client
        else:
            client_details_obj = Client.query.filter_by(
                id=self.reserve_release.client_id, is_deleted=False
            ).first()
            client_details = client_schema.dump(client_details_obj).data
        return client_details

    @property
    def client_settings(self):
        get_client_settings = self.reserve_release.rr_client_settings()
        # if self.saved_client_settings:
        #     get_client_settings = self.saved_client_settings
        # else:
        #     if self.reserve_release.client.client_settings:
        #         get_client_settings = client_settings_schema.dump(
        #             self.reserve_release.client.client_settings[0]
        #         ).data
        return get_client_settings
    
    @property
    def business_settings_disclaimer(self):
        business_settings = self.reserve_release.get_business_settings_disclaimer()
        return (
            business_settings[0]["text"]
            if business_settings
            and isinstance(business_settings, list)
            and "text" in business_settings[0]
            else None
        )

    @property
    def client_funds(self):
        get_client_funds = {}
        if self.saved_client_funds:
            get_client_funds = self.saved_client_funds
        else:
            if self.reserve_release.client.client_funds:
                get_client_funds = client_funds_schema.dump(
                    self.reserve_release.client.client_funds[0]
                ).data
        return get_client_funds

    @property
    def cal_fee_to_client(self):
        # cal fee to client (lc-1683)
        cal_disbursement_total_fees = self.reserve_release.cal_disbursement_total_fees()
        return cal_disbursement_total_fees

    def get(self):
        self.reserve_release_dict.update(
            {
                "total_fee_to_client": self.cal_fee_to_client["total_fee_to_client"],
                "disbursement": self.reserve_release_disburesments,
                "client_account": self.client_accounts,
                "comments": self.reserve_release_comments,
                "payee": self.payees,
                "reason": self.reserve_release_reasons,
                "client": self.client,
                "attachments": self.reserve_release_supporting_documents,
                "created_by": self.reserve_release_created_by,
                "reserve_release_submitted_by_principal": self.rr_submitted_by_principal,
                "reserve_release_approved": self.rr_approved_by,
                "control_account": self.control_account_name,
                "activity_log": self.activity_log,
                "submission_activity": self.submission_activity,
                "client_funds": self.client_funds,
                "client_settings": self.client_settings,
                "business_settings_disclaimer": self.business_settings_disclaimer,
            }
        )
        return self.reserve_release_dict
