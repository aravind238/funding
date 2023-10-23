from src import db
from datetime import datetime


class LCRAExport(db.Model):
    """ LCRAExport model """

    __tablename__ = "lcra_export"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    soa_id = db.Column(db.Integer, nullable=True)
    reserve_release_id = db.Column(db.Integer, nullable=True)
    is_uploaded = db.Column(db.Boolean, default=False)
    exported_by = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __init__(self, data):
        self.soa_id = data.get("soa_id")
        self.reserve_release_id = data.get("reserve_release_id")
        self.is_uploaded = data.get("is_uploaded")
        self.exported_by = data.get("exported_by")
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
    def get_all_lcra_exports():
        return LCRAExport.query.all()

    @staticmethod
    def get_one_lcra_export(id):
        return LCRAExport.query.filter_by(id=id).first()
