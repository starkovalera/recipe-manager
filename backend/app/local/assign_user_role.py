import argparse

from app.access.constants import UserRole
from app.auth.constants import AuthProviderType
from app.db.session import db_session
from app.local.users import assign_role_to_auth_user


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign a fixed local role to an existing auth-linked user.")
    parser.add_argument("--auth-provider", choices=[provider.value for provider in AuthProviderType], required=True)
    parser.add_argument("--auth-user-id", required=True)
    parser.add_argument("--role", required=True, choices=[role.value for role in UserRole])
    arguments = parser.parse_args()
    with db_session() as session:
        user = assign_role_to_auth_user(
            session,
            AuthProviderType(arguments.auth_provider),
            arguments.auth_user_id,
            UserRole(arguments.role),
        )
    print(f"Assigned role {arguments.role} to internal user {user.id}.")


if __name__ == "__main__":
    main()
