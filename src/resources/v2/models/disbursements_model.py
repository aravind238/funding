from src import db
import enum
from datetime import datetime
from decimal import Decimal


class PaymentMethod(enum.Enum):
    cheque = "cheque"
    direct_deposit = "direct_deposit"
    international_wire = "international_wire"
    same_day_ach = "same_day_ach"
    wire = "wire"

class DisbursementRefType(enum.Enum):
    reserve_release = "reserve_release"
    soa = "soa"


class Disbursements(db.Model):
    """ Disbursement model """

    __tablename__ = "disbursements"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    soa_id = db.Column(
        db.Integer, db.ForeignKey("soa.id", ondelete="CASCADE"), nullable=True
    )
    payee_id = db.Column(
        db.Integer, db.ForeignKey("payees.id", ondelete="CASCADE"), nullable=True
    )
    ref_type = db.Column(
        db.Enum(DisbursementRefType), default=DisbursementRefType.soa.value
    )
    ref_id = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.Enum(PaymentMethod), default=PaymentMethod.wire.value)
    client_fee = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    amount = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    third_party_fee = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    tp_ticket_number = db.Column(db.String(64), nullable=True)
    is_reviewed = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    # relationship
    clients = db.relationship("Client", backref="disbursements")
    soa = db.relationship("SOA", backref="disbursements")
    reserve_release = db.relationship(
        "ReserveRelease",
        secondary="reserve_release_disbursements",
        backref=db.backref("disbursements"),
    )
    payee = db.relationship("Payee", backref="disbursements")

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.soa_id = data.get("soa_id")
        self.payee_id = data.get(
            "payee_id"
        )
        self.ref_type = data.get("ref_type")
        self.ref_id = data.get("ref_id")
        self.payment_method = data.get("payment_method")
        self.client_fee = data.get("client_fee")
        self.amount = data.get("amount")
        self.third_party_fee = data.get("third_party_fee")
        self.tp_ticket_number = data.get("tp_ticket_number")
        self.is_reviewed = data.get("is_reviewed")
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(str(e))

    def update(self, data):
        try:
            for key, item in data.items():
                setattr(self, key, item)
            self.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(str(e))

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(str(e))

    @staticmethod
    def get_all_disbursements():
        return Disbursements.query.filter_by(is_deleted=False).all()

    @staticmethod
    def get_one_disbursement(id):
        return Disbursements.query.filter_by(id=id, is_deleted=False).first()

    def cal_rr_disbursement_amount(reserve_release_id=None):
        """ 
        calculate reserve release disbursement amount 
        """
        disbursement_amount = Decimal(0)
        payees = []
        if reserve_release_id:
            sql_query = f"SELECT \
                        d.client_fee, \
                        d.third_party_fee, \
                        d.amount, \
                        d.payee_id \
                        from disbursements d, \
                        reserve_release_disbursements rrd \
                        WHERE rrd.disbursements_id = d.id \
                        AND rrd.reserve_release_id = {reserve_release_id} \
                        AND rrd.is_deleted = false;"

            disbursements_data = db.session.execute(db.text(sql_query)).fetchall()

            if disbursements_data:
                for disbursement_data in disbursements_data:
                    # disbursement fees
                    wire_fee = (
                        disbursement_data["client_fee"]
                        if disbursement_data["client_fee"] is not None
                        else Decimal(0)
                    )
                    tp_payment_fee = (
                        disbursement_data["third_party_fee"]
                        if disbursement_data["third_party_fee"] is not None
                        else Decimal(0)
                    )
                    total_fees = Decimal(wire_fee) + Decimal(tp_payment_fee)

                    # disbursement amount
                    amount = (
                        disbursement_data["amount"]
                        if disbursement_data["amount"] is not None
                        else Decimal(0)
                    )

                    # payees
                    payee = disbursement_data["payee_id"]
                    payees.append(payee)

                    # calculate reserve release disbursement amount
                    disbursement_amount += Decimal(amount) - Decimal(total_fees)

        rr_disbursement = {
            "payee_ids": payees,
            "disbursement_amount": Decimal(disbursement_amount)
        }

        return rr_disbursement

    def cal_net_amount(self):
        # calculate net amount
        third_party_fee = (
            Decimal(self.third_party_fee)
            if self.third_party_fee != None
            else Decimal(0)
        )
        client_fee = (
            Decimal(self.client_fee) if self.client_fee != None else Decimal(0)
        )
        tp_wire_total = client_fee + third_party_fee
        amount = Decimal(self.amount) if self.amount != None else Decimal(0)
        net_amount = amount - tp_wire_total
        return Decimal("%.2f" % net_amount)

