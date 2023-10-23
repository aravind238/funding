from flask import request
from src.models import ClientFund
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import ClientFundSchema
from decimal import Decimal

client_fund_schema = ClientFundSchema()


@Auth.auth_required
def create():
  """
  Create ClientFund Function
  """
  try:
    req_data = request.get_json()
    data, error = client_fund_schema.load(req_data)
    if error:
      return custom_response(error, 400)

    client_fund = ClientFund(data)
    client_fund.save()

    data = client_fund_schema.dump(client_fund).data
    return custom_response(data, 201)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def get_all():
  """
  Get All ClientFund
  """
  try:
    client_funds = ClientFund.get_all_client_funds()
    data = client_fund_schema.dump(client_funds, many=True).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def get_one(client_funds_id):
  """
  Get A ClientFund
  """
  try:
    client_fund = ClientFund.get_one_client_fund(client_funds_id)
    if not client_fund:
      return custom_response({'status': 'error', 'msg': 'client_fund not found'}, 404)
    data = client_fund_schema.dump(client_fund).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def update(client_funds_id):
  """
  Update A ClientFund
  """
  try:
    req_data = request.get_json()
    client_fund = ClientFund.get_one_client_fund(client_funds_id)
    
    if not client_fund:
      return custom_response({'status': 'error', 'msg': 'client_fund not found'}, 404)
    
    if req_data:
      data, error = client_fund_schema.load(req_data, partial=True)
      if error:
        return custom_response(error, 400)
      client_fund.update(data)
    
    else:
      client_fund = ClientFund.query.filter_by(is_deleted=False, id=client_funds_id).first()
        
    data = client_fund_schema.dump(client_fund).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def delete(client_funds_id):
  """
  Delete A ClientFund
  """
  try:
    client_fund = ClientFund.get_one_client_fund(client_funds_id)
    if not client_fund:
      return custom_response({'status': 'error', 'msg': 'client_fund not found'}, 404)
    
    # client_fund.is_deleted = True
    # client_fund.deleted_at = datetime.datetime.utcnow()

    client_fund.delete()
    return custom_response({'status': 'success', 'msg': 'Clients fund deleted'}, 202)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def calculate_fee_advance():
  try:
    client_id = request.args.get("client_id", None)
    invoice_total = Decimal("%.2f" % float(request.args.get("invoice_total", 0)))

    client_fund = (
      ClientFund.query.filter(ClientFund.client_id == client_id)
      .filter_by(is_deleted=False)
      .first()
    )
    
    if client_fund:
      client_fund_dict = {}

      # calculate discount_fees
      get_discount_fees = client_fund.discount_fees_percentage
      discount_fees = float(0)
      if get_discount_fees:
        rounded_discount_fees = Decimal(invoice_total) * get_discount_fees / 100
        discount_fees = Decimal("%.2f" % rounded_discount_fees)
          
      # calculate credit_insurance_total_percentage
      get_credit_insurance_total_percentage = client_fund.credit_insurance_total_percentage
      credit_insurance_total_percentage = float(0)
      if get_credit_insurance_total_percentage:
        rounded_credit_insurance_total_percentage = Decimal(invoice_total) * get_credit_insurance_total_percentage / 100
        credit_insurance_total_percentage = Decimal("%.2f" % rounded_credit_insurance_total_percentage)

      # calculate reserves_withheld_percentage
      get_reserves_withheld_percentage = client_fund.reserves_withheld_percentage
      reserves_withheld_percentage = float(0)
      if get_reserves_withheld_percentage:
        rounded_reserves_withheld_percentage = Decimal(invoice_total) * get_reserves_withheld_percentage / 100
        reserves_withheld_percentage = Decimal("%.2f" % rounded_reserves_withheld_percentage)

      client_fund_dict.update(
        {
          "discount_fees": float(discount_fees),
          "credit_insurance_total": float(credit_insurance_total_percentage),
          "invoice_total": float(invoice_total),
          "reserves_withheld": float(reserves_withheld_percentage),
        }
      )
      return custom_response(client_fund_dict)
    
    else:
      return custom_response({"status": "error", "msg": "client funds not found"}, 404)
  except Exception as e:
    return custom_response({"status": "error", "msg": str(e)}, 404)
