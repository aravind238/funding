from flask import request, json
from decimal import Decimal
from src.resources.v2.helpers import bankers_rounding
from src.models import *
from src.resources.v2.schemas import *

client_fund_schema = ClientFundSchema()


class CalculateClientbalances:

    def __init__(self, request_type, invoice_total=Decimal(0), client_id=None):
        # request_type = SOA|reserve_release
        self.request_type = request_type
        self.client_id = client_id # ToDo: Need to be updated
        self.invoice_total = Decimal(invoice_total)
        self.client_funds = None

        self.cal_invoice_total = Decimal(0)        
        self.advance_amount = Decimal(0)
        self.discount_fees = Decimal(0)        
        self.fee_adjustment = Decimal(0)        
        self.ar_balance = Decimal(0)
        self.funding_balance = Decimal(0)
        self.reserve_balance = Decimal(0)
        self.client_limit = Decimal(0)

        self.preview_ar_balance = Decimal(0)
        self.preview_funding_balance = Decimal(0)
        self.preview_reserve_balance = Decimal(0)
        self.client_funding_balance = Decimal(0)
        
        self.cal_client_balances()
    
    def get_client_funds(self):
        request_type_status = self.request_type.status.value
        request_type_funded = None
        
        approved_at = 'created_at'
        if request_type_status == 'pending':
            approved_at = 'submitted_at'

        if request_type_status == 'approved':
            approved_at = 'approved_at'

        if request_type_status == 'completed':
            approved_at = 'funded_at' 

        if request_type_status == 'approved' or request_type_status == 'completed':
            if self.request_type.object_as_string().lower() == 'soa':
                request_type_funded = ApprovalsHistory.query.filter_by(
                                                soa_id=self.request_type.id, 
                                                is_deleted=False
                                            ).filter(
                                                ApprovalsHistory.key == approved_at
                                            ).order_by(
                                                ApprovalsHistory.id.desc()
                                            ).first()
                
            else:
                request_type_funded = ApprovalsHistory.query.filter_by(
                                                reserve_release_id=self.request_type.id, 
                                                is_deleted=False
                                            ).filter(
                                                ApprovalsHistory.key == approved_at
                                            ).order_by(
                                                ApprovalsHistory.id.desc()
                                            ).first()
            
        
        if request_type_funded:
            if isinstance(request_type_funded.attribute, str):
                attribute_json = json.loads(request_type_funded.attribute)
                self.client_funds = attribute_json['client_funds']

            if isinstance(request_type_funded.attribute, dict) and 'client_funds' in request_type_funded.attribute and request_type_funded.attribute['client_funds'] is not None:
                self.client_funds = request_type_funded.attribute['client_funds']

        if self.client_funds is None:
            get_client_funds = ClientFund.query.filter_by(is_deleted=False, client_id=self.client_id).first()
            self.client_funds = client_fund_schema.dump(get_client_funds).data
    
    def get_invoice_total(self):
        if self.invoice_total and self.request_type.object_as_string().lower() == 'soa' and self.request_type.status.value == 'draft':
            self.cal_invoice_total = Decimal(round(self.invoice_total, 2))
        else:
            if self.request_type.object_as_string().lower() == 'soa' and self.request_type.invoice_total is not None:
                self.cal_invoice_total = Decimal(self.request_type.invoice_total)

    def get_advance_amount(self):
        if self.request_type.object_as_string().lower() == 'soa' and self.request_type.advance_amount is not None:
            self.advance_amount = Decimal(self.request_type.advance_amount)
        return self.advance_amount
    
    def get_discount_fees(self):       
        if self.request_type.object_as_string().lower() == 'soa' and self.request_type.discount_fees is not None:
            self.discount_fees = Decimal(self.request_type.discount_fees)

    def get_fee_adjustment(self):
        if self.request_type.object_as_string().lower() == 'soa' and self.request_type.fee_adjustment is not None:
            self.fee_adjustment = Decimal(self.request_type.fee_adjustment)
        
    def get_ar_balance(self):
        if self.client_funds and self.client_funds['ar_balance'] is not None:
            roundoff_ar_balance = bankers_rounding(self.client_funds['ar_balance'])
            self.ar_balance = roundoff_ar_balance['bankers_rounding']

    def get_funding_balance(self):
        if self.client_funds and self.client_funds['funding_balance'] is not None:
            roundoff_funding_balance = bankers_rounding(self.client_funds['funding_balance']) 
            self.funding_balance = roundoff_funding_balance['bankers_rounding']

    def get_reserve_balance(self):
        if self.client_funds and self.client_funds['reserve_balance'] is not None:
            roundoff_reserve_balance = bankers_rounding(self.client_funds['reserve_balance'])
            self.reserve_balance = roundoff_reserve_balance['bankers_rounding']

    def get_client_limit(self):
        if self.client_funds and self.client_funds['current_limit'] is not None:
            roundoff_client_limit = bankers_rounding(self.client_funds['current_limit'])
            self.client_limit = roundoff_client_limit['bankers_rounding']

    def get_preview_ar_balance(self):
        # calculate preview_ar_balance
        #   Code: COC1
        #   Name: Preview Client A/R Balance
        #   Formula: A/R Balance + Invoice Total(SOA1)
        self.preview_ar_balance = self.ar_balance + self.cal_invoice_total

    def get_preview_funding_balance(self):
        # calculate preview_funding_balance
        #   Code: COC2
        #   Name: Preview Client Funding Balance
        #   Formula: Funding Balance + Advance Amount(SOA6) + Discount Fees + Adjustment Fees
        self.preview_funding_balance = self.funding_balance + self.advance_amount + self.discount_fees + self.fee_adjustment

    def get_preview_reserve_balance(self):
        # calculate preview_reserves_balance
        #   Code: COC3
        #   Name: Preview Client Reserve Balance
        #   Formula: COC1 - COC2
        self.preview_reserve_balance = self.preview_ar_balance - self.preview_funding_balance           
        
    def get_client_funding_balance(self):
        # calculate client_funding_balance (percentage)
        #   Code: COC4
        #   Name: Client Limit Comparison Percentage(%)
        #   Formula: [ABS(Client Limit - COC2)/(Client Limit)]*100%
        # 
        # if client_limit == 0
        if self.client_limit > Decimal(0):
            get_client_funding_balance = (abs(self.client_limit - self.preview_funding_balance) / self.client_limit) * 100
            roundoff_client_funding_balance = bankers_rounding(get_client_funding_balance)
            self.client_funding_balance = roundoff_client_funding_balance['bankers_rounding']
        else:
            self.client_funding_balance = self.client_limit

    @property
    def client_limit_flag(self):
        # Client Preview Balances(LC-1021)
        #   Code: COC5
        #   Name: Client Limit Flag
        #   Formula:
        #    1. Display Orange message IF COC2 < 0
        #    2. Display Green message IF COC2 < Client Limit AND COC4 > 10%
        #    3. Display Orange message IF COC2 < Client Limit AND COC4 is between 10% of client limit below and over
        #    4. Display Red message IF COC2 > Client Limit
        #   Message: 
        #    1. Orange Message -> "Client Funding Balance is negative."
        #    2. Green Message -> "Client Funding Balance will be COC4 % below the client limit facility set by the Credit Committee if this SOA is funded"
        #    3. Orange Message -> "Client Funding Balance will be COC4 % below the client limit facility set by the Credit Committee if this SOA is funded"
        #    4. Red Message -> "Client Funding Balance will be COC4 % over the client limit facility set by the Credit Committee if this SOA is funded"
        
        client_limit_ten = round(self.client_limit * Decimal(0.1), 2) if self.client_limit > 0 else Decimal(0)
        client_limit_ten = Decimal(client_limit_ten)
                
        # Display Orange message: IF COC2 < 0
        if self.preview_funding_balance < 0:
            self.coc5 = {
                'flag_type': 'warning',
                'flag_msg': 'Client Funding Balance is negative.'
            }
        # Display Green message: IF COC2 < Client Limit AND COC4 > 10%
        elif self.preview_funding_balance < self.client_limit and self.client_funding_balance > Decimal(0.1):
            self.coc5 = {
                'flag_type': 'success',
                'flag_msg': f'Client Funding Balance will be {self.client_funding_balance}% below the client limit facility set by the Credit Committee if this SOA is funded'
            }
        # Display Orange message: IF COC2 < Client Limit AND COC4 is between 10% of client limit below and over
        elif self.preview_funding_balance < self.client_limit and (self.client_funding_balance > Decimal(0) and self.client_funding_balance < Decimal(0.1)):
            self.coc5 = {
                'flag_type': 'warning',
                'flag_msg': f'Client Funding Balance will be {self.client_funding_balance}% below the client limit facility set by the Credit Committee if this SOA is funded'
            }
        # Display Red message: IF COC2 > Client Limit
        elif self.preview_funding_balance > self.client_limit:
            self.coc5 = {
                'flag_type': 'error',
                'flag_msg': f'Client Funding Balance will be {self.client_funding_balance}% over the client limit facility set by the Credit Committee if this SOA is funded'
            }
        else:
            self.coc5 = {
                'flag_type': 'warning',
                'flag_msg': 'Client Funding Balance not available'
            }
        return self.coc5

    def cal_client_balances(self):
        self.get_client_funds()
        self.get_invoice_total()
        self.get_advance_amount()
        self.get_discount_fees()
        self.get_fee_adjustment()
        self.get_ar_balance()
        self.get_funding_balance()
        self.get_reserve_balance()
        self.get_client_limit()
        self.get_preview_ar_balance()
        self.get_preview_funding_balance()
        self.get_preview_reserve_balance()
        self.get_client_funding_balance()
