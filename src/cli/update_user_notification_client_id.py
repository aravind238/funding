from src import db
from flask_script import Command
from datetime import datetime
from src.models import (
    UserNotifications,
    ReserveRelease,
    SOA,
    ClientPayee,
    Payee,
    GenericRequest,
    DebtorLimitApprovals,
    ComplianceRepository,
)
from sqlalchemy import and_, or_


class UpdateUserNotificationClientID(Command):
    def __init__(self, db=None):
        self.db = db

    def run(self):
        print("started at: ", datetime.utcnow())

        user_notifications = False
        limit_record = 1000  
        while True:  
            user_notifications = UserNotifications.query.filter(
                or_(
                    UserNotifications.client_id == None,
                    UserNotifications.client_id == 0,
                )
            )
            total_user_notifications = user_notifications.count()
            user_notifications = user_notifications.limit(limit_record).all()

            print(f"Total user_notifications: {total_user_notifications} - limit_record: {limit_record}")

            if not user_notifications:
                print("Funding: No user notifications found")
                print("completed at: ", datetime.utcnow())
                return

            for user_notification in user_notifications:
                client_id = None
                request_id = None
                try:
                    url_link = user_notification.url_link
                    request_type = (
                        user_notification.notification_type.value
                        if user_notification.notification_type
                        else None
                    )

                    if url_link and "/" in url_link:
                        # request_name = url_link.split("/")[0]
                        request_id = url_link.split("/")[1]

                    # reserve release
                    if request_type == "reserve_release":
                        reserve_release = (
                            ReserveRelease.query.with_entities(ReserveRelease.client_id)
                            .filter_by(id=request_id)
                            .first()
                        )

                        client_id = reserve_release[0] if reserve_release else None

                    # soa
                    if request_type == "soa":
                        soa = (
                            SOA.query.with_entities(SOA.client_id)
                            .filter_by(id=request_id)
                            .first()
                        )

                        client_id = soa[0] if soa else None

                    # generic request
                    if request_type == "generic_request":
                        generic_request = (
                            GenericRequest.query.with_entities(GenericRequest.client_id)
                            .filter_by(id=request_id)
                            .first()
                        )

                        client_id = generic_request[0] if generic_request else None

                    # debtor limit approvals(credit limit)
                    if request_type == "credit_limit":
                        debtor_limit_approvals = (
                            DebtorLimitApprovals.query.with_entities(
                                DebtorLimitApprovals.client_id
                            )
                            .filter_by(id=request_id)
                            .first()
                        )

                        client_id = (
                            debtor_limit_approvals[0] if debtor_limit_approvals else None
                        )

                    # compliance repository
                    if request_type == "compliance_repository":
                        compliance_repository = (
                            ComplianceRepository.query.with_entities(
                                ComplianceRepository.client_id
                            )
                            .filter_by(id=request_id)
                            .first()
                        )

                        client_id = (
                            compliance_repository[0] if compliance_repository else None
                        )

                    # payee
                    if request_type == "payee":
                        client_payee = ClientPayee.query.filter_by(
                            payee_id=request_id
                        ).first()

                        client_id = client_payee.client_id if client_payee else None
                    
                    # save client id in user notification
                    if client_id:
                        user_notification.client_id = client_id
                        user_notification.save()

                        print(
                            f"Added client_id: {user_notification.client_id} in user notification: {user_notification.id} for url_link: {url_link}"
                        )
                except Exception as e:
                    print(e)
                    self.db.session.rollback()
                    continue

            print("completed at: ", datetime.utcnow())
