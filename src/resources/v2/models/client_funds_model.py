from src import db
from datetime import datetime



class ClientFund(db.Model):
    """ Client fund model """

    __tablename__ = "client_funds"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    ar_balance = db.Column(db.Numeric(12, 4), nullable=True)
    funding_balance = db.Column(db.Numeric(12, 4), nullable=True)
    reserve_balance = db.Column(db.Numeric(12, 4), nullable=True)
    credit_commitee = db.Column(db.Numeric(12, 4), nullable=True)
    purchage_sales_agreement = db.Column(db.Numeric(12, 4), nullable=True)
    discount_fees_percentage = db.Column(db.Numeric(9, 4), nullable=True)
    credit_insurance_total_percentage = db.Column(db.Numeric(9, 4), nullable=True)
    reserves_withheld_percentage = db.Column(db.Numeric(9, 4), nullable=True)
    current_limit = db.Column(db.Numeric(12, 4), nullable=True)
    loan_limit = db.Column(db.Numeric(12, 4), nullable=True)
    cash_reserves = db.Column(db.Numeric(12, 4), nullable=True)
    escrow_reserves = db.Column(db.Numeric(12, 4), nullable=True)
    total_reserves = db.Column(db.Numeric(12, 4), nullable=True)
    adjusted_reserves = db.Column(db.Numeric(12, 4), nullable=True)
    required_reserves = db.Column(db.Numeric(12, 4), nullable=True)
    additional_reserves_required = db.Column(db.Numeric(12, 4), nullable=True)
    ineligible_value = db.Column(db.Numeric(12, 4), nullable=True)
    accrued_invoice_fees = db.Column(db.Numeric(12, 4), nullable=True)
    available_for_release = db.Column(db.Numeric(12, 4), nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.ar_balance = data.get("ar_balance")
        self.funding_balance = data.get("funding_balance")
        self.reserve_balance = data.get("reserve_balance")
        self.credit_commitee = data.get("credit_commitee")
        self.purchage_sales_agreement = data.get("purchage_sales_agreement")
        self.discount_fees_percentage = data.get("discount_fees_percentage")
        self.credit_insurance_total_percentage = data.get(
            "credit_insurance_total_percentage"
        )
        self.reserves_withheld_percentage = data.get("reserves_withheld_percentage")
        self.current_limit = data.get("current_limit")
        self.loan_limit = data.get("loan_limit")
        self.cash_reserves = data.get("cash_reserves")
        self.escrow_reserves = data.get("escrow_reserves")
        self.total_reserves = data.get("total_reserves")
        self.adjusted_reserves = data.get("adjusted_reserves")
        self.required_reserves = data.get("required_reserves")
        self.additional_reserves_required = data.get("additional_reserves_required")
        self.ineligible_value = data.get("ineligible_value")
        self.accrued_invoice_fees = data.get("accrued_invoice_fees")
        self.available_for_release = data.get("available_for_release")
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
    def get_all_client_funds():
        return ClientFund.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_client_fund(id):
        return ClientFund.query.filter_by(id=id, is_deleted=False).first()
