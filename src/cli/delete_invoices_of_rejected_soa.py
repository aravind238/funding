from src import db
from flask_script import Command
from datetime import datetime
from src.models import (
    Invoice, SOA
)


class DeleteInvoicesOfRejectedSoa(Command):
    def __init__(self, db=None):
        self.db = db

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            ## soft deleted invoices whose soa are rejected ##
            # get soa invoices
            Invoices = Invoice.query.filter(
                Invoice.soa_id == SOA.id,
                SOA.status.in_(
                    [
                        "rejected",
                        "principal_rejection",
                    ]
                ),
                Invoice.is_deleted == False,
                SOA.is_deleted == False
            ).update(
                {
                    Invoice.is_deleted: True,
                    Invoice.deleted_at: datetime.utcnow(),
                },
                synchronize_session=False,
            )
            db.session.flush()
            
            print('-- total invoices soft deleted --', Invoices)

            self.commit()
        except Exception as e:
            print(e)
            self.rollback()
