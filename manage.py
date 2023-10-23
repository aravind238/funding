import os
from flask_script import Manager, Server
from flask_migrate import Migrate, MigrateCommand
from src import db
from src.app import create_app
from src.cli import (
    ImportPayees,
    DeletePayees,
    SetClientDisclaimerText,
    DeleteInvoicesOfRejectedSoa,
    PayeesImportAch,
    PayeesImportWire,
    PayeesImportThirdParty,
    PayeesImportBoth,
    PayeesImportNewBankChanges,
    UpdateDebtorLimitApprovalsHistory,
    SyncClientsToLocationsScript,
    MergeDuplicateDebtors,
    DebtorCleanup,
    UpdateUserNotificationClientID,
    InactiveCadenceClients,
    InactiveCadenceDebtors
)


env_name = os.getenv("FLASK_ENV")
app = create_app(env_name)

migrate = Migrate(app=app, db=db)

manager = Manager(app=app)

manager.add_command("runserver", Server(port=(os.getenv("PORT") or 5000)))

manager.add_command("db", MigrateCommand)

manager.add_command('delete_payees', DeletePayees(db=db))
manager.add_command('import_payees', ImportPayees(db=db))
manager.add_command('delete_invoices_of_rejected_soa', DeleteInvoicesOfRejectedSoa(db=db))
manager.add_command('update_dla_history', UpdateDebtorLimitApprovalsHistory(db=db))
manager.add_command('debtor_cleanup', DebtorCleanup(db=db))
manager.add_command('update_user_notification_client_id', UpdateUserNotificationClientID(db=db))
manager.add_command('inactive_cadence_clients', InactiveCadenceClients(db=db))
manager.add_command('inactive_cadence_debtors', InactiveCadenceDebtors(db=db))

@manager.command
def set_client_disclaimer_text(filename):
    set_quebec_client_disclaimer = SetClientDisclaimerText(db=db, filename=filename)
    set_quebec_client_disclaimer.run()


@manager.command
@manager.option("-s", "--sheetname", dest="sheetname")
def import_payees_by_file(filename, sheetname=None):
    # import payees list: for uat and prod
    if not sheetname:
        sheetname="IMPORT ACH"

    # checking, if sheetname == "IMPORT BOTH"
    if sheetname == "IMPORT BOTH":
        import_payees = PayeesImportBoth(db=db, filename=filename, sheetname=sheetname)
    # IMPORT WIRE
    elif sheetname == "IMPORT WIRE":
        import_payees = PayeesImportWire(db=db, filename=filename, sheetname=sheetname)
    # IMPORT 3RD PARTIES -> ACH THIRD PARTIES
    elif sheetname == "ACH THIRD PARTIES":
        import_payees = PayeesImportThirdParty(db=db, filename=filename, sheetname=sheetname)
    # NEW BANK CHANGES
    elif sheetname == "NEW BANK CHANGES":
        import_payees = PayeesImportNewBankChanges(db=db, filename=filename, sheetname=sheetname)
    # IMPORT ACH
    else:
        import_payees = PayeesImportAch(
            db=db, filename=filename, sheetname=sheetname
        )

    import_payees.run()

@manager.command
@manager.option("-b", "--business_ids", dest="business_ids")
def sync_clients_to_locations(business_ids=None):
    # # for prod
    # #
    # # if have BUSINESS_ID='x-123,x-567' in .env file then run command in terminal: 
    # python manage.py sync_clients_to_locations
    # # else:
    # python manage.py sync_clients_to_locations --business_ids "x-123,x-567"

    print("<-- script start -->")
    
    add_clients_to_locations = SyncClientsToLocationsScript(
        db=db, business_ids=business_ids
    )
    add_clients_to_locations.run()
    
@manager.command
@manager.option("-d", "--debtor_id", dest="debtor_id")
def merge_duplicate_debtors(debtor_id=None):
    # # for all environments
    # #
    # # run command in terminal: 
    # python manage.py merge_duplicate_debtors
    # # else:
    # python manage.py merge_duplicate_debtors --debtor_id 234
    if debtor_id:
        print(f"debtor_id: {debtor_id}")
    merge_funding_duplicate_debtors = MergeDuplicateDebtors(
        db=db, debtor_id=debtor_id
    )
    merge_funding_duplicate_debtors.run()

if __name__ == "__main__":
    manager.run()
