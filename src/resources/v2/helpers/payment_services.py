import requests
import os
from decimal import Decimal


class PaymentServices:
    def __init__(self, request_type=None, req_data=None) -> None:
        # Payment Services
        self.url = os.environ.get("PAYMENT_URL")
        self.api_token = os.environ.get("PAYMENT_API_TOKEN")

        # Payment Processing
        self.payment_processing_url = os.environ.get("PAYMENT_PROCESSING_URL")
        self.payment_processing_api_token = os.environ.get("PAYMENT_PROCESSING_API_TOKEN")

        # request_type = payee|client
        self.request_type = request_type
        self.request_type_dict = request_type.__dict__ if request_type else None
        self.ref_id_type = (
            req_data["ref_type"] if req_data and "ref_type" in req_data else None
        )

        self.debtor = "debtor"
        self.creditor = "creditor"
        self.get_all = False
        self.req_data = req_data
        self.accounts_banking_label = [
            "bank_account_name",
            "us_wire_banking_info",
            "us_wire_intermediary_banking_info",
            "us_ach_banking_info",
            "canada_wire_banking_info",
            # "canada_eft_banking_info", # LC-1636
        ]

    @property
    def request_id(self):
        return self.request_type.id if self.request_type else None

    @property
    def object_string(self):
        return (
            self.request_type.object_as_string().lower() if self.request_type else None
        )

    @property
    def entity_type(self):
        if self.ref_id_type == "payee" or self.ref_id_type == "client":
            return self.creditor
        else:
            return self.debtor

    def get_entity(self, params=""):
        send_request = requests.get(
            self.url + f"api/v1/entity{params}",
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None
        # print("--get_entity payload--", payload)
        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def get_entity_details(self, params=""):
        send_request = requests.get(
            self.url + f"api/v1/entity/details{params}",
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None
        
        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def save_entity(self, data={}):
        # print("--save_entity--", data)
        send_request = requests.post(
            self.url + f"api/v1/entity",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def update_entity(self, id=None, data={}):
        # print("--update_entity--", data)
        send_request = requests.patch(
            self.url + f"api/v1/entity/{id}",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def save_entity_meta(self, data={}):
        # print("--save_entity_meta--", data)
        send_request = requests.post(
            self.url + f"api/v1/entity_meta",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def save_institution(self, data={}):
        # print("--save_institution--", data)
        send_request = requests.post(
            self.url + f"api/v1/institution",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def update_institution(self, id=None, data={}):
        # print("--update_institution--", data)
        send_request = requests.patch(
            self.url + f"api/v1/institution/{id}",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def get_institution(self, params=""):
        # print("--get_institution--", params)
        send_request = requests.get(
            self.url + f"api/v1/institution{params}",
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def update_entity_contact_details(self, id=None, data={}):
        # print("--update_entity_contact_details--", data)
        send_request = requests.patch(
            self.url + f"api/v1/contact_detail/{id}",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def save_entity_contact_details(self, data={}):
        # print("--save_entity_contact_details--", data)
        send_request = requests.post(
            self.url + f"api/v1/contact_detail",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def get_entity_contact_details(self, params=""):
        # print("--get_entity_contact_details--", params)
        send_request = requests.get(
            self.url + f"api/v1/contact_detail{params}",
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None
        # print(params, "--get_entity_contact_details--", msg, payload)
        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def get_entity_address(self, params=""):
        # print("--get_entity_address--", params)
        send_request = requests.get(
            self.url + f"api/v1/address{params}",
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def save_entity_address(self, data={}):
        # print("--save_entity_address--", data)
        send_request = requests.post(
            self.url + f"api/v1/address",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def update_entity_address(self, id=None, data={}):
        # print("--update_entity_address--", data)
        send_request = requests.patch(
            self.url + f"api/v1/address/{id}",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def save_institution_accounts(self, data={}):
        # print("--save_institution_accounts--", data)
        send_request = requests.post(
            self.url + f"api/v1/accounts",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def update_institution_accounts(self, id=None, data={}):
        # print("--update_institution_accounts--", data)
        send_request = requests.patch(
            self.url + f"api/v1/accounts/{id}",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def get_institution_accounts(self, params=""):
        # print("--get_institution_accounts--", params)
        send_request = requests.get(
            self.url + f"api/v1/accounts{params}",
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None

        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }

    def add_in_payment_services(self):
        # save entity
        saved_entity = self.add_in_entity()

        # checking, if data saved/updated in entity
        if saved_entity["status_code"] in [200, 201]:
            entity_id = saved_entity["payload"]["id"]

            # checking, if entity' label exists in entity contact detail
            if self.request_type_dict and "email" in self.request_type_dict:
                self.add_in_entity_contact_details(entity_id=entity_id, label="email")
                # print("--payee email--", self.request_type.email)

            if self.request_type_dict and "phone" in self.request_type_dict:
                self.add_in_entity_contact_details(entity_id=entity_id, label="phone")
                # print("--payee phone--", self.request_type.phone)

            saved_entity_address = self.add_in_entity_address(entity_id=entity_id)
            print("--saved_entity_address--", saved_entity_address)

            saved_institution = self.add_in_institution(entity_id=entity_id)
            print("--saved_institution--", saved_institution)

            if (
                saved_institution["status_code"] in [200, 201]
                and saved_institution["payload"]
            ):
                institution_id = saved_institution["payload"]["id"]

                saved_institution_accounts = self.add_in_institution_accounts(
                    institution_id=institution_id,
                )
                print("--saved_institution_accounts--", saved_institution_accounts)

    def add_in_entity(self):
        # get entity
        get_entity = self.get_entity(
            params=f"?ref_id={self.request_id}&ref_id_type={self.ref_id_type}&get_all={self.get_all}"
        )

        entity_data = {
            "entity_type": f"{self.entity_type}",
            "ref_id": f"{self.request_id}",
            "ref_id_type": f"{self.ref_id_type}",
        }

        # # payee first name
        # first_name = (
        #     self.req_data["first_name"] if "first_name" in self.req_data else None
        # )
        # # payee last name
        # last_name = self.req_data["last_name"] if "last_name" in self.req_data else None
        # payee account nickname
        account_nickname = self.req_data["account_nickname"] if "account_nickname" in self.req_data else None

        # # first name not none
        # if first_name and not last_name:
        #     entity_data.update({"name": first_name})
        # # last name not none
        # if not first_name and last_name:
        #     entity_data.update({"name": last_name})
        # # first name and last name not none
        # if first_name and last_name:
        #     entity_data.update({"name": first_name + " " + last_name})

        if account_nickname:
            entity_data.update({"name": account_nickname})

        # checking, if entity already exists
        if get_entity["status_code"] == 200 and get_entity["payload"]:
            # print("--get_entity--", get_entity["payload"])
            entity_id = get_entity["payload"]["id"]

            # update existing data in entity
            saved_entity = self.update_entity(id=entity_id, data=entity_data)
            print("--updated_entity--", saved_entity)
        else:
            # save new data in entity
            saved_entity = self.save_entity(data=entity_data)
            print("--saved_entity--", saved_entity)

        return saved_entity

    def add_in_entity_contact_details(self, entity_id=None, label=None):
        get_request_type_key = {
            key for key in self.request_type_dict.keys() if label == key
        }
        saved_contact_details = {
            "status_code": 404,
            "msg": f"{label} not found",
            "payload": None,
        }

        # print(label, "--label--", get_request_type_key)
        # checking, if entitys' label exists in entity contact detail
        if label and self.request_type_dict[label]:
            get_entity_contact_details = self.get_entity_contact_details(
                params=f"?entity_id={entity_id}&label={label}&get_all={self.get_all}"
            )
            if (
                get_entity_contact_details["status_code"] == 200
                and get_entity_contact_details["payload"]
            ):
                contact_details_id = get_entity_contact_details["payload"]["id"]
                
                # update data in address of entity
                saved_contact_details = self.update_entity_contact_details(
                    id=contact_details_id,
                    data={"contact_value": self.request_type_dict[label]},
                )
                print("--updated contact_details email--", saved_contact_details)
            else:
                # save new data in address of entity
                saved_contact_details = self.save_entity_contact_details(
                    data={
                        "entity_id": f"{entity_id}",
                        "label": f"{label}",
                        "contact_value": self.request_type_dict[label],
                    }
                )
            print("--saved contact_details email--", saved_contact_details)
        return saved_contact_details

    def add_in_entity_address(self, entity_id=None):
        # get entity address
        get_entity_address = self.get_entity_address(
            params=f"?entity_id={entity_id}&get_all={self.get_all}"
        )

        # checking, if entity address exists
        if get_entity_address["status_code"] == 200 and get_entity_address["payload"]:
            address_id = get_entity_address["payload"]["id"]

            address_line_1 = (
                self.request_type_dict["address_line_1"]
                if "address_line_1" in self.request_type_dict
                else get_entity_address["payload"]["address_line_1"]
            )
            # address_line_2 = (
            #     self.request_type_dict["address_line_2"]
            #     if "address_line_2" in self.request_type_dict
            #     else get_entity_address["payload"]["address_line_2"]
            # )
            city = (
                self.request_type_dict["city"]
                if "city" in self.request_type_dict
                else get_entity_address["payload"]["city"]
            )
            province = (
                self.request_type_dict["state_or_province"]
                if "state_or_province" in self.request_type_dict
                else get_entity_address["payload"]["province"]
            )
            country = (
                self.request_type_dict["country"]
                if "country" in self.request_type_dict
                else get_entity_address["payload"]["country"]
            )
            postal_code = (
                self.request_type_dict["postal_code"]
                if "postal_code" in self.request_type_dict
                else get_entity_address["payload"]["postal_code"]
            )

            # data to be updated in address
            entity_address_data = {
                "address_line_1": address_line_1,
                # "address_line_2": address_line_2,
                "city": city,
                "province": province,
                "country": country,
                "postal_code": postal_code,
            }

            # update data in address of entity
            saved_entity_address = self.update_entity_address(
                id=address_id, data=entity_address_data
            )
            print(address_id, "--updated_entity_address--", saved_entity_address)
        else:
            address_line_1 = (
                self.request_type_dict["address_line_1"]
                if "address_line_1" in self.request_type_dict
                else None
            )
            # address_line_2 = (
            #     self.request_type_dict["address_line_2"]
            #     if "address_line_2" in self.request_type_dict
            #     else None
            # )
            city = (
                self.request_type_dict["city"]
                if "city" in self.request_type_dict
                else None
            )
            province = (
                self.request_type_dict["state_or_province"]
                if "state_or_province" in self.request_type_dict
                else None
            )
            country = (
                self.request_type_dict["country"]
                if "country" in self.request_type_dict
                else None
            )
            postal_code = (
                self.request_type_dict["postal_code"]
                if "postal_code" in self.request_type_dict
                else None
            )

            # data to be saved in address
            entity_address_data = {
                "entity_id": entity_id,
                "address_line_1": address_line_1,
                # "address_line_2": address_line_2,
                "city": city,
                "province": province,
                "country": country,
                "postal_code": postal_code,
            }

            # save new data in address of entity
            saved_entity_address = self.save_entity_address(data=entity_address_data)

        return saved_entity_address

    def add_in_institution(self, entity_id=None):
        get_institution = self.get_institution(
            params=f"?entity_id={entity_id}&get_all={self.get_all}"
        )

        # bank name
        bank_name = (
            self.req_data["bank_name"] if "bank_name" in self.req_data else None
        )
        
        # bank address line 1
        if "bank_address_line_1" in self.req_data:
            address_line_1 = self.req_data["bank_address_line_1"]
        elif "address_line_1" in self.req_data:
            address_line_1 = self.req_data["address_line_1"]
        else: 
            address_line_1 = None
        
        # bank address line 2
        if "bank_address_line_2" in self.req_data:
            address_line_2 = self.req_data["bank_address_line_2"]
        elif "address_line_2" in self.req_data:
            address_line_2 = self.req_data["address_line_2"]
        else: 
            address_line_2 = None
        
        # bank city
        if "bank_city" in self.req_data:
            city = self.req_data["bank_city"]
        elif "city" in self.req_data:
            city = self.req_data["city"]
        else: 
            city = None
        
        # bank province
        if "bank_province" in self.req_data:
            province = self.req_data["bank_province"]
        elif "state_or_province" in self.req_data:
            province = self.req_data["state_or_province"]
        else: 
            province = None

        # bank country
        if "bank_country" in self.req_data:
            country = self.req_data["bank_country"]
        elif "country" in self.req_data:
            country = self.req_data["country"]
        else: 
            country = None

        # bank postal code
        if "bank_postal_code" in self.req_data:
            postal_code = self.req_data["bank_postal_code"]
        elif "postal_code" in self.req_data:
            postal_code = self.req_data["postal_code"]
        else: 
            postal_code = None
        
        # checking, if institution exists
        if get_institution["status_code"] == 200 and get_institution["payload"]:
            institution_id = get_institution["payload"]["id"]

            if not bank_name:
                get_institution["payload"]["name"]

            if not address_line_1:
                get_institution["payload"]["address_line_1"]
            
            if not address_line_2:
                get_institution["payload"]["address_line_2"]

            if not city:
                get_institution["payload"]["city"]

            if not province:
                get_institution["payload"]["province"]

            if not postal_code:
                get_institution["payload"]["postal_code"]

            if not country:
                get_institution["payload"]["country"]

            institution_data = {
                "name": bank_name,
                "address_line_1": address_line_1,
                "address_line_2": address_line_2,
                "city": city,
                "province": province,
                "postal_code": postal_code,
                "country": country,
            }

            # update data in institution
            saved_institution = self.update_institution(
                id=institution_id, data=institution_data
            )
            print(institution_id, "--updated_institution--", saved_institution)
        else:

            institution_data = {
                "entity_id": entity_id,
                "name": bank_name,
                "address_line_1": address_line_1,
                "address_line_2": address_line_2,
                "city": city,
                "province": province,
                "postal_code": postal_code,
                "country": country,
            }

            # save new data in institution
            saved_institution = self.save_institution(data=institution_data)

        return saved_institution

    def add_in_institution_accounts(self, institution_id=None):
        banking_label_key = list(
            key
            for key in self.req_data.keys()
            if self.req_data and key in self.accounts_banking_label
        )
        # print(banking_label_key, "--banking_label_key--", banking_label_key)

        saved_institution_accounts = None
        if banking_label_key and len(banking_label_key) > 0:
            for label_key in banking_label_key:
                params = f"?institution_id={institution_id}&get_all={self.get_all}"
                if label_key:
                    params = f"{params}&label={label_key}"

                banking_info = {}
                if self.req_data:
                    if f"{label_key}" in self.req_data and not isinstance(
                        self.req_data[label_key], dict
                    ):
                        banking_info.update({f"{label_key}": self.req_data[label_key]})
                    if f"{label_key}" in self.req_data and isinstance(
                        self.req_data[label_key], dict
                    ):
                        banking_info.update(self.req_data[label_key])
                            
                # checking, if institution accounts exists
                get_institution_accounts = self.get_institution_accounts(params=params)

                if (
                    get_institution_accounts["status_code"] == 200
                    and get_institution_accounts["payload"]
                ):
                    institution_accounts_id = get_institution_accounts["payload"]["id"]
                    
                    if not banking_info:
                        banking_info = (
                            get_institution_accounts["payload"][label_key]
                            if f"{label_key}" in get_institution_accounts["payload"]
                            else None
                        )

                    # if banking_info and not isinstance(banking_info, dict):
                    #     banking_info = dict(banking_info)
                    
                    # update data of institution accounts
                    if banking_info and isinstance(banking_info, dict):
                        saved_institution_accounts = self.update_institution_accounts(
                            id=institution_accounts_id,
                            data={"label": label_key, "attribute": banking_info},
                        )
                        print(
                            "--updated_institution_accounts--", saved_institution_accounts
                        )
                else:
                    # banking_info = (
                    #     self.req_data[label_key]
                    #     if self.req_data and f"{label_key}" in self.req_data
                    #     else None
                    # )
                    
                    # if banking_info and not isinstance(banking_info, dict):
                    #     banking_info = dict(banking_info)
                    
                    # save data in institution accounts
                    saved_institution_accounts = self.save_institution_accounts(
                        data={
                            "institution_id": institution_id,
                            "label": label_key,
                            "attribute": banking_info,
                        }
                    )
                    print("--saved_institution_accounts--", saved_institution_accounts)
                

            return saved_institution_accounts

    def get_institution_details(self, ref_id=None, ref_id_type=None):
        url_params = self.url + f"api/v1/institution/accounts"

        if ref_id and not ref_id_type:
            url_params = self.url + f"api/v1/institution/accounts?ref_id={ref_id}"

        if not ref_id and ref_id_type:
            url_params = (
                self.url + f"api/v1/institution/accounts?ref_id_type={ref_id_type}"
            )

        if ref_id and ref_id_type:
            url_params = (
                self.url
                + f"api/v1/institution/accounts?ref_id={ref_id}&ref_id_type={ref_id_type}"
            )

        send_request = requests.get(
            url_params,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None
        # print("--get_institution_details--", payload)
        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }


    def payment_processing(self, data={}):
        send_request = requests.post(
            self.url + f"api/v1/transaction/process",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None
        
        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }


    def transaction_status(self, data={}):
        send_request = requests.post(
            self.url + f"api/v1/transaction/status",
            json=data,
            headers={"api-token": self.api_token},
        )

        # extracting data in json format
        result_json = send_request.json()
        payload = result_json["payload"] if "payload" in result_json else None
        msg = result_json["msg"] if "msg" in result_json else None
        
        return {
            "status_code": send_request.status_code,
            "msg": msg,
            "payload": payload,
        }
        

    # def payment_processing(self, data={}):
    #     # currency
    #     currency = (
    #         data["currency"] 
    #         if "currency" in data and data["currency"] 
    #         else None
    #     )

    #     # disbursement_id
    #     disbursement_id = (
    #         data["disbursement_id"] 
    #         if "disbursement_id" in data and data["disbursement_id"] 
    #         else None
    #     )

    #     # amount
    #     amount = (
    #         Decimal(data["amount"])
    #         if "amount" in data and data["amount"]
    #         else Decimal(0)
    #     )
    #     # ref_type
    #     self.ref_type = (
    #         data["ref_type"] 
    #         if "ref_type" in data and data["ref_type"] 
    #         else None
    #     )
    #     # ref_id
    #     ref_id = (
    #         data["ref_id"] 
    #         if "ref_id" in data and data["ref_id"] 
    #         else None
    #     )
        
    #     # get transaction
    #     get_transaction = self.get_transaction(
    #         params=f"?ref_id={disbursement_id}&get_all=false"
    #     )

    #     if get_transaction["status_code"] == 200 and get_transaction["payload"]:
    #         print(get_transaction, f"payment already done for disbursement - {disbursement_id}")
    #         return

    #     entity_name = None
    #     entity_id = None
    #     institution_id = None
    #     postal_code = None
    #     institution_accounts_id = None
    #     account_number = None
    #     bank_name = None
    #     bank_id_ach = None
    #     entity_address = {
    #         "address_line_1": "",
    #         "address_line_2": "",
    #         "city": "",
    #         "postal_code": "",
    #         "country": "us"
    #     }
    #     institution_address = {
    #         "address_line_1": "",
    #         "address_line_2": "",
    #         "city": "",
    #         "postal_code": "",
    #         "country": "us"
    #     }

    #     # get entity
    #     get_entity = self.get_entity_details(
    #         params=f"?ref_id={ref_id}&ref_id_type={self.ref_type}"
    #     )

    #     # get entity, if entity exists
    #     if get_entity["status_code"] == 200 and get_entity["payload"]:
    #         entity_id = get_entity["payload"]["id"]
    #         entity_name = get_entity["payload"]["name"]
            
    #         # get entity address, if entity address exists
    #         if "address" in get_entity["payload"] and get_entity["payload"]["address"]:
    #             address = get_entity["payload"]["address"]
    #             address_postal_code = address["postal_code"]
    #             entity_address = {
    #                 "address_line_1": address["address_line_1"],
    #                 "address_line_2": address["address_line_2"],
    #                 "city": address["city"],
    #                 "postal_code": address_postal_code,
    #                 "country": "us"
    #             }
            
    #         # get institution, if institution exists
    #         if "institution" in get_entity["payload"] and get_entity["payload"]["institution"]:
    #             institution = get_entity["payload"]["institution"]
    #             institution_id = institution["id"]
    #             # if postal_code null in institution then postal_code from entity->address
    #             postal_code = (
    #                 institution["postal_code"]
    #                 if institution["postal_code"]
    #                 else address_postal_code
    #             )
    #             institution_address = {
    #                 "address_line_1": institution["address_line_1"],
    #                 "address_line_2": institution["address_line_2"],
    #                 "city": institution["city"],
    #                 "postal_code": postal_code,
    #                 "country": "us"
    #             }
                
    #             # checking, if institution accounts exists
    #             if "accounts" in institution and institution["accounts"]:
    #                 accounts = institution["accounts"]
    #                 print('--acc--', accounts)
    #                 for account in accounts:
    #                     if account["label"] == "us_ach_banking_info":
    #                         institution_accounts_id = account["id"]
    #                         attribute = account["attribute"]
    #                         account_number = (
    #                             attribute["account_number"]
    #                             if "account_number" in attribute and attribute["account_number"]
    #                             else None
    #                         )
    #                         bank_name = (
    #                             attribute["bank_name"]
    #                             if "bank_name" in attribute and attribute["bank_name"]
    #                             else None
    #                         )
    #                         bank_id_ach = (
    #                             attribute["bank_id_ach"]
    #                             if "bank_id_ach" in attribute and attribute["bank_id_ach"]
    #                             else None
    #                         )

    #     ## data for bofa payment transaction ##
    #     # for now debtor details hardcoded
    #     payment_json_data = {
    #         "amount": amount,
    #         "type": "CREDIT",
    #         "debtor_name": "Richard Coles",
    #         "debtor_identification": "3980446851",
    #         "debtor_account_name": "debtor account",
    #         "debtor_account_identification": "223015370191",
    #         "debtor_account_currency": currency,
    #         "debtor_institution_identification": "3980446851",
    #         "debtor_institution_address": {
    #             "address_line_1": "921 W New Hope Dr",
    #             "address_line_2": "Ste 702",
    #             "city": "Cedar Park",
    #             "postal_code": "78613",
    #             "country": "us"
    #         },
    #         "creditor_name": entity_name,
    #         "creditor_identification": entity_id,
    #         "creditor_address": entity_address,
    #         "creditor_account_name": bank_name,
    #         "creditor_account_identification": account_number,
    #         "creditor_account_currency": currency,
    #         "creditor_institution_identification": bank_id_ach,
    #         "creditor_institution_address": institution_address,
    #         "reason": "testing"
    #     }

    #     send_request = requests.post(
    #         self.payment_processing_url + f"api/v1/bofa/transactions/payments",
    #         json=payment_json_data,
    #         headers={"x-api-token": self.payment_processing_api_token},
    #     )

    #     # extracting data in json format
    #     payment_processed_result_json = send_request.json()
    #     payment_processed_payload = payment_processed_result_json["payload"] if "payload" in payment_processed_result_json else None
    #     msg = payment_processed_result_json["msg"] if "msg" in payment_processed_result_json else None
        
    #     # payment process response
    #     get_response = {
    #         "status_code": send_request.status_code,
    #         "response": payment_processed_result_json,
    #     }
        
    #     request_res = payment_processed_payload
    #     # error from payment process then save json response
    #     if send_request.status_code not in [200, 201]:
    #         payment_processed_result_json.update({
    #             "transaction_ref_id": f"{disbursement_id}",
    #         })
    #         request_res = payment_processed_result_json
        
    #     # save transaction logs
    #     transaction_logs_data = {
    #         "request_data": payment_json_data,
    #         "request_res": request_res,
    #     }
    #     save_transaction_logs = self.save_transaction_logs(data=transaction_logs_data)
        
    #     # exit, if error on payment process
    #     if send_request.status_code not in [200, 201]:
    #         print(f"{get_response}")
    #         return
        
    #     # payment process done
    #     if send_request.status_code in [200, 201]:
    #         data = {
    #             "ref_id": f"{disbursement_id}",
    #             "creditor_id": entity_id,
    #             "tx_type": "credit",
    #             "amount": amount,
    #             "currency": currency,
    #             "creditor_institution_id": institution_id,
    #             "creditor_account_id": institution_accounts_id
    #         }
            
    #         # save transactions
    #         save_transaction = self.save_transaction(data=data)

    #         # if data saved in transactions table
    #         if save_transaction["status_code"] in [200, 201]:
    #             transaction_id = save_transaction["payload"]["id"]

    #             if save_transaction_logs["status_code"] in [200, 201]:
    #                 transaction_logs_id = save_transaction_logs["payload"]["id"]
    #                 # add transaction id in logs
    #                 self.update_transaction_logs(
    #                     id=transaction_logs_id, 
    #                     data={
    #                         "transaction_id": transaction_id,
    #                     }
    #                 )
        
    #     return get_response


    # def save_transaction(self, data={}):
    #     print('--save_transaction--')
    #     send_request = requests.post(
    #         self.url + f"api/v1/transaction",
    #         json=data,
    #         headers={"api-token": self.api_token},
    #     )

    #     # extracting data in json format
    #     result_json = send_request.json()
    #     payload = result_json["payload"] if "payload" in result_json else None
    #     msg = result_json["msg"] if "msg" in result_json else None
    #     print(send_request.status_code, '----save_transaction---', payload, data)
    #     return {
    #         "status_code": send_request.status_code,
    #         "msg": msg,
    #         "payload": payload,
    #     }

    # def get_transaction(self, params=""):
    #     print('--get_transaction--')
    #     send_request = requests.get(
    #         self.url + f"api/v1/transaction{params}",
    #         headers={"api-token": self.api_token},
    #     )

    #     # extracting data in json format
    #     result_json = send_request.json()
    #     payload = result_json["payload"] if "payload" in result_json else None
    #     msg = result_json["msg"] if "msg" in result_json else None

    #     return {
    #         "status_code": send_request.status_code,
    #         "msg": msg,
    #         "payload": payload,
    #     }

    # def save_transaction_logs(self, data={}):
    #     print('--save_transaction_logs--')
    #     send_request = requests.post(
    #         self.url + f"api/v1/transaction_log",
    #         json=data,
    #         headers={"api-token": self.api_token},
    #     )

    #     # extracting data in json format
    #     result_json = send_request.json()
    #     payload = result_json["payload"] if "payload" in result_json else None
    #     msg = result_json["msg"] if "msg" in result_json else None
    #     print(msg, '--save_transaction_logs payload--', payload)
    #     return {
    #         "status_code": send_request.status_code,
    #         "msg": msg,
    #         "payload": payload,
    #     }

    # def update_transaction_logs(self, id=None, data={}):
    #     print('--update_transaction_logs--')
    #     send_request = requests.patch(
    #         self.url + f"api/v1/transaction_log/{id}",
    #         json=data,
    #         headers={"api-token": self.api_token},
    #     )

    #     # extracting data in json format
    #     result_json = send_request.json()
    #     payload = result_json["payload"] if "payload" in result_json else None
    #     msg = result_json["msg"] if "msg" in result_json else None
    #     print(send_request.status_code, '--update logs--', payload)
    #     return {
    #         "status_code": send_request.status_code,
    #         "msg": msg,
    #         "payload": payload,
    #     }
