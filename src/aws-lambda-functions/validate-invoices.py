import json
import time
import requests


print("Loading function")


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    client_ref_key = event["client_ref_key"]
    validate_invoices = event["validate_invoices"]
    debtors = event["debtors"]
    debtor_swap = event["debtor_swap"]
    funding_invoices = event["funding_invoices"]
    funding_unique_invoices = event["funding_unique_invoices"]
    funding_unique_invoices_update = event["funding_unique_invoices_update"]
    debtor_ref_key_exists = event["debtor_ref_key_exists"]

    # Re-mapping [String to list of tuples]
    if len(funding_invoices) and len(debtors):
        debtors = eval(debtors)
        funding_invoices = list(eval(funding_invoices))
        funding_unique_invoices = list(eval(funding_unique_invoices))
        funding_unique_invoices_update = list(eval(funding_unique_invoices_update))

    if len(debtor_swap):
        debtor_swap = eval(debtor_swap)

    validated_invoices = CadenceValidateInvoices(
        client_ref_key=client_ref_key,
        validate_invoices=validate_invoices,
        debtors=debtors,
        debtor_swap=debtor_swap,
        debtor_ref_key_exists=debtor_ref_key_exists,
        funding_invoices=funding_invoices,
        funding_unique_invoices=funding_unique_invoices,
        funding_unique_invoices_update=funding_unique_invoices_update,
    )
    return validated_invoices.get_return_payload


class CadenceValidateInvoices:
    def __init__(
        self,
        client_ref_key="",
        validate_invoices=[],
        debtors=[],
        debtor_swap=[],
        debtor_ref_key_exists=False,
        funding_invoices=[],
        funding_unique_invoices=[],
        funding_unique_invoices_update=[],
    ):
        self.cadence_invoices = []
        self.client_ref_key = client_ref_key
        self.validate_invoices = validate_invoices
        self.funding_invoices = funding_invoices
        self.funding_unique_invoices = funding_unique_invoices
        self.funding_unique_invoices_update = funding_unique_invoices_update
        self.all_invoice_numbers = list(
            map(lambda invoice: invoice["invoice_number"], self.validate_invoices)
        )

        # Debtors
        self.debtors = debtors
        self.debtor_swap = debtor_swap
        self.debtor_ref_key_exists = debtor_ref_key_exists

        # Init Variables
        self.already_exist_funding = []
        self.already_exist_cadence = []
        self.wrong_debtors = []
        self.insert_invoices = []
        self.update_invoices = []
        self.wrong_invoice_data = []

        self.current_date = (
            self.validate_invoices[0]["current_date"]
            if self.validate_invoices
            and self.validate_invoices[0]
            and "current_date" in self.validate_invoices[0]
            and self.validate_invoices[0]["current_date"]
            else ""
        )

        # Calling methods
        self.cadence_api_request()
        self.compute()
        self.print_status()

    def cadence_api_request(self):
        # Third Party API's
        api_url = "https://lc-third-party.dev.api.50c.io/api/v1/cadence/getClientDebtorInvoices"
        api_headers = {
            "app-id": "ATnfvRJAXe0xpHTfFy1yP3gPaD2uBQc1",
            "app-secret": "RLtCnIdpX6bRietkhkQmsxqwGnYrMG2r",
        }
        invoice_debtors = []  # Get the list from imported invoices.
        params = {
            "clientKey": self.client_ref_key,
            "debtors": invoice_debtors,
            "invoices": self.all_invoice_numbers,
        }
        r = requests.post(url=api_url, json=params, headers=api_headers, timeout=8)
        print(r.json())
        if r.status_code == 200:
            data = r.json()
            self.cadence_invoices = data["invoices"]

    def compute(self):
        print("## Starting")
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

            # print('imported-invoice',invoice)
            invoice_number = invoice["invoice_number"].lower() # converted to lowercase for matching with invoice_number_lower(invoice table)
            is_invoice_update = "id" in invoice

            # checking, if invoice_date is greater than current date(EST)
            if self.current_date and self.current_date < invoice["invoice_date"]:
                invoice[
                    "msg"
                ] = f"invoice_date is greater than current date({self.current_date})"
                wrong_invoice_data.append(invoice)
                continue

            # Putting in this swap logic so that if invoices doesnt have ref_key, will fetch it from debtor-id swap
            if self.debtor_ref_key_exists:
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

    @property
    def get_return_payload(self):
        return {
            "already_exist_funding": self.already_exist_funding,
            "already_exist_cadence": self.already_exist_cadence,
            "wrong_debtors": self.wrong_debtors,
            "wrong_invoice_data": self.wrong_invoice_data,
            "insert_invoices": self.insert_invoices,
            "update_invoices": self.update_invoices,
        }

    def print_status(self):
        print(
            {
                "self.already_exist_funding": self.already_exist_funding,
                "self.already_exist_cadence": self.already_exist_cadence,
                "self.wrong_debtors": self.wrong_debtors,
                "self.wrong_invoice_data": self.wrong_invoice_data,
                "self.insert_invoices": self.insert_invoices,
                "self.update_invoices": self.update_invoices,
            }
        )
