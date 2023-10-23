from src import db
from flask_script import Command
from src.models import (
    Client
)
from sqlalchemy import or_


class InactiveCadenceClients(Command):
    def __init__(self, db=None):
        self.db = db

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            ## inactive all the cadence/lcra clients ##
            Clients = Client.query.filter(
                or_(
                    Client.source == "cadence",
                    Client.source == "lcra",
                ),
                Client.is_deleted == False,
            ).update(
                {
                    Client.is_active: False,
                },
                synchronize_session=False,
            )
            db.session.flush()
            
            print('-- total cadence/lcra clients inactivated --', Clients)

            self.commit()
        except Exception as e:
            print(e)
            self.rollback()
