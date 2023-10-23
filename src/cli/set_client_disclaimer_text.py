from src import db
from flask_script import Command
from src.models import (
    Client,
    ClientSettings,
    Disclaimers,
)
import pandas as pd
import numpy as np


class SetClientDisclaimerText(Command):
    def __init__(self, db=None, disclaimer_name="Quebec", filename=None):
        self.db = db
        self.disclaimer_name = disclaimer_name
        self.filename = filename

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()

    def run(self):
        try:
            if not self.filename:
                print("please provide filename argument -f=filename.xlsx")
                return

            file_data = []
            ref_client_no = None
            client_name = None
            try:
                file_data = pd.read_excel(self.filename, engine="openpyxl")

                # if having value Null or NaN
                if not file_data.empty:
                    file_data = file_data.replace({np.nan: None})
            except FileNotFoundError as e:
                print(f"no such file found of name {self.filename}")
                return

            # clients_list = []
            # [clients_list.append(i) for i in file_data["ClientNo"]]

            disclaimer = Disclaimers.query.filter_by(
                is_deleted=False, name=self.disclaimer_name
            ).first()

            for k in file_data.to_dict(orient="records"):
                # ref_client_no: get "ClientNo" from file
                if "ClientNo" in k and k["ClientNo"]:
                    ref_client_no = k["ClientNo"]

                # client_name: get "Client" from file
                if "Client" in k and k["Client"]:
                    client_name = k["Client"]

                client = Client.query.filter(
                    Client.is_deleted == False, Client.ref_client_no == ref_client_no
                ).first()

                if not client:
                    print(f"Client {client_name} not found")
                    continue

                client_settings = client.client_settings
                if client_settings:
                    client_settings[0].disclaimer_text = disclaimer.text
                    db.session.flush()
                    print(
                        "client",
                        client.id,
                        "--updated client settings--",
                        client_settings,
                    )
                else:
                    client_settings_obj = {
                        "client_id": client.id,
                        "disclaimer_text": disclaimer.text,
                    }
                    add_client_settings = ClientSettings(client_settings_obj)
                    add_client_settings.save()
                    db.session.flush()
                    print(
                        "client",
                        client.id,
                        "--updated client settings--",
                        add_client_settings,
                    )

                print(ref_client_no, "--file records--", k)
            self.commit()
        except Exception as e:
            print(e)
            self.rollback()
