from multiprocessing.connection import Client
from src import db
import enum
from datetime import datetime
import math
from sqlalchemy import and_, or_, not_
from src.middleware.organization import Organization
from src.middleware.permissions import Permissions

class DebtorSource(enum.Enum):
    cadence = "cadence"
    factorcloud = "factorcloud"
    funding = "funding"
    lcra = "lcra"

class Debtor(db.Model):
    """
    Debtor Model
    """

    __tablename__ = "debtors"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=True)
    source = db.Column(db.Enum(DebtorSource), default=DebtorSource.lcra.value)
    ref_key = db.Column(db.String(255), nullable=False)
    ref_debtor_no = db.Column(db.String(255), nullable=True)
    uuid = db.Column(db.String(100), unique=True)
    address_1 = db.Column(db.String(255), nullable=True)
    address_2 = db.Column(db.String(255), nullable=True)
    state = db.Column(db.String(150), nullable=True)
    city = db.Column(db.String(150), nullable=True)
    postal_code = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)
    
    clients_debtor = db.relationship("ClientDebtor", backref="debtor")
    invoice = db.relationship("Invoice", backref="debtors")
    debtor_limit_approvals = db.relationship("DebtorLimitApprovals", backref="debtor")
    collection_notes = db.relationship("CollectionNotes", backref="debtor")
    verification_notes = db.relationship("VerificationNotes", backref="debtor")
    invoice_supporting_documents = db.relationship("InvoiceSupportingDocuments", backref="debtor")
    
    # Indexes
    __table_args__ = (
        db.Index("idx_ref_key", "ref_key"),
    )

    def __init__(self, data):
        self.source = data.get("source")
        self.name = data.get("name")
        self.ref_key = data.get("ref_key")
        self.ref_debtor_no = data.get("ref_debtor_no")
        self.uuid = data.get("uuid")
        self.address_1 = data.get("address_1")
        self.address_2 = data.get("address_2")
        self.state = data.get("state")
        self.city = data.get("city")
        self.postal_code = data.get("postal_code")
        self.country = data.get("country")
        self.phone = data.get("phone")
        self.email = data.get("email")
        self.is_active = data.get("is_active")
        self.is_deleted = data.get("is_deleted")
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

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.save()

    @staticmethod
    def get_all_debtors():
        return Debtor.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_debtor(id):
        return Debtor.query.filter_by(id=id, is_deleted=False).first()

    @staticmethod
    def get_one_based_off_control_accounts(id, client_id=None):
        from src.models import (
            ControlAccount,
            Client,
            ClientDebtor,
            ClientControlAccounts,
        )
        
        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        debtor = Debtor.query.join(
            ClientDebtor, Client, ClientControlAccounts, ControlAccount
        ).filter(
            Debtor.is_deleted == False,
            ClientDebtor.is_deleted == False,
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            ControlAccount.name.in_(business_control_accounts),
            Debtor.id == id,
        )
        if client_id:
            debtor = debtor.filter(ClientDebtor.client_id == client_id)

        debtor = debtor.first()
        return debtor
    
    @staticmethod
    def get_all_based_off_control_accounts(client_id=None):
        from src.models import (
            ControlAccount,
            Client,
            ClientDebtor,
            ClientControlAccounts,
        )
        
        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        debtor = Debtor.query.join(
            ClientDebtor, Client, ClientControlAccounts, ControlAccount
        ).filter(
            Debtor.is_deleted == False,
            ClientDebtor.is_deleted == False,
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            ControlAccount.name.in_(business_control_accounts),
        )
        if client_id:
            debtor = debtor.filter(ClientDebtor.client_id == client_id)
        
        return debtor

    def get_duplicate_debtors(self, client_id=None, search=""):
        """
        Get duplicate debtors based off ref_key(LC-1934)
        """
        from src.models import (
            Client,
            ClientDebtor,
        )

        # debtor not to merge
        keep_debtor_id = self.id
        keep_debtor_ref_key = self.ref_key

        # get duplicate debtors based off ref_key
        duplicate_debtors = db.session.query(
            Debtor.id,
            Debtor.name,
            Debtor.ref_debtor_no,
            Debtor.ref_key,
            Debtor.source,
            Debtor.address_1,
            Debtor.address_2,
            Debtor.state,
            Debtor.city,
            Debtor.postal_code,
            Debtor.country,
            Client.name.label("client_name"),
        ).join(
            ClientDebtor, ClientDebtor.debtor_id == Debtor.id
        ).join(
            Client, Client.id == ClientDebtor.client_id
        ).filter(
            ClientDebtor.is_deleted == False,
            Debtor.is_deleted == False,
            Debtor.id != keep_debtor_id,
        )

        # Merge debtors: code commented for removing restrictions to merge with same debtor ref_keys, now user can merge any debtors of same client
        # # added condition for debtor having ref_key=0 should be able to merge into any debtor of same client(LC-2186)
        # if keep_debtor_ref_key != 0:
        #     duplicate_debtors = duplicate_debtors.filter(
        #         Debtor.ref_key.in_(
        #             [
        #                 keep_debtor_ref_key,
        #                 0,
        #             ]
        #         )
        #     )
        # else:
        #     duplicate_debtors = duplicate_debtors.filter(
        #         Debtor.ref_key == keep_debtor_ref_key,
        #     )

        if client_id:
            duplicate_debtors = duplicate_debtors.filter(                
                ClientDebtor.client_id == client_id
            )

        # search based off 'FC ID'(debtor id) or debtors name(LC-1934)
        if search:
            duplicate_debtors = duplicate_debtors.filter(                
                Debtor.name.like("%" + search + "%")
                | Debtor.id.like("%" + search + "%")
            )
        
        duplicate_debtors = duplicate_debtors.all()
        db.session.commit()
        return duplicate_debtors

    
    def get_debtors_duplicate_names(name=name, client_id=None, create_forcefully=None):
        """
        Get debtors duplicate names
        """
        from src.models import ClientDebtor

        # Organization
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        get_debtor = Debtor.query.join(
            ClientDebtor
        ).filter(
            ClientDebtor.debtor_id == Debtor.id,
            Debtor.is_deleted == False,
            ClientDebtor.is_deleted == False
        )

        if client_id:
            has_debtor_name = get_debtor.filter(
                Debtor.name == name, ClientDebtor.client_id == client_id
                ).all()
            if has_debtor_name:
                return {
                    "msg": "Debtor name already exists",
                    "status": "error",
                    "status_code": 400,
                    "can_create_forcefully": False
                }

        if create_forcefully is None:
            has_debtor_names = get_debtor.filter(
                Debtor.name == name, ClientDebtor.client_id.in_(client_ids)
                ).all()
            if has_debtor_names:
                clients_list = []
                for has_debtor_name in has_debtor_names:
                    client_debtors =  has_debtor_name.clients_debtor
                    for client_debtor in client_debtors:
                        if client_debtor.client.id in (client_ids):
                            clients_list.append(client_debtor.client.name)
                clients_list = ", ".join(clients_list)
                return {
                    "msg": f"Debtor name already exists with clients: {clients_list} ",
                    "status": "error",
                    "status_code": 400,
                    "can_create_forcefully": True
                }

            has_debtor_existed = get_debtor.filter(
                Debtor.name == name,
                not_(
                    ClientDebtor.client_id.in_(client_ids)
                )
                ).all()
            if has_debtor_existed:
                return {
                    "msg": "The debtor already exists. But your role does not grant you access to the client and its debtors. Please request access to the administrator.",
                    "status": "error",
                    "status_code": 400,
                    "can_create_forcefully": True
                }

        return {
            "msg": "Debtor's duplicate names not found",
            "status": "success",
            "status_code": 200,
            "can_create_forcefully": False
        }


    def merge_duplicate_debtors_invoice(self, client_id=None, merge_debtors=[]):
        """
        Merge duplicate debtors' invoice and soft delete clientdebtor, debtor(LC-1934)
        """
        from src.models import (
            Invoice,
            Debtor,
            ClientDebtor,
        )
        
        # debtor not to merge
        keep_debtor_id = self.id

        # invoice
        Invoice.query.filter(
            Invoice.debtor.in_(merge_debtors), 
            Invoice.is_deleted == False
        ).update(
            {
                Invoice.debtor: keep_debtor_id,
            },
            synchronize_session=False,
        )
        
        # client debtor
        ClientDebtor.query.filter(
            ClientDebtor.is_deleted == False,
            ClientDebtor.client_id == client_id,
            ClientDebtor.debtor_id.in_(merge_debtors),
        ).update(
            {
                ClientDebtor.is_deleted: True,
                ClientDebtor.deleted_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )

        # debtor
        Debtor.query.filter(
            Debtor.id.in_(merge_debtors),
            Debtor.is_deleted == False,
        ).update(
            {
                Debtor.is_deleted: True,
                Debtor.deleted_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )


    def approvals_history(self):
        from src.resources.v2.models.debtor_approvals_history_model import (
            DebtorApprovalsHistory,
        )
        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log = []
        # checking, if the debtor is not created from Cadence or FactorCloud(LC-2022)
        if self.source and self.source.value == "funding":
            debtor_approvals_history = DebtorApprovalsHistory.get_by_debtor_id(self.id)

            if debtor_approvals_history:
                for debtor_approvals in debtor_approvals_history:
                    history_status = None
                    # activity log
                    if (
                        debtor_approvals.key == "client_created_at"
                        or debtor_approvals.key == "created_at"
                    ):
                        history_status = "Created by"

                    if history_status:
                        activity_log.append(
                            {
                                "added_at": utc_to_local(
                                    dt=debtor_approvals.created_at.isoformat()
                                ),
                                "description": history_status,
                                "user": debtor_approvals.user,
                            }
                        )

        return {
            "activity_log": activity_log
        }

    def collection_notes(self, client_id=None):
        from src.models import (
            CollectionNotes,
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import CollectionNotesRefSchema

        collection_notes_schema = CollectionNotesRefSchema(many=True)

        # # Organization
        # get_locations = Organization.get_locations()
        # client_ids = get_locations["client_list"]

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        collection_notes = (
            CollectionNotes.query.join(
                Debtor, Client, ClientControlAccounts, ControlAccount
            )
            .filter(
                CollectionNotes.deleted_at == None,
                Debtor.is_deleted == False,
                Client.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                CollectionNotes.client_id == client_id,
                ControlAccount.name.in_(business_control_accounts),
                CollectionNotes.debtor_id == self.id,
            )
            .order_by(CollectionNotes.id.desc())
            .all()
        )

        collection_notes_data = collection_notes_schema.dump(collection_notes, many=True).data

        return collection_notes_data

    def cn_approvals_history(self, client_id=None):
        from src.models import (
            CollectionNotes,
            CollectionNotesApprovalHistory,
        )

        collection_notes = (
            CollectionNotes.query.filter(
                CollectionNotes.deleted_at == None,
                CollectionNotes.client_id == client_id,
                CollectionNotes.debtor_id == self.id,
            )
            .order_by(CollectionNotes.id.desc())
            .all()
        )
        print(client_id, self.id,'--dd--', collection_notes)
        if not collection_notes:
            return []

        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log_list = []
        activity_log = []
        for collection_note in collection_notes:            
            # activity_log = []
            
            # collection notes approval history
            approvals_history = CollectionNotesApprovalHistory.query.filter(
                CollectionNotesApprovalHistory.deleted_at == None,
                CollectionNotesApprovalHistory.collection_notes_id == collection_note.id,
            ).order_by(CollectionNotesApprovalHistory.updated_at.asc()).all()

            if approvals_history:
                for each_history in approvals_history:
                    history_status = None

                    if (
                        each_history.key == "client_created_at"
                        or each_history.key == "created_at"
                    ):
                        history_status = "Created by"

                    if each_history.key == "client_submission_at":
                        history_status = "Submitted by Client"

                    if each_history.key == "submitted_at":
                        history_status = "Submitted by Principal"

                    ref_client_no = collection_note.client.ref_client_no if collection_note.client else None
                    cn_reference = f"{ref_client_no}-CNID{collection_note.id}"

                    # activity log
                    if history_status:
                        activity_log.append(
                            {   
                                "id": each_history.id,
                                "collection_notes_id": collection_note.id,
                                "added_at": utc_to_local(
                                    dt=each_history.created_at.isoformat()
                                ),
                                "description": history_status,
                                "user": each_history.user,
                                "cn_reference": cn_reference,
                            }
                        )
                    
            # activity_log_list.append({
            #     "collection_notes_id": collection_note.id,
            #     "activity_log": activity_log,
            # })
            
            # activity_log_list.append(activity_log)

        # return activity_log_list
        return {
            "activity_log": activity_log,
        }


class DebtorListing:

    def get_all():
        from src.resources.v2.schemas import DebtorSchema
        from src.models import Client, ClientDebtor

        debtor_schema = DebtorSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        client_id = get_locations["client_list"]

        client_debtor = ClientDebtor.query.filter(
            ClientDebtor.is_deleted == False, ClientDebtor.client_id.in_(client_id)
        )
        debtors = Debtor.query.filter_by(is_deleted=False)

        debtorResults = debtor_schema.dump(debtors).data

        if len(debtorResults) < 1:
            return None

        debtorResult = []

        for debtor in debtorResults:
            debtor_obj = Debtor.get_one_debtor(debtor["id"])
            clients_debtor_obj = debtor_obj.clients_debtor
            if bool(clients_debtor_obj):
                client_name = Client.get_one_client(
                    clients_debtor_obj[0].client_id
                ).name
            else:
                client_name = None
            debtor.update({"client_name": client_name})
            debtorResult.append(debtor)

        return debtorResult

    def get_paginated_debtors(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        ordering = kwargs.get("ordering", None)
        search = kwargs.get("search", None)
        control_account = kwargs.get("control_account", None)
        active = kwargs.get("active", None)

        from src.models import ControlAccount, Client, ClientDebtor, ClientControlAccounts
        from src.resources.v2.schemas import DebtorLimitsSchema

        debtor_client_schema = DebtorLimitsSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        client_id = get_locations["client_list"]
        
        # control accounts
        business_control_accounts = Permissions.get_business_settings()["control_accounts"]
        
        # get debtor details and client name by client_id
        joined_table_query = (
            db.session.query(
                Debtor.id,
                Debtor.name,
                ClientDebtor.credit_limit,
                ClientDebtor.current_ar,
                ClientDebtor.days_1_30,
                ClientDebtor.days_31_60,
                ClientDebtor.days_61_90,
                ClientDebtor.days_91_120,
                ClientDebtor.default_term_value,
                Debtor.ref_debtor_no,
                Debtor.ref_key,
                Debtor.source,
                Debtor.created_at,
                Debtor.updated_at,
                Client.name.label("client_name"),
                Client.id.label("client_id"),
                Debtor.address_1,
                Debtor.address_2,
                Debtor.state,
                Debtor.city,
                Debtor.postal_code,
                Debtor.country,
                Debtor.phone,
                Debtor.email,
                Debtor.is_active,
            )
            .filter(
                ClientDebtor.debtor_id == Debtor.id,
                Client.id == ClientDebtor.client_id,
                ClientControlAccounts.client_id == Client.id,
                ControlAccount.id == ClientControlAccounts.control_account_id,
                Debtor.is_deleted == False,
                ClientDebtor.is_deleted == False,
                Client.is_deleted == False,
                Client.is_active == True,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                Client.id.in_(client_id),
                ControlAccount.name.in_(business_control_accounts),
            )
        )

        # filter by is_active
        if active is not None:
            if active == "active":
                joined_table_query = joined_table_query.filter(Debtor.is_active == True)
            
            if active == "inactive":
                joined_table_query = joined_table_query.filter(Debtor.is_active == False)

        # sorting
        if ordering is not None:
            if "id" == ordering:
                joined_table_query = joined_table_query.order_by(Debtor.id.asc())

            if "-id" == ordering:
                joined_table_query = joined_table_query.order_by(Debtor.id.desc())
                
            if "name" == ordering:
                joined_table_query = joined_table_query.order_by(Debtor.name.asc())

            if "-name" == ordering:
                joined_table_query = joined_table_query.order_by(Debtor.name.desc())

            if "ref_credit_limit" == ordering:
                joined_table_query = joined_table_query.order_by(
                    ClientDebtor.credit_limit.asc()
                )

            if "-ref_credit_limit" == ordering:
                joined_table_query = joined_table_query.order_by(
                    ClientDebtor.credit_limit.desc()
                )

            if "client_name" == ordering:
                joined_table_query = joined_table_query.order_by(Client.name.asc())

            if "-client_name" == ordering:
                joined_table_query = joined_table_query.order_by(Client.name.desc())

            if "ref_key" == ordering:
                joined_table_query = joined_table_query.order_by(Debtor.ref_key.asc())

            if "-ref_key" == ordering:
                joined_table_query = joined_table_query.order_by(Debtor.ref_key.desc())

            if "ref_debtor_no" == ordering:
                joined_table_query = joined_table_query.order_by(Debtor.ref_debtor_no.asc())

            if "-ref_debtor_no" == ordering:
                joined_table_query = joined_table_query.order_by(Debtor.ref_debtor_no.desc())
        else:
            joined_table_query = joined_table_query.order_by(Debtor.updated_at.desc())

        # search
        if search is not None:
            joined_table_query = joined_table_query.filter(
                (Client.name.like("%" + search + "%"))
                | (Client.ref_client_no.like("%" + search + "%"))
                | (Debtor.id.like("%" + search + "%"))
                | (Debtor.name.like("%" + search + "%"))
                | (Debtor.ref_key.like("%" + search + "%"))
                | (Debtor.ref_debtor_no.like("%" + search + "%"))
                | (ClientDebtor.credit_limit.like("%" + search + "%"))
                # | (Debtor.address_1.like("%" + search + "%"))
                # | (Debtor.address_2.like("%" + search + "%"))
                # | (Debtor.state.like("%" + search + "%"))
                # | (Debtor.city.like("%" + search + "%"))
                # | (Debtor.postal_code.like("%" + search + "%"))
                # | (Debtor.country.like("%" + search + "%"))
                # | (Debtor.phone.like("%" + search + "%"))
                # | (Debtor.email.like("%" + search + "%"))
            )

        # control account
        if control_account is not None:
            joined_table_query = joined_table_query.filter(
                ControlAccount.name == control_account
            )

        # pagination
        debtors = joined_table_query.paginate(page, rpp, False)
        total_pages = debtors.pages
        debtors_data = debtor_client_schema.dump(debtors.items).data
        total_count = debtors.total
        # print('waheguru')
        db.session.commit()

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(debtors_data) < 1:
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
            "data": debtors_data,
        }
