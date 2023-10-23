from flask import request
from sqlalchemy.sql.sqltypes import DateTime
from src.models import *
from src.resources.v2.schemas import *
from src.resources.v2.helpers import (
    custom_response,
    calculate_time_remaining,
    principal_settings,
)
from decimal import Decimal
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from src.middleware.organization import Organization
from datetime import date, datetime
from sqlalchemy import cast, Date, or_
from src.resources.v2.helpers.convert_datetime import *


@Auth.auth_required
def get_time_remaining():
    try:
        same_day_ach_flag = False

        # You could also pass datetime.time object in this part and convert it to string.
        same_day_ach_time = str(
            "13:00:00"
        )  # static time if same_day_ach has not been added in permission resources
        submission_time = str(
            "15:00:00"
        )  # static time if submission has not been added in permission resources

        # user role and permissions
        get_user_permissions = Permissions.get_user_role_permissions()
        user_permissions = get_user_permissions["user_permissions"]

        # for getting client's settings custom same day ach cut off time (LC-1715)
        client_id = request.args.get("client_id", None)
        client_settings = {}

        if client_id:
            client = Client.get_one_client(client_id)
            if not client:
                return custom_response(
                    {"status": "error", "msg": "client not found"}, 404
                )

            if (
                client.client_settings
                and client.client_settings[0].is_deleted == False
            ):
                client_settings = ClientSettingsSchema().dump(
                    client.client_settings[0]
                ).data

        # checking, if client settings has same_day_ach_cut_off_time
        if (
            client_settings
            and "same_day_ach_cut_off_time" in client_settings
            and client_settings["same_day_ach_cut_off_time"]
        ):
            same_day_ach_time = client_settings["same_day_ach_cut_off_time"]
            same_day_ach_flag = True

        # check time limits in permission resources
        time_limits = (
            user_permissions["time_limits"]
            if "time_limits" in user_permissions and user_permissions["time_limits"]
            else {}
        )

        # checking, same day ach in permission
        if (
            not same_day_ach_flag
            and time_limits
            and "same_day_ach" in time_limits
            and time_limits["same_day_ach"]
            and isinstance(time_limits["same_day_ach"], dict)
        ):
            same_day_ach_time = list(time_limits["same_day_ach"].keys())[0]
            same_day_ach_flag = True

        # checking, submission in permission
        if (
            time_limits
            and "submission" in time_limits
            and time_limits["submission"]
            and isinstance(time_limits["submission"], dict)
        ):
            submission_time = list(time_limits["submission"].keys())[0]

        # cal same day ach time remaining
        same_day_ach_time_remaining = calculate_time_remaining(
            time_end=same_day_ach_time
        )
        # cal submission time remaining
        submission_time_remaining = calculate_time_remaining(time_end=submission_time)
        
        # Required for principal (LC-1146)
        if (
            get_user_permissions["user_role"] != "principal"
            and not same_day_ach_flag
        ):
            same_day_ach_time_remaining["diff"] = None

        return custom_response(
            {
                "remaining_time": {
                    "same_day_ach": same_day_ach_time_remaining["diff"],
                    "submission": submission_time_remaining["diff"],
                }
            }
        )
    except Exception as e:
        print(str(e))
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_dashboard():
    try:
        # filters
        page = request.args.get("page", 1, type=int)
        rpp = request.args.get("rpp", 20, type=int)
        ordering = request.args.get("ordering", None, type=str)
        use_ref = False
        if request.path == "/requests":
            use_ref = True
        search = request.args.get("search", None, type=str)
        start_date = request.args.get("start_date", None, type=str)
        end_date = request.args.get("end_date", None, type=str)
        control_account = request.args.get("control_account", None, type=str)
        stage = request.args.get("stage", None, type=str)
        high_priority = request.args.get("high_priority", None, type=str)
        dashboard = True

        # client ids
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        # user role
        user_role = get_locations["user_role"]
        
        # control accounts
        business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        # date
        if start_date is not None:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")

        if end_date is not None:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")

        if start_date and end_date and start_date > end_date:
            return custom_response(
                {"status": "error", "msg": "end_date must be greater than start_date."},
                400,
            )

        # Funding Completed Lane: Don't need start_date and end_date for dashboard
        if (
            dashboard 
            and stage and stage == "completed"
        ):
            start_date = None
            end_date = None

        ## SOA Listing ##
        soa_resource = SOAListing.get_paginated_soa(
            page=page,
            rpp=rpp,
            ordering=ordering,
            search=search,
            start_date=start_date,
            end_date=end_date,
            control_account=control_account,
            stage=stage,
            use_ref=use_ref,
            high_priority=high_priority,
            dashboard=dashboard,
            client_ids=client_ids,
            user_role=user_role,
            business_control_accounts=business_control_accounts,
        )
        
        # soa: data
        soa_data = (
            soa_resource["data"] if soa_resource and "data" in soa_resource else []
        )
        
        # soa: total count
        soa_total_count = (
            int(soa_resource["total_count"])
            if soa_resource and "total_count" in soa_resource
            else int(0)
        )
        
        # soa: total pages
        soa_total_pages = (
            int(soa_resource["total_pages"])
            if soa_resource and "total_pages" in soa_resource
            else int(0)
        )
        
        # soa: rpp
        soa_rpp = (
            int(soa_resource["per_page"])
            if soa_resource and "per_page" in soa_resource
            else int(0)
        )

        # Reserve Release Listing 
        reserve_release_resource = ReserveReleaseListing.get_paginated_reserve_release(
            page=page,
            rpp=rpp,
            ordering=ordering,
            search=search,
            start_date=start_date,
            end_date=end_date,
            control_account=control_account,
            stage=stage,
            use_ref=use_ref,
            high_priority=high_priority,
            dashboard=dashboard,
            client_ids=client_ids,
            user_role=user_role,
            business_control_accounts=business_control_accounts,
        )

        # reserve release: data
        reserve_release_data = (
            reserve_release_resource["data"]
            if reserve_release_resource and "data" in reserve_release_resource
            else []
        )

        # reserve release: total count
        reserve_release_total_count = (
            int(reserve_release_resource["total_count"])
            if reserve_release_resource and "total_count" in reserve_release_resource
            else int(0)
        )

        # reserve release: total pages
        reserve_release_total_pages = (
            int(reserve_release_resource["total_pages"])
            if reserve_release_resource and "total_pages" in reserve_release_resource
            else int(0)
        )

        # reserve release: rpp
        reserve_release_rpp = (
            int(reserve_release_resource["per_page"])
            if reserve_release_resource and "per_page" in reserve_release_resource
            else int(0)
        )
        
        # total count: soa total count + reserve release total count
        total_count = soa_total_count + reserve_release_total_count

        # total_pages: soa total_pages + reserve release total_pages
        total_pages = (
            soa_total_pages
            if soa_total_pages > reserve_release_total_pages
            else reserve_release_total_pages
        )
        
        # per_page: soa rpp + reserve release rpp
        per_page = soa_rpp + reserve_release_rpp

        # merged soa data and reserve release data
        soa_data.extend(reserve_release_data)

        ## Payee Listing ##
        # for payee(LC-1650): show in principal dashboard(Client's Request)
        if stage and stage == "client_submission":
            # payee resource
            payee_resource = PayeeListing.get_paginated_payees(
                page=page,
                rpp=rpp,
                ordering=ordering,
                search=search,
                start_date=start_date,
                end_date=end_date,
                control_account=control_account,
                stage=stage,
                dashboard=dashboard,
                client_ids=client_ids,
                user_role=user_role,
                business_control_accounts=business_control_accounts,
            )

            # payee: total count
            payee_total_count = (
                int(payee_resource["total_count"])
                if payee_resource and "total_count" in payee_resource
                else int(0)
            )

            # payee: total pages
            payee_total_pages = (
                int(payee_resource["total_pages"])
                if payee_resource and "total_pages" in payee_resource
                else int(0)
            )

            # payee: rpp
            payee_rpp = (
                int(payee_resource["per_page"])
                if payee_resource and "per_page" in payee_resource
                else int(0)
            )
            
            # total count: total count + payee total count
            total_count = total_count + payee_total_count
            
            # total pages: total pages + payee total pages
            total_pages = (
                total_pages
                if total_pages > payee_total_pages
                else payee_total_pages
            )

            # per page: per page + payee rpp
            per_page = per_page + payee_rpp

            # payee: data
            payee_data = (
                payee_resource["data"]
                if payee_resource
                and "data" in payee_resource
                and payee_resource["data"]
                else []
            )

            # merged payee data
            soa_data.extend(payee_data)

            ## Compliance Repository Listing ##
            # LC-2083: show in principal dashboard(Client's Request)
            cr_resource = ComplianceRepositoryListing.get_paginated(
                page=page,
                rpp=rpp,
                ordering=ordering,
                search=search,
                start_date=start_date,
                end_date=end_date,
                control_account=control_account,
                stage=stage,
                dashboard=dashboard,
                client_ids=client_ids,
                user_role=user_role,
                business_control_accounts=business_control_accounts,
            )

            # cr: total count
            cr_total_count = (
                int(cr_resource["total_count"])
                if cr_resource and "total_count" in cr_resource
                else int(0)
            )

            # cr: total pages
            cr_total_pages = (
                int(cr_resource["total_pages"])
                if cr_resource and "total_pages" in cr_resource
                else int(0)
            )

            # cr: rpp
            cr_rpp = (
                int(cr_resource["per_page"])
                if cr_resource and "per_page" in cr_resource
                else int(0)
            )
            
            # total count: total count + cr total count
            total_count = total_count + cr_total_count
            
            # total pages: total pages + cr total pages
            total_pages = (
                total_pages
                if total_pages > cr_total_pages
                else cr_total_pages
            )

            # per page: per page + cr rpp
            per_page = per_page + cr_rpp

            # cr: data
            cr_data = (
                cr_resource["data"]
                if cr_resource
                and "data" in cr_resource
                and cr_resource["data"]
                else []
            )
            
            # merged cr data
            soa_data.extend(cr_data)

        ## "Today's Pending Working Items" lane (dashboard) ##
        if stage and stage == "pending" and start_date:
            ## Debtor Limit Approvals(Credit Limit) Listing ##
            # for LC-1909: show in "Today's Pending Working Items" lane (dashboard)
            dla_resource = DebtorLimitApprovalsListing.get_paginated(
                page=page,
                rpp=rpp,
                ordering=ordering,
                search=search,
                start_date=start_date,
                end_date=end_date,
                control_account=control_account,
                stage=stage,
                dashboard=dashboard,
                client_ids=client_ids,
                user_role=user_role,
                business_control_accounts=business_control_accounts,
            )

            # dla: total count
            dla_total_count = (
                int(dla_resource["total_count"])
                if dla_resource and "total_count" in dla_resource
                else int(0)
            )

            # dla: total pages
            dla_total_pages = (
                int(dla_resource["total_pages"])
                if dla_resource and "total_pages" in dla_resource
                else int(0)
            )

            # dla: rpp
            dla_rpp = (
                int(dla_resource["per_page"])
                if dla_resource and "per_page" in dla_resource
                else int(0)
            )
            
            # total count: total count + dla total count
            total_count = total_count + dla_total_count
            
            # total pages: total pages + dla total pages
            total_pages = (
                total_pages
                if total_pages > dla_total_pages
                else dla_total_pages
            )

            # per page: per page + dla rpp
            per_page = per_page + dla_rpp

            # dla: data
            dla_data = (
                dla_resource["data"]
                if dla_resource
                and "data" in dla_resource
                and dla_resource["data"]
                else []
            )

            # merged dla data
            soa_data.extend(dla_data)

            ## Generic Request Listing ##
            # for LC-2014: show in "Today's Pending Working Items" lane (dashboard)
            gn_resource = GenericRequestListing.get_paginated(
                page=page,
                rpp=rpp,
                ordering=ordering,
                search=search,
                start_date=start_date,
                end_date=end_date,
                control_account=control_account,
                stage=stage,
                dashboard=dashboard,
                client_ids=client_ids,
                user_role=user_role,
                business_control_accounts=business_control_accounts,
            )

            # gn: total count
            gn_total_count = (
                int(gn_resource["total_count"])
                if gn_resource and "total_count" in gn_resource
                else int(0)
            )

            # gn: total pages
            gn_total_pages = (
                int(gn_resource["total_pages"])
                if gn_resource and "total_pages" in gn_resource
                else int(0)
            )

            # gn: rpp
            gn_rpp = (
                int(gn_resource["per_page"])
                if gn_resource and "per_page" in gn_resource
                else int(0)
            )
            
            # total count: total count + gn total count
            total_count = total_count + gn_total_count
            
            # total pages: total pages + gn total pages
            total_pages = (
                total_pages
                if total_pages > gn_total_pages
                else gn_total_pages
            )

            # per page: per page + gn rpp
            per_page = per_page + gn_rpp

            # gn: data
            gn_data = (
                gn_resource["data"]
                if gn_resource
                and "data" in gn_resource
                and gn_resource["data"]
                else []
            )
            
            # merged gn data
            soa_data.extend(gn_data)
        
        msg = "Records not found"

        # sort list
        data = []
        if soa_data:
            msg = "Records found"
            if (
                (not stage or stage not in ["client_submission"])
                and (not start_date and not end_date)
            ):
                # sorted list by high_priority desc and payment_type based on a given order payment_type_list(LC-1600)
                payment_type_list = ["", "S", "W", "A"]

                data = sorted(
                    soa_data,
                    key=lambda inv: (
                        -inv["high_priority"],
                        payment_type_list.index([inv["payment_type"]][0][0] if [inv["payment_type"]][0] else ""), # get the first character from the payment_type in the list
                        inv["last_processed_at"]
                    ),
                )
            else:
                # sorted list by updated_at desc
                data = sorted(soa_data, key=lambda inv: inv["updated_at"], reverse=True)

        response_data = {
            "msg": msg,
            "per_page": per_page,  # soa + reserve release
            "total_count": total_count,  # soa + reserve release
            "total_pages": total_pages,
            "current_page": page,
            "data": data,  # soa + reserve release
        }

        return custom_response(response_data, 200)
    except Exception as e:
        print(f"Dashboard Exception: {e}")
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_soa_total():
    try:
        # Organization
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        control_account_id = request.args.get("control_account_id", None)
        # control accounts
        business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        # current est date: for comparing with last_processed_at(utc)
        today = date_concat_time(date_concat="current")
        next_day = date_concat_time(date_concat="next")
        
        soa = (
            SOA.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                SOA.is_deleted == False, SOA.client_id.in_(client_ids),
                cast(SOA.last_processed_at, DateTime) >= today,
                cast(SOA.last_processed_at, DateTime) <= next_day,
                Client.is_active == True,
                ControlAccount.name.in_(business_control_accounts),
            )
            .group_by(SOA.id)
        )

        soa_obj = {}

        # reserve release
        reserve_release = (
            ReserveRelease.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                ReserveRelease.is_deleted == False,
                ReserveRelease.client_id.in_(client_ids),
                cast(ReserveRelease.last_processed_at, DateTime) >= today,
                cast(ReserveRelease.last_processed_at, DateTime) <= next_day,
                Client.is_active == True,
                ControlAccount.name.in_(business_control_accounts),
            )
            .group_by(ReserveRelease.id)
        )

        if control_account_id == "undefined":
            control_account_id = None

        if control_account_id:
            soa = soa.filter(
                ClientControlAccounts.control_account_id == control_account_id
            )
            reserve_release = reserve_release.filter(
                ClientControlAccounts.control_account_id == control_account_id
            )

        # ToDo: commented code to be removed
        # SOA Approvals by BO Count
        # get_soa_completed = soa.filter(SOA.status == "completed")
        # soa_completed_total = get_soa_completed.count()

        # # SOA pending Count
        # soa_pending_total = soa.filter(SOA.status == "pending").count()

        # # SOA action required Count
        # soa_action_required_total = soa.filter(SOA.status == "action_required").count()

        # # SOA rejected Count
        # soa_rejected_total = soa.filter(SOA.status == "rejected").count()

        # # SOA reviewed Count
        # soa_reviewed_total = soa.filter(SOA.status == "reviewed").count()

        # # SOA approved by AE Count
        # soa_approved_total = soa.filter(SOA.status == "approved").count()

        # SOA current day principal, ae, bo requests submitted total
        soa_total_submitted = soa.filter(
            or_(
                SOA.status == "completed",
                SOA.status == "pending",
                SOA.status == "action_required",
                SOA.status == "rejected",
                SOA.status == "reviewed",
                SOA.status == "approved",
            )
        ).count()
        # soa_total_submitted = (
        #     soa_pending_total
        #     + soa_action_required_total
        #     + soa_rejected_total
        #     + soa_reviewed_total
        #     + soa_approved_total
        #     + soa_completed_total
        # )

        # soa approved by BO
        get_soa_completed = soa.filter(SOA.status == "completed")
        all_soa_completed = get_soa_completed.all()

        # soa approved by BO count
        soa_completed_total = get_soa_completed.count()

        soa_approved_amount = Decimal(0)
        total_invoice_amount = Decimal(0)
        if all_soa_completed:
            for each_soa in all_soa_completed:
                # total soa disbursement_amount
                if each_soa.disbursement_amount is not None:
                    soa_approved_amount += each_soa.disbursement_amount

                # total soa invoice_total
                if each_soa.invoice_total is not None:
                    total_invoice_amount += each_soa.invoice_total

            # soa_approved_amount = sum(
            #     soa_completed.disbursement_amount
            #     for soa_completed in get_soa_completed
            #     if soa_completed.disbursement_amount is not None
            # )
        # ToDo: commented code to be removed
        # Soa Invoice Total
        # get_invoice_total = soa.filter(SOA.status == "completed")
        # total_invoice_amount = Decimal(0)
        # if get_invoice_total:
        #     total_invoice_amount = sum(
        #         invoice.invoice_total
        #         for invoice in get_invoice_total
        #         if invoice.invoice_total is not None
        #     )

        # # For Reserve Release count
        # reserve_release_submitted_total = int(0)
        # rr_completed_total = int(0)
        total_rr_completed_amount = Decimal(0)
        # if reserve_release:
        #     # Reserve Release Approvals by BO Count
        #     get_rr_completed = reserve_release.filter(
        #         ReserveRelease.status == "completed"
        #     )
        #     rr_completed_total = get_rr_completed.count()

        #     # Reserve Release pending Count
        #     rr_pending_total = reserve_release.filter(
        #         ReserveRelease.status == "pending"
        #     ).count()

        #     # Reserve Release action required Count
        #     rr_action_required_total = reserve_release.filter(
        #         ReserveRelease.status == "action_required"
        #     ).count()

        #     # Reserve Release rejected Count
        #     rr_rejected_total = reserve_release.filter(
        #         ReserveRelease.status == "rejected"
        #     ).count()

        #     # Reserve Release reviewed Count
        #     rr_reviewed_total = reserve_release.filter(
        #         ReserveRelease.status == "reviewed"
        #     ).count()

        #     # Reserve Release approved Count
        #     rr_approved_total = reserve_release.filter(
        #         ReserveRelease.status == "approved"
        #     ).count()

        # Reserve Release: current day requests submitted total by principal, ae, bo 
        reserve_release_submitted_total = reserve_release.filter(
            or_(
                ReserveRelease.status == "completed",
                ReserveRelease.status == "pending",
                ReserveRelease.status == "action_required",
                ReserveRelease.status == "rejected",
                ReserveRelease.status == "reviewed",
                ReserveRelease.status == "approved",
            )
        ).count()
            # reserve_release_submitted_total = (
            #     rr_pending_total
            #     + rr_action_required_total
            #     + rr_rejected_total
            #     + rr_reviewed_total
            #     + rr_approved_total
            #     + rr_completed_total
            # )

        # Reserve Release approved by BO
        get_rr_completed = reserve_release.filter(
            ReserveRelease.status == "completed"
        )
        all_rr_completed = get_rr_completed.all()
        # Reserve Release approved by BO count
        rr_completed_total = get_rr_completed.count()
        
        # total reserve release disbursement amount
        if all_rr_completed:
            total_rr_completed_amount = sum(
                rr_completed.disbursement_amount
                for rr_completed in all_rr_completed
                if rr_completed.disbursement_amount is not None
            )

        # Cash Advanced: Total soa and reserve release disbursement amount
        total_approved_advance = soa_approved_amount + total_rr_completed_amount

        soa_obj.update(
            {
                "soa_submitted": soa_total_submitted,
                "soa_approved": soa_completed_total,
                "invoice_total": Decimal(total_invoice_amount),
                "reserve_submitted": reserve_release_submitted_total,
                "reserve_approved": rr_completed_total,
                "approved_advance": Decimal(total_approved_advance),
            }
        )

        return custom_response(soa_obj)
    except Exception as e:
        print(str(e))
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def total_soa_amount():
    try:
        # Organization
        get_locations = Organization.get_locations()
        client_id_list = get_locations["client_list"]
        
        # control accounts
        business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        # current est date: for comparing with last_processed_at(utc)
        today = date_concat_time(date_concat="current")
        next_day = date_concat_time(date_concat="next")

        control_account_id = request.args.get("control_account_id", None)

        soa = (
            SOA.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                SOA.is_deleted == False, 
                SOA.client_id.in_(client_id_list),
                Client.is_active == True,
                ControlAccount.name.in_(business_control_accounts),
            )
            .group_by(SOA.id)
        )

        soa_obj = {}
        # if not soa:
        #     return custom_response({"status": "error", "msg": "soa not found"}, 404)

        # reserve release
        reserve_release = (
            ReserveRelease.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                ReserveRelease.is_deleted == False,
                ReserveRelease.client_id.in_(client_id_list),
                Client.is_active == True,
                ControlAccount.name.in_(business_control_accounts),
            )
            .group_by(ReserveRelease.id)
        )

        if control_account_id == "undefined":
            control_account_id = None

        if control_account_id:
            soa = soa.filter(
                ClientControlAccounts.control_account_id == control_account_id
            )
            reserve_release = reserve_release.filter(
                ClientControlAccounts.control_account_id == control_account_id
            )

        # get Reserve Release total
        total_rr_pending_amount = Decimal(0)
        total_rr_approved_amount = Decimal(0)
        total_rr_completed_amount = Decimal(0)
        if reserve_release:
            # get Reserve Release total_pending_amount
            get_rr_pending = reserve_release.filter(ReserveRelease.status == "pending")
            if get_rr_pending:
                total_rr_pending_amount = sum(
                    rr_pending.disbursement_amount
                    for rr_pending in get_rr_pending
                    if rr_pending.disbursement_amount is not None
                )

            # get Reserve Release total_approved_amount
            get_rr_approved = reserve_release.filter(
                ReserveRelease.status == "approved"
            )
            if get_rr_approved:
                total_rr_approved_amount = sum(
                    rr_approved.disbursement_amount
                    for rr_approved in get_rr_approved
                    if rr_approved.disbursement_amount is not None
                )

            # get Reserve Release total_completed_amount
            get_rr_completed = reserve_release.filter(
                ReserveRelease.status == "completed",
                cast(ReserveRelease.last_processed_at, DateTime) >= today,
                cast(ReserveRelease.last_processed_at, DateTime) <= next_day
            )
            if get_rr_completed:
                total_rr_completed_amount = sum(
                    rr_completed.disbursement_amount
                    for rr_completed in get_rr_completed
                    if rr_completed.disbursement_amount is not None
                )

        # get total_pending_amount
        get_pending_value = soa.filter(SOA.status == "pending")
        total_pending_value = Decimal(0)
        for pending_value in get_pending_value:
            total_pending_value += (
                pending_value.disbursement_amount
                if pending_value.disbursement_amount is not None
                else Decimal(0)
            )
        total_pending_value = total_pending_value + total_rr_pending_amount

        # get total_approved_amount
        get_approved_value = soa.filter(SOA.status == "approved")
        total_approved_amount = Decimal(0)
        for approved_value in get_approved_value:
            total_approved_amount += (
                approved_value.disbursement_amount
                if approved_value.disbursement_amount is not None
                else Decimal(0)
            )

        total_approved_amount = total_approved_amount + total_rr_approved_amount

        # get total_completed_amount
        get_completed_value = soa.filter(SOA.status == "completed").filter(            
            cast(SOA.last_processed_at, DateTime) >= today,
            cast(SOA.last_processed_at, DateTime) <= next_day,
        )
        total_completed_amount = Decimal(0)
        for completed_value in get_completed_value:
            total_completed_amount += (
                completed_value.disbursement_amount
                if completed_value.disbursement_amount is not None
                else Decimal(0)
            )

        total_completed_amount = total_completed_amount + total_rr_completed_amount

        soa_obj.update(
            {
                "total_pending_amount": float(total_pending_value),
                "total_approved_amount": float(total_approved_amount),
                "total_completed_amount": float(total_completed_amount),
            }
        )

        return custom_response(soa_obj)
    except Exception as e:
        print(str(e))
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_principal_fees():
    principal_fee = principal_settings()

    fees = {
        "high_priority_fee": principal_fee["high_priority_fee"],
        "same_day_ach_fee": principal_fee["same_day_ach_fee"],
        "third_party_fee": principal_fee["third_party_fee"],
        "wire_fee": principal_fee["wire_fee"],
    }

    return custom_response(fees)
