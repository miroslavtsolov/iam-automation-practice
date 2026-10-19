import pandas as pd
from reconcile import reconcile

def test_reconcile_returns_dataframe(monkeypatch):
    # mock fetch_all_users to avoid hitting the real API in tests
    import reconcile as r
    monkeypatch.setattr(r, "fetch_all_users", lambda: [
        {"username": "test.user", "email": "not.in.hr@example.com", "enabled": True}
    ])
    merged, orphaned, _ = reconcile()
    assert isinstance(merged, pd.DataFrame)
    assert len(orphaned) == 1

def test_terminated_but_enabled_detection(monkeypatch):
    import reconcile as r
    monkeypatch.setattr(r, "fetch_all_users", lambda: [
        {"username": "cdiaz", "email": "carla.diaz@example.com", "enabled": True}
    ])
    merged, orphaned, terminated = reconcile()
    assert len(terminated) == 1
    assert len(orphaned) == 0


def test_accounts_without_email_are_skipped_not_matched(monkeypatch):
    # A blank-email Keycloak account (e.g. a service account) must not match the
    # blank-email rows in the HR feed, and must not be reported as orphaned.
    import reconcile as r
    monkeypatch.setattr(r, "fetch_all_users", lambda: [
        {"username": "service-account-x", "enabled": True},
        {"username": "bob", "email": "bob.smith@example.com", "enabled": True},
        {"username": "ghost", "email": "ghost@example.com", "enabled": True},
    ])
    merged, orphaned, _ = reconcile()
    assert len(merged) == 2                      # no duplicated rows
    assert list(orphaned["username"]) == ["ghost"]
