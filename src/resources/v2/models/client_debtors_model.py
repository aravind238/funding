from src import db
from datetime import datetime
from src.middleware.organization import Organization


class ClientDebtor(db.Model):
    """ ClientDebtor model """

    __tablename__ = "client_debtors"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    debtor_id = db.Column(
        db.Integer, db.ForeignKey("debtors.id", ondelete="CASCADE"), nullable=False
    )
    client_ref_no = db.Column(db.String(255), nullable=True)
    credit_limit = db.Column(db.Numeric(12, 2), nullable=True)
    default_term_value = db.Column(db.Integer, nullable=True)
    days_1_30 = db.Column(db.String(255), nullable=True)
    days_31_60 = db.Column(db.String(255), nullable=True)
    days_61_90 = db.Column(db.String(255), nullable=True)
    days_91_120 = db.Column(db.String(255), nullable=True)
    current_ar = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.debtor_id = data.get("debtor_id")
        self.client_ref_no = data.get("client_ref_no")
        self.credit_limit = data.get("credit_limit")
        self.default_term_value = data.get("default_term_value")
        self.days_1_30 = data.get("days_1_30")
        self.days_31_60 = data.get("days_31_60")
        self.days_61_90 = data.get("days_61_90")
        self.days_91_120 = data.get("days_91_120")
        self.current_ar = data.get("current_ar")
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
    def get_all_client_debtors():
        # Organization
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]
        return ClientDebtor.query.filter(
            ClientDebtor.is_deleted == False, ClientDebtor.client_id.in_(client_ids)
        )

    @staticmethod
    def get_one_client_debtor(id):
        # Organization
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]
        return ClientDebtor.query.filter(
            ClientDebtor.id == id,
            ClientDebtor.is_deleted == False,
            ClientDebtor.client_id.in_(client_ids),
        ).first()


    @staticmethod
    def get_client_debtor_by_debtor_id(debtor_id, client_id=None):
        client_debtor = ClientDebtor.query.filter(
            ClientDebtor.is_deleted == False,
            ClientDebtor.debtor_id == debtor_id,
        )

        if client_id:
            client_debtor = client_debtor.filter(
                ClientDebtor.client_id == client_id,
            )

        client_debtor = client_debtor.first()
        return client_debtor
