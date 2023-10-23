from src import db
from datetime import datetime


class Participant(db.Model):
    """ Participant model """

    __tablename__ = "participants"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(255), nullable=True)
    ratio = db.Column(db.Numeric(10, 2))
    funds_required = db.Column(db.Numeric(10, 2))
    funds_available = db.Column(db.Numeric(10, 2))
    ref_id = db.Column(db.Integer, nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.source = data.get("source")
        self.name = data.get("name")
        self.role = data.get("role")
        self.ratio = data.get("ratio")
        self.funds_required = data.get("funds_required")
        self.funds_available = data.get("funds_available")
        self.ref_id = data.get("ref_id")
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
    def get_all_participants():
        return Participant.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_participants(id):
        return Participant.query.filter_by(id=id, is_deleted=False).first()


class ParticipantsListing:

    def get_all(client_id=None):
        from src.models import (
            ClientParticipant,
            Client,
        )

        from src.resources.v2.schemas import ParticipantSchema
        participants_schema = ParticipantSchema(many=True)

        participants = Participant.query.join(ClientParticipant, Client).filter(
            Participant.id == ClientParticipant.participant_id,
            Participant.is_deleted == False,
            ClientParticipant.is_deleted == False,
            ClientParticipant.client_id == Client.id,
        )
        
        if client_id:
            participants = participants.filter(Client.id == client_id)

        # participants = participants.order_by(Participant.updated_at.desc())
        participants_results = participants_schema.dump(participants).data

        if len(participants_results) < 1:
            return None

        return participants_results

    def get_paginated_participants(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        ordering = kwargs.get("ordering", None)
        search = kwargs.get("search", None)
        client_id = kwargs.get("client_id", None)

        from src.models import (
            ClientParticipant,
            Client,
        )

        from src.resources.v2.schemas import ParticipantSchema
        participants_schema = ParticipantSchema(many=True)

        participants = Participant.query.join(ClientParticipant, Client).filter(
            Participant.id == ClientParticipant.participant_id,
            Participant.is_deleted == False,
            ClientParticipant.is_deleted == False,
            ClientParticipant.client_id == Client.id,
        )
        if client_id:
            participants = participants.filter(Client.id == client_id)

        participants = participants.order_by(Participant.updated_at.desc())
        
        
        # pagination
        participants = participants.paginate(page, rpp, False)
        total_pages = participants.pages
        participants_results = participants_schema.dump(participants.items).data
        total_count = participants.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(participants_results) < 1:
            return {
                "msg": get_invalid_page_msg,
                "per_page": rpp,
                "current_page": page,
                "total_pages": 0,
                "data": [],
                "total_count": 0,
            }

        return {
            "msg": "Records found",
            "per_page": rpp,
            "current_page": page,
            "total_pages": total_pages,
            "data": participants_results,
            "total_count": total_count,
        }
