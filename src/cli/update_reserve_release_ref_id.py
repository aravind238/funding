from src import db
from flask_script import Command
from src.models import (
    ReserveRelease,
)
from sqlalchemy import func, not_
from sqlalchemy.orm import load_only


class UpdateReserveReleaseRefID(Command):
    def __init__(self, db=None):
        self.db = db

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            reserve_release = ReserveRelease.query.filter(
                ReserveRelease.is_deleted == False,
                ReserveRelease.ref_id.in_(
                    [
                        0,
                        None,
                    ]
                ),
            ).all()

            print("--out reserve_release--", len(reserve_release))

            if not reserve_release:
                print(f"Reserve Release not found")

            for rr in reserve_release:
                # update ref id for reserve release
                rr.ref_id = rr.id
                db.session.flush()
                print(
                    rr.id,
                    "--client id--",
                    rr.client_id,
                    "--reserve release ref id--",
                    rr.ref_id,
                )

            self.commit()
        except Exception as e:
            print(e)
            self.rollback()
