from src import db
import enum
from datetime import datetime
from src.middleware.organization import Organization
from sqlalchemy import and_, or_, not_
from src.middleware.permissions import Permissions

class ClientSource(enum.Enum):
    cadence = "cadence"
    factorcloud = "factorcloud"
    lc = "lc"
    lcra = "lcra"


class Client(db.Model):
    """ Client model """

    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(100), unique=True)
    source = db.Column(db.Enum(ClientSource))
    name = db.Column(db.String(255), nullable=False)
    ref_key = db.Column(db.Integer)
    ref_client_no = db.Column(db.String(255), nullable=True)
    ref_account_exec = db.Column(db.String(255), nullable=True)
    lcra_client_accounts_id = db.Column(db.String(255), nullable=True)
    lcra_client_accounts_number = db.Column(db.String(255), nullable=True)
    lcra_control_account_organizations_id = db.Column(db.String(255), nullable=True)
    default_disclaimer_id = db.Column(
        db.Integer, db.ForeignKey("disclaimers.id", ondelete="CASCADE"), nullable=True
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    # back relation field
    clients_control_account = db.relationship("ClientControlAccounts", backref="client")
    soa = db.relationship("SOA", backref="client")
    invoice = db.relationship("Invoice", backref="client")
    client_debtor = db.relationship("ClientDebtor", backref="client")
    reserve_release = db.relationship("ReserveRelease", backref="client")
    client_funds = db.relationship("ClientFund", backref="client")
    client_payee = db.relationship("ClientPayee", backref="client")
    client_settings = db.relationship("ClientSettings", backref="client")
    debtor_limit_approvals = db.relationship("DebtorLimitApprovals", backref="client")
    generic_request = db.relationship("GenericRequest", backref="client")
    compliance_repository = db.relationship("ComplianceRepository", backref="client")
    collection_notes = db.relationship("CollectionNotes", backref="client")
    verification_notes = db.relationship("VerificationNotes", backref="client")
    invoice_supporting_documents = db.relationship("InvoiceSupportingDocuments", backref="client")

    # Indexes
    __table_args__ = (
        db.Index("lcra_client_accounts_id", "lcra_client_accounts_id", unique=True),
        db.Index(
            "lcra_client_accounts_number", "lcra_client_accounts_number", unique=True
        ),
        db.Index("idx_ref_key", "ref_key"),
        db.Index("idx_ref_client_no", "ref_client_no"),
    )

    def __init__(self, data):
        self.uuid = data.get("uuid")
        self.source = data.get("source")
        self.name = data.get("name")
        self.ref_key = data.get("ref_key")
        self.ref_client_no = data.get("ref_client_no")
        self.ref_account_exec = data.get("ref_account_exec")
        self.lcra_client_accounts_id = data.get("lcra_client_accounts_id")
        self.lcra_client_accounts_number = data.get("lcra_client_accounts_number")
        self.lcra_control_account_organizations_id = data.get(
            "lcra_control_account_organizations_id"
        )
        self.default_disclaimer_id = data.get("default_disclaimer_id")
        self.is_deleted = data.get("is_deleted")
        self.is_active = data.get("is_active")
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
    def get_all_clients():
        return Client.query.filter(
            Client.is_deleted == False,
            and_(
                Client.ref_client_no != "TODO-cadence",
                Client.ref_client_no != "Cadence:sync-pending",
                Client.ref_client_no != "TODO-factorcloud",
            ),
        )

    @staticmethod
    def get_one_client(id):
        return Client.query.filter_by(id=id, is_deleted=False).first()

    @staticmethod
    def get_one_based_off_control_accounts(id):
        from src.models import (
            ControlAccount,
            ClientControlAccounts,
        )

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        return (
            Client.query.join(ClientControlAccounts, ControlAccount)
            .filter(
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                Client.is_deleted == False,
                not_(
                    Client.ref_client_no.in_(
                        [
                            "TODO-cadence",
                            "Cadence:sync-pending",
                            "TODO-factorcloud",
                        ]
                    )
                ),
                ControlAccount.name.in_(business_control_accounts),
                Client.id == id,
            )
            .first()
        )
    
    def object_as_string(self):
        return "Client"

    def get_debtors(self):
        from src.models import Debtor, ClientDebtor
        # from src.resources.v1.client_debtors.model.client_debtors import ClientDebtor

        get_client_debtors = (
            db.session.query(Debtor, ClientDebtor)
            .outerjoin(ClientDebtor, ClientDebtor.debtor_id == Debtor.id)
            .filter(
                ClientDebtor.client_id == self.id,
                Debtor.is_deleted == False,
                Debtor.is_active == True,
                ClientDebtor.is_deleted == False,
            )
            .order_by(Debtor.name.asc())
            .all()
        )
        db.session.commit()
        return get_client_debtors

    def get_payees(self):
        from src.models import Payee, ClientPayee

        get_client_payees = (
            Payee.query.outerjoin(ClientPayee, ClientPayee.payee_id == Payee.id)
            .filter(
                ClientPayee.client_id == self.id,
                ClientPayee.ref_type == "payee",
                Payee.is_deleted == False,
                Payee.is_active == True,
                ClientPayee.is_deleted == False,
                Payee.status == "approved",
            )
            .all()
        )
        return get_client_payees

    def get_client_payees(self):
        from src.models import Payee, ClientPayee

        get_client_payees = (
            Payee.query.outerjoin(ClientPayee, ClientPayee.payee_id == Payee.id)
            .filter(
                ClientPayee.client_id == self.id,
                ClientPayee.ref_type == "client",
                Payee.is_deleted == False,
                Payee.is_active == True,
                ClientPayee.is_deleted == False,
                Payee.status == "approved",
            )
            .all()
        )
        return get_client_payees
    
    def get_control_account(self):
        control_account = None
        clients_control_account = self.clients_control_account if self.clients_control_account else None
        if clients_control_account:
            control_account = clients_control_account[0].control_account
        return control_account

    def get_business_settings_disclaimer(self):
        """
        Get disclaimer from business settings based off control account(used in multiple functions)
        """
        business_settings_disclaimer = []

        # get disclaimer from business settings(admin portal)
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

    def get_disclaimer(self):
        has_disclaimer = False
        client_disclaimer = []
        client_settings = {}        
        
        # checking, if has client settings
        if (
            self.client_settings
            and self.client_settings[0].is_deleted == False
        ):
            from src.resources.v2.schemas.client_settings_schema import ClientSettingsSchema

            client_settings = ClientSettingsSchema().dump(
                self.client_settings[0]
            ).data
        
        # checking, if client settings has disclaimer_text
        if (
            client_settings
            and "disclaimer_text" in client_settings
            and client_settings["disclaimer_text"]
        ):
            client_disclaimer.append(
                {
                    "text": client_settings["disclaimer_text"],
                    "name": "Custom Jurisdiction",
                }
            )
            has_disclaimer = True

        # get disclaimer from business settings
        if not has_disclaimer:
            business_settings = self.get_business_settings_disclaimer()
            if (
                business_settings
                and isinstance(business_settings, list)
                and "text" in business_settings[0]
            ):
                client_disclaimer.append(
                    {
                        "text": business_settings[0]["text"],
                        "name": "Custom Jurisdiction",
                    }
                )            
                has_disclaimer = True
        
        # get disclaimer from disclaimers table
        if not has_disclaimer:            
            from src.resources.v2.models.disclaimers_model import Disclaimers
            from src.resources.v2.schemas.disclaimers_schema import DisclaimerOnlySchema
            
            # get client's default disclaimer id
            client_default_disclaimer_id = self.default_disclaimer_id

            disclaimers = Disclaimers.query.filter_by(is_deleted=False)
            
            # if client has default disclaimer
            if client_default_disclaimer_id:
                disclaimers = disclaimers.filter_by(id=client_default_disclaimer_id)

            disclaimers_data = DisclaimerOnlySchema().dump(
                disclaimers, many=True
            ).data

            client_disclaimer.extend(disclaimers_data)

        return client_disclaimer

class ClientListing:

    def get_all():
        from src.models import (
            Client,  
            ControlAccount, 
            ClientControlAccounts,
        )
        from src.resources.v2.schemas import (
            ClientInfoSchema,
        )
        client_scema = ClientInfoSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        get_client_ids = get_locations["client_list"]

        clients = Client.query.filter(
            Client.is_deleted == False,                            
            and_(                      
                Client.ref_client_no != "TODO-cadence",
                Client.ref_client_no != "Cadence:sync-pending",
                Client.ref_client_no != "TODO-factorcloud",
            ),
            Client.id.in_(get_client_ids)
        ).order_by(Client.name.asc())

        client_results = client_scema.dump(clients).data
        
        if len(client_results) < 1:
            return None

        return client_results

    def get_paginated_clients(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        ordering = kwargs.get("ordering", None)
        search = kwargs.get("search", None)
        control_account = kwargs.get("control_account", None)
        active = kwargs.get("active", None)

        from src.models import (
            Client,  
            ControlAccount, 
            ClientControlAccounts,
        )
        from src.resources.v2.schemas import (
            ClientInfoSchema,
        )
        client_schema = ClientInfoSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        get_client_ids = get_locations["client_list"]
        
        # control accounts
        business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        clients = (
            Client.query.join(ClientControlAccounts, ControlAccount)
            .filter(
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                Client.is_deleted == False,
                not_(
                    Client.ref_client_no.in_(
                        [
                            "TODO-cadence",
                            "Cadence:sync-pending",
                            "TODO-factorcloud",
                        ]
                    )
                ),
                Client.id.in_(get_client_ids),
                ControlAccount.name.in_(business_control_accounts),
            )
            .group_by(Client.id)
        )

        # client search
        if search is not None:
            clients = clients.filter(
                (Client.name.like("%" + search + "%"))
                | (Client.ref_client_no.like("%" + search + "%"))
            )

        # filter by control_account
        if control_account is not None:
            clients = clients.filter(ControlAccount.name == control_account)

        # filter by is_active
        if active is not None:
            if active in ["active", "true"]:
                clients = clients.filter(Client.is_active == True)
            
            if active == "inactive":
                clients = clients.filter(Client.is_active == False)

        # ordering(sorting)
        if ordering is not None:
            if "name" == ordering:
                clients = clients.order_by(Client.name.asc())

            if "-name" == ordering:
                clients = clients.order_by(Client.name.desc())

            if "ref_client_no" == ordering:
                clients = clients.order_by(Client.ref_client_no.asc())

            if "-ref_client_no" == ordering:
                clients = clients.order_by(Client.ref_client_no.desc())

            if "control_account_name" == ordering:
                clients = clients.order_by(ControlAccount.name.asc())

            if "-control_account_name" == ordering:
                clients = clients.order_by(ControlAccount.name.desc())
        else:
            clients = clients.order_by(Client.name.asc())

        # pagination
        clients = clients.paginate(page, rpp, False)
        total_pages = clients.pages
        client_results = client_schema.dump(clients.items).data
        total_count = clients.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(client_results) < 1:
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
            "data": client_results,
        }
