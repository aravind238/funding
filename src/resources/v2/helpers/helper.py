from flask import json



def principal_settings():
    cheque_fee = 20
    high_priority_fee = 25
    same_day_ach_fee = 5
    third_party_fee = 5
    wire_fee = 20

    return {
        "cheque_fee": cheque_fee,
        "high_priority_fee": high_priority_fee,
        "same_day_ach_fee": same_day_ach_fee,
        "third_party_fee": third_party_fee,
        "wire_fee": wire_fee,
    }
