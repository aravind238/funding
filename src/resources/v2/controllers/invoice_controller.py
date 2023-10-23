from flask import request, make_response, json
from src.models import *
from datetime import datetime, timedelta, date
import dateutil.parser
import pandas as pd
import io
from decimal import Decimal
from src.middleware.authentication import Auth
from src.resources.v2.helpers import (
    validate_invoice_debtor,
    validate_invoice,
    CadenceValidateInvoices,
    custom_response,
)
from src import db
from src.resources.v2.schemas import InvoiceAEReadOnlySchema, InvoiceSchema, InvoiceDebtorSchema
from src.middleware.permissions import Permissions
import hashlib
from src.resources.v2.helpers.convert_datetime import current_date

invoice_schema = InvoiceSchema()
invoice_debtor_schema = InvoiceDebtorSchema()


@Auth.auth_required
def create():
    """
    Create Invoice Function
    """
    try:
        req_data = request.get_json()
        data, error = invoice_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        invoice_number = req_data.get("invoice_number", None)

        # check invoice with cadance db
        soa_id = req_data["soa_id"]

        soa = SOA.get_one_based_off_control_accounts(soa_id)
        if not soa:
            return custom_response({"status": "error", "msg": "soa not found"}, 404) 

        debtor_id = data["debtor"]
        debtor = Debtor.query.filter_by(is_deleted=False, id=debtor_id).first()
        debtor_key = debtor.ref_key

        validated_invoice_list = validate_invoice_debtor(soa.client.ref_key)

        if type(validated_invoice_list) == list:
            for validated_invoice in validated_invoice_list:
                if (
                    validated_invoice["invoice_number"] == invoice_number
                    and validated_invoice["debtor_key"] == debtor_key
                ):
                    return custom_response(
                        {
                            "invoice_number": invoice_number,
                            "msg": "This invoice is already purchased and cannot be added again.",
                        },
                        409,
                    )

        ## check unique together
        client_id = data["client_id"]
        check_unique_invoice = bool(
            Invoice.query.join(SOA).filter(
                Invoice.is_deleted == False,
                Invoice.invoice_number == invoice_number,
                Invoice.client_id == client_id,
                Invoice.debtor == debtor_id,
                SOA.status.in_(
                    [
                        "approved",
                        "completed",
                    ]
                ),
            ).first()
        )

        invoice = Invoice(data)

        if check_unique_invoice is False:
            invoice.save()
        else:
            return custom_response(
                {
                    "invoice_number": invoice_number,
                    "msg": "This invoice is already purchased and cannot be added again.",
                },
                409,
            )

        if not data["actions"] == InvoiceActions.non_factored:
            soa.invoice_total = float(soa.invoice_total) + data.get("amount", 0)
            soa.save()

        data = invoice_schema.dump(invoice).data
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)
    except:
        db.session.rollback()
        raise
    finally:
        db.session.close()


@Auth.auth_required
def add_invoices():
    """
    Function to add or update multiple invoices
    """
    try:
        request_data = request.get_json()
        invoices = request_data.get("invoices", None)

        # checks invoices has data
        if invoices is None or len(invoices) == 0:
            return custom_response({"status": "error", "msg": "Please add invoices."}, 404)

        soa_id = invoices[0].get("soa_id", None)
        client_id = invoices[0].get("client_id", None)

        # check soa exists
        soa = SOA.get_one_based_off_control_accounts(soa_id)
        if not soa:
            return custom_response({"status": "error", "msg": "soa not found"}, 404)            
        
        # current EST date
        invoices[0]["current_date"] = current_date().isoformat()
        
        if (
            not soa.is_request_updated() 
            and soa.status.value in ['pending', 'reviewed']
        ):
            get_invoices = Invoice.query.filter_by(
                is_deleted=False, 
                soa_id=soa_id
            ).all()
            
            invoices_in_db = InvoiceAEReadOnlySchema(many=True).dump(get_invoices).data

            # md5 hash fetched invoices from invoice table
            invoices_in_db_md5 = hashlib.md5(
                str(invoices_in_db).encode('UTF-8')
            ).hexdigest()

        validated_invoices = CadenceValidateInvoices(
            soa=soa, validate_invoices=invoices, debtor_ref_key_exists=False
        )
        # print(validated_invoices.get_valid_invoices)

        if (
            len(validated_invoices.get_wrong_debtors) 
            or len(validated_invoices.get_already_exist_invoices)
            or len(validated_invoices.get_wrong_invoice_data)
        ):
            msg = "Invoice having invalid data"
            if len(validated_invoices.get_already_exist_invoices):
                msg = "Invoice number already exists"

            if len(validated_invoices.get_wrong_debtors):
                msg = "Invoice having wrong debtors"

            if (
                len(validated_invoices.get_wrong_invoice_data)
                and "msg" in validated_invoices.get_wrong_invoice_data[0]
            ):
                msg = validated_invoices.get_wrong_invoice_data[0]["msg"]

            return custom_response(
                {
                    "status": "error",
                    "msg": msg,
                    "wrong_invoice_data": validated_invoices.get_wrong_invoice_data,
                    "wrong_debtors": validated_invoices.get_wrong_debtors,
                    "invoice_already_exists": validated_invoices.get_already_exist_invoices,
                },
                400,
            )

        # print('I',validated_invoices.get_invoices_to_insert)
        # print('U',validated_invoices.get_invoices_to_update)

        insert_obj = []
        for each_invoice in validated_invoices.get_invoices_to_insert:
            insert_obj.append(Invoice(each_invoice))

        approvals_history_data = {}
        if len(validated_invoices.get_invoices_to_update):
            db.session.bulk_update_mappings(
                Invoice, validated_invoices.get_invoices_to_update
            )
            
            # to be saved in approval history
            approvals_history_data = {
                'key': 'updated_at',
                'value': datetime.utcnow(),
                'soa_id': soa_id,
                'attribute': {
                    'updated': 'invoice_updated'
                },
            }

        if len(insert_obj):
            db.session.add_all(insert_obj)

        db.session.commit()
        
        # on AE update invoice, add in approvals history
        if (
            approvals_history_data 
            and not soa.is_request_updated() 
            and soa.status.value in ['pending', 'reviewed']
        ):
            get_invoices_updated = Invoice.query.filter_by(
                is_deleted=False,
                soa_id=soa_id
            ).all()
            
            invoices_updated = InvoiceAEReadOnlySchema(many=True).dump(get_invoices_updated).data

            # md5 hash invoices updated
            invoices_updated_md5 = hashlib.md5(
                str(invoices_updated).encode('UTF-8')
            ).hexdigest()

            user_permissions = Permissions.get_user_role_permissions()
            user_role = user_permissions['user_role']
            
            # checking, if user has role 'AE' then add in approvals history
            if (
                user_role 
                and user_role.lower() == 'ae' 
                and invoices_in_db_md5 != invoices_updated_md5
            ):
                get_user_detail = Permissions.get_user_details()
                user_email = get_user_detail['email']
                
                approvals_history_data.update({'user': user_email})
                approvals_history = ApprovalsHistory(approvals_history_data)
                approvals_history.save()

        soa.update_invoice_total()  # Always updating SOA Total

        all_invoices = soa.get_invoices()
        all_invoices = invoice_schema.dump(all_invoices, many=True).data

        return custom_response(all_invoices, 201)

    except Exception as e:
        print(str(e))
        db.session.rollback()
        raise
    finally:
        db.session.close()


@Auth.auth_required
def get_all():
    """
    Get All Invoice
    """
    try:
        page = request.args.get("page", 0, type=int)
        rpp = request.args.get("rpp", 20, type=int)
        search = request.args.get("search", None, type=str)
        ordering = request.args.get("ordering", None, type=str)
        actions = request.args.get("actions", None, type=str)
        debtor_id = request.args.get("debtor_id", None, type=int)
        client_id = request.args.get("client_id", None, type=int)

        if page > 0:
            data = InvoicesListing.get_paginated_invoices(
                page = page,
                rpp = rpp,
                ordering = ordering,
                search = search,
                actions = actions,
                debtor_id = debtor_id,
                client_id = client_id,
            )
        else:
            data = InvoicesListing.get_all()

        if data is None:
            data = []

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(invoice_id):
    """
    Get A Invoice
    """
    try:
        invoice = Invoice.get_one_based_off_control_accounts(invoice_id)
        if not invoice:
            return custom_response({"status": "error", "msg": "invoice not found"}, 404)
        data = invoice_debtor_schema.dump(invoice).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(invoice_id):
    """
    Update A Invoice
    """
    # TODO: Do we need to re-validate invoices.
    try:
        req_data = request.get_json()

        invoice = Invoice.get_one_based_off_control_accounts(invoice_id)
        if not invoice:
            return custom_response({"status": "error", "msg": "invoice not found"}, 404)

        # soa_id
        soa_id = (
            req_data["soa_id"]
            if "soa_id" in req_data and req_data["soa_id"] is not None
            else invoice.soa_id
        )

        soa = SOA.query.filter_by(is_deleted=False, id=soa_id).first()
        if not soa:
            return custom_response({"status": "error", "msg": "soa not found"}), 404

        if "id" not in req_data:
            req_data["id"] = invoice.id

        if "client_id" not in req_data:
            req_data["client_id"] = soa.client.id

        if "debtor" not in req_data and invoice.debtor:
            req_data["debtor"] = invoice.debtor

        if "invoice_number" not in req_data:
            req_data["invoice_number"] = invoice.invoice_number

        if "debtor" not in req_data:
            return custom_response(
                {
                    "status": "error", 
                    "msg": "Debtor is required"
                },
                400,
            )

        if "invoice_number" not in req_data:
            return custom_response(
                {
                    "status": "error", 
                    "msg": "invoice_number is required"
                },
                400,
            )

        if (
            not soa.is_request_updated() 
            and soa.status.value in ['pending', 'reviewed']
        ):
            invoice_in_db = InvoiceAEReadOnlySchema().dump(invoice).data

            # md5 hash fetched invoices from invoice table
            invoice_in_db_md5 = hashlib.md5(
                str(invoice_in_db).encode('UTF-8')
            ).hexdigest()

        approvals_history_data = {}
        if req_data:
            data, error = invoice_schema.load(req_data, partial=True)
            # if (
            #     "debtor" in req_data and
            #     req_data["debtor"] != invoice.invoice_number
            # ):
            #     return custom_response(
            #         {
            #             "status": "error", 
            #             "msg": "Can't update debtor. Please remove and add invoice again."
            #         },
            #         400,
            #     )

            if (
                "invoice_number" in req_data and
                req_data["invoice_number"] != invoice.invoice_number
            ):
                return custom_response(
                    {
                        "status": "error", 
                        "msg": "Can't update invoice number."
                    },
                    400,
                )
            
            # if "debtor" in data:
            #     del data["debtor"]

            # if "invoice_number" in data:
            #     del data["invoice_number"]

            if error:
                return custom_response(error, 400)
            
            # current EST date
            req_data["current_date"] = current_date().isoformat()

            validated_invoices = CadenceValidateInvoices(
                soa=soa, validate_invoices=[req_data], debtor_ref_key_exists=False
            )
            
            if (
                len(validated_invoices.get_wrong_debtors) 
                or len(validated_invoices.get_already_exist_invoices)
                or len(validated_invoices.get_wrong_invoice_data)
            ):
                msg = "Invoice having invalid data"
                if len(validated_invoices.get_already_exist_invoices):
                    msg = "Invoice number already exists"
                
                if len(validated_invoices.get_wrong_debtors):
                    msg = "Invoice having wrong debtors"
                
                if (
                    len(validated_invoices.get_wrong_invoice_data)
                    and "msg" in validated_invoices.get_wrong_invoice_data[0]
                ):
                    msg = validated_invoices.get_wrong_invoice_data[0]["msg"]
                    
                return custom_response(
                    {
                        "status": "error",
                        "msg": msg,
                        "wrong_invoice_data": validated_invoices.get_wrong_invoice_data,
                        "wrong_debtors": validated_invoices.get_wrong_debtors,
                        "invoice_already_exists": validated_invoices.get_already_exist_invoices,
                    },
                    400,
                )

            invoice.update(data)

            # to be saved in approval history
            approvals_history_data = {
                'key': 'updated_at',
                'value': datetime.utcnow(),
                'soa_id': soa_id,
                'attribute': {
                    'updated': 'invoice_updated'
                },
            }

        # on AE update invoice, add in approvals history
        if (
            approvals_history_data 
            and not soa.is_request_updated() 
            and soa.status.value in ['pending', 'reviewed']
        ):
            get_invoice_updated = Invoice.get_one_invoice(invoice_id)
            
            invoice_updated = InvoiceAEReadOnlySchema().dump(get_invoice_updated).data

            # md5 hash invoices updated
            invoice_updated_md5 = hashlib.md5(
                str(invoice_updated).encode('UTF-8')
            ).hexdigest()

            user_permissions = Permissions.get_user_role_permissions()
            user_role = user_permissions['user_role']
            
            # checking, if user has role 'AE' then add in approvals history
            if (
                user_role 
                and user_role.lower() == 'ae' 
                and invoice_in_db_md5 != invoice_updated_md5
            ):
                get_user_detail = Permissions.get_user_details()
                user_email = get_user_detail['email']
                
                approvals_history_data.update({'user': user_email})
                approvals_history = ApprovalsHistory(approvals_history_data)
                approvals_history.save()

        soa.update_invoice_total()  # Always updating SOA Total

        data = invoice_schema.dump(invoice).data
        data.update({"debtor_name": invoice.debtors.name})

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update_invoices():
    """
    Update Invoices
    """
    try:
        req_data = request.get_json()

        invoices = req_data.get("invoices")

        if not invoices:
            return custom_response({"status": "error", "msg": "Please upload invoice file"}, 404)

        soa = SOA.get_one_based_off_control_accounts(invoices[0]["soa_id"])
        if not soa:
            return custom_response({"status": "error", "msg": "soa not found"}, 404)          

        wrong_invoice_data = []
        updated_invoice_list = []

        for invoice_data in invoices:

            invoice = Invoice.get_one_invoice(invoice_data.get("id"))
            if not invoice:
                wrong_invoice_data.append(invoice_data)
                continue

            debtor_id = invoice_data.get("debtor")
            debtor = Debtor.query.filter_by(is_deleted=False, id=debtor_id).first()
            if not debtor:
                return custom_response({"status": "error", "msg": "debtor not found"}, 404) 
            debtor_key = debtor.ref_key

            validated_invoice_list = validate_invoice_debtor(soa.client.ref_key)

            for validated_invoice in validated_invoice_list:
                if (
                    validated_invoice["invoice_number"]
                    == invoice_data.get("invoice_number")
                    and validated_invoice["debtor_key"] == debtor_key
                ):
                    return custom_response(
                        {
                            "status": "error", 
                            "msg": "This invoice is already purchased and cannot be added again."
                        },
                        409,
                    )

            data, error = invoice_schema.load(invoice_data, partial=True)

            if error:
                wrong_invoice_data.append(invoice_data)
                continue

            if (
                "actions" in data
                and not data.get("actions") == InvoiceActions.non_factored
            ):

                if not data.get("amount") is None:
                    invoice_total = soa.invoice_total - invoice.amount
                    soa.invoice_total = float(invoice_total) + data.get("amount")
                    soa.save()

            if wrong_invoice_data:
                return custom_response(
                    {
                        "status": "error",
                        "msg": "Found invalid invoices data",
                        "wrong_invoice_data": wrong_invoice_data,
                    },
                    404,
                )
            else:
                invoice.update(data)

            updated_invoice_list.append(invoice_schema.dump(invoice).data)

        return custom_response(updated_invoice_list, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(invoice_id):
    """
    Delete A Invoice
    """
    try:
        invoice = Invoice.get_one_based_off_control_accounts(invoice_id)
        if not invoice:
            return custom_response({"status": "error", "msg": "invoice not found"}, 404)

        # Assigned to variable soa_id before deleting invoice
        soa_id = invoice.soa_id

        # invoice.is_deleted = True
        # invoice.deleted_at = datetime.utcnow()

        ##  deleting invoice supporting documents also when deleting an invoice
        InvoiceSupportingDocuments.query.filter(
            InvoiceSupportingDocuments.invoice_id == invoice_id
        ).delete()
        ## deleting the invoice
        invoice.delete()
        
        user_permissions = Permissions.get_user_role_permissions()
        user_role = user_permissions["user_role"]

        # checking, if user has role 'AE' then add in approvals history
        if (
            user_role 
            and user_role.lower() == "ae"
        ):
            soa = SOA.query.filter_by(is_deleted=False, id=soa_id).first()
            
            if not soa.is_request_updated():                
                get_user_detail = Permissions.get_user_details()
                user_email = get_user_detail["email"]
                
                # to be saved in approval history
                approvals_history_data = {
                    "key": "updated_at",
                    "value": datetime.utcnow(),
                    "user": user_email,
                    "soa_id": soa.id,
                    "attribute": {"updated": "invoice_deleted"},
                }
                
                approvals_history = ApprovalsHistory(approvals_history_data)
                approvals_history.save()

        return custom_response({"status": "success", "msg": "Invoice deleted"}, 202)

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update_invoice_status():
    """
  Update Invoice Status
  """
    try:
        request_data = request.get_json()
        soa_id = request_data.get("soa_id", None)

        # check soa exists
        soa = SOA.get_one_based_off_control_accounts(soa_id)
        if not soa:
            return custom_response({"status": "error", "msg": "soa not found"}, 404) 

        # invoice status = approved
        # Ref: https://docs.sqlalchemy.org/en/13/orm/query.html#sqlalchemy.orm.query.Query.update
        invoice_data = Invoice.query.filter_by(is_deleted=False, soa_id=soa_id)
        invoice_data.update({Invoice.status: "approved"}, synchronize_session="fetch")

        db.session.commit()

        return custom_response(
            {"status": "success", "msg": "Invoices' status updated"}, 200
        )
    except Exception as e:
        print(str(e))
        db.session.rollback()
        raise
    finally:
        db.session.close()


@Auth.auth_required
def generate_invoice_csv():
    try:
        request_data = request.get_json()
        soa_id = request_data.get('soa_id', None)
        # Change the export format from CSV to EXCEL file .xlsx(LC-1103)
        generate_file_extension = 'xlsx'
        
        file_extensions = ['xlsx']        
        if generate_file_extension.lower() not in file_extensions:
            return custom_response({"status": "error", "msg": "Please input xlsx extension for generating invoice file"}, 404)
        
        # File Name
        get_soa = SOA.query.filter_by(is_deleted=False, id=soa_id, status='completed').first()
        if not get_soa:
            return custom_response({"status": "error", "msg": "SOA does not exist"}, 404)
        
        # Get SOA date and convert datetime to date
        get_date = str(get_soa.updated_at)
        soa_date = dateutil.parser.parse(get_date).date()

        # get soa approval history if approved by BO
        soa_completed_attribute = None
        if get_soa.status.value == 'completed':
            soa_completed = get_soa.request_approved_by_bo()
            if soa_completed:
                if isinstance(soa_completed.attribute, str):
                    soa_completed_attribute = json.loads(soa_completed.attribute)
                else:
                    soa_completed_attribute = soa_completed.attribute

        # get invoice             
        get_invoices = Invoice.query.filter_by(is_deleted=False, soa_id=soa_id, status='approved').all()
        if not get_invoices:
            return custom_response({"status": "error", "msg": "No approved invoice found"}, 404)
        
        invoice_count = len(get_invoices)
        
        # generate file name
        filename = f'{soa_date}-{get_soa.client.ref_client_no}-{get_soa.client.name}-{get_soa.id}-{invoice_count}.{generate_file_extension.lower()}'
        
        invoice_numbers = []
        amount = []
        date = []
        due_date = []
        po_number = []
        refno = []
        for invoice in get_invoices:
            # date format changed for cadence requirement
            get_calculated_date = invoice.invoice_date + timedelta(days=int(invoice.terms))  

            # Change date format from DD-MM-YYYY to YYYY-MM-DD(LC-1103)
            invoice_date = invoice.invoice_date.strftime("%Y-%m-%d")

            invoice_amount = float(0)
            if invoice.amount is not None:
                invoice_amount = "{0:,.2f}".format(invoice.amount)

            if soa_completed_attribute and 'client_debtors' in soa_completed_attribute and soa_completed_attribute['client_debtors']:
                get_client_debtor = [client_debtors for client_debtors in soa_completed_attribute['client_debtors'] if client_debtors['client_id'] == invoice.client_id and client_debtors['debtor_id'] == invoice.debtor]
                client_ref_no = get_client_debtor[0]['client_ref_no'] if get_client_debtor and get_client_debtor[0]['client_ref_no'] is not None else None
            else:
                get_client_debtor = ClientDebtor.query.filter_by(client_id=invoice.client_id, debtor_id=invoice.debtor, is_deleted=False).first()
                client_ref_no = get_client_debtor.client_ref_no if get_client_debtor and get_client_debtor.client_ref_no is not None else None
            
            invoice_numbers.append(f'{invoice.invoice_number}')
            amount.append(f'{invoice_amount}')
            date.append(invoice_date)
            # Change date format from DD-MM-YYYY to YYYY-MM-DD(LC-1103)
            due_date.append(get_calculated_date.strftime("%Y-%m-%d"))
            po_number.append(invoice.po_number)
            refno.append(client_ref_no)

        
        df = pd.DataFrame({
                'invoice': invoice_numbers,
                'amount': amount,
                'date': date,
                'due_date': due_date,
                'po': po_number,
                'refno': refno                    
            })

        # write bytes to file in memory
        in_memory_buffer = io.BytesIO()
        excel_writer = pd.ExcelWriter(in_memory_buffer, engine='xlsxwriter')
        df.to_excel(excel_writer, index=False)
        excel_writer.save()
        
        in_memory_buffer.seek(0)
        response = make_response(in_memory_buffer.getvalue())
        response.headers["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
        response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response.headers["Access-Control-Expose-Headers"] = "content-disposition"

        return response        

    except ValueError as e:
        print('Error', str(e))
        return custom_response({"status": "error", "msg": str(e)}, 404)
    except Exception as e:
        print('Error', str(e))
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_nonfactored_and_deleted_invoices(soa_id):
    try:
        # get invoice
        get_invoices = Invoice.query.filter_by(soa_id=soa_id).all()
        if not get_invoices:
            return custom_response({"status": "error", "msg": "Invoices not found"}, 404)

        column_list = [
            "id",
            "actions",
            "added_by",
            "amount",
            "client_id",
            "debtor",
            "invoice_date",
            "invoice_number",
            "is_credit_insured",
            "is_release_from_reserve",
            "notes",
            "po_number",
            "soa_id",
            "status",
            "terms",
            "verified_by",
            "updated_at",
            "is_deleted",
        ]
        obj_to_dict = lambda table_obj: {
            column: getattr(table_obj, column) for column in column_list
        }

        get_nonfactored_invoice = []
        get_deleted_invoice = []
        invoice_obj = {}
        for get_invoice in get_invoices:
            invoice_dict = obj_to_dict(get_invoice)

            # date format to ISO 8601
            invoice_dict["invoice_date"] = invoice_dict["invoice_date"].isoformat()
            invoice_dict["updated_at"] = invoice_dict["updated_at"].isoformat()

            # debtor name
            invoice_dict["debtor_name"] = get_invoice.debtors.name

            # fixed error Object of type is not JSON serializable
            invoice_dict["actions"] = invoice_dict.pop("actions").value
            invoice_dict["status"] = invoice_dict.pop("status").value
            invoice_dict["amount"] = float(invoice_dict.pop("amount"))

            # get deleted invoice
            if invoice_dict["is_deleted"] == True:
                get_deleted_invoice.append(invoice_dict)

            # # get non-factored invoice
            if invoice_dict["actions"] == "non_factored":
                get_nonfactored_invoice.append(invoice_dict)

        return custom_response(
            {
                "deleted_invoice": get_deleted_invoice,
                "non_factored_invoice": get_nonfactored_invoice,
            },
            200,
        )

    except Exception as e:
        print("Error", str(e))
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def upload_invoices():
    try:
        request_data = request.get_json()
        soa_id = request_data.get("soa_id", None)
        invoices = request_data.get("invoices", None)

        if soa_id is None or invoices is None or len(invoices) == 0:
            return custom_response({"status": "error", "msg": "SOA does not exist/ file is empty"}, 404)
            
        if (len(invoices) > 0) and ("invoice_number" not in invoices[0]):
            return custom_response({"status": "error", "msg": "Please upload invoice file"}, 404)

        soa = SOA.get_one_based_off_control_accounts(soa_id)
        if not soa:
            return custom_response({"status": "error", "msg": "soa not found"}, 404)

        data_list_added = []
        data_list_exists = []
        wrong_debtors = []
        wrong_values = []

        invoice_number_list = [
            invoice_number_data["invoice_number"] for invoice_number_data in invoices
        ]

        # Get invoice list from cadance db
        validated_invoice_list = validate_invoice(soa.client.ref_key)

        get_existing_invoice = (
            Invoice.query.with_entities(Invoice.invoice_number)
            .filter(
                Invoice.is_deleted == False,
                Invoice.invoice_number.in_(invoice_number_list),
                Invoice.soa_id == soa_id,
            )
            .all()
        )

        # Changed debtor name to ref no in csv (LC-516)
        invoice_debtor_list = [
            invoice_data["debtorkey"]
            for invoice_data in invoices
            if "debtorkey" in invoice_data and invoice_data["debtorkey"]
        ]

        get_all_debtor = (
            Debtor.query.join(ClientDebtor, Client)
            .filter(Debtor.id == ClientDebtor.debtor_id)
            .filter(ClientDebtor.client == soa.client)
            .filter(Debtor.is_deleted == False, Debtor.ref_key.in_(invoice_debtor_list))
            .with_entities(Debtor.id, Debtor.ref_key)
            .all()
        )

        seen = set()
        for row_obj in invoices:
            row = row_obj.copy()

            if row["debtorkey"] == "":
                wrong_debtors.append(row_obj)
                continue
            debtor_obj = [
                item for item in get_all_debtor if item[1] == int(row["debtorkey"])
            ]
            if not debtor_obj:
                wrong_debtors.append(row_obj)
                continue

            # check for existing invoice
            invoice_number_obj = [
                item
                for item in get_existing_invoice
                if item[0] == row["invoice_number"]
            ]
            if invoice_number_obj:
                data_list_exists.append(row_obj)
                continue

            # check invoice with cadance db
            if row["invoice_number"] in validated_invoice_list:
                data_list_exists.append(row_obj)
                continue

            if row["invoice_number"] not in seen:
                seen.add(row_obj["invoice_number"])
            else:
                data_list_exists.append(row_obj)
                continue

            row.update(
                {
                    "client_id": soa.client_id,
                    "soa_id": soa.id,
                    "debtor": debtor_obj[0][0],
                    "invoice": row["invoice_number"],
                }
            )

            data, error = invoice_schema.load(row)
            if not error:
                invoice = Invoice(data)
                data_list_added.append(invoice)
            else:
                row_obj["error"] = error
                wrong_values.append(row_obj)

        db.session.add_all(data_list_added)
        db.session.commit()

        data_list_added = invoice_schema.dump(data_list_added, many=True).data

        [
            (
                obj.update(
                    {
                        "invoice": obj.pop("invoice_number"),
                        "credit_insured": obj.pop("is_credit_insured"),
                        "debtor_id": obj.pop("debtor"),
                    }
                )
            )
            for obj in data_list_added
        ]
        
        return custom_response(
            {
                "data_list_added": data_list_added,
                "data_list_exists": data_list_exists,
                "wrong_debtors": wrong_debtors,
                "wrong_values": wrong_values
            },
            200
        )                
    
    except:
        db.session.rollback()
        raise
    finally:
        db.session.close()
        

@Auth.auth_required
def validate_uploading_invoices():
    try:
        request_data = request.get_json()
        soa_id = request_data.get("soa_id", None)
        invoices = request_data.get("invoices", None)

        if (soa_id is None or invoices is None or len(invoices) == 0):
            return custom_response({"status": "error", "msg": "SOA does not exist/ file is empty"}, 404)

        if (len(invoices) > 0) and ("invoice_number" not in invoices[0]):
            return custom_response({"status": "error", "msg": "Please upload invoice file"}, 404)
        
        soa = SOA.get_one_based_off_control_accounts(soa_id)
        if not soa:
            return custom_response({"status": "error", "msg": "soa not found"}, 404)

        # current EST date
        invoices[0]["current_date"] = current_date().isoformat()

        validated_invoices = CadenceValidateInvoices(
            soa=soa, validate_invoices=invoices, debtor_ref_key_exists=True
        )

        return custom_response(
            {
                "data_list_added": validated_invoices.get_valid_invoices,
                "data_list_exists": validated_invoices.get_already_exist_invoices,
                "wrong_debtors": validated_invoices.get_wrong_debtors,
                "wrong_values": validated_invoices.get_wrong_invoice_data,
            }, 
            200
        )
        
    except Exception as e:
        print("Error", str(e))
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_collection_notes(invoice_id):
    """
    Get Invoice's collection notes
    """
    client_id = request.args.get("client_id", 0, type=int)
    if not client_id:
        return custom_response({"status": "error", "msg": "client_id is required"}, 400)

    invoice = Invoice.get_one_based_off_control_accounts(invoice_id)

    if not invoice:
        return custom_response({"status": "error", "msg": "Invoice not found"}, 404)

    collection_notes = invoice.collection_notes(client_id)

    return custom_response(collection_notes, 200)

@Auth.auth_required
def get_cn_approval_history(invoice_id):
    """
    Get Invoice's collection notes approval history
    """
    client_id = request.args.get("client_id", 0, type=int)
    if not client_id:
        return custom_response({"status": "error", "msg": "client_id is required"}, 400)

    invoice = Invoice.get_one_based_off_control_accounts(invoice_id)

    if not invoice:
        return custom_response({"status": "error", "msg": "Invoice not found"}, 404)

    approval_history = invoice.cn_approvals_history(client_id)

    return custom_response(approval_history, 200)

@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.verification_notes)
def get_verification_notes(invoice_id):
    """
    Get Invoice's verification notes
    """
    # client_id = request.args.get("client_id", 0, type=int)
    # if not client_id:
    #     return custom_response({"status": "error", "msg": "client_id is required"}, 400)

    invoice = Invoice.get_one_based_off_control_accounts(invoice_id)

    if not invoice:
        return custom_response({"status": "error", "msg": "Invoice not found"}, 404)

    verification_notes = invoice.get_verification_notes()

    return custom_response(verification_notes, 200)

@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.verification_notes)
def get_vn_approval_history(invoice_id):
    """
    Get Invoice's verification notes approval history
    """
    client_id = request.args.get("client_id", 0, type=int)
    if not client_id:
        return custom_response({"status": "error", "msg": "client_id is required"}, 400)

    invoice = Invoice.get_one_based_off_control_accounts(invoice_id)

    if not invoice:
        return custom_response({"status": "error", "msg": "Invoice not found"}, 404)

    approval_history = invoice.vn_approvals_history(client_id)

    return custom_response(approval_history, 200)

@Auth.auth_required
def get_invoice_supporting_documents(invoice_id):
    """
    Get Invoice's invoice_supporting_documents
    """
    invoice = Invoice.get_one_based_off_control_accounts(invoice_id)

    if not invoice:
        return custom_response({"status": "error", "msg": "Invoice not found"}, 404)

    invoice_supporting_documents = invoice.get_invoice_supporting_documents()

    return custom_response(invoice_supporting_documents, 200)
