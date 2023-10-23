from src import db
from flask_script import Command
from datetime import datetime
from sqlalchemy import not_, or_, and_, func
from sqlalchemy.orm import aliased
from src.models import Debtor, ClientDebtor, Invoice, DebtorLimitApprovals

class DebtorCleanup(Command):
    def __init__(self, db=None):
        self.db = db

    def run(self):
        print('Cleaning Up Debtors...')
        debtors = self.get_all_duplicate_debtors()
        for debtor in debtors:
            # We're removing debtors from the system if there's no invoice or approval limits exists
            if self.invoices_exists(debtor.id) == 0 and self.approval_limits_exists(debtor.id) == 0:
                print('Delete',debtor.id, self.remove_debtor(debtor.id))

        client_debtors = self.get_all_duplicate_client_debtors()

        for client_debtor in client_debtors:
            print('Removing client_debtor',self.remove_client_debtor_records(client_debtor.client_id, client_debtor.debtor_id, (client_debtor.d_count - 1)))
    
    def get_all_duplicate_client_debtors(self):
        results = ClientDebtor.query.with_entities(ClientDebtor.client_id, ClientDebtor.debtor_id, func.count(ClientDebtor.debtor_id).label('d_count')) \
            .group_by(ClientDebtor.client_id, ClientDebtor.debtor_id) \
            .having(func.count(ClientDebtor.debtor_id) > 1) \
            .all()
        
        return results

    def remove_client_debtor_records(self, client_id, debtor_id, limit_count):
        results = ClientDebtor.query.with_entities(ClientDebtor.id).filter(ClientDebtor.client_id == client_id, ClientDebtor.debtor_id == debtor_id).limit(limit_count).all()

        if results is None:
            print('No Duplicate Client_Debtors')
            return None

        ids = [id for id, in results]
        # print(ids)
        deleted = self.db.session.query(ClientDebtor).filter(ClientDebtor.id.in_(ids)).delete(synchronize_session=False)
        self.db.session.commit()
        return deleted        

    def get_all_duplicate_debtors(self):
        results = Debtor.query.with_entities(Debtor.ref_key) \
            .filter(Debtor.ref_key != 0) \
            .group_by(Debtor.ref_key) \
            .having(func.count(Debtor.ref_key) > 1) \
            .all()
        
        if results is None:
            print('No Duplicate Debtors')
            return None

        debtor_ref_keys = [ref_key for ref_key, in results]

        debtors = Debtor.query.filter(Debtor.ref_key.in_(debtor_ref_keys)).all()
        return debtors
        

    def invoices_exists(self, debtor_id):
        return Invoice.query.filter(Invoice.debtor == debtor_id).count()
    
    def approval_limits_exists(self, debtor_id):
        return DebtorLimitApprovals.query.filter(DebtorLimitApprovals.debtor_id == debtor_id).count()

    def remove_debtor(self, debtor_id):
        deleted = self.db.session.query(Debtor).filter(Debtor.id == debtor_id).delete(synchronize_session=False)
        self.db.session.commit()
        return deleted

    # def get_all 


# TODO:
# 1. Delete all the duplicate debtors which doesn't have any data with them. -- data_cleanup_script.py
#    * Get all duplicate debtor.
#    * check it any invoice or debtor approval limit exists
#    * if not, remove from system

# 2. How to merge duplicate debtors with the associated records.
#    * Get all duplicate debtor.
#    [each record: ref_key will be same]
#    * API to update debtor records based off of ref_key. [third party - can create separate script]
#    * Select keep debtor last record & select all other debtors as merge debtor.
#    * Update invoice & approval history.
#       * GET all the invoices associated to merge debtors.
#       * Save this SOA_ID and Update debtor_id to keep_debtor_id.
#       * Update approval history based off of SOA_ID, merge_debtor_id and keep_debtor_id - UPDATE ALL DEBTOR INFO
#    * Update debtor_approvals & debtor approval history.
#    * Remove debtor from system.

# 3. Resync all debtors from third party.



# 2. Will client-debtor, history, credit limit table will be autofixed?
# 3. Fix client-control accounts. : Seems like already fixed.
# 4. Fix clients.
