from flask import make_response, json
from src.models import *
from src.resources.v2.schemas import *
from datetime import datetime, timedelta, date
import dateutil.parser
import io
import csv
import os
from decimal import Decimal
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
import ftplib
from src.resources.v2.helpers import custom_response
from pytz import timezone
from src.resources.v2.helpers.convert_datetime import datetime_to_string_format

lcra_export_schema = LCRAExportSchema()


def generate_soa_lcra_csv(soa_id: int=None):
    # Soa
    get_soa = SOA.query.filter_by(is_deleted=False, id=soa_id).first()
    if not get_soa:
        return custom_response(
            {"status": "error", "msg": "SOA does not exist"}, 404
        )

    if get_soa.status.value != "completed":
        return custom_response(
            {"status": "error", "msg": "SOA is not completed"}, 404
        )

    # client id
    client_id = get_soa.client_id

    # get soa approval history if approved by BO
    soa_completed = get_soa.request_approved_by_bo()
    
    saved_client = {}
    if soa_completed:
        if isinstance(soa_completed.attribute, str):
            soa_completed_attribute = json.loads(
                soa_completed.attribute
            )
        else:
            soa_completed_attribute = (
                soa_completed.attribute
            )

        # get saved client
        if (
            soa_completed_attribute
            and "client" in soa_completed_attribute
            and soa_completed_attribute["client"]
        ):
            saved_client = soa_completed_attribute["client"]
            lcra_client_accounts_id = saved_client["lcra_client_accounts_id"]
            lcra_client_accounts_number = saved_client["lcra_client_accounts_number"]
            lcra_control_account_organizations_id = saved_client["lcra_control_account_organizations_id"]

    # soa additional cash reserve release
    additional_cash_reserve_release = Decimal(get_soa.additional_cash_reserve_release) if get_soa.additional_cash_reserve_release else Decimal(0)
    # soa additional cash reserve held
    additional_cash_reserve_held = Decimal(get_soa.additional_cash_reserve_held) if get_soa.additional_cash_reserve_held else Decimal(0)
    # soa adjustment from ae
    adjustment_from_ae = Decimal(get_soa.adjustment_from_ae) if get_soa.adjustment_from_ae else Decimal(0)
    
    # client
    if not saved_client:
        get_client = Client.query.filter_by(id=client_id, is_deleted=False).first()                
        lcra_client_accounts_id = get_client.lcra_client_accounts_id
        lcra_client_accounts_number = get_client.lcra_client_accounts_number
        lcra_control_account_organizations_id = get_client.lcra_control_account_organizations_id
    
    # invoices
    get_invoices = Invoice.query.filter_by(is_deleted=False, soa_id=soa_id).all()
    invoices_dict = InvoiceSchema().dump(get_invoices, many=True).data

    # disbursements
    get_disbursements = Disbursements.query.filter(
        Disbursements.soa_id == soa_id,
        Disbursements.is_deleted == False,
        Client.id == Disbursements.client_id,
        ClientPayee.client_id == Client.id,
        ClientPayee.payee_id == Disbursements.payee_id,
    )
    disbursements = get_disbursements.all()

    # File timestamp should be EST(LC-1281)
    date_time = datetime_to_string_format(fmt="%Y-%m-%d %H:%M:%S")

    # 1. transaction_id
    # Data type: string
    # The funding interface should generate a transaction id a global variable, or general sequence of SOA and Reserve Release submitted, this ID should be unique across the whole client list. Example: cf1, please keep the cf on the string
    last_lcra_export = LCRAExport.query.order_by(LCRAExport.id.desc()).first()
    last_lcra_export_id = last_lcra_export.id if last_lcra_export else int(0)
    generate_cf = last_lcra_export_id + 1
    transaction_id = f"{os.getenv('LCRA_EXPORT_PREFIX')}{generate_cf}"
    
    # 2. status
    # Data type: string
    # It should always be 0, it’s just a way for iTristan to keep track of what has been upload and prevent duplication
    status = "0"
    
    # 3. client_account_id
    # Data type: integer
    # This value comes from LCRA replica DB, table: client_accounts, field: id
    # You would have to use the client mapping (Cadence/LCRA) to get this value
    client_account_id = lcra_client_accounts_id

    # 4. funding_date
    # Data type: string, format: YYYY-mm-dd, example: 2019-01-30
    # funding_date (date when the SOA was approved by the BO)
    # convert updated_at("UTC") to est("US/Eastern")
    # Data with the submission time should be EST(LC-1281)
    get_est_updated_at = get_soa.updated_at.replace(tzinfo=timezone("UTC")).astimezone(timezone("US/Eastern"))
    get_string_datetime = str(get_est_updated_at)
    funding_date = dateutil.parser.parse(get_string_datetime).date()

    # 5. lcra client number
    # Data type: string
    # This value comes from LCRA replica DB, table: client_accounts, field: number
    # You should use the client mapping* (Cadence/LCRA) to get this value
    lcra_client_number = lcra_client_accounts_number

    # 6. reference
    # Data type: string; 
    # SOA ID from the funding interface, 
    # Example: SOAID123, please keep the SOAID word on the string, in this way we can distinguish what comes from the funding interface
    reference_soa = "SOAID" + str(get_soa.soa_ref_id)

    # 7. invoice_total
    # Data type: double
    # From the funding interface, Advance Review screen take the “Invoice total” value. This is the total of the invoices that the ppal entered on the invoice table.
    invoice_total = get_soa.invoice_total

    # 8. reserve_held
    # Data type: double
    # DO NOT Override, user default value is number -123456789 // otherwise it would create a rounding problem
    reserve_held = '-123456789'

    # 9. discount_fee
    # Data type: double
    # From the funding interface, Advance Review screen, add “Discount Fees” + “Fee Adjustment (Disc Fees)” and take resulting value. 
    # “disc fee - fee adjustment = subtotal_discount_fees” (only for the SOA Request LCRA Export)(LC-1676)
    # Subtotal Discount Fees from step 3
    discount_fee = get_soa.discount_fees - get_soa.fee_adjustment

    # 10. others
    # Data type: double
    # Just leave with “0”, we are not going to override this field
    others = 0

    # 11. adjustments (Adjustments are Fees charged to the client)
    # Data type: double
    # Fees charged to the client
    # TOTAL FEES TO CLIENTS = Client ASAP Fee + All Client’s 3rd Party Fees + All Client’s Same-Day ACH Fees + All Client’s WIRE Fees should be the Adjustment field (LC-1695)
    adjustments = Decimal(get_soa.cal_disbursement_total_fees()["total_fees_asap"])
    
    # 12. reserve_paid
    # Data type: double
    # Add (+) “Cash Reserve Release” from Advance Review screen
    # Subtract: (-) negative sign before “Selected invoices to hold in reserves” from Advance Review screen
    # Subtract: (-) negative sign before “Cash reserve held” from Advance Review screen
    # Add (+) Adjustment from AE
    sum_hold_in_reserve = Decimal(0)
    if invoices_dict:
        for get_invoice in invoices_dict:
            if (get_invoice['actions'] == 'hold_in_reserves'):
                invoice_amount = Decimal(get_invoice['amount']) if get_invoice['amount'] is not None else Decimal(0)
                sum_hold_in_reserve += invoice_amount

    reserve_paid = additional_cash_reserve_release - sum_hold_in_reserve - additional_cash_reserve_held + adjustment_from_ae

    # 13. payment_method_id
    # Data type: Integer
    # 1 is ACH
    # 2 is wire
    # 3 is cheque

    # New requirements
    # 1 is direct_deposit
    # Just use payment_method of first disbursement
    # The variable #13 should show number 1 (ACH transfer); 
    # any LCRA export that does not have a payment, we default it to ACH payment method.(LC-1495)
    payment_method_id = 1
    # disbursement = []
    if disbursements:
        soa_disbursement = disbursements[0] # Consider just first one.
        if soa_disbursement.payment_method.value == 'wire':
            payment_method_id = 2
        elif soa_disbursement.payment_method.value == 'cheque':
            payment_method_id = 3
        elif soa_disbursement.payment_method.value == 'same_day_ach' or soa_disbursement.payment_method.value == 'direct_deposit':
            payment_method_id = 1
        
        # disbursement = payment_method_id

    # 14. processing_fee
    # Data type: double
    # Leave with default value -123456789, we are not going to override this field 
    processing_fee = '-123456789'

    # 15. exchange_fee
    # Data type: double
    # Leave with default value -123456789, we are not going to override this field 
    exchange_fee = '-123456789'

    # 16. credit_insurance_fee
    # Data type: double
    # Leave with default value -123456789, we are not going to override this field 
    credit_insurance_fee = '-123456789'

    fees_charged_to_principal = ''
    first_adjustment = ''
    second_adjustment = ''

    # 17. misc_adj,description, control_account_organization_id, SP_id| misc_adj,description, control_account_organization_id, SP_id
    # 'cheque': 20,
    # 'wire': 20,
    # 'international_wire': 40,
    # 'same_day_ach': 5,
    # 'tp': 5,
    
    # Data type: double
    # From Disbursement details screen “Principal charges section”
    # 	•	Add all “wire fees” charged to the principal. We charge $20 per wire to the principal regardless of the control account. And $45 for international wires 
    # 	•	Add all “cheque fees” charged to the principal. We charge $20 per cheque to the principal
    # 	•	Add all “same day ACH fees”. We charge 5$ per same day ACH to the principal  regardless of the control account
    payment_info = {
        "wire" : 20,
        "cheque" : 20,
        "international_wire" : 45,
        "same_day_ach" : 5,
        "high_priority" : 25,
        "tp" : 5
    }

    payment_desc = {
        "wire" : 'wirefee',
        "cheque" : 'chequefee',
        "same_day_ach" : 'ACHfees',
        "high_priority" : 'ASAPfees',
        "tp" : 'Thirdpartyfees'
    }

    show_section_1 = False
    p_misc_adj_1 = Decimal(0)
    p_misc_adj_1_desc = []
    if disbursements:
        for soa_disbursement in disbursements:
            if soa_disbursement.payment_method.value == 'wire':
                p_misc_adj_1 += payment_info['wire']
                if payment_desc['wire'] not in p_misc_adj_1_desc:
                    p_misc_adj_1_desc.append(payment_desc['wire']) 
            if soa_disbursement.payment_method.value == 'cheque':
                p_misc_adj_1 += payment_info['cheque']
                if payment_desc['cheque'] not in p_misc_adj_1_desc:
                    p_misc_adj_1_desc.append(payment_desc['cheque']) 
            if soa_disbursement.payment_method.value == 'same_day_ach':
                p_misc_adj_1 += payment_info['same_day_ach']
                if payment_desc['same_day_ach'] not in p_misc_adj_1_desc:
                    p_misc_adj_1_desc.append(payment_desc['same_day_ach']) 

    # Data type: string  Wire fee, chequefee or/and ACHfees, CONCAT if more than 1 
    p_misc_adj_1_desc = "-".join(p_misc_adj_1_desc)

    # This value correspond to the Manager caorgID of the Client. 
    # This principal has a control_account_organization_ID, 
    # this value is on “control_account_organizations” table from the LCRA, field ID.
    p_control_account_organization_id_1 = lcra_control_account_organizations_id

    # Data type: int
    #   LCRA Export code(LC-1860):
    # 	•	IF control account = LCEC CDN, THEN use 11 – LCEC CDN Bank charges
    # 	•	IF control account = LCEC US, THEN use 12 – LCEC US bank charges
    # 	•	IF control account = LCEI. US, THEN use 13 – LCEI. US bank charges
    # 	•	IF control account = NFI CDN, THEN use 471 – NFI CDN bank charges
    # 	•	IF control account = NFI US, THEN use 475 – NFI US bank charges
    # 	•	IF control account = NII US, THEN use 473 – NII US bank charges
    # 	•	IF control account = NTFI USD, THEN use 580 – NTFI USD bank charges
    # 	•	IF control account = LFC USD, THEN use 627 – LFC USD bank charges
    # 	•	IF control account = LFSI - CAD, THEN use 638 – LFSI - CAD bank charges
    # 	•	IF control account = NPLP- CAD, THEN use 642 – NPLP- CAD bank charges
    client_control_account = ClientControlAccounts.query.filter_by(client_id=client_id, is_deleted=False).first()
    control_account = ControlAccount.query.filter_by(id=client_control_account.control_account_id, is_deleted=False).first()

    p_sp_id = 0
    if control_account.lcra_export_id:
        p_sp_id = control_account.lcra_export_id

    if p_misc_adj_1 > 0 :
        show_section_1 = True

    first_adjustment = [
        p_misc_adj_1, p_misc_adj_1_desc, p_control_account_organization_id_1, p_sp_id
    ]

    # Data type: double
    # From Disbursement details screen “Principal charges section”
    # 	•	Add all “ASAP fees” charged to the principal. TBD
    # 	•	Add all “Third party fees”. We charge 5$ per TP to the principal
    show_section_2 = False
    p_misc_adj_2 = Decimal(0)
    p_misc_adj_2_desc = []
    payee_soa_disbursements = get_disbursements.filter(
        ClientPayee.ref_type == "payee",
    ).all()
    if payee_soa_disbursements:
        for soa_disbursement in payee_soa_disbursements:
            p_misc_adj_2 += payment_info['tp']
            if payment_desc['tp'] not in p_misc_adj_2_desc:
                p_misc_adj_2_desc.append(payment_desc['tp'])

    if get_soa.high_priority:
        p_misc_adj_2 += payment_info['high_priority']
        p_misc_adj_2_desc.append(payment_desc['high_priority'])

    # Data type: string  ASAP fees , Thrid party fees, CONCAT if both
    p_misc_adj_2_desc = "-".join(p_misc_adj_2_desc)

    # Data type: int
    # Each principal has a control_account_organization_ID, this field is on “control_account_organizations” table from the LCRA field ID
    p_control_account_organization_id_2 = lcra_control_account_organizations_id

    # 1.4 SP_id
    # Data type: int
    #   LCRA Export code(LC-1860):
    # 	•	IF control account = LCEC CDN, THEN use 11 – LCEC CDN Bank charges
    # 	•	IF control account = LCEC US, THEN use 12 – LCEC US bank charges
    # 	•	IF control account = LCEI. US, THEN use 13 – LCEI. US bank charges
    # 	•	IF control account = NFI CDN, THEN use 471 – NFI CDN bank charges
    # 	•	IF control account = NFI US, THEN use 475 – NFI US bank charges
    # 	•	IF control account = NII US, THEN use 473 – NII US bank charges
    # 	•	IF control account = NTFI USD, THEN use 580 – NTFI USD bank charges
    # 	•	IF control account = LFC USD, THEN use 627 – LFC USD bank charges
    # 	•	IF control account = LFSI - CAD, THEN use 638 – LFSI - CAD bank charges
    # 	•	IF control account = NPLP- CAD, THEN use 642 – NPLP- CAD bank charges
    #  SAME AS ABOVE
    if p_misc_adj_2 > 0 :
        show_section_2 = True
        
    second_adjustment = [p_misc_adj_2, p_misc_adj_2_desc, p_control_account_organization_id_2, p_sp_id]
    
    # Concat strings         
    first_adjustment = ",".join(map(str, first_adjustment))
    second_adjustment = ",".join(map(str, second_adjustment))
    
    # Fees charged to principal logic:
    if show_section_1 == True and show_section_2 == True:
        fees_charged_to_principal = [first_adjustment, second_adjustment]
        fees_charged_to_principal = "|".join(map(str, fees_charged_to_principal))
    elif show_section_1 == True and show_section_2 == False:
        fees_charged_to_principal = first_adjustment
    elif show_section_1 == False and show_section_2 == True:
        fees_charged_to_principal = second_adjustment
    
    # File names must follow this pattern: 
    #   client_fundings_1_2019-11-25 20:47:37.csv 
    # 
    #   The name of the file is a concatenation of the following strings:
    #       1. String 1: client_fundings
    #       2. String 2: sequence number, which is a global variable that counts SOAs and Reserve Releases
    #       3. String 3: time stamp YYYY-MM-DD HH:MM:SS
    filename = f'client_fundings_{generate_cf}_{date_time}.csv'
    
    memory_file = io.StringIO()
    writer = csv.writer(memory_file, delimiter=';')
    
    writer.writerow(
        [
            transaction_id,
            status,
            client_account_id,
            funding_date,
            lcra_client_number,
            reference_soa,
            invoice_total,
            reserve_held,
            discount_fee,
            others,
            adjustments,
            reserve_paid,
            payment_method_id,
            processing_fee,
            exchange_fee,
            credit_insurance_fee,
            fees_charged_to_principal,
        ]
    )
    
    memory_file.seek(0)

    output = make_response(memory_file.getvalue())
    output.headers["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
    output.headers["Content-type"] = "text/csv"
    output.headers["Access-Control-Expose-Headers"] = "content-disposition"

    # store record to lcra database
    
    # get user details
    get_user_detail = Permissions.get_user_details()
    user_email = get_user_detail['email'] 
    
    # store to db
    data = {'soa_id': soa_id, 'is_uploaded': False, 'exported_by': user_email}
    data, error = lcra_export_schema.load(data)
    if error:
        return custom_response(error, 400)
    lcra_export = LCRAExport(data)
    lcra_export.save()
    # Data with the submission time should be EST(LC-1281)
    est_lcra_export_created_at = lcra_export.created_at.replace(tzinfo=timezone("UTC")).astimezone(timezone("US/Eastern"))
    lcra_export_created_at = est_lcra_export_created_at.strftime("%Y-%m-%d %H:%M:%S")

    # TODO: check if we compare with status code not string
    if output.status == "200 OK":
        session = ftplib.FTP(os.getenv('LCRA_EXPORT_FTP_SERVER'), os.getenv('LCRA_EXPORT_FTP_USERNAME'), os.getenv('LCRA_EXPORT_FTP_PASSWORD'))
        session.cwd(os.getenv('LCRA_EXPORT_PATH'))
        b1 = bytes(memory_file.getvalue(), encoding = 'utf-8')
        bio = io.BytesIO(b1)
        csv_file_name = 'client_fundings' + '_' + str(lcra_export.id) + '_' + str(lcra_export_created_at) + '.csv'
        session.storbinary('STOR ' + csv_file_name, bio)
        # TODO: check for storbinary status
        # PATCH lcra
        data = {'is_uploaded': True}
        lcra_export = LCRAExport.get_one_lcra_export(lcra_export.id)
        if not lcra_export:
            return custom_response(
                {"status": "error", "msg": "lcra_export not found"}, 404
            )

        data, error = lcra_export_schema.load(data, partial=True)
        if error:
            return custom_response(error, 400)
        lcra_export.update(data)

        session.quit()
    return output
