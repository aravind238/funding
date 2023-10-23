from src import db
from flask_script import Command
from src.models import (
    Debtor
)
from sqlalchemy import or_


class InactiveCadenceDebtors(Command):
    def __init__(self, db=None):
        self.db = db

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            ## inactive all the cadence/lcra debtors ##
            Debtors = Debtor.query.filter(
                or_(
                    Debtor.source == "cadence",
                    Debtor.source == "lcra",
                ),
                Debtor.is_deleted == False,
            ).update(
                {
                    Debtor.is_active: False,
                },
                synchronize_session=False,
            )
            db.session.flush()
            
            print('-- total cadence/lcra debtors inactivated --', Debtors)

            self.commit()
        except Exception as e:
            print(e)
            self.rollback()
