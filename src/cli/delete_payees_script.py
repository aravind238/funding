from src import db
from flask_script import Command
from datetime import datetime
from src.models import (
    Client,
    ClientControlAccounts,
    ControlAccount,
    ClientPayee,
    Payee,
)
from sqlalchemy import and_, or_, not_


class DeletePayees(Command):
    def __init__(self, db=None):
        self.db = db

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            ## Set payees to is_active=false who don't have control accounts("LCEC CDN", "LCEC US") ##
            # get payees from client payees based off relation with clients, clients control account, control account
            client_payees = (
                ClientPayee.query
                .join(
                    Client,
                    and_(                        
                        Client.is_deleted == False,
                        Client.id == ClientPayee.client_id,
                        not_(
                                Client.ref_client_no.in_(
                                [
                                    "TODO-cadence",
                                    "Cadence:sync-pending",
                                    "TODO-factorcloud",
                                ]
                            )
                        ),
                    )
                )
                .join(
                    ClientControlAccounts,
                    and_(                        
                        ClientControlAccounts.is_deleted == False,
                        ClientControlAccounts.client_id == Client.id,
                    )
                )
                .join(
                    ControlAccount,
                    and_(                        
                        ControlAccount.is_deleted == False,
                        ControlAccount.id == ClientControlAccounts.control_account_id,
                        not_(
                            ControlAccount.name.in_(
                                [
                                    "LCEC CDN",
                                    "LCEC US",
                                ]
                            )
                        )
                    )
                )
                # .filter(
                #     ClientPayee.is_deleted == False,
                # )
                .all()
            )

            if not client_payees:                
                print(f"Payees not found")

            # add payee_ids in list
            payees_list = []
            [payees_list.append(k.payee_id) for k in client_payees]
            
            print('--payees_list--', len(payees_list))

            # checking, if payees exists then set is_active to false
            payees = (
                Payee.query
                .filter(
                    Payee.is_deleted == False,
                    # Payee.is_active == True,
                    Payee.id.in_(payees_list),
                )
                .update(
                    {
                        Payee.is_active: False,
                    },
                    synchronize_session=False,
                )
            )

            db.session.flush()

            print('-- payees set to is_active=false --', payees)

            self.commit()
        except Exception as e:
            print(e)
            self.rollback()
