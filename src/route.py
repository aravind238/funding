# v2 Apis
from src.resources.v2.routes.clients_route import (
    clients_v2_api,
    client_details_v2_api,
    calculate_client_balances_v2_api,
)
from src.resources.v2.routes.approvals_history_route import approvals_history_v2_api
from src.resources.v2.routes.client_control_accounts_route import (
    client_control_accounts_v2_api,
)
from src.resources.v2.routes.client_debtors_route import client_debtors_v2_api
from src.resources.v2.routes.client_funds_route import (
    client_funds_v2_api,
    calculate_fee_advance_v2_api,
)
from src.resources.v2.routes.client_participants_route import client_participants_v2_api
from src.resources.v2.routes.client_payees_route import client_payees_v2_api
from src.resources.v2.routes.comments_route import comments_v2_api
from src.resources.v2.routes.control_accounts_route import control_accounts_v2_api
from src.resources.v2.routes.debtors_route import (
    debtors_v2_api,
    get_debtor_limits_v2_api,
)
from src.resources.v2.routes.disbursements_route import disbursements_v2_api
from src.resources.v2.routes.disclaimers_route import (
    disclaimers_v2_api,
    get_different_disclaimers_v2_api,
)
from src.resources.v2.routes.invoice_route import (
    invoice_v2_api,
    generate_invoice_csv_v2_api,
    nonfactored_deleted_invoices_v2_api,
    upload_invoices_v2_api,
)
from src.resources.v2.routes.lcra_export_route import lcra_export_v2_api
from src.resources.v2.routes.logs_route import logs_v2_api
from src.resources.v2.routes.organization_client_account_route import (
    organization_client_account_v2_api,
)
from src.resources.v2.routes.participants_route import participants_v2_api
from src.resources.v2.routes.payees_route import (
    payees_v2_api,
    import_payees_v2_api,
)
from src.resources.v2.routes.reasons_route import reasons_v2_api
from src.resources.v2.routes.reserve_release_route import (
    reserve_release_v2_api,
    download_reserve_release_v2_api,
    generate_rr_lcra_csv_v2_api,
    reserve_release_details_v2_api,
)
from src.resources.v2.routes.reserve_release_disbursements_route import (
    reserve_release_disbursements_v2_api,
)
from src.resources.v2.routes.soa_route import (
    soa_v2_api,
    download_soa_v2_api,
    generate_lcra_csv_v2_api,
    get_soa_details_v2_api,
)
from src.resources.v2.routes.supporting_documents_route import (
    supporting_documents_v2_api,
    get_presigned_url_v2_api,
)
from src.resources.v2.routes.user_notifications_route import (
    user_notifications_v2_api,
    get_user_notifications_v2_api,
)
from src.resources.v2.routes.users_route import user_v2_api, users_v2_api
from src.resources.v2.routes.dashboard_route import (
    calculate_time_remaining_v2_api,
    dashboard_v2_api,
    get_soa_total_v2_api,
    total_soa_amount_v2_api,
    principal_fees_v2_api,
)
from src.resources.v2.routes.client_settings_route import client_settings_v2_api
from src.resources.v2.routes.debtor_limit_approvals_route import debtor_limit_approvals_v2_api
from src.resources.v2.routes.generic_request_route import generic_request_v2_api
from src.resources.v2.routes.compliance_repository_route import compliance_repository_v2_api
from src.resources.v2.routes.collection_notes_route import collection_notes_v2_api
from src.resources.v2.routes.verification_notes_route import verification_notes_v2_api
from src.resources.v2.routes.invoice_supporting_documents_route import invoice_supporting_documents_v2_api


def register_v2_blueprints(app):
    """
    Register all v2 blueprints
    """
    url_api_prefix = "/api/v1"

    app.register_blueprint(
        approvals_history_v2_api, url_prefix=f"{url_api_prefix}/approvals-history"
    )
    app.register_blueprint(
        client_control_accounts_v2_api,
        url_prefix=f"{url_api_prefix}/client-control-account",
    )
    app.register_blueprint(
        client_debtors_v2_api, url_prefix=f"{url_api_prefix}/client-debtors"
    )
    app.register_blueprint(
        client_funds_v2_api, url_prefix=f"{url_api_prefix}/client-fund"
    )
    app.register_blueprint(
        client_participants_v2_api, url_prefix=f"{url_api_prefix}/client-participants"
    )
    app.register_blueprint(
        client_payees_v2_api, url_prefix=f"{url_api_prefix}/client-payees"
    )
    app.register_blueprint(clients_v2_api, url_prefix=f"{url_api_prefix}/client")
    app.register_blueprint(comments_v2_api, url_prefix=f"{url_api_prefix}/comment")
    app.register_blueprint(
        control_accounts_v2_api, url_prefix=f"{url_api_prefix}/control-accounts"
    )
    app.register_blueprint(debtors_v2_api, url_prefix=f"{url_api_prefix}/debtor")
    app.register_blueprint(
        disbursements_v2_api, url_prefix=f"{url_api_prefix}/disbursements"
    )
    app.register_blueprint(
        disclaimers_v2_api, url_prefix=f"{url_api_prefix}/disclaimer"
    )
    app.register_blueprint(invoice_v2_api, url_prefix=f"{url_api_prefix}/invoice")
    app.register_blueprint(
        lcra_export_v2_api, url_prefix=f"{url_api_prefix}/lcra-export"
    )
    app.register_blueprint(logs_v2_api, url_prefix=f"{url_api_prefix}/logs")
    app.register_blueprint(
        organization_client_account_v2_api,
        url_prefix=f"{url_api_prefix}/organization-client-account",
    )
    app.register_blueprint(
        participants_v2_api, url_prefix=f"{url_api_prefix}/participants"
    )
    app.register_blueprint(payees_v2_api, url_prefix=f"{url_api_prefix}/payee")
    app.register_blueprint(reasons_v2_api, url_prefix=f"{url_api_prefix}/reasons")
    app.register_blueprint(
        reserve_release_v2_api, url_prefix=f"{url_api_prefix}/reserve-release"
    )
    app.register_blueprint(
        reserve_release_disbursements_v2_api,
        url_prefix=f"{url_api_prefix}/reserve-release-disbursements",
    )
    app.register_blueprint(soa_v2_api, url_prefix=f"{url_api_prefix}/soa")
    app.register_blueprint(
        supporting_documents_v2_api, url_prefix=f"{url_api_prefix}/supporting-document"
    )
    app.register_blueprint(
        user_notifications_v2_api, url_prefix=f"{url_api_prefix}/user-notifications"
    )
    app.register_blueprint(user_v2_api, url_prefix=f"{url_api_prefix}/user")
    app.register_blueprint(users_v2_api, url_prefix=f"{url_api_prefix}/users")
    app.register_blueprint(
        client_details_v2_api, url_prefix=f"{url_api_prefix}/get-client-details"
    )
    app.register_blueprint(
        calculate_client_balances_v2_api,
        url_prefix=f"{url_api_prefix}/calculate-client-balances",
    )
    app.register_blueprint(
        download_soa_v2_api, url_prefix=f"{url_api_prefix}/download-soa"
    )
    app.register_blueprint(
        generate_lcra_csv_v2_api, url_prefix=f"{url_api_prefix}/generate-lcra-csv"
    )
    app.register_blueprint(
        calculate_time_remaining_v2_api,
        url_prefix=f"{url_api_prefix}/calculate-time-remaining",
    )
    app.register_blueprint(dashboard_v2_api, url_prefix=f"{url_api_prefix}/dashboard")
    app.register_blueprint(
        get_different_disclaimers_v2_api,
        url_prefix=f"{url_api_prefix}/get-different-disclaimers",
    )
    app.register_blueprint(
        get_soa_total_v2_api, url_prefix=f"{url_api_prefix}/get-soa-total"
    )
    app.register_blueprint(
        total_soa_amount_v2_api, url_prefix=f"{url_api_prefix}/total-soa-amount"
    )
    app.register_blueprint(
        get_debtor_limits_v2_api, url_prefix=f"{url_api_prefix}/get-debtor-limits"
    )
    app.register_blueprint(
        generate_invoice_csv_v2_api, url_prefix=f"{url_api_prefix}/generate-invoice-csv"
    )
    app.register_blueprint(
        nonfactored_deleted_invoices_v2_api,
        url_prefix=f"{url_api_prefix}/get-nonfactored-and-deleted-invoices",
    )
    app.register_blueprint(
        upload_invoices_v2_api, url_prefix=f"{url_api_prefix}/upload-invoices"
    )
    app.register_blueprint(
        import_payees_v2_api, url_prefix=f"{url_api_prefix}/import-payees"
    )
    app.register_blueprint(
        get_user_notifications_v2_api,
        url_prefix=f"{url_api_prefix}/get-user-notifications",
    )
    app.register_blueprint(
        download_reserve_release_v2_api,
        url_prefix=f"{url_api_prefix}/download-reserve-release",
    )
    app.register_blueprint(
        generate_rr_lcra_csv_v2_api,
        url_prefix=f"{url_api_prefix}/generate-lcra-csv/reserve-release",
    )
    app.register_blueprint(
        reserve_release_details_v2_api,
        url_prefix=f"{url_api_prefix}/get-reserve-release-details",
    )
    app.register_blueprint(
        calculate_fee_advance_v2_api,
        url_prefix=f"{url_api_prefix}/calculate-fee-advance",
    )
    app.register_blueprint(
        get_presigned_url_v2_api, url_prefix=f"{url_api_prefix}/get-presigned-url"
    )
    app.register_blueprint(
        get_soa_details_v2_api, url_prefix=f"{url_api_prefix}/get-soa-details"
    )
    app.register_blueprint(
        client_settings_v2_api, url_prefix=f"{url_api_prefix}/client-settings"
    )
    app.register_blueprint(
        principal_fees_v2_api, url_prefix=f"{url_api_prefix}/principal-fees"
    )
    app.register_blueprint(
        debtor_limit_approvals_v2_api, url_prefix=f"{url_api_prefix}/debtor-limit-approvals"
    )
    app.register_blueprint(
        generic_request_v2_api, url_prefix=f"{url_api_prefix}/generic-request"
    )
    app.register_blueprint(
        compliance_repository_v2_api, url_prefix=f"{url_api_prefix}/compliance-repository"
    )
    app.register_blueprint(
        collection_notes_v2_api, url_prefix=f"{url_api_prefix}/collection-notes"
    )
    app.register_blueprint(
        verification_notes_v2_api, url_prefix=f"{url_api_prefix}/verification-notes"
    )
    app.register_blueprint(
        invoice_supporting_documents_v2_api, url_prefix=f"{url_api_prefix}/invoice-supporting-documents"
    )
