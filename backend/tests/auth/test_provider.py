from app.auth import provider as provider_module
from app.auth.constants import AuthProviderType


class StubAuthProvider:
    provider = AuthProviderType.CLERK


def test_get_auth_provider_reuses_created_provider(monkeypatch):
    created_provider = StubAuthProvider()
    factory_calls: list[object] = []
    settings = object()

    monkeypatch.setattr(provider_module, "_auth_provider", None)
    monkeypatch.setattr(provider_module, "get_settings", lambda: settings)

    def create_provider(received_settings):
        factory_calls.append(received_settings)
        return created_provider

    monkeypatch.setattr(provider_module, "create_auth_provider", create_provider)

    first = provider_module.get_auth_provider()
    second = provider_module.get_auth_provider()

    assert first is created_provider
    assert second is created_provider
    assert factory_calls == [settings]
