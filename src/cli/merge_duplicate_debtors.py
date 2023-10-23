from src import db
from flask_script import Command
from datetime import datetime
from sqlalchemy import not_, or_, and_, func
from sqlalchemy.orm import aliased
from src.models import (
    Debtor,
    ClientDebtor,
    Invoice,
    ApprovalsHistory,
    DebtorLimitApprovals,
    DebtorLimitApprovalsHistory,
    InvoiceSupportingDocuments,
    VerificationNotes,
    VerificationNotesApprovalHistory,
    CollectionNotes,
    CollectionNotesApprovalHistory,
)
from copy import deepcopy

## Merge Duplicate Debtors ##
# - invoice
# - client_debtor
# - approval_history
# - debtor_limit_approvals & debtor_limit_approvals_history
# - invoice_supporting_documents
# - verification_notes & verification_notes_approvals_history
# - collection_notes & collection_notes_approvals_history
# - debtor
class MergeDuplicateDebtors(Command):
    def __init__(self, db=None, debtor_id=None, debtor_ref_key=None, merge_debtors=[]):
        self.db = db
        # debtor not to merge
        self.keep_debtor_id = debtor_id
        # keep debtor ref_key
        self.keep_debtor_ref_key = str(debtor_ref_key)
        # debtors to be merged
        self.merge_debtors = merge_debtors

    def run(self):
        # if getting debtors' id in merge_debtors then manual_merge will run
        if self.keep_debtor_ref_key and self.merge_debtors:
            print("--manual merge-->")
            self.manual_merge()
        else:
            print("--auto merge-->")
            self.auto_merge()

    def manual_merge(self):
        print("Duplicate debtors merge started at: ", datetime.utcnow())

        try:
            self.merge_duplicate_funding_debtors()
        except Exception as e:
            print(e)
            self.db.session.rollback()

        print("Duplicate debtors merge completed at: ", datetime.utcnow())

    def auto_merge(self):
        print("Duplicate debtors merge started at: ", datetime.utcnow())

        duplicate_debtors_ref_key = self.get_duplicate_debtors_ref_key()
        if not duplicate_debtors_ref_key:
            print("Funding: No duplicate Debtors found", datetime.utcnow())
            return

        print(
            len(duplicate_debtors_ref_key),
            "--duplicate funding debtors--",
            duplicate_debtors_ref_key,
        )

        debtor_ref_keys = []
        for debtor in duplicate_debtors_ref_key:
            try:
                print(
                    f"keep_debtor_id: {debtor.id} - debtor.ref_key: {debtor.ref_key}"
                )
                                
                # checking, not merging already merged debtors
                if debtor.ref_key in debtor_ref_keys:
                    print(f"debtors having ref_key {debtor.ref_key} already merged")
                    continue

                debtor_ref_keys.append(debtor.ref_key)
                # print('--debtor_ref_keys--', debtor_ref_keys)

                self.keep_debtor_id = debtor.id
                self.keep_debtor_ref_key = debtor.ref_key
                self.merge_duplicate_funding_debtors()
                # need to empty merge_debtors after every merge
                self.merge_debtors = []
            except Exception as e:
                print(e)
                self.db.session.rollback()
                continue

        print("Duplicate debtors merge completed at: ", datetime.utcnow())

    def get_duplicate_debtors_ref_key(self):
        # debtor aliase
        debtor_aliase = aliased(Debtor)

        # get ref_key by subquery
        duplicate_debtors_ref_key_subquery = (
            self.db.session.query(debtor_aliase.ref_key)
            .filter(
                debtor_aliase.ref_key != str(0),
            )
            .group_by(debtor_aliase.ref_key)
            .having(func.count(debtor_aliase.ref_key) > 1)
            .subquery()
        )

        duplicate_debtors = (
            Debtor.query
            .filter(
                Debtor.is_deleted == False,
                Debtor.deleted_at == None,
                # Debtor.ref_key != 0,
                Debtor.ref_key.in_(duplicate_debtors_ref_key_subquery),
            )
            .order_by(Debtor.updated_at.desc())
            .all()
        )
        return duplicate_debtors

    def get_duplicate_funding_merge_debtors(self):
        # get debtors to be merged based off keep_debtor_id and keep_debtor_ref_key
        merge_debtors = (
            Debtor.query
            .filter(
                Debtor.ref_key == self.keep_debtor_ref_key,
                Debtor.id != self.keep_debtor_id,
            )
            .with_entities(Debtor.id)
            .all()
        )
        return merge_debtors

    def get_invoices_by_merge_debtors(self, merge_debtors):
        return Invoice.query.filter(
                Invoice.debtor.in_(merge_debtors)
            ).all()

    def merge_duplicate_funding_debtors(self):
        # get debtors to be merged based off keep_debtor_id and keep_debtor_ref_key
        if not self.merge_debtors:
            self.merge_debtors = self.get_duplicate_funding_merge_debtors()

        print(f"keep_debtor_id: {self.keep_debtor_id} --debtors to be merged-- {self.merge_debtors}")

        if self.merge_debtors:
            soa_ids_list = []
            # invoice
            invoices = self.get_invoices_by_merge_debtors(self.merge_debtors)
            if invoices:
                for invoice in invoices:
                    # get all soa_id
                    soa_ids_list.append(invoice.soa_id)

                    # update debtor_id to keep_debtor_id
                    invoice.debtor = self.keep_debtor_id
                    invoice.save()

            print(f"invoice: {invoices} -- soa_ids: {soa_ids_list}")
            
            # client debtor: to be run before update_approval_history for checking client_id association with keep_debtor_id
            self.update_client_debtors(self.keep_debtor_id, self.merge_debtors)

            # approval history
            if soa_ids_list:
                self.update_approval_history(soa_ids_list, self.merge_debtors)

            # debtor limit approvals
            self.update_debtor_limit_approvals(self.keep_debtor_id, self.merge_debtors)

            # invoice supporting documents
            self.update_invoice_supporting_documents(self.keep_debtor_id, self.merge_debtors)

            # verification notes
            self.update_verification_notes(self.keep_debtor_id, self.merge_debtors)

            # collection notes
            self.update_collection_notes(self.keep_debtor_id, self.merge_debtors)
                        
            # soft delete merge_debtors
            Debtor.query.filter(
                Debtor.id.in_(self.merge_debtors)
            ).update(
                {
                    Debtor.is_deleted: True,
                    Debtor.deleted_at: datetime.utcnow(),
                },
                synchronize_session=False,
            )
            
            self.db.session.commit()
            print(
                f"keep_debtor_id: {self.keep_debtor_id} --Duplicate debtors {self.merge_debtors} merged"
            )

    def update_client_debtors(self, keep_debtor_id, merge_debtors):
        # client debtor
        client_debtors = ClientDebtor.query.filter(
            ClientDebtor.is_deleted == False,
            ClientDebtor.debtor_id.in_(merge_debtors),
        ).all()
        print(f"client_debtors: {client_debtors} -- merge_debtors: {merge_debtors}")
        if client_debtors:
            for client_debtor in client_debtors:
                # merge_debtors: soft delete client_debtors
                client_debtor.is_deleted = True
                client_debtor.deleted_at = datetime.utcnow()
                client_debtor.save()
                
                # checking keep_debtor is associated with client which merge_debtor has, if not then create client debtor association
                has_keep_client_debtor = ClientDebtor.query.filter(
                    ClientDebtor.is_deleted == False,
                    ClientDebtor.debtor_id == keep_debtor_id,
                    ClientDebtor.client_id == client_debtor.client_id,
                ).first()
                if not has_keep_client_debtor:
                    req_data = {
                        "debtor_id": keep_debtor_id,
                        "client_id": client_debtor.client_id,
                        "client_ref_no": client_debtor.client_ref_no,
                        "credit_limit": client_debtor.credit_limit,
                        "current_ar": client_debtor.current_ar,
                        "days_1_30": client_debtor.days_1_30,
                        "days_31_60": client_debtor.days_31_60,
                        "days_61_90": client_debtor.days_61_90,
                        "days_61_90": client_debtor.days_61_90,
                        "days_61_90": client_debtor.days_61_90,
                        "default_term_value": client_debtor.default_term_value,
                    }
                    # save client debtor
                    keep_client_debtor = ClientDebtor(req_data)
                    keep_client_debtor.save()
                    print(
                        f"keep_debtor_id: {keep_debtor_id} client_id: {keep_client_debtor.client_id} -->created client_debtor: {keep_client_debtor}"
                    )

    def update_approval_history(self, soa_ids_list, merge_debtors):
        # approval history
        approvals_history = ApprovalsHistory.query.filter(
            ApprovalsHistory.soa_id.in_(soa_ids_list),
            ApprovalsHistory.attribute["debtors"] != [],
        ).all()

        if not approvals_history:
            print(f"Funding: No approval history found for soa {soa_ids_list}")
            return False

        print(len(approvals_history), '--approvals_history--', approvals_history)
        for history in approvals_history:
            attribute_data = deepcopy(history.attribute)
            debtors = attribute_data["debtors"]
            client_debtors = attribute_data["client_debtors"]
            is_updated = False
            
            # checking, if debtor array is not empty
            if debtors:
                for debtor in debtors:
                    # checking debtor id(debtor) in merged debtors
                    if (debtor["id"],) in merge_debtors:
                        # get debtor
                        get_debtor = Debtor.get_one_debtor(self.keep_debtor_id)

                        # update debtor in attribute
                        debtor["id"] = self.keep_debtor_id
                        debtor["name"] = get_debtor.name
                        debtor["source"] = get_debtor.source.value if get_debtor.source else None
                        debtor["ref_debtor_no"] = get_debtor.ref_debtor_no
                        debtor["address_1"] = get_debtor.address_1
                        debtor["address_2"] = get_debtor.address_2
                        debtor["state"] = get_debtor.state
                        debtor["city"] = get_debtor.city
                        debtor["postal_code"] = get_debtor.postal_code
                        debtor["country"] = get_debtor.country
                        debtor["phone"] = get_debtor.phone
                        debtor["email"] = get_debtor.email
                        is_updated = True
                    
            # checking, if client debtors array is not empty
            if client_debtors:
                for client_debtor in client_debtors:
                    # checking debtor id(client debtor) in merged debtors
                    if (client_debtor["debtor_id"],) in merge_debtors:
                        get_client_debtor = ClientDebtor.get_client_debtor_by_debtor_id(
                            self.keep_debtor_id, client_debtor["client_id"]
                        )
                        
                        # update client_debtor in attribute
                        client_debtor["debtor_id"] = self.keep_debtor_id
                        client_debtor["id"] = get_client_debtor.id
                        client_debtor["client_ref_no"] = get_client_debtor.client_ref_no
                        client_debtor["default_term_value"] = get_client_debtor.default_term_value
                        is_updated = True

            # update attribute(json data)
            if is_updated:
                history.attribute = attribute_data
                self.db.session.commit()
                print(f"approval history - {history.id}: debtor updated to {self.keep_debtor_id}")

    def update_debtor_limit_approvals(self, keep_debtor_id, merge_debtors):
        debtor_limit_approvals = DebtorLimitApprovals.query.filter(
            DebtorLimitApprovals.debtor_id.in_(merge_debtors), 
            # DebtorLimitApprovals.deleted_at == None
        ).all()

        if not debtor_limit_approvals:
            print(f"Funding: No debtor limit approvals found for debtors {merge_debtors}")
            return False

        for debtor_limit_approval in debtor_limit_approvals:
            debtor_limit_approval_id = debtor_limit_approval.id

            # updated debtor limit approval
            debtor_limit_approval.debtor_id = keep_debtor_id
            debtor_limit_approval.save()
            print(f"debtor limit approvals - {debtor_limit_approval_id}: debtor updated to {self.keep_debtor_id}")

            # get all debtor limit approvals history based off debtor_limit_approvals_id
            debtor_limit_approvals_history = DebtorLimitApprovalsHistory.query.filter(
                DebtorLimitApprovalsHistory.debtor_limit_approvals_id == debtor_limit_approval_id,
                # DebtorLimitApprovalsHistory.deleted_at == None
            ).all()
            
            if debtor_limit_approvals_history:
                for approvals_history in debtor_limit_approvals_history:
                    attribute_data = deepcopy(approvals_history.attribute)

                    # updated debtor limit approvals history
                    attribute_data["debtor_id"] = keep_debtor_id
                    approvals_history.attribute = attribute_data
                    self.db.session.commit()
                    print(f"debtor limit approvals history - {approvals_history.id} updated")


    def update_invoice_supporting_documents(self, keep_debtor_id, merge_debtors):
        invoice_supporting_documents = InvoiceSupportingDocuments.query.filter(
            InvoiceSupportingDocuments.debtor_id.in_(merge_debtors), 
            # InvoiceSupportingDocuments.deleted_at == None
        ).all()

        if not invoice_supporting_documents:
            print(f"Funding: No invoice supporting documents found for debtors {merge_debtors}")
            return False

        for invoice_supporting_document in invoice_supporting_documents:
            invoice_supporting_document_id = invoice_supporting_document.id

            # updated invoice supporting document
            invoice_supporting_document.debtor_id = keep_debtor_id
            invoice_supporting_document.save()
            print(f"invoice supporting document - {invoice_supporting_document_id}: debtor updated to {self.keep_debtor_id}")


    def update_verification_notes(self, keep_debtor_id, merge_debtors):
        verification_notes = VerificationNotes.query.filter(
            VerificationNotes.debtor_id.in_(merge_debtors), 
            # VerificationNotes.deleted_at == None
        ).all()

        if not verification_notes:
            print(f"Funding: No verification notes found for debtors {merge_debtors}")
            return False

        for verification_note in verification_notes:
            verification_note_id = verification_note.id

            # updated verification note
            verification_note.debtor_id = keep_debtor_id
            verification_note.save()
            print(f"verification notes - {verification_note_id}: debtor updated to {self.keep_debtor_id}")

            # get all verification notes approvals history based off verification_notes_id
            verification_notes_approvals_history = VerificationNotesApprovalHistory.query.filter(
                VerificationNotesApprovalHistory.verification_notes_id == verification_note_id,
                # VerificationNotesApprovalHistory.deleted_at == None
            ).all()
            
            if verification_notes_approvals_history:
                for vn_approvals_history in verification_notes_approvals_history:
                    attribute_data = deepcopy(vn_approvals_history.attribute)

                    # updated verification notes approvals history
                    attribute_data["debtor_id"] = keep_debtor_id
                    vn_approvals_history.attribute = attribute_data
                    self.db.session.commit()
                    print(f"verification notes approvals history - {vn_approvals_history.id} updated")


    def update_collection_notes(self, keep_debtor_id, merge_debtors):
        collection_notes = CollectionNotes.query.filter(
            CollectionNotes.debtor_id.in_(merge_debtors), 
            # CollectionNotes.deleted_at == None
        ).all()

        if not collection_notes:
            print(f"Funding: No collection notes found for debtors {merge_debtors}")
            return False

        for collection_note in collection_notes:
            collection_note_id = collection_note.id

            # updated collection note
            collection_note.debtor_id = keep_debtor_id
            collection_note.save()
            print(f"collection notes - {collection_note_id}: debtor updated to {self.keep_debtor_id}")

            # get all collection notes approvals history based off collection_notes_id
            collection_notes_approvals_history = CollectionNotesApprovalHistory.query.filter(
                CollectionNotesApprovalHistory.collection_notes_id == collection_note_id,
                # CollectionNotesApprovalHistory.deleted_at == None
            ).all()
            
            if collection_notes_approvals_history:
                for cn_approvals_history in collection_notes_approvals_history:
                    attribute_data = deepcopy(cn_approvals_history.attribute)

                    # updated collection notes approvals history
                    attribute_data["debtor_id"] = keep_debtor_id
                    cn_approvals_history.attribute = attribute_data
                    self.db.session.commit()
                    print(f"collection notes approvals history - {cn_approvals_history.id} updated")
                    