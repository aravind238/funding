from src import db
import enum
from datetime import datetime


class DisclaimersName(enum.Enum):
    Canada = "Canada"
    Quebec = "Quebec"
    US = "US"


class DisclaimersType(enum.Enum):
    soa = "soa"


class Disclaimers(db.Model):
    __tablename__ = "disclaimers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Enum(DisclaimersName), nullable=False)
    text = db.Column(db.Text, nullable=False)
    disclaimer_type = db.Column(
        db.Enum(DisclaimersType), default=DisclaimersType.soa.value
    )
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.name = data.get("name")
        self.text = data.get("text")
        self.disclaimer_type = data.get("disclaimer_type")
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
