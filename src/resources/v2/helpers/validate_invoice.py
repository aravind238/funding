from flask import request
from src.models import *
from src.resources.v2.schemas import *
import requests
from datetime import datetime
import os
from src.resources.v2.helpers import custom_response


def validate_invoice(client_ref_key):
    try:
        url = os.getenv("LC_THIRD_PARTY_API_URL") + "v1/cadence/getClientInvoices"

        # defining a headers dict for the parameters to be sent to the API
        headers = {
            "app-id": os.getenv("LC_THIRD_PARTY_APP_ID"),
            "app-secret": os.getenv("LC_THIRD_PARTY_APP_SECRET"),
        }
        # defining a params dict for the parameters to be sent to the API

        params = {"clientKey": client_ref_key}
        r = requests.get(url=url, params=params, headers=headers, timeout=8)

        # extracting data in json format
        data = r.json()

        if r.status_code == 200 and data["msg"] == "invoice already exists":
            return []

        return data["invoices"]

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


def validate_invoice_debtor(client_ref_key):
    try:
        url = os.getenv("LC_THIRD_PARTY_API_URL") + "v1/cadence/getClientDebtorInvoices"

        # defining a headers dict for the parameters to be sent to the API
        headers = {
            "app-id": os.getenv("LC_THIRD_PARTY_APP_ID"),
            "app-secret": os.getenv("LC_THIRD_PARTY_APP_SECRET"),
        }
        # defining a params dict for the parameters to be sent to the API

        params = {"clientKey": client_ref_key}
        r = requests.get(url=url, params=params, headers=headers, timeout=8)

        # extracting data in json format
        data = r.json()

        if r.status_code == 200 and data["msg"] == "invoice already exists":
            return []

        return data["invoices"]

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


class CadenceValidateInvoices:
    def __init__(
        self,
        soa,
        validate_invoices=[],
        debtor_ref_key_exists=False,
        run_aws_lambda=True,
    ):
        self.soa = soa
        self.client_ref_key = soa.client.ref_key
        self.validate_invoices = validate_invoices
        self.all_invoice_numbers = list(
            map(lambda invoice: invoice["invoice_number"], self.validate_invoices)
        )
        self.run_aws_lambda = run_aws_lambda

        self.funding_invoices = []
        self.funding_unique_invoices = []
        self.funding_unique_invoices_update = []
        self.cadence_invoices = []
        self.insert_invoices = []
        self.update_invoices = []

        self.debtor_ref_key_exists = debtor_ref_key_exists
        self.debtors = []
        self.debtor_swap = []

        self.already_exist_funding = []
        self.already_exist_cadence = []
        self.wrong_debtors = []
        self.valid_invoices = []
        self.wrong_invoice_data = []

        self.current_date = (
            self.validate_invoices[0]["current_date"]
            if self.validate_invoices
            and self.validate_invoices[0]
            and "current_date" in self.validate_invoices[0]
            and self.validate_invoices[0]["current_date"]
            else ""
        )

        self.get_debtors()
        self.get_invoices()

        if self.run_aws_lambda:
            self.compute_on_aws_lambda()
        else:
            self.compute_on_server()

        self.print_status()

    def compute_on_aws_lambda(self):
        self.aws_lambda_api_request()

    def compute_on_server(self):
        self.cadence_api_request()
        self.compute()

    def aws_lambda_api_request(self):
        api_url = os.getenv("PARSING_INVOICES_AWS_LAMBDA_URL")
        params = {
            "client_ref_key": self.client_ref_key,
            "validate_invoices": self.validate_invoices,
            "debtor_swap": str(self.debtor_swap),
            "debtors": str(self.debtors),
            "funding_invoices": str(self.funding_invoices),
            "debtor_ref_key_exists": self.debtor_ref_key_exists,
            "funding_unique_invoices": str(self.funding_unique_invoices),
            "funding_unique_invoices_update": str(self.funding_unique_invoices_update),
        }

        r = requests.post(url=api_url, json=params, timeout=30)
        if r.status_code == 200:
            data = r.json()
            self.already_exist_funding = data["already_exist_funding"]
            self.already_exist_cadence = data["already_exist_cadence"]
            self.wrong_debtors = data["wrong_debtors"]
            self.wrong_invoice_data = data["wrong_invoice_data"]
            self.insert_invoices = data["insert_invoices"]
            self.update_invoices = data["update_invoices"]

    def cadence_api_request(self):
        api_url = (
            os.getenv("LC_THIRD_PARTY_API_URL") + "v1/cadence/getClientDebtorInvoices"
        )
        api_headers = {
            "app-id": os.getenv("LC_THIRD_PARTY_APP_ID"),
            "app-secret": os.getenv("LC_THIRD_PARTY_APP_SECRET"),
        }
        invoice_debtors = []  # Get the list from imported invoices.
        params = {
            "clientKey": self.client_ref_key,
            "debtors": invoice_debtors,
            "invoices": self.all_invoice_numbers,
        }
        r = requests.post(url=api_url, json=params, headers=api_headers, timeout=8)
        if r.status_code == 200:
            data = r.json()
            self.cadence_invoices = data["invoices"]

    def get_debtors(self):
        # get all debtors by client_id
        all_debtors = (
            Debtor.query.join(ClientDebtor)
            .filter(Debtor.id == ClientDebtor.debtor_id)
            .filter(ClientDebtor.client == self.soa.client)
            .filter(Debtor.is_deleted == False)
        )

        self.debtors = dict(all_debtors.with_entities(Debtor.ref_key, Debtor.id).all())
        # swap key value pairs, just to get debtor ref key by debtor-id
        if not self.debtor_ref_key_exists:
            self.debtor_swap = dict(
                all_debtors.with_entities(Debtor.id, Debtor.ref_key).all()
            )

    def get_invoices(self):
        """
        Filter only invoices which needs to be compared.
        """
        all_invoices = (
            Invoice.query.join(Debtor, SOA)
            .filter(Invoice.client == self.soa.client)
            .filter(Debtor.id == Invoice.debtor)
            .filter(Invoice.is_deleted == False)
        )
        # pulling invoices only of approved/completed SOA(LC-2291)
        self.funding_invoices = (
            all_invoices.filter(Invoice.invoice_number.in_(self.all_invoice_numbers),
            SOA.status.in_(
                    [
                        "approved",
                        "completed",
                    ]
                ),
            )
            .with_entities(Debtor.ref_key, Invoice.invoice_number_lower)
            .all()
        )
        self.funding_unique_invoices = (
            all_invoices.filter(Invoice.soa_id == self.soa.id)
            .with_entities(
                Invoice.id, Invoice.client_id, Invoice.debtor, Invoice.invoice_number_lower
            )
            .all()
        )
        self.funding_unique_invoices_update = (
            all_invoices.filter(Invoice.soa_id == self.soa.id)
            .with_entities(
                Invoice.id, Invoice.client_id, Invoice.invoice_number_lower
            )
            .all()
        )

    @property
    def get_valid_invoices(self):
        return self.insert_invoices + self.update_invoices

    @property
    def get_already_exist_invoices(self):
        return self.already_exist_funding + self.already_exist_cadence

    @property
    def get_invoices_to_insert(self):
        return self.insert_invoices

    @property
    def get_invoices_to_update(self):
        return self.update_invoices

    @property
    def get_wrong_debtors(self):
        return self.wrong_debtors

    @property
    def get_wrong_invoice_data(self):
        return self.wrong_invoice_data

    def compute(self):
        insert_invoices = []
        update_invoices = []
        wrong_debtors = []
        already_exist_funding = []
        already_exist_cadence = []
        wrong_invoice_data = []

        for invoice in self.validate_invoices:
            # Don't need created_at and updated_at from frontend
            if "created_at" in invoice:
                del invoice["created_at"]

            if "updated_at" in invoice:
                del invoice["updated_at"]

            # print('imported-invoice',invoice),
            invoice_number = invoice["invoice_number"].lower() # converted to lowercase for matching with invoice_number_lower(invoice table)
            is_invoice_update = "id" in invoice

            # checking, if invoice_date is greater than current date(EST)
            if self.current_date and self.current_date < invoice["invoice_date"]:
                invoice["msg"] = f"invoice_date is greater than current date({self.current_date})"
                wrong_invoice_data.append(invoice)
                continue

            # Putting in this swap logic so that if invoices doesnt have ref_key, will fetch it from debtor-id swap
            if self.debtor_ref_key_exists:

                # Checking invoice['ref_key'] if debtorkey is not None
                ref_key = None
                if invoice["ref_key"]:
                    ref_key = int(invoice["ref_key"])

                # Checking against funding DB debtors - like ((36427,) in self.funding_invoices):
                if ref_key not in self.debtors.keys():
                    invoice["msg"] = "Invoice having wrong debtor"
                    wrong_debtors.append(invoice)
                    continue
            else:
                # Checking invoice['debtor'] if is not None
                debtor_id = None
                if invoice["debtor"]:
                    debtor_id = int(invoice["debtor"])

                if debtor_id not in self.debtor_swap.keys():
                    invoice["msg"] = "Invoice having wrong debtor"
                    wrong_debtors.append(invoice)
                    continue
                ref_key = self.debtor_swap[debtor_id]

            # Validate invoices which are for update.
            if is_invoice_update:
                # 1. checking invoice number is unique on invoice update
                # - Checking against funding DB invoices - like ((191590, 1572, 38143, 'we13') in self.funding_unique_invoices) and
                # 2. checking ref_key and invoice number is unique(funding DB invoices(soa approved/completed)) on invoice update(LC-2291)
                # - Checking against funding DB invoices(soa approved/completed) - like ((38143, 'we13') in self.funding_invoices):
                if (
                    (
                        invoice["id"],
                        invoice["client_id"],
                        invoice["debtor"],
                        invoice_number,
                    )
                    in self.funding_unique_invoices
                    and ((ref_key, invoice_number) not in self.funding_invoices)
                # Checking against ref_key == 0 and funding DB invoices - like ((191590, 1572, 'we13') in self.funding_invoices):
                ) or (
                    not ref_key
                    and (
                        invoice["id"],
                        invoice["client_id"],
                        invoice_number,
                    )
                    in self.funding_unique_invoices_update
                    and ((ref_key, invoice_number) not in self.funding_invoices)
                # Checking against funding DB invoices - like ((0, 'we13') not in self.funding_invoices):
                ) or ((ref_key, invoice_number) not in self.funding_invoices):
                    update_invoices.append(invoice)
                    continue

            # Checking against funding DB invoices- like ((36427, '43d2d17c6d0b51f69d049541e3977a3133xx') in self.funding_invoices):
            if (ref_key, invoice_number) in self.funding_invoices:
                already_exist_funding.append(invoice)
                continue

            # Checking against funding DB invoices- like ('4606|OA-7353 in self.cadence_invoices):
            # And invoice isn't updating
            if f"{ref_key}|{invoice_number}" in self.cadence_invoices:
                already_exist_cadence.append(invoice)
                continue

            # After uploading frontend is listing for this key for updating debtor name.
            invoice.update({"debtor_id": self.debtors[ref_key]})
            insert_invoices.append(invoice)

        self.already_exist_funding = already_exist_funding
        self.already_exist_cadence = already_exist_cadence
        self.wrong_debtors = wrong_debtors
        self.insert_invoices = insert_invoices
        self.update_invoices = update_invoices
        self.wrong_invoice_data = wrong_invoice_data

    def print_status(self):
        print(
            {
                # "self.cadence_invoices": self.cadence_invoices,
                "self.validate_invoices": len(self.validate_invoices),
                "self.cadence_invoices": len(self.cadence_invoices),
                "self.funding_invoices": len(self.funding_invoices),
            }
        )
