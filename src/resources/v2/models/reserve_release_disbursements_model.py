from src import db
from datetime import datetime


class ReserveReleaseDisbursements(db.Model):
    __tablename__ = "reserve_release_disbursements"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    disbursements_id = db.Column(
        db.Integer,
        db.ForeignKey("disbursements.id", ondelete="CASCADE"),
        nullable=False,
    )
    reserve_release_id = db.Column(
        db.Integer,
        db.ForeignKey("reserve_release.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint(
            "disbursements_id",
            "reserve_release_id",
            "is_deleted",
            name="disbursements__reserve_release_id",
        ),
    )

    def __init__(self, data):
        self.disbursements_id = data.get("disbursements_id")
        self.reserve_release_id = data.get("reserve_release_id")
        self.is_deleted = data.get("is_deleted")
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
