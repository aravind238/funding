# from src.resources.v2.schemas import client_settings_schema
from src import db
from flask import abort, json
import enum
import math
from datetime import date, datetime, timedelta
from sqlalchemy import cast, Date, and_, or_, func, not_, DateTime
from src.middleware.organization import Organization
from decimal import Decimal
from src.middleware.permissions import Permissions


class ReserveReleaseStatus(enum.Enum):
    action_required = "action_required"
    action_required_by_client = "action_required_by_client"
    approved = "approved"
    client_draft = "client_draft"
    client_submission = "client_submission"
    completed = "completed"
    draft = "draft"
    pending = "pending"
    principal_rejection = "principal_rejection"
    rejected = "rejected"
    reviewed = "reviewed"
    submitted = "submitted"


# ReserveRelease model
class ReserveRelease(db.Model):
    __tablename__ = "reserve_release"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    ref_id = db.Column(db.Integer, nullable=True, default=0)
    reference_number = db.Column(db.String(255), nullable=True)
    advance_amount = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    discount_fee_adjustment = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    reason_for_disc_fee_adj = db.Column(db.String(255), nullable=True)
    miscellaneous_adjustment = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    reason_miscellaneous_adj = db.Column(db.Text, nullable=True)
    disbursement_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    disclaimer_id = db.Column(
        db.Integer, db.ForeignKey("disclaimers.id", ondelete="CASCADE"), nullable=True
    )
    status = db.Column(
        db.Enum(ReserveReleaseStatus), default=ReserveReleaseStatus.draft.value
    )
    high_priority = db.Column(db.Boolean, default=False)
    last_processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    deleted_at = db.Column(db.DateTime)

    approvals_history = db.relationship("ApprovalsHistory", backref="reserve_release")
    
    # Indexes
    __table_args__ = (
        db.Index("idx_ref_id", "ref_id"),
    )

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.ref_id = data.get("ref_id")
        self.reference_number = data.get("reference_number")
        self.status = data.get("status")
        self.advance_amount = data.get("advance_amount")
        self.discount_fee_adjustment = data.get("discount_fee_adjustment")
        self.reason_for_disc_fee_adj = data.get("reason_for_disc_fee_adj")
        self.miscellaneous_adjustment = data.get("miscellaneous_adjustment")
        self.reason_miscellaneous_adj = data.get("reason_miscellaneous_adj")
        self.disbursement_amount = data.get("disbursement_amount")
        self.disclaimer_id = data.get("disclaimer_id")
        self.high_priority = data.get("high_priority")
        self.last_processed_at = data.get("last_processed_at")
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def update(self, data):
        for key, item in data.items():
            setattr(self, key, item)
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def get_all_reserve_release():
        return ReserveRelease.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_reserve_release(id):
        return ReserveRelease.query.filter_by(id=id, is_deleted=False).first()

    @staticmethod
    def get_one_based_off_control_accounts(id):        
        from src.models import (
            Client,
            ClientControlAccounts, 
            ControlAccount
        )

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        return (
            ReserveRelease.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                ReserveRelease.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                Client.is_deleted == False,
                ReserveRelease.id == id,
                ControlAccount.name.in_(business_control_accounts),
            )
            .first()
        )

    def get_ref_client_rr_id(self):
        ref_client_no = self.client.ref_client_no if self.client else None
        ref_client_rr_id = f"{ref_client_no}-RRID{self.ref_id}"
        return ref_client_rr_id

    def had_action_required(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            reserve_release_id=self.id, key="action_required", is_deleted=False
        ).count()

    def had_client_submitted(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            reserve_release_id=self.id, key="client_submission_at", is_deleted=False
        ).count()

    def object_as_string(self):
        return "Reserve Release"

    def request_created_by_client(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            reserve_release_id=self.id, key="client_created_at", is_deleted=False
        ).first()

    def request_submitted_by_client(self):
        from src.models import ApprovalsHistory

        return (
            ApprovalsHistory.query.filter_by(
                reserve_release_id=self.id, key="client_submission_at", is_deleted=False
            )
            .order_by(ApprovalsHistory.id.desc())
            .first()
        )

    def request_created_by_principal(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            reserve_release_id=self.id, key="created_at", is_deleted=False
        ).first()

    def request_submitted_by_principal(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            reserve_release_id=self.id, key="submitted_at", is_deleted=False
        ).first()

    def request_approved_by_ae(self):
        from src.models import ApprovalsHistory

        return (
            ApprovalsHistory.query.filter_by(
                reserve_release_id=self.id, key="approved_at", is_deleted=False
            )
            .order_by(ApprovalsHistory.id.desc())
            .first()
        )

    def request_approved_by_bo(self):
        from src.models import ApprovalsHistory

        return (
            ApprovalsHistory.query.filter_by(
                reserve_release_id=self.id, key="funded_at", is_deleted=False
            )
            .order_by(ApprovalsHistory.id.desc())
            .first()
        )

    def is_request_updated(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            reserve_release_id=self.id, key="updated_at", is_deleted=False
        ).count()

    def get_disbursements_payment_type(self):
        """
        related to card LC-1594
        """
        from src.models import Disbursements, ReserveReleaseDisbursements, ClientPayee

        return (
            db.session.query(Disbursements.payment_method, ClientPayee.payment_status)
            .join(ClientPayee, ClientPayee.payee_id == Disbursements.payee_id)
            .join(ReserveReleaseDisbursements)
            .filter(
                ReserveReleaseDisbursements.reserve_release_id == self.id,
                Disbursements.is_deleted == False,
                Disbursements.payee_id != None,
            )
            .distinct()
            .all()
        )

    def cal_disbursement_total_fees(self):
        """
        Using in reserve release update
        """
        from src.models import (
            Disbursements,
            ReserveReleaseDisbursements,
            Client,
            ClientSettings,
            ClientPayee,
        )

        fee_to_client = Decimal(0)
        high_priority_fee = Decimal(0)
        same_day_ach_fee = Decimal(0)
        wire_fee = Decimal(0)
        third_party_fee = Decimal(0)

        has_client_settings = False
        total_client_fees = Decimal(0)
        third_party_fee_total = Decimal(0)
        client_fee_total = Decimal(0)
        total_fees_asap = Decimal(0)  # for lcra export
        total_amount = Decimal(0)
        high_priority_amount = Decimal(0)
        asap_amount = Decimal(0)  # for outstanding amount cal

        get_payees = []

        # # checking, reserve release is approved/completed
        # if self.status.value == "approved":
        #     rr_approved = self.request_approved_by_ae()
        # elif self.status.value == "completed":
        #     rr_approved = self.request_approved_by_bo()
        # else:
        #     rr_approved = {}

        # client_settings = {}
        # has_client_settings = False
        # # get reserve release approval history
        # if rr_approved:
        #     if isinstance(rr_approved.attribute, str):
        #         rr_approved_attribute = json.loads(rr_approved.attribute)
        #     else:
        #         rr_approved_attribute = rr_approved.attribute

        #     # get saved client settings
        #     if (
        #         rr_approved_attribute
        #         and "client_settings" in rr_approved_attribute
        #         and rr_approved_attribute["client_settings"]
        #     ):
        #         client_settings = rr_approved_attribute["client_settings"]
        #         high_priority_fee = Decimal(client_settings["high_priority_fee"])
        #         same_day_ach_fee = Decimal(client_settings["same_day_ach_fee"])
        #         wire_fee = Decimal(client_settings["wire_fee"])
        #         third_party_fee = Decimal(client_settings["third_party_fee"])
        #         has_client_settings = True
        #         high_priority_amount = Decimal(client_settings["high_priority_fee"])

        # if not client_settings and not rr_approved:
        #     # get client settings
        #     client_settings = ClientSettings.query.filter_by(
        #         client_id=self.client.id, is_deleted=False
        #     ).first()

        client_settings = self.rr_client_settings()

        # client settings in table
        if client_settings:
            high_priority_fee = Decimal(client_settings["high_priority_fee"])
            same_day_ach_fee = Decimal(client_settings["same_day_ach_fee"])
            wire_fee = Decimal(client_settings["wire_fee"])
            third_party_fee = Decimal(client_settings["third_party_fee"])
            has_client_settings = True
            high_priority_amount = Decimal(client_settings["high_priority_fee"])

        # add high_priority to fee_to_client
        if self.high_priority:
            fee_to_client += high_priority_fee
            total_fees_asap += high_priority_fee
            asap_amount = high_priority_fee

            # # if no client settings then add principal's high priority fee
            # if not has_client_settings:
            #     from src.resources.v2.helpers.helper import principal_settings

            #     fee_to_client += principal_settings()["high_priority_fee"]
            #     total_fees_asap += principal_settings()["high_priority_fee"]
            #     high_priority_amount = principal_settings()["high_priority_fee"]

        # get total client fees
        total_client_fees = Decimal(0)
        third_party_fee_total = Decimal(0)
        client_fee_total = Decimal(0)

        # Reserve Release disbursements
        get_rr_disbursements = Disbursements.query.join(
            ReserveReleaseDisbursements
        ).filter(
            ReserveReleaseDisbursements.reserve_release_id == self.id,
            ReserveReleaseDisbursements.is_deleted == False,
            Disbursements.is_deleted == False,
            Client.id == Disbursements.client_id,
            ClientPayee.client_id == Client.id,
            ClientPayee.payee_id == Disbursements.payee_id,
        )

        ## Disbursement: client as payee ##
        get_client_fees = get_rr_disbursements.filter(
            ClientPayee.ref_type == "client",
        ).all()
        if get_client_fees:
            for client_fees in get_client_fees:
                # get payees
                get_payees.append(client_fees.payee.id)

                # fee_to_client
                if client_fees.payment_method.value == "wire":
                    fee_to_client += wire_fee

                if client_fees.payment_method.value == "same_day_ach":
                    fee_to_client += same_day_ach_fee

                third_party_fee_total += (
                    Decimal(client_fees.third_party_fee)
                    if client_fees.third_party_fee is not None
                    else Decimal(0)
                )
                client_fee_total += (
                    Decimal(client_fees.client_fee)
                    if client_fees.client_fee is not None
                    else Decimal(0)
                )

                # cal total amount of client as payee
                total_amount += Decimal(client_fees.amount)

        total_client_fees = (
            third_party_fee_total + client_fee_total
        )

        # cal total fee to client(LC-1695) for lcra export
        total_fees_asap += client_fee_total

        # get total payee fees
        total_payee_fees = Decimal(0)
        third_party_fee_total = Decimal(0)
        client_fee_total = Decimal(0)

        ## Disbursement: Third party as payee  ##
        get_payee_fees = get_rr_disbursements.filter(
            ClientPayee.ref_type == "payee",
        ).all()
        if get_payee_fees:
            for payee_fees in get_payee_fees:
                # get payees
                get_payees.append(payee_fees.payee.id)

                # fee_to_client
                if payee_fees.payment_method.value == "wire":
                    fee_to_client += wire_fee
                    fee_to_client += third_party_fee

                if payee_fees.payment_method.value == "same_day_ach":
                    fee_to_client += same_day_ach_fee
                    fee_to_client += third_party_fee

                if payee_fees.payment_method.value == "direct_deposit":
                    fee_to_client += third_party_fee

                third_party_fee_total += (
                    Decimal(payee_fees.third_party_fee)
                    if payee_fees.third_party_fee is not None
                    else Decimal(0)
                )
                client_fee_total += (
                    Decimal(payee_fees.client_fee)
                    if payee_fees.client_fee is not None
                    else Decimal(0)
                )

                # cal total amount of third party as payee
                total_amount += Decimal(payee_fees.amount)

        total_payee_fees = (
            third_party_fee_total + client_fee_total
        )

        # cal total fee to client(LC-1695) for lcra export
        total_fees_asap += third_party_fee_total + client_fee_total

        advance_subtotal = (
            Decimal(self.advance_amount)
            - Decimal(self.discount_fee_adjustment)
            - Decimal(self.miscellaneous_adjustment)
        )

        # cal disbursement amount
        disbursement_amount = advance_subtotal - total_fees_asap

        # cal outstanding amount
        outstanding_amount = advance_subtotal - Decimal(
            total_amount + asap_amount
        )

        return {
            "total_fee_to_client": Decimal(fee_to_client),
            "total_fees_asap": Decimal(total_fees_asap),  # for lcra export
            "payee_ids": get_payees,
            "advance_subtotal": Decimal(advance_subtotal), # for reserve release cal
            "disbursement_amount": Decimal(disbursement_amount),
            "outstanding_amount": Decimal(outstanding_amount),
            "high_priority_amount": Decimal(high_priority_amount),
        }

    def get_selected_disclaimer(self):
        """
        Get disclaimer selected by user
        """
        has_disclaimer = False
        disclaimers_data = {}
        client_settings = {}

        if self.status.value not in ["client_draft", "client_submission", "draft"]:
            disclaimers_data = self.get_saved_disclaimer()
            if disclaimers_data:
                has_disclaimer = True
        
        # checking, if has client settings
        if not has_disclaimer:
            client_settings = self.get_client_settings_disclaimer()
            # checking, if client settings has disclaimer_text
            if (
                client_settings
                and "text" in client_settings[0]
                and client_settings[0]["text"]
            ):
                disclaimers_data.update(
                    {
                        "text": client_settings[0]["text"],
                    }
                )
                has_disclaimer = True

        # checking, if has business settings
        if not has_disclaimer:
            business_settings = self.get_business_settings_disclaimer()
            
            # checking, if business settings has disclaimer_text
            if (
                business_settings
                and "text" in business_settings[0]
                and business_settings[0]["text"]
            ):
                disclaimers_data.update(
                    {
                        "text": business_settings[0]["text"],
                    }
                )
                has_disclaimer = True

        # get disclaimer from disclaimers table, when no disclaimer_text in client settings
        if not has_disclaimer:
            disclaimer = self.get_default_disclaimer()
            if disclaimer:
                disclaimers_data = disclaimer
        
        return disclaimers_data


    def rr_payment_process(self):
        """
        Using for reserve release payment process(LC-1668)
        """
        from src.models import (
            Disbursements,
            ReserveReleaseDisbursements,
            ClientPayee,
            ClientControlAccounts,
        )
        from src.resources.v2.helpers.payment_services import PaymentServices

        if self.status.value != "completed":
            abort(400, f"Reserve Release is not completed")

        clients_control_account = ClientControlAccounts.query.filter_by(
            client_id=self.client_id,
            is_deleted=False,
        ).first()

        control_account_name = None
        currency = None
        if clients_control_account:
            control_account_name = clients_control_account.control_account.name
            currency = clients_control_account.control_account.currency

        # Approved Request for LCEI US Control Account Only(LC-1668)
        if control_account_name != "LCEI. US":
            print(f"Control account is not 'LCEI. US'")
            return

        # Reserve Release disbursements
        disbursements = (
            Disbursements.query.join(ReserveReleaseDisbursements)
            .filter(
                ReserveReleaseDisbursements.reserve_release_id == self.id,
                ReserveReleaseDisbursements.is_deleted == False,
                Disbursements.is_deleted == False,
                Disbursements.is_reviewed == True,
            )
            .all()
        )

        if not disbursements:
            print(f"disbursements not found for reserve release - {self.id}")
            return

        # payment services
        payment_services = PaymentServices(request_type=self)

        for disbursement in disbursements:
            # only for Client as Payee and/or Third Party as Payee with ACH or Same Day ACH
            if disbursement.payment_method.value in ["direct_deposit", "same_day_ach"]:
                ref_type = None

                # client payee
                client_payee = ClientPayee.query.filter_by(
                    client_id=self.client_id,
                    payee_id=disbursement.payee_id,
                    is_deleted=False,
                ).first()
                if client_payee:
                    ref_type = client_payee.ref_type.value

                data = {
                    "amount": disbursement.cal_net_amount(),
                    "ref_type": ref_type,
                    "ref_id": disbursement.payee_id,
                    "currency": currency,
                    "disbursement_id": disbursement.id,
                }
                payment_services.payment_processing(data=data)

    def get_control_account(self):
        control_account = None
        clients_control_account = self.client.clients_control_account if self.client else None
        if clients_control_account:
            control_account = clients_control_account[0].control_account
        return control_account
    
    def rr_approved_history(self):
        """
        Get reserve release approved history(used in multiple functions)
        """
        # checking reserve release is pending/approved/completed
        if self.status.value == "pending":
            rr_approved = self.request_submitted_by_principal()
        elif self.status.value == "approved":
            rr_approved = self.request_approved_by_ae()
        elif self.status.value == "completed":
            rr_approved = self.request_approved_by_bo()
        else:
            rr_approved = {}

        rr_approved_attribute = {}

        # get reserve release approval history
        if rr_approved:
            if isinstance(rr_approved.attribute, str):
                rr_approved_attribute = json.loads(
                    rr_approved.attribute
                )
            else:
                rr_approved_attribute = (
                    rr_approved.attribute
                )
        return rr_approved_attribute

    
    def get_saved_disclaimer(self):
        """
        Get saved disclaimer from db for reserve release
        """
        saved_disclaimer = {}
        has_disclaimer = False

        rr_approved_attribute = self.rr_approved_history()

        # get saved client settings from approval history
        if (
            rr_approved_attribute
            and "client_settings" in rr_approved_attribute
            and rr_approved_attribute["client_settings"]
        ):
            client_settings = rr_approved_attribute["client_settings"]
            if client_settings and "disclaimer_text" in client_settings:
                saved_disclaimer.update(
                    {
                        "text": client_settings["disclaimer_text"],
                        "name": "Custom Jurisdiction",
                    }
                )
                has_disclaimer = True

        # get saved business settings from approval history
        if (
            not has_disclaimer
            and rr_approved_attribute
            and "business_settings" in rr_approved_attribute
            and rr_approved_attribute["business_settings"]
        ):
            business_settings = rr_approved_attribute["business_settings"]
            if business_settings and "disclaimer_text" in business_settings:
                saved_disclaimer.update(
                    {
                        "text": business_settings["disclaimer_text"],
                        "name": "Custom Jurisdiction",
                    }
                )
                has_disclaimer = True

        # get disclaimer from disclaimer table
        if not has_disclaimer:
            from src.resources.v2.models.disclaimers_model import Disclaimers
            from src.resources.v2.schemas import DisclaimerOnlySchema

            disclaimer_id = self.disclaimer_id
            if not self.disclaimer_id:
                disclaimer_id = self.client.default_disclaimer_id
                
            disclaimer = Disclaimers.query.filter_by(id=disclaimer_id, is_deleted=False).first()
            if disclaimer:
                disclaimers_data = DisclaimerOnlySchema().dump(disclaimer).data
                saved_disclaimer.update(
                    {
                        "text": disclaimers_data["text"],
                        "name": disclaimers_data["name"],
                    }
                )
        return saved_disclaimer

    def rr_client_settings(self):
        """
        Get client settings(fees) for reserve release(used in multiple functions)
        """
        client_settings = {}
        # checking soa is pending/approved/completed
        rr_approved_attribute = self.rr_approved_history()

        # get saved client settings from approval history
        if (
            rr_approved_attribute
            and "client_settings" in rr_approved_attribute
            and rr_approved_attribute["client_settings"]
        ):
            client_settings = rr_approved_attribute["client_settings"]
        
        # checking, if no saved client settings
        if not client_settings:            
            from src.models import (
                ClientSettings,
            )
            # get client settings
            get_client_settings = ClientSettings.query.filter_by(
                client_id=self.client.id, is_deleted=False
            ).first()

            # if no client settings in db
            if not get_client_settings:
                # save client settings
                client_settings_obj = {
                    "client_id": self.client_id
                }
                get_client_settings = ClientSettings(client_settings_obj)
                get_client_settings.save()

            # client settings
            if get_client_settings:
                from src.resources.v2.schemas.client_settings_schema import ClientSettingsSchema
                
                client_settings = ClientSettingsSchema().dump(
                    get_client_settings
                ).data

        return client_settings

    
    def get_client_disclaimer(self):
        """
        LC-1873: updated as per comments in card for system disclaimer flow
        """
        has_disclaimer = False       
        client_disclaimer = []

        # checking, if client settings has disclaimer_text
        client_disclaimer = self.get_client_settings_disclaimer()
        if client_disclaimer:
            has_disclaimer = True

        # get disclaimer from business settings(admin portal), when no disclaimer_text in client settings
        if not has_disclaimer:
            client_disclaimer = self.get_business_settings_disclaimer()
            if client_disclaimer:
                has_disclaimer = True
        
        # get disclaimer from disclaimers table, when no disclaimer_text in client settings and business settings(admin portal)
        if not has_disclaimer:
            client_disclaimer = self.get_default_disclaimer()

        return client_disclaimer


    def rr_payment_status(self):
        """
        Using for reserve release payment status(LC-1669)
        """
        from src.models import (
            Disbursements,
            Payee,
            ClientPayee,
            ClientControlAccounts,
        )
        from src.resources.v2.helpers.payment_services import PaymentServices

        if self.status.value != "completed":
            abort(400, f"Reserve Release is not completed")

        clients_control_account = ClientControlAccounts.query.filter_by(
            client_id=self.client_id,
            is_deleted=False,
        ).first()

        control_account_name = None
        if clients_control_account:
            control_account_name = clients_control_account.control_account.name

        # Reserve Release disbursements
        disbursements = Disbursements.query.filter(
            Disbursements.ref_type == "reserve_release",
            Disbursements.ref_id == self.id,
            Disbursements.is_deleted == False,
            Disbursements.is_reviewed == True,
            Disbursements.payee_id != None,
        ).all()

        if not disbursements:
            abort(404, f"disbursements not found for reserve release - {self.id}")

        # payment services
        payment_services = PaymentServices(request_type=self)

        disbursement_ids = []
        payment_details = []
        transaction_status = "Manual"
        transaction_id = "N/A"
        payment_method_dict = {
            "same_day_ach": "Same Day ACH",
            "wire": "Wire",
            "direct_deposit": "ACH",
        }
        for disbursement in disbursements:
            account_nickname = None

            # payee
            payee = Payee.query.filter_by(
                id=disbursement.payee_id,
            ).first()
            if payee:
                account_nickname = payee.account_nickname

            # client_payee
            client_payee = ClientPayee.query.filter_by(
                payee_id=disbursement.payee_id,
                client_id=disbursement.client_id,
            ).first()
            if client_payee:
                payment_status = client_payee.payment_status

            # only for Client as Payee and/or Third Party as Payee with ACH or Same Day ACH
            # Approved Request for LCEI US Control Account Only(LC-1668)
            if (
                disbursement.payment_method.value in ["direct_deposit", "same_day_ach"]
                and control_account_name == "LCEI. US"
            ):
                disbursement_ids.append(disbursement.id)
            
            # for showing payment type in frontend
            payment_type = disbursement.payment_method.value
            for k, v in payment_method_dict.items():
                if disbursement and disbursement.payment_method.value == k:
                    payment_type = v

            # transaction info
            payment_details_dict = {
                "ref_id": disbursement.id,
                "account_nickname": account_nickname,
                "payment_type": payment_type,
                "payment_status": payment_status,
                "status": transaction_status,
                "transaction_id": transaction_id,
                "amount": disbursement.cal_net_amount(),
            }
            payment_details.append(payment_details_dict)

        # if approved Request for LCEI US Control Account and payment type with ACH or Same Day ACH 
        if disbursement_ids:
            data = {
                "disbursement_ids": disbursement_ids,
            }
            # get bofa transaction (LC-1669)
            bofa_payment_status = payment_services.transaction_status(data=data)
            
            # On dev and beta, payment services is temporarily disabled
            if bofa_payment_status["status_code"] != 200:
                print(bofa_payment_status["status_code"], bofa_payment_status["msg"])
            
            if (
                bofa_payment_status["status_code"] == 200 
                and "payload" in bofa_payment_status 
                and bofa_payment_status["payload"]
            ):
                for payment_detail in payment_details:
                    # update status and transaction id if disbursement_id == ref_id(from payment services(transactions table))
                    [
                        payment_detail.update(
                            {
                                "status": k["bofa_status"],
                                "transaction_id": k["bofa_transaction_id"],
                            }
                        )
                        for k in bofa_payment_status["payload"]
                        if "disbursement_id" in k
                        and k["disbursement_id"] == payment_detail["ref_id"]
                    ]

        return payment_details


    def get_default_disclaimer(self):
        """
        Get disclaimers from disclaimer table(used in multiple functions)
        """
        from src.resources.v2.models.disclaimers_model import Disclaimers
        from src.resources.v2.schemas import DisclaimerOnlySchema

        default_disclaimer = []
        
        # get client's default disclaimer id
        client_default_disclaimer_id = self.client.default_disclaimer_id
        disclaimers = Disclaimers.query.filter_by(is_deleted=False)
            
        # if client has default disclaimer
        if client_default_disclaimer_id:
            disclaimers = disclaimers.filter_by(id=client_default_disclaimer_id)

        disclaimers_data = DisclaimerOnlySchema().dump(
            disclaimers, many=True
        ).data
        default_disclaimer.extend(disclaimers_data)

        return default_disclaimer


    def get_client_settings_disclaimer(self):
        """
        Get disclaimer from client settings based off client(used in multiple functions)
        """
        client_settings_disclaimer = []

        # checking, if has client settings
        if (
            self.client.client_settings
            and self.client.client_settings[0].is_deleted == False
        ):
            from src.resources.v2.schemas.client_settings_schema import ClientSettingsSchema

            client_settings = ClientSettingsSchema().dump(
                self.client.client_settings[0]
            ).data
            
        # checking, if client settings has disclaimer_text
        if (
            client_settings
            and "disclaimer_text" in client_settings
            and client_settings["disclaimer_text"]
        ):
            client_settings_disclaimer.append(
                {
                    "text": client_settings["disclaimer_text"],
                    "name": "Custom Jurisdiction",
                }
            )

        return client_settings_disclaimer


    def get_business_settings_disclaimer(self):
        """
        Get disclaimer from business settings based off control account(used in multiple functions)
        """
        business_settings_disclaimer = []
        rr_approved_attribute = {}
        has_disclaimer = False

        # checking reserve release is pending/approved/completed
        rr_approved_attribute = self.rr_approved_history()

        # get saved business settings from approval history
        if (
            rr_approved_attribute
            and "business_settings" in rr_approved_attribute
            and rr_approved_attribute["business_settings"]
        ):
            business_settings = rr_approved_attribute["business_settings"]
            if (
                business_settings 
                and "disclaimer_text" in business_settings 
                and business_settings["disclaimer_text"]
            ):
                business_settings_disclaimer.append(
                    {
                        "text": business_settings["disclaimer_text"],
                        "name": "Custom Jurisdiction",
                    }
                )
                has_disclaimer = True

        # get disclaimer from business settings(admin portal)
        if not has_disclaimer:
            control_accounts = Permissions.get_business_settings()[
                "control_accounts_disclaimer"
            ]
            
            if control_accounts:
                for k, v in control_accounts.items():
                    client_control_account = self.get_control_account()

                    if (
                        client_control_account
                        and client_control_account.name == k
                        and v
                    ):
                        business_settings_disclaimer.append(
                            {
                                "text": v,
                                "name": "Custom Jurisdiction",
                            }
                        )
        return business_settings_disclaimer


    def archive(self):
        from src.models import (
            ApprovalsHistory,
            Comments,
            Disbursements,
            ReserveReleaseDisbursements,
            Reasons,
            SupportingDocuments,
        )
        # soft delete approvals history, comments, disbursements, reasons and supporting documents
        ApprovalsHistory.query.filter_by(reserve_release_id=self.id, is_deleted=False).update(
            {
                ApprovalsHistory.is_deleted: True,
                ApprovalsHistory.deleted_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )

        Comments.query.filter_by(reserve_release_id=self.id, is_deleted=False).update(
            {
                Comments.is_deleted: True, 
                Comments.deleted_at: datetime.utcnow()
            },
            synchronize_session=False,
        )

        reserve_release_disbursements = ReserveReleaseDisbursements.query.filter_by(reserve_release_id=self.id, is_deleted=False).all()
        if reserve_release_disbursements:
            for reserve_release_disbursement in reserve_release_disbursements:
                disbursement_id = reserve_release_disbursement.disbursements_id
                # disbursement
                Disbursements.query.filter_by(id=disbursement_id, is_deleted=False).update(
                    {
                        Disbursements.is_deleted: True, 
                        Disbursements.deleted_at: datetime.utcnow()
                    },
                    synchronize_session=False,
                )

                # reserve release disbursement
                reserve_release_disbursement.is_deleted = True
                reserve_release_disbursement.deleted_at = datetime.utcnow()
                reserve_release_disbursement.save()

        Reasons.query.filter_by(reserve_release_id=self.id, is_deleted=False).update(
            {
                Reasons.is_deleted: True, 
                Reasons.deleted_at: datetime.utcnow()
            },
            synchronize_session=False,
        )

        SupportingDocuments.query.filter_by(soa_id=self.id, is_deleted=False).update(
            {
                SupportingDocuments.is_deleted: True,
                SupportingDocuments.deleted_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )

        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.save()
        db.session.commit()

class ReserveReleaseListing:
    def get_all():
        from src.resources.v2.schemas import ReserveReleaseResourseSchema

        reserve_release_schema = ReserveReleaseResourseSchema(many=True)

        # ORGANIZATION
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        # user role
        user_role = get_locations["user_role"]

        reserve_release = ReserveRelease.query.filter(
            ReserveRelease.is_deleted == False,
            and_(
                ReserveRelease.status != "action_required_by_client",
                ReserveRelease.status != "client_draft",
                ReserveRelease.status != "principal_rejection",
            ),
            ReserveRelease.client_id.in_(client_ids),
        )

        # get reserve release having status == client_submission only for principal
        if user_role and user_role.lower() != "principal":
            reserve_release = reserve_release.filter(
                ReserveRelease.status != "client_submission"
            )

        reserve_release_results = reserve_release_schema.dump(reserve_release).data

        if len(reserve_release_results) < 1:
            return None

        return reserve_release_results

    def get_paginated_reserve_release(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        ordering = kwargs.get("ordering", None)
        search = kwargs.get("search", None)
        start_date = kwargs.get("start_date", None)
        end_date = kwargs.get("end_date", None)
        control_account = kwargs.get("control_account", None)
        stage = kwargs.get("stage", None)
        use_ref = kwargs.get("use_ref", False)
        high_priority = kwargs.get("high_priority", None)
        dashboard = kwargs.get("dashboard", False)
        client_ids = kwargs.get("client_ids", None)
        user_role = kwargs.get("user_role", None)
        business_control_accounts = kwargs.get("business_control_accounts", [])
        
        from src.models import (
            Client,
            ClientControlAccounts,
            ControlAccount,
        )

        from src.resources.v2.schemas import (
            ReserveReleaseResourseSchema,
            ReserveReleaseDashboardSchema,
            ReserveReleaseClientSchema,
        )

        reserve_release_schema = ReserveReleaseResourseSchema(many=True)
        if dashboard:
            reserve_release_schema = ReserveReleaseDashboardSchema(many=True)

        # Dashboard: get reserve release based off disbursement: no start_date and no end_date) and not ("client_submission")
        if (
            dashboard
            and (not stage or stage not in ["client_submission", "completed"])
            and (not start_date and not end_date)
        ):
            return ReserveReleaseListing.get_reserve_release_by_disbursement(**kwargs)
        
        # only for Client's Request lane in principal dashboard
        if (
            dashboard
            and stage
            and stage == "client_submission"
        ):
            reserve_release_schema = ReserveReleaseDashboardSchema(many=True)

        if not dashboard:
            # ORGANIZATION
            get_locations = Organization.get_locations()
            client_ids = get_locations["client_list"]

            # user role
            user_role = get_locations["user_role"]
            
            # control accounts
            business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        reserve_release = (
            ReserveRelease.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                ReserveRelease.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                Client.is_deleted == False,
                not_(
                    ReserveRelease.status.in_(
                        [
                            "action_required_by_client",
                            "client_draft",
                            "principal_rejection",
                        ]
                    )
                ),
                ReserveRelease.client_id.in_(client_ids),
                ControlAccount.name.in_(business_control_accounts)
            )
            .group_by(ReserveRelease.id)
        )

        # get only completed requests for inactive clients LC-2188
        reserve_release = reserve_release.filter(
            or_(
                Client.is_active == True,
                and_(
                        Client.is_active == False,
                        ReserveRelease.status == "completed",
                    )
            )
        )

        # # get reserve release having status == client_submission only for principal
        if user_role and user_role.lower() != "principal":
            reserve_release = reserve_release.filter(
                ReserveRelease.status != "client_submission"
            )

        # filter by control_account
        if control_account is not None:
            reserve_release = reserve_release.filter(
                ControlAccount.name == control_account
            )

        # filter for status
        if stage is not None:
            stages_split = stage.split(",")

            if len(stages_split) > 1:
                reserve_release = reserve_release.filter(
                    ReserveRelease.status.in_(stages_split)
                )
            else:
                if stage == "archived":
                    reserve_release = reserve_release.filter(
                        or_(
                            # ReserveRelease.status == "rejected",
                            ReserveRelease.status
                            == "completed"
                        )
                    )
                elif stage == "rejected":
                    reserve_release = reserve_release.filter(
                        ReserveRelease.status == "rejected"
                    )
                elif stage == "completed":
                    from src.resources.v2.helpers.convert_datetime import date_concat_time
                    # current est date: for comparing with last_processed_at(utc)
                    today = date_concat_time(date_concat="current")
                    next_day = date_concat_time(date_concat="next")

                    reserve_release = reserve_release.filter(
                        ReserveRelease.status == "completed",
                        cast(ReserveRelease.last_processed_at, DateTime) >= today,
                        cast(ReserveRelease.last_processed_at, DateTime) <= next_day
                    )
                elif stage == "pending":
                    reserve_release = reserve_release.filter(
                        or_(
                            ReserveRelease.status == "pending",
                            ReserveRelease.status == "reviewed",
                        )
                    )
                else:
                    reserve_release = reserve_release.filter(
                        ReserveRelease.status == stage
                    )

        # start_date and end_date filter
        if start_date and end_date:
            if start_date == end_date:
                reserve_release = reserve_release.filter(
                    ReserveRelease.last_processed_at >= start_date,
                    ReserveRelease.last_processed_at < (start_date + timedelta(days=1)),
                )
            else:
                reserve_release = reserve_release.filter(
                    ReserveRelease.last_processed_at > start_date,
                    ReserveRelease.last_processed_at < (end_date + timedelta(days=1)),
                )
        elif start_date:
            reserve_release = reserve_release.filter(
                ReserveRelease.last_processed_at >= start_date
            )
        elif end_date:
            reserve_release = reserve_release.filter(
                ReserveRelease.last_processed_at < (end_date + timedelta(days=1))
            )

        # Reserve Release search
        if search is not None:
            if "-RRID" in search.upper():
                ref_client_no = search.upper().split("-RRID")[0]
                rr_id = search.upper().split("-RRID")[1]
                reserve_release = reserve_release.filter(
                    and_(
                        Client.ref_client_no.like("%" + ref_client_no + "%"),
                        ReserveRelease.ref_id.like(rr_id + "%"),
                    )
                )
            elif "RRID" in search.upper():
                rr_id = search.upper().split("RRID")[1]
                reserve_release = reserve_release.filter(
                    ReserveRelease.ref_id.like(rr_id + "%")
                )
            elif "RR" in search.upper():
                rr_id = search.upper().split("RR")[1]
                if rr_id:
                    reserve_release = reserve_release.filter(
                        ReserveRelease.ref_id.like(rr_id + "%")
                    )
            elif use_ref:
                reserve_release = reserve_release.filter(
                    or_(
                        Client.name.like("%" + search + "%"),
                        ReserveRelease.disbursement_amount.like("%" + search + "%"),
                        ReserveRelease.ref_id.like("%" + search + "%"),
                        Client.ref_client_no.like("%" + search + "%"),
                    )
                )
            else:
                reserve_release = reserve_release.filter(
                    or_(
                        Client.name.like("%" + search + "%"),
                        ReserveRelease.ref_id.like("%" + search + "%"),
                        ReserveRelease.disbursement_amount.like("%" + search + "%"),
                        ReserveRelease.reference_number.like("%" + search + "%"),
                        Client.ref_client_no.like("%" + search + "%"),
                    )
                )

        # high priority filter
        if high_priority is not None:
            reserve_release = reserve_release.filter(
                ReserveRelease.high_priority == True
            )

        # ordering(sorting)
        if ordering is not None:
            if "date" == ordering:
                reserve_release = reserve_release.order_by(
                    ReserveRelease.last_processed_at.asc()
                )

            if "-date" == ordering:
                reserve_release = reserve_release.order_by(
                    ReserveRelease.last_processed_at.desc()
                )

            if "advance_amount" == ordering:
                reserve_release = reserve_release.order_by(
                    ReserveRelease.advance_amount.asc()
                )

            if "-advance_amount" == ordering:
                reserve_release = reserve_release.order_by(
                    ReserveRelease.advance_amount.desc()
                )

            if "status" == ordering:
                reserve_release = reserve_release.order_by(ReserveRelease.status.asc())

            if "-status" == ordering:
                reserve_release = reserve_release.order_by(ReserveRelease.status.desc())

            if "high_priority" == ordering:
                reserve_release = reserve_release.order_by(
                    ReserveRelease.high_priority.asc()
                )

            if "-high_priority" == ordering:
                reserve_release = reserve_release.order_by(
                    ReserveRelease.high_priority.desc()
                )

            if "client_name" == ordering:
                reserve_release = reserve_release.order_by(Client.name.asc())

            if "-client_name" == ordering:
                reserve_release = reserve_release.order_by(Client.name.desc())

            if "disbursement_amount" == ordering:
                reserve_release = reserve_release.order_by(
                    ReserveRelease.disbursement_amount.asc()
                )

            if "-disbursement_amount" == ordering:
                reserve_release = reserve_release.order_by(
                    ReserveRelease.disbursement_amount.desc()
                )

            if "created_at" == ordering:
                reserve_release = reserve_release.order_by(
                    ReserveRelease.created_at.asc()
                )

            if "-created_at" == ordering:
                reserve_release = reserve_release.order_by(
                    ReserveRelease.created_at.desc()
                )

            if "ref_client_rr_id" == ordering:
                reserve_release = reserve_release.order_by(ReserveRelease.ref_id.asc())

            if "-ref_client_rr_id" == ordering:
                reserve_release = reserve_release.order_by(ReserveRelease.ref_id.desc())
        else:
            reserve_release = reserve_release.order_by(ReserveRelease.updated_at.desc())

        # pagination
        reserve_release = reserve_release.paginate(page, rpp, False)
        total_pages = math.ceil(reserve_release.total / rpp)
        reserve_release_results = reserve_release_schema.dump(
            reserve_release.items
        ).data
        total_count = reserve_release.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(reserve_release_results) < 1:
            return {
                "msg": get_invalid_page_msg,
                "per_page": rpp,
                "current_page": page,
                "total_pages": 0,
                "total_count": 0,
                "data": [],
            }

        return {
            "msg": "Records found",
            "per_page": rpp,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "data": reserve_release_results,
        }


    def get_reserve_release_by_disbursement(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        # start_date = kwargs.get("start_date", None)
        # end_date = kwargs.get("end_date", None)
        control_account = kwargs.get("control_account", None)
        stage = kwargs.get("stage", None)
        high_priority = kwargs.get("high_priority", None)
        # ordering = kwargs.get("ordering", None)
        dashboard = kwargs.get("dashboard", False)
        client_ids = kwargs.get("client_ids", None)
        user_role = kwargs.get("user_role", None)
        business_control_accounts = kwargs.get("business_control_accounts", [])
        
        from src.models import (
            Client,
            ClientControlAccounts,
            ControlAccount,
            Disbursements,
        )
        from src.resources.v2.schemas import (
            ReserveReleaseDashboardSchema,
        )

        reserve_release_schema = ReserveReleaseDashboardSchema(many=True)

        if not dashboard:
            # client ids
            get_locations = Organization.get_locations()
            client_ids = get_locations["client_list"]

            # user role
            user_role = get_locations["user_role"]
            
            # control accounts
            business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        # reserve release
        reserve_release = (
            ReserveRelease.query.join(Client, ClientControlAccounts, ControlAccount)
            .outerjoin(
                Disbursements,
                and_(
                    Disbursements.ref_type == "reserve_release",
                    Disbursements.ref_id == ReserveRelease.id,
                    Disbursements.is_deleted == False,
                    Disbursements.payment_method.in_(
                        ["same_day_ach", "wire", "direct_deposit"]
                    ),
                    Disbursements.payee_id != None,
                ),
            )
            .filter(
                ReserveRelease.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                Client.is_deleted == False,
                not_(
                    ReserveRelease.status.in_(
                        [
                            "draft",
                            "action_required_by_client",
                            "client_draft",
                            "principal_rejection",
                        ]
                    )
                ),
                ReserveRelease.client_id.in_(client_ids),
                ControlAccount.name.in_(business_control_accounts),
            )
            .group_by(ReserveRelease.id)
        )

        # only show active clients requests in dashboard
        if dashboard:
            reserve_release = reserve_release.filter(Client.is_active == True)

        # get reserve release having status == client_submission only for principal
        if user_role and user_role.lower() != "principal":
            reserve_release = reserve_release.filter(
                ReserveRelease.status != "client_submission"
            )

        # high priority filter
        if high_priority:
            reserve_release = reserve_release.filter(
                ReserveRelease.high_priority == True
            )

        # filter by control_account
        if control_account:
            reserve_release = reserve_release.filter(
                ControlAccount.name == control_account
            )

        # filter for status
        if stage:
            stages_split = stage.split(",")

            if len(stages_split) > 1:
                reserve_release = reserve_release.filter(
                    ReserveRelease.status.in_(stages_split)
                )
            else:                
                if stage == "pending":
                    reserve_release = reserve_release.filter(
                        or_(
                            ReserveRelease.status == "pending",
                            ReserveRelease.status == "reviewed",
                        )
                    )
                # elif stage == "completed":
                #     from src.resources.v2.helpers.convert_datetime import date_concat_time
                #     # current est date: for comparing with last_processed_at(utc)
                #     today = date_concat_time(date_concat="current")
                #     next_day = date_concat_time(date_concat="next")

                #     reserve_release = reserve_release.filter(
                #         ReserveRelease.status == "completed",
                #         cast(ReserveRelease.last_processed_at, DateTime) >= today,
                #         cast(ReserveRelease.last_processed_at, DateTime) <= next_day
                #     )
                else:
                    reserve_release = reserve_release.filter(
                        ReserveRelease.status == stage
                    )

        reserve_release = reserve_release.order_by(
            ReserveRelease.high_priority.desc(),
            func.field(
                Disbursements.payment_method,
                "same_day_ach",
                "wire",
                "direct_deposit",
            ),
            ReserveRelease.last_processed_at.asc(),
        )
        
        # pagination
        pagination_obj = reserve_release.paginate(page, rpp, False)
        total_pages = pagination_obj.pages
        reserve_release_data = reserve_release_schema.dump(pagination_obj.items).data
        total_count = pagination_obj.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )
        
        # invalid page number
        if len(reserve_release_data) < 1:
            return {
                "msg": get_invalid_page_msg,
                "per_page": rpp,
                "current_page": page,
                "total_pages": 0,
                "total_count": 0,
                "data": [],
            }

        return {
            "msg": "Records found",
            "per_page": rpp,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "data": reserve_release_data,
        }
