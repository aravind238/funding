from src.middleware.permissions import Permissions
from src import db


class Organization:
    @staticmethod
    def get_locations():
        # user role and permissions
        get_user_role_permissions = Permissions.get_user_role_permissions()

        user_role = (
            get_user_role_permissions["user_role"]
            if "user_role" in get_user_role_permissions
            else None
        )

        client_list = []
        if get_user_role_permissions["status_code"] == 200:
            # Get organization ids
            organization_access = get_user_role_permissions["organization_access"]
            organization_ids = (
                ",".join(map(lambda k: "'" + k + "'", organization_access))
                if organization_access
                else None
            )

            # Pull clients based of organization_ids
            if organization_ids:
                sql_query = f"SELECT \
                            c.id \
                            FROM organization_client_account oca, \
                            clients c \
                            WHERE c.lcra_client_accounts_id = oca.lcra_client_account_id \
                            AND c.is_deleted = false \
                            AND c.ref_client_no NOT IN ('TODO-cadence', 'Cadence:sync-pending', 'TODO-factorcloud') \
                            AND oca.is_deleted = false \
                            AND oca.organization_id IN ({organization_ids})"

                # Returns a list of data in tuples
                client_data = db.session.execute(db.text(sql_query)).fetchall()

                # client data
                if client_data:
                    [client_list.append(row[0]) for row in client_data]
                    # client_list = list(map(lambda row: row[0], client_data))

        return_obj = {"client_list": client_list, "user_role": user_role}

        return return_obj
