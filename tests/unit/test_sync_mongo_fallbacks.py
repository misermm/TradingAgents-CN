from app.services.data_sources.manager import DataSourceManager
from tradingagents.dataflows.providers.china.tushare import TushareProvider


class _Adapter:
    def __init__(self, name: str, default_priority: int):
        self.name = name
        self._default_priority = default_priority
        self._priority = None

    def _get_default_priority(self):
        return self._default_priority


def test_data_source_manager_uses_default_priorities_when_sync_mongo_unavailable(monkeypatch):
    manager = object.__new__(DataSourceManager)
    manager.adapters = [_Adapter("tushare", 3), _Adapter("akshare", 2), _Adapter("baostock", 1)]

    monkeypatch.setattr("app.core.database.get_mongo_db_sync_if_available", lambda: None)

    DataSourceManager._load_priority_from_database(manager)

    assert [adapter._priority for adapter in manager.adapters] == [3, 2, 1]


def test_tushare_provider_skips_db_lookup_when_sync_mongo_unavailable(monkeypatch):
    provider = TushareProvider()

    monkeypatch.setattr("app.core.database.get_mongo_db_sync_if_available", lambda: None)

    assert provider._get_token_from_database() is None
