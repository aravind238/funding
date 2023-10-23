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
from sqlalchemy import and_, or_, not_
import pandas as pd
import numpy as np


class ImportPayees(Command):
    def __init__(self, db=None):
        self.db = db

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            # For reading excel file
            file_path = "src/cli/August 17 Payees.xlsx"

            # set engine parameter to "openpyxl", pandas has removed xlrd support for anything other than xls files
            file_data = pd.read_excel(
                file_path, engine="openpyxl", 
                dtype=str # Keeping leading zeros(ex. 0913): converted to str
            )            

            # if having value Null or NaN
            if not file_data.empty:
                file_data = file_data.replace({np.nan: None})

            for i in file_data.index:
                beneficiary_name = None
                beneficiary_account_number = None
                beneficiary_account_type = None
                beneficiary_address_line_1 = ""
                beneficiary_city = ""
                beneficiary_state = ""
                beneficiary_zip = ""
                beneficiary_bank_name = None
                beneficiary_bank_id = None
                beneficiary_bank_address_1 = ""
                beneficiary_bank_address_2 = ""
                beneficiary_bank_city = ""
                beneficiary_bank_state = ""
                beneficiary_bank_zip = ""
                lcra_client_no = None
                country = "USA"

                # Beneficiary Name
                if "Beneficiary Name" in file_data and file_data["Beneficiary Name"][i]:
                    beneficiary_name = str(file_data["Beneficiary Name"][i])

                # Beneficiary Account Number
                if (
                    "Beneficiary Account Number" in file_data
                    and file_data["Beneficiary Account Number"][i]
                ):
                    beneficiary_account_number = str(
                        file_data["Beneficiary Account Number"][i]
                    )
                    # if float, convert to int then str
                    if isinstance(file_data["Beneficiary Account Number"][i], float):
                        beneficiary_account_number = str(
                            int(file_data["Beneficiary Account Number"][i])
                        )

                # Beneficiary Account Type
                if (
                    "Beneficiary Account Type" in file_data
                    and file_data["Beneficiary Account Type"][i]
                ):
                    beneficiary_account_type = str(
                        file_data["Beneficiary Account Type"][i]
                    ).lower()
                    # if float, convert to int then str
                    if isinstance(file_data["Beneficiary Account Type"][i], float):
                        beneficiary_account_type = str(
                            int(file_data["Beneficiary Account Type"][i])
                        ).lower()

                # Beneficiary Address Line 1
                if (
                    "Beneficiary Address Line 1" in file_data
                    and file_data["Beneficiary Address Line 1"][i]
                ):
                    beneficiary_address_line_1 = str(
                        file_data["Beneficiary Address Line 1"][i]
                    )

                # Beneficiary City
                if "Beneficiary City" in file_data and file_data["Beneficiary City"][i]:
                    beneficiary_city = str(file_data["Beneficiary City"][i])

                # Beneficiary State
                if (
                    "Beneficiary State" in file_data
                    and file_data["Beneficiary State"][i]
                ):
                    beneficiary_state = str(file_data["Beneficiary State"][i])

                # Beneficiary Zip
                if "Beneficiary Zip" in file_data and file_data["Beneficiary Zip"][i]:
                    beneficiary_zip = str(file_data["Beneficiary Zip"][i])
                    # if float, convert to int then str
                    if isinstance(file_data["Beneficiary Zip"][i], float):
                        beneficiary_zip = str(int(file_data["Beneficiary Zip"][i]))

                # Beneficiary Bank Name
                if (
                    "Beneficiary Bank Name" in file_data
                    and file_data["Beneficiary Bank Name"][i]
                ):
                    beneficiary_bank_name = str(file_data["Beneficiary Bank Name"][i])

                # Beneficiary Bank Id
                if (
                    "Beneficiary Bank Id" in file_data
                    and file_data["Beneficiary Bank Id"][i]
                ):
                    beneficiary_bank_id = str(file_data["Beneficiary Bank Id"][i])
                    # if float, convert to int then str
                    if isinstance(file_data["Beneficiary Bank Id"][i], float):
                        beneficiary_bank_id = str(
                            int(file_data["Beneficiary Bank Id"][i])
                        )

                # Beneficiary Bank Address 1
                if (
                    "Beneficiary Bank Address 1" in file_data
                    and file_data["Beneficiary Bank Address 1"][i]
                ):
                    beneficiary_bank_address_1 = str(
                        file_data["Beneficiary Bank Address 1"][i]
                    )

                # Beneficiary Bank Address 2
                if (
                    "Beneficiary Bank Address 2" in file_data
                    and file_data["Beneficiary Bank Address 2"][i]
                ):
                    beneficiary_bank_address_2 = str(
                        file_data["Beneficiary Bank Address 2"][i]
                    )

                # Beneficiary Bank City
                if (
                    "Beneficiary Bank City" in file_data
                    and file_data["Beneficiary Bank City"][i]
                ):
                    beneficiary_bank_city = str(file_data["Beneficiary Bank City"][i])

                # Beneficiary Bank State
                if (
                    "Beneficiary Bank State" in file_data
                    and file_data["Beneficiary Bank State"][i]
                ):
                    beneficiary_bank_state = str(file_data["Beneficiary Bank State"][i])

                # Beneficiary Bank Zip
                if (
                    "Beneficiary Bank Zip" in file_data
                    and file_data["Beneficiary Bank Zip"][i]
                ):
                    beneficiary_bank_zip = str(file_data["Beneficiary Bank Zip"][i])
                    # if float, convert to int then str
                    if isinstance(file_data["Beneficiary Bank Zip"][i], float):
                        beneficiary_bank_zip = str(
                            int(file_data["Beneficiary Bank Zip"][i])
                        )

                # LCRA Client No
                if "LCRA Client No" in file_data and file_data["LCRA Client No"][i]:
                    lcra_client_no = str(file_data["LCRA Client No"][i])
                    # if float, convert to int then str
                    if isinstance(file_data["LCRA Client No"][i], float):
                        lcra_client_no = str(int(file_data["LCRA Client No"][i]))

                # checking, if client exists
                client = Client.query.filter(
                    Client.is_deleted == False,
                    not_(
                        Client.ref_client_no.in_(
                            [
                                "TODO-cadence",
                                "Cadence:sync-pending",
                                "TODO-factorcloud",
                            ]
                        )
                    ),
                    Client.lcra_client_accounts_number == lcra_client_no,
                ).first()
                                
                if client:
                    # checking, if payee exists having account_nickname == client name
                    payee = (
                        Payee.query.join(ClientPayee)
                        .filter(
                            Payee.account_nickname == beneficiary_name,
                            Payee.is_deleted == False,
                            Payee.is_active == True,
                            ClientPayee.is_deleted == False,
                            ClientPayee.ref_type == "client",
                        )
                        .first()
                    )

                    # data to be saved
                    req_data = {
                        "account_nickname": beneficiary_name,
                        "address_line_1": beneficiary_address_line_1,
                        "city": beneficiary_city,
                        "province": beneficiary_state,
                        "state_or_province": beneficiary_state,  # for payee
                        "country": country,
                        "postal_code": beneficiary_zip,
                        "phone": "",
                        "email": "",
                        "ref_type": "client",
                        "bank_name": beneficiary_bank_name,
                        "bank_address_line_1": beneficiary_bank_address_1,
                        "bank_address_line_2": beneficiary_bank_address_2,
                        "bank_city": beneficiary_bank_city,
                        "bank_province": beneficiary_bank_state,
                        "bank_country": country,
                        "bank_postal_code": beneficiary_bank_zip,
                        "bank_account_name": beneficiary_name,
                        "us_wire_banking_info": {
                            "swift_code": None,
                            "institution_routing": None,
                        },
                        "us_wire_intermediary_banking_info": {
                            "intermediary_bank_name": None,
                            "intermediary_bank_account": None,
                            "intermediary_bank_routing": None,
                        },
                        "us_ach_banking_info": {
                            "type": beneficiary_account_type,
                            "bank_name": beneficiary_bank_name,
                            "bank_id_ach": beneficiary_bank_id,
                            "account_number": beneficiary_account_number,
                        },
                    }
                    
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
                        
                    # delete state_or_province
                    if "state_or_province" in req_data:
                        del req_data["state_or_province"]
                        
                    # payment services
                    payment_services = PaymentServices(
                        request_type=payee, req_data=req_data
                    )
                    payment_services.add_in_payment_services()

                    db.session.flush()

                    print(client.id, "--added client as payee--", payee.id)
                print(beneficiary_name, "--beneficiary--", i)
            self.commit()
        except Exception as e:
            print(e)
            self.rollback()
