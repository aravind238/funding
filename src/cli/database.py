import json
from src import db
from flask_script import Command
from src.models import (
    SOA,
    ReserveRelease,
    Payee,
)


class PayeeLastProcessedAtSeed(Command):
    def __init__(self, db=None):
        self.db = db

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            payee = (
                Payee.query.options(db.joinedload(Payee.approvals_history))
                .filter(Payee.last_processed_at == None)
                .all()
            )
            if not payee:
                print(f"No payee found having last_processed_at == null")

            if payee:
                for p in payee:                    
                    approvalshistory = p.approvals_history
                    if approvalshistory:
                        # get latest approval history of soa
                        status_updated_at = approvalshistory[-1].created_at
                        p.last_processed_at = status_updated_at
                        db.session.flush()
                        print(p.id, "--payee last_processed_at--", p.last_processed_at)
                    else:
                        p.last_processed_at = p.updated_at
                        db.session.flush()
                        print(p.id, "--payee last_processed_at--", p.last_processed_at)
                self.commit()

        except Exception as e:
            print(e)
            self.rollback()

# ToDo: Need to be removed
# class SOALastProcessedAtSeed(Command):

#     def __init__(self, db=None):
#         self.db = db

#     def commit(self):
#         self.db.session.commit()

#     def rollback(self):
#         self.db.session.rollback()

#     def run(self):
#         try:
            
#             soa = SOA.query.options(db.joinedload(SOA.approvals_history)).filter(SOA.last_processed_at == None).all()
#             if not soa:
#                 print(f'No soa found having last_processed_at == null')

#             if soa:
#                 for s in soa:
#                     approvalshistory = s.approvals_history
#                     if approvalshistory:
#                         # get latest approval history of soa
#                         status_updated_at = approvalshistory[-1].created_at
#                         s.last_processed_at = status_updated_at
#                         db.session.flush()
#                         print(s.id, '--soa last_processed_at--', s.last_processed_at)
#                     else:
#                         s.last_processed_at = s.updated_at
#                         db.session.flush()
#                         print(s.id, '--soa last_processed_at--', s.last_processed_at)
#                 db.session.commit()
#             reserve_release = ReserveRelease.query.options(db.joinedload(ReserveRelease.approvals_history)).filter(ReserveRelease.last_processed_at == None).all()
#             if not reserve_release:
#                 print(f'No reserve release found having last_processed_at == null')

#             if reserve_release:
#                 for rr in reserve_release:
#                     approvalshistory = rr.approvals_history
#                     if approvalshistory:
#                         # get latest approval history of reserve release
#                         status_updated_at = approvalshistory[-1].created_at
#                         rr.last_processed_at = status_updated_at
#                         db.session.flush()
#                         print(rr.id, '--rr last_processed_at--', rr.last_processed_at)
#                     else:
#                         rr.last_processed_at = s.updated_at
#                         db.session.flush()
#                         print(rr.id, '--rr last_processed_at--', rr.last_processed_at)
#                 db.session.commit()
#         except Exception as e:
#             print(e)
#             self.rollback()

