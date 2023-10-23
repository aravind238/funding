from src import db
from flask_script import Command
from src.models import DebtorLimitApprovalsHistory


class UpdateDebtorLimitApprovalsHistory(Command):
    def __init__(self, db=None):
        self.db = db

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            dla_history = (
                DebtorLimitApprovalsHistory.query.filter(
                    DebtorLimitApprovalsHistory.deleted_at == None,
                )
                .all()
            )
            if not dla_history:
                print(f"Debtor Limit Approvals History not found")

            if dla_history:
                for dla in dla_history:
                    dla_attribute = dla.attribute
                    if "credit_limit" in dla_attribute:
                        dla_attribute = {**dla_attribute, "credit_limit_requested": dla_attribute["credit_limit"], "credit_limit_approved": dla_attribute["credit_limit"]}
                        del dla_attribute["credit_limit"]
                        dla.attribute = dla_attribute
                        db.session.flush()
                        print('-- updated debtor limit approvals history --', dla_attribute["id"])
                self.commit()

        except Exception as e:
            print(e)
            self.rollback()
