import json
from src import db
from flask_script import Command
from datetime import datetime
from src.models import (
    Client,
    ClientPayee,
    Payee,
)
from src.resources.v2.helpers import PaymentServices
from sqlalchemy import and_, or_


class AddClientAsPayee(Command):
    def __init__(self, db=None):
        self.db = db

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            clients = (
                Client.query.filter(
                    Client.is_deleted == False,
                    ClientPayee.is_deleted == False,
                    and_(                      
                        Client.ref_client_no != "TODO-cadence",
                        Client.ref_client_no != "Cadence:sync-pending",
                        Client.ref_client_no != "TODO-factorcloud",
                    ),
                    ClientPayee.ref_type != "client",
                )
                .all()
            )
            print("--out client--", len(clients))

            if not clients:
                print(f"Clients not found")

            for client in clients:
                # data to be saved
                req_data = {
                    "account_nickname": client.name,
                    "address_line_1": "",
                    "city": "",
                    "province": "",
                    "country": "",
                    "postal_code": "",
                    "phone": "",
                    "email": "",
                    "ref_type": "client",
                }

                payee = Payee.query.filter(
                    Payee.account_nickname == client.name,
                    Payee.is_deleted == False,
                ).first()

                print(client.id, '--client payee--', payee)
                
                # checking, if payee exists having name == client name 
                if not payee:
                    # save payee
                    payee = Payee(req_data)
                    payee.last_processed_at = datetime.utcnow()
                    payee.status = "approved"
                    payee.save()

                    # client payee
                    client_payee_json = {
                        "client_id": client.id,
                        "payee_id": payee.id,
                        "ref_type": req_data["ref_type"],
                    }
                    # save client payee
                    client_payee = ClientPayee(client_payee_json)
                    client_payee.save()

                    # payment services
                    payment_services = PaymentServices(
                        request_type=payee, req_data=req_data
                    )
                    payment_services.add_in_payment_services()

                    db.session.flush()

                    print(client.id, "--added client as payee--", payee.id)
                        
            self.commit()
        except Exception as e:
            print(e)
            self.rollback()
