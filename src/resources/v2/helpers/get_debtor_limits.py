import os
import requests
from src.resources.v2.helpers import custom_response
from flask import abort



def get_debtor_limits_from_third_party(debtor_ref_key=None, client_ref_key=None):
    """
    Get DEBTOR Limits From 3rd Party db
    """
    # try:
    if (debtor_ref_key is None) or (not isinstance(debtor_ref_key, str)):
        return abort(404, "debtor ref_key not found")

    if (client_ref_key is None) or (not isinstance(client_ref_key, int)):
        return abort(404, "client ref_key not found")

    # integrate 3rd party
    url = os.getenv("LC_THIRD_PARTY_API_URL") + "v1/cadence/debtorLimits/new"

    # defining a headers dict for the parameters to be sent to the API
    headers = {
        "app-id": os.getenv("LC_THIRD_PARTY_APP_ID"),
        "app-secret": os.getenv("LC_THIRD_PARTY_APP_SECRET"),
    }

    params = {
        "debtorKey": debtor_ref_key, 
        "clientKey": client_ref_key
    }

    data = {}
    try:
        r = requests.get(url=url, params=params, headers=headers)
        data = r.json()
        data["status_code"] = r.status_code
    except requests.ConnectionError as e:
        data["status_code"] = 502
    except requests.Timeout as e:
        data["status_code"] = 408
    except Exception as e:
        data["status_code"] = 500

    return data
    # except Exception as e:
    #     return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)
