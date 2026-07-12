from app.schemas.base import CamelModel


class CurrentUserFeaturesOut(CamelModel):
    show_admin_pages: bool
    show_role_management: bool
    show_recipe_debug: bool


class CurrentUserOut(CamelModel):
    id: str
    email: str
    features: CurrentUserFeaturesOut
