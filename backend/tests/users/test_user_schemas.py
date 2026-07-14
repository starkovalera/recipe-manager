from app.access.constants import UserRole
from app.models import User, UserRoleAssignment
from app.schemas.users import CurrentUserOut


def test_current_user_schema_computes_capabilities_without_exposing_roles_or_model():
    user = User(
        id="debug-user",
        email="debug@example.test",
        role_assignments=[UserRoleAssignment(role=UserRole.DEBUG)],
    )

    payload = CurrentUserOut(user=user).model_dump(mode="json", by_alias=True)

    assert payload == {
        "id": "debug-user",
        "email": "debug@example.test",
        "features": {
            "showAdminPages": True,
            "showRoleManagement": False,
            "showRecipeDebug": True,
        },
    }
