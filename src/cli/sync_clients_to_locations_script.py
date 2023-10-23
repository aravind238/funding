import os
import requests
import json
from src import db
from flask_script import Command
from src.middleware.permissions import Permissions
from src.models import (
    Client,
    ClientControlAccounts,
    ControlAccount,
)
from sqlalchemy import and_, or_, not_


class SyncClientsToLocationsScript(Command):
    def __init__(self, db=None, business_ids=None):
        self.db = db
        self.business_id = None

        # get business ids from terminal command
        self.business_ids = str(business_ids)

        # checking, get business ids from .env
        if not business_ids:
            business_ids = str(os.getenv("SYNC_BUSINESS_IDS", ""))

        self.business_ids = [i for i in business_ids.split(",")]

        # location
        self.locations_host = os.getenv("LOCATIONS_HOST")
        self.locations_api_token = os.getenv("LOCATIONS_API_TOKEN")

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            if not self.business_ids or (
                len(self.business_ids) and "" in self.business_ids
            ):
                print("please provide business_ids")
                return

            print("-- business ids --", self.business_ids)
            
            for business_id in self.business_ids:
                self.business_id = business_id

                # Get control accounts for business_id
                business_control_accounts = Permissions.get_business_settings(
                    business_id=self.business_id
                )["control_accounts"]

                print("-- business control accounts --", business_control_accounts)

                # Get all the clients which are valid based off of business control accounts
                clients = (
                    Client.query.join(ClientControlAccounts, ControlAccount).filter(
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
                        ControlAccount.name.in_(business_control_accounts),
                    )
                ).all()

                # checking, if clients not found
                if not clients:
                    print(f"Clients not found")
                    return

                print("-- total clients --", len(clients))

                for client in clients:
                    # client data
                    req_data = {
                        "name": client.name,
                        "display_name": client.lcra_client_accounts_number,
                        "internal_id": client.lcra_client_accounts_id,
                        "is_corporate": False,
                    }

                    self.sync_clients_to_locations(params=req_data)

            print("<-- script end -->")
        except Exception as e:
            print(e)
            self.rollback()

    def sync_clients_to_locations(self, params={}):
        """_summary_: Sync clients to add in locations

        Args:
            params (dict, optional): _description_. Defaults to {}.
        """
        result_json = {}
        msg = "Something went wrong, please try again"
        status_code = 500
        try:
            # api endpoint
            url = (
                self.locations_host
                + "integrators/businesses/"
                + self.business_id
                + "/locations/create"
            )

            # defining a headers dict for the parameters to be sent to the API
            headers = {
                "Content-Type": "application/json",
                "api-token": self.locations_api_token,
            }

            # sending post request
            result = requests.post(url=url, headers=headers, json=params)

            # extracting data in json format
            result_json = result.json()
            status_code = result.status_code

            if "msg" in result_json:
                msg = result_json["msg"]

        except requests.ConnectionError as e:
            msg = f"Connection Error: {e}"
            status_code = 502
        except requests.HTTPError as e:
            msg = f"HTTP Error: {e}"
        except requests.Timeout as e:
            msg = f"Timeout Error: {e}"
            status_code = 408
        except Exception as e:
            msg = f"Sync clients to locations- RequestException Error: {e}"

        print({"status_code": status_code, "msg": msg, "response": result_json})
