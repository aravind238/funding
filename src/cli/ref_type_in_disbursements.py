from src import db
from flask_script import Command
from src.models import (
    Disbursements,
    ReserveReleaseDisbursements,
)


class AddRefTypeInDisbursements(Command):
    def __init__(self, db=None):
        self.db = db

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            disbursements = (
                Disbursements.query.filter(
                    Disbursements.is_deleted == False,
                )
                .all()
            )

            print("--out disbursements--", len(disbursements))

            if not disbursements:
                print(f"Disbursements not found")

            for disbursement in disbursements:
                if not disbursement.ref_type:
                    if disbursement.soa_id:
                        disbursement.ref_type = "soa"
                        disbursement.ref_id = disbursement.soa_id
                        db.session.flush()
                        print(disbursement.id, "--disbursement soa_id--", disbursement.soa_id)
                    else:
                        rr_disbursement = ReserveReleaseDisbursements.query.filter(
                            ReserveReleaseDisbursements.disbursements_id == disbursement.id,
                            ReserveReleaseDisbursements.is_deleted == False,
                        ).first()

                        if rr_disbursement:
                            disbursement.ref_type = "reserve_release"
                            disbursement.ref_id = rr_disbursement.reserve_release_id
                            db.session.flush()
                            print(disbursement.id, "--disbursement reserve_release_id--", rr_disbursement.reserve_release_id)
                        
            self.commit()
        except Exception as e:
            print(e)
            self.rollback()
