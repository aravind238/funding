import json
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
from src.resources.v2.helpers import PaymentServices
from sqlalchemy import and_, or_, not_
import pandas as pd
import numpy as np
from src.resources.v2.helpers.logs import Logs


class PayeesImportBoth(Command):
    def __init__(self, db=None, filename=None, sheetname="IMPORT BOTH"):
        self.db = db
        self.filename = filename
        self.sheetname = sheetname
        self.sheetname_lower = self.sheetname.lower().replace(" ", "_")

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            if not self.filename:
                print("please provide filename argument -f=filename.xlsx")
                return

            return self.import_both()

        except Exception as e:
            print(e)
            self.rollback()

    def read_file(self):
        # set engine parameter to "openpyxl", pandas has removed xlrd support for anything other than xls files
        file_data = pd.read_excel(
            self.filename,
            sheet_name=self.sheetname,
            engine="openpyxl",
            dtype=str,  # Keeping leading zeros(ex. 0913): converted to str
        )

        # if having value Null or NaN
        if not file_data.empty:
            file_data = file_data.replace(
                {
                    np.nan: None,
                    0: None,
                    "0": None,  # All values with 0 is actually NULL
                    "#REF!": None,  # All values with 0 is actually NULL
                }
            )

        return file_data

    def import_both(self):
        file_data = self.read_file()
        # print("--import ach--", file_data.columns)
        import_payees_list = []
        payees_to_be_imported_flag = 0
        payees_already_exist_flag = 0
        payees_imported_flag = 0
        payees_approved_flag = 0
        payees_draft_flag = 0

        for i in file_data.index:
            print("====start====")
            beneficiary_name = None
            bank_account_name = None
            beneficiary_account_number = None
            beneficiary_account_type = "checking"
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
            beneficiary_bank_institution_routing = None
            lcra_client_accounts_number = None
            country = "USA"

            # Beneficiary Name/ACH LIST
            if "Beneficiary Name" in file_data and file_data["Beneficiary Name"][i]:
                beneficiary_name = str(file_data["Beneficiary Name"][i])
            # elif (
            #     "ACH LIST" in file_data
            #     and file_data["ACH LIST"][i]
            # ):
            #     beneficiary_name = str(file_data["ACH LIST"][i])

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

            # # Beneficiary Account Type
            # if (
            #     "Beneficiary Account Type" in file_data
            #     and file_data["Beneficiary Account Type"][i]
            # ):
            #     beneficiary_account_type = str(
            #         file_data["Beneficiary Account Type"][i]
            #     ).lower()
            #     # if float, convert to int then str
            #     if isinstance(file_data["Beneficiary Account Type"][i], float):
            #         beneficiary_account_type = str(
            #             int(file_data["Beneficiary Account Type"][i])
            #         ).lower()

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
            if "Beneficiary State" in file_data and file_data["Beneficiary State"][i]:
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
                    beneficiary_bank_id = str(int(file_data["Beneficiary Bank Id"][i]))

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
            
            # bank account name
            if not bank_account_name:
                bank_account_name = beneficiary_name

            # Client ID
            if "Client ID" in file_data and file_data["Client ID"][i]:
                lcra_client_accounts_number = str(file_data["Client ID"][i])
                # if float, convert to int then str
                if isinstance(file_data["Client ID"][i], float):
                    lcra_client_accounts_number = str(int(file_data["Client ID"][i]))

            # Third Party: payee as third party
            payee_as_third_party = False
            if (
                "Third Party" in file_data 
                and file_data["Third Party"][i]
                and file_data["Third Party"][i] == "Yes"
            ):
                payee_as_third_party = True

            # checking, if client exists having control account == "LCEI. US"
            client = (
                Client.query.join(ClientControlAccounts, ControlAccount)
                .filter(
                    ControlAccount.is_deleted == False,
                    ClientControlAccounts.is_deleted == False,
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
                    ControlAccount.name == "LCEI. US",
                    Client.lcra_client_accounts_number == lcra_client_accounts_number,
                )
                .first()
            )
            print(lcra_client_accounts_number, '--client--', client)
            if client:
                
                client_payee_ref_type = "client"
                if payee_as_third_party:
                    client_payee_ref_type = "payee"

                # checking, if payee exists having account_nickname == beneficiary_name
                payee = (
                    Payee.query.join(ClientPayee)
                    .filter(
                        Payee.account_nickname == beneficiary_name,
                        Payee.is_deleted == False,
                        Payee.is_active == True,
                        ClientPayee.is_deleted == False,
                        ClientPayee.ref_type == client_payee_ref_type,
                        ClientPayee.client_id == client.id,
                        ClientPayee.payee_id == Payee.id,
                    )
                    .first()
                )

                payee_already_exist = False
                payee_not_exists = False
                # checking, if payee exists
                if payee:
                    payees_already_exist_flag += 1
                    payee_already_exist = True
                    # append word "import" if beneficinary name exists for approved payee
                    if payee.status.value == "approved":
                        beneficiary_name = f"{beneficiary_name} - import"
                        payee_not_exists = True

                else:
                    payee_not_exists = True

                # data to be saved
                req_data = {
                    "account_nickname": beneficiary_name,
                    "address_line_1": beneficiary_address_line_1,
                    "city": beneficiary_city,
                    "province": beneficiary_state,
                    "state_or_province": beneficiary_state,  # for payee table
                    "country": country,
                    "postal_code": beneficiary_zip,
                    "phone": "",
                    "email": "",
                    "ref_type": client_payee_ref_type,
                    "bank_name": beneficiary_bank_name,
                    "bank_address_line_1": beneficiary_bank_address_1,
                    "bank_address_line_2": beneficiary_bank_address_2,
                    "bank_city": beneficiary_bank_city,
                    "bank_province": beneficiary_bank_state,
                    "bank_country": country,
                    "bank_postal_code": beneficiary_bank_zip,
                    "bank_account_name": bank_account_name,
                    "us_wire_banking_info": {
                        "swift_code": None,
                        "institution_routing": None, # Institution Routing (WIRE)
                    },
                    "us_wire_intermediary_banking_info": {
                        "intermediary_bank_name": None,
                        "intermediary_bank_account": None,
                        "intermediary_bank_routing": None,
                    },
                    "us_ach_banking_info": {
                        "type": beneficiary_account_type,
                        "bank_name": beneficiary_bank_name,
                        "bank_id_ach": beneficiary_bank_id, # Institution Routing (ACH)
                        "account_number": beneficiary_account_number,
                    },
                }

                payee_imported = False
                if payee_not_exists:
                    payee_status_to_be = "draft"
                    payees_draft_flag += 1

                    # save payee
                    payee = Payee(req_data)
                    payee.last_processed_at = datetime.utcnow()
                    payee.status = payee_status_to_be
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

                    payee_imported = True
                    payees_imported_flag += 1

                import_payees_list.append(
                    {
                        "index": i,
                        "client_id": client.id,
                        "lcra_client_accounts_number": lcra_client_accounts_number,
                        "control_account": client.clients_control_account[
                            0
                        ].control_account.name,
                        "payee": payee.account_nickname,
                        "payee_id": payee.id,
                        "status": payee.status.value,
                        "payee_already_exist": payee_already_exist,
                        "payee_imported": payee_imported,
                        "import_data": req_data,
                    }
                )

                payees_to_be_imported_flag += 1

                # delete state_or_province
                if "state_or_province" in req_data:
                    del req_data["state_or_province"]

                # payment services
                payment_services = PaymentServices(
                    request_type=payee, req_data=req_data
                )
                payment_services.add_in_payment_services()

                db.session.flush()

                print(client.id, f"--added as {client_payee_ref_type}--", payee.id)
            print(beneficiary_name, "--import both - beneficiary--", i)
            print("====end====")

        import_payees_list.append(
            {
                "sheetname": self.sheetname,
                "total_payees_to_be_imported": payees_to_be_imported_flag,
                "total_payees_already_exist": payees_already_exist_flag,
                "total_payees_imported": payees_imported_flag,
                # "total_payees_approved": payees_approved_flag,
                "total_payees_draft": payees_draft_flag,
            }
        )

        # save imort payees data in logs
        logs = Logs(
            filename=f"payee_{self.sheetname_lower}_logs", data=import_payees_list
        )
        logs.save_logs()
        self.commit()
