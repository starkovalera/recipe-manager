from enum import StrEnum

# Trusted identity header populated by the authenticated gateway.
TRUSTED_SUBJECT_HEADER = "X-Authenticated-Subject"


class AuthProviderType(StrEnum):
    CLERK = "CLERK"
