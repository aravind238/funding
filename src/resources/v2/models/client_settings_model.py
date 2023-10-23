from src import db
from datetime import datetime


class ClientSettings(db.Model):
    """ Client Settings model """

    __tablename__ = "client_settings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    high_priority_fee = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    same_day_ach_fee = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    wire_fee = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    third_party_fee = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    same_day_ach_cut_off_time = db.Column(db.Time, nullable=True)
    disclaimer_text = db.Column(db.Text, nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.high_priority_fee = data.get("high_priority_fee")
        self.same_day_ach_fee = data.get("same_day_ach_fee")
        self.wire_fee = data.get("wire_fee")
        self.third_party_fee = data.get("third_party_fee")
        self.same_day_ach_cut_off_time = data.get("same_day_ach_cut_off_time")
        self.disclaimer_text = data.get("disclaimer_text")
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
    def get_all():
        return ClientSettings.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one(id):
        return ClientSettings.query.filter_by(id=id, is_deleted=False).first()
