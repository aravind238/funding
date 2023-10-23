from src import db
from datetime import datetime
from enum import Enum


class ControlAccountsName(Enum):
    """
    For matching with control accounts from business settings(admin portal)
    """

    lcec_cdn = "LCEC CDN"
    lcec_us = "LCEC US"
    lcei_us = "LCEI. US"
    nfi_cdn = "NFI CDN"
    nfi_us = "NFI US"
    nii_us = "NII US"    
    ntfi_usd = "NTFI USD"
    lfc_usd = "LFC USD"
    lfsi_cad = "LFSI - CAD"
    nplp_cad = "NPLP- CAD"

    def describe(self):
        # self is the member here
        return self.name, self.value


class ControlAccount(db.Model):
    """ Control Account model """

    __tablename__ = "control_accounts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=True)
    currency = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(255), nullable=True)
    lcra_export_id = db.Column(db.Integer)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)
    # relationship
    control_account = db.relationship(
        "ClientControlAccounts", backref="control_account"
    )

    def __init__(self, data):
        self.name = data.get("name")
        self.currency = data.get("currency")
        self.country = data.get("country")
        self.lcra_export_id = data.get("lcra_export_id")
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

    @staticmethod
    def get_all_control_accounts():
        return ControlAccount.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_control_account(id):
        return ControlAccount.query.filter_by(id=id, is_deleted=False).first()
