from src import db
from datetime import datetime


class Logs(db.Model):
    """ Logs model """

    __tablename__ = "logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request = db.Column(db.JSON)
    response = db.Column(db.JSON)
    status_code = db.Column(db.String(255), nullable=True)
    token = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __init__(self, data):
        self.request = data.get("request")
        self.response = data.get("response")
        self.status_code = data.get("status_code")
        self.token = data.get("token")
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
    def get_all_logs():
        return Logs.query.all()

    @staticmethod
    def get_one_log(id):
        return Logs.query.filter_by(id=id).first()
