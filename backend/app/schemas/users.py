from pydantic import Field, computed_field
from pydantic.json_schema import SkipJsonSchema

from app.access.constants import ADMIN_PAGE_ROLES, UserRole
from app.access.rules import has_any_role, has_role
from app.models import User
from app.schemas.base import CamelModel


class CurrentUserFeaturesOut(CamelModel):
    user: SkipJsonSchema[User] = Field(exclude=True)

    @computed_field
    @property
    def show_admin_pages(self) -> bool:
        return has_any_role(self.user, ADMIN_PAGE_ROLES)

    @computed_field
    @property
    def show_role_management(self) -> bool:
        return has_role(self.user, UserRole.SUPERADMIN)

    @computed_field
    @property
    def show_recipe_debug(self) -> bool:
        return has_role(self.user, UserRole.DEBUG)


class CurrentUserOut(CamelModel):
    user: SkipJsonSchema[User] = Field(exclude=True)

    @computed_field
    @property
    def id(self) -> str:
        return self.user.id

    @computed_field
    @property
    def email(self) -> str:
        return self.user.email

    @computed_field
    @property
    def features(self) -> CurrentUserFeaturesOut:
        return CurrentUserFeaturesOut(user=self.user)
