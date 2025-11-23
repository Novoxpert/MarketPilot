import pytest
from unittest.mock import patch

from marketpilot.data_farm.adapters.price_adapter import ResilientPriceAdapter
from marketpilot.data_farm.adapters.news_adapter import ResilientNewsAdapter
from marketpilot.data_farm.adapters.fundamental_adapter import (
    ResilientFundamentalAdapter,
)


@pytest.mark.asyncio
async def test_price_adapter_basic():
    config = {
        "vendor": "yfinance",
        "id": "test_price_001",
        "cadence": "1min",
        "schema_type": "price",
    }
    adapter = ResilientPriceAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    assert result["success"]
    assert result["data"]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_price_adapter_numeric_fields():
    config = {
        "vendor": "yfinance",
        "id": "test_numeric_001",
        "cadence": "1min",
        "schema_type": "price",
    }
    adapter = ResilientPriceAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    data = result["data"]
    for f in ["open", "high", "low", "close", "volume"]:
        assert isinstance(data[f], (int, float))


@pytest.mark.asyncio
async def test_price_adapter_timestamp_exists():
    config = {
        "vendor": "yfinance",
        "id": "test_timestamp_001",
        "cadence": "1min",
        "schema_type": "price",
    }
    adapter = ResilientPriceAdapter(config)
    result = await adapter.execute_ingest("GOOGL")
    assert "timestamp" in result["data"]


@pytest.mark.asyncio
async def test_price_adapter_error_handling():
    config = {
        "vendor": "yfinance",
        "id": "test_error_001",
        "cadence": "1min",
        "schema_type": "price",
    }

    adapter = ResilientPriceAdapter(config)
    with patch.object(
        adapter, "_execute_ingest_internal", side_effect=Exception("API Error")
    ):
        result = await adapter.execute_ingest("AAPL")

    assert result["success"] is False
    assert "API Error" in result["error"]


@pytest.mark.asyncio
async def test_price_adapter_multiple_symbols():
    config = {
        "vendor": "yfinance",
        "id": "test_multi_001",
        "cadence": "1min",
        "schema_type": "price",
    }
    adapter = ResilientPriceAdapter(config)

    for symbol in ["AAPL", "GOOGL", "MSFT", "TSLA"]:
        result = await adapter.execute_ingest(symbol)
        assert result["success"]
        assert result["data"]["symbol"] == symbol


class TestPriceAdapter:
    @pytest.fixture
    def price_config(self):
        return {
            "vendor": "yfinance",
            "id": "price_001",
            "cadence": "1min",
            "schema_type": "price",
        }

    @pytest.mark.asyncio
    async def test_price_adapter_all_fields(self, price_config):
        adapter = ResilientPriceAdapter(price_config)
        result = await adapter.execute_ingest("AAPL")

        data = result["data"]
        required = [
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adjusted_close",
        ]

        for f in required:
            assert f in data

    @pytest.mark.asyncio
    async def test_price_numeric_validation(self, price_config):
        adapter = ResilientPriceAdapter(price_config)
        result = await adapter.execute_ingest("GOOGL")
        data = result["data"]

        assert data["open"] > 0
        assert data["high"] >= data["open"]
        assert data["low"] <= data["close"]

    @pytest.mark.asyncio
    async def test_price_adapter_log_methods(self, price_config):
        adapter = ResilientPriceAdapter(price_config)
        adapter.log_success("AAPL", 1)
        adapter.log_error("GOOGL", "error message")


# دnews adapter test


@pytest.mark.asyncio
async def test_news_adapter_basic():
    config = {
        "vendor": "alphavantage",
        "id": "test_news_001",
        "cadence": "daily",
        "schema_type": "news",
    }
    adapter = ResilientNewsAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    assert result["success"]
    assert isinstance(result["data"]["data"], list)


class TestNewsAdapter:
    @pytest.fixture
    def news_config(self):
        return {
            "vendor": "alphavantage",
            "id": "news_001",
            "cadence": "daily",
            "schema_type": "news",
        }

    @pytest.mark.asyncio
    async def test_news_init(self, news_config):
        adapter = ResilientNewsAdapter(news_config)
        assert adapter.vendor == "alphavantage"

    @pytest.mark.asyncio
    async def test_news_success_path(self, news_config):
        adapter = ResilientNewsAdapter(news_config)
        result = await adapter.execute_ingest("AAPL")
        assert result["success"]
        assert "ingested_at" in result

    @pytest.mark.asyncio
    async def test_news_structure(self, news_config):
        adapter = ResilientNewsAdapter(news_config)
        result = await adapter.execute_ingest("GOOGL")
        data = result["data"]

        for f in ["symbol", "timestamp", "startdate", "enddate", "data"]:
            assert f in data

    @pytest.mark.asyncio
    async def test_multiple_news_items(self, news_config):
        adapter = ResilientNewsAdapter(news_config)
        result = await adapter.execute_ingest("TSLA")
        assert len(result["data"]["data"]) >= 2

    @pytest.mark.asyncio
    async def test_news_error_handling(self, news_config):
        adapter = ResilientNewsAdapter(news_config)

        with patch.object(
            adapter, "validate_schema", side_effect=Exception("Schema error")
        ):
            result = await adapter.execute_ingest("AAPL")
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_log_methods(self, news_config):
        adapter = ResilientNewsAdapter(news_config)
        adapter.log_success("AAPL", 5)
        adapter.log_error("GOOGL", "error")


@pytest.mark.asyncio
async def test_news_adapter_has_timestamp():
    config = {
        "vendor": "alphavantage",
        "id": "test_news_timestamp_001",
        "cadence": "daily",
        "schema_type": "news",
    }
    adapter = ResilientNewsAdapter(config)
    result = await adapter.execute_ingest("AAPL")
    assert "timestamp" in result["data"]


@pytest.mark.asyncio
async def test_news_adapter_data_list_not_empty():
    config = {
        "vendor": "alphavantage",
        "id": "test_news_list_001",
        "cadence": "daily",
        "schema_type": "news",
    }
    adapter = ResilientNewsAdapter(config)
    result = await adapter.execute_ingest("TSLA")
    assert len(result["data"]["data"]) > 0


@pytest.mark.asyncio
async def test_news_item_structure():
    config = {
        "vendor": "alphavantage",
        "id": "test_news_structure_001",
        "cadence": "daily",
        "schema_type": "news",
    }
    adapter = ResilientNewsAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    item = result["data"]["data"][0]
    for f in ["title", "url", "published_at"]:
        assert f in item


# fundamental adapter tests
@pytest.mark.asyncio
async def test_fundamental_adapter_basic():
    config = {
        "vendor": "fmp",
        "id": "test_fundamental_001",
        "cadence": "daily",
        "schema_type": "fundamental",
    }
    adapter = ResilientFundamentalAdapter(config)
    result = await adapter.execute_ingest("AAPL")

    assert result["success"]
    assert "data" in result["data"]


class TestFundamentalAdapter:
    @pytest.fixture
    def fund_config(self):
        return {
            "vendor": "fmp",
            "id": "fund_001",
            "cadence": "daily",
            "schema_type": "fundamental",
        }

    @pytest.mark.asyncio
    async def test_sections(self, fund_config):
        adapter = ResilientFundamentalAdapter(fund_config)
        data = (await adapter.execute_ingest("AAPL"))["data"]["data"]

        for section in ["income_statement", "balance_sheet", "cash_flow", "ratios"]:
            assert section in data

    @pytest.mark.asyncio
    async def test_income_statement(self, fund_config):
        adapter = ResilientFundamentalAdapter(fund_config)
        income = (await adapter.execute_ingest("AAPL"))["data"]["data"][
            "income_statement"
        ]
        for f in ["revenue", "net_income", "eps"]:
            assert f in income

    @pytest.mark.asyncio
    async def test_balance_sheet(self, fund_config):
        adapter = ResilientFundamentalAdapter(fund_config)
        balance = (await adapter.execute_ingest("AAPL"))["data"]["data"][
            "balance_sheet"
        ]
        for f in ["total_assets", "total_liabilities", "stockholders_equity"]:
            assert f in balance

    @pytest.mark.asyncio
    async def test_log_methods(self, fund_config):
        adapter = ResilientFundamentalAdapter(fund_config)
        adapter.log_success("AAPL", 1)
        adapter.log_error("GOOGL", "error")


@pytest.mark.asyncio
async def test_fundamental_timestamp():
    config = {
        "vendor": "fmp",
        "id": "test_fund_timestamp_001",
        "cadence": "daily",
        "schema_type": "fundamental",
    }
    adapter = ResilientFundamentalAdapter(config)
    result = await adapter.execute_ingest("AAPL")
    assert "timestamp" in result["data"]


@pytest.mark.asyncio
async def test_fundamental_numeric_values():
    config = {
        "vendor": "fmp",
        "id": "test_fund_numeric_001",
        "cadence": "daily",
        "schema_type": "fundamental",
    }
    adapter = ResilientFundamentalAdapter(config)
    income = (await adapter.execute_ingest("AAPL"))["data"]["data"]["income_statement"]

    assert isinstance(income["revenue"], (int, float))
    assert isinstance(income["net_income"], (int, float))


# ═══════════════════════════════════════════════════════════════
# CROSS-ADAPTER TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_all_adapters_run_independently():
    configs = [
        {
            "vendor": "yfinance",
            "id": "price_001",
            "cadence": "1min",
            "schema_type": "price",
        },
        {
            "vendor": "alphavantage",
            "id": "news_001",
            "cadence": "daily",
            "schema_type": "news",
        },
        {
            "vendor": "fmp",
            "id": "fund_001",
            "cadence": "daily",
            "schema_type": "fundamental",
        },
    ]

    a = ResilientPriceAdapter(configs[0])
    b = ResilientNewsAdapter(configs[1])
    c = ResilientFundamentalAdapter(configs[2])

    assert (await a.execute_ingest("TSLA"))["success"]
    assert (await b.execute_ingest("TSLA"))["success"]
    assert (await c.execute_ingest("TSLA"))["success"]


@pytest.mark.asyncio
async def test_all_adapters_vendor_field():
    configs = [
        {
            "vendor": "yfinance",
            "id": "v_price",
            "cadence": "1min",
            "schema_type": "price",
        },
        {
            "vendor": "alphavantage",
            "id": "v_news",
            "cadence": "daily",
            "schema_type": "news",
        },
        {
            "vendor": "fmp",
            "id": "v_fund",
            "cadence": "daily",
            "schema_type": "fundamental",
        },
    ]

    assert (await ResilientPriceAdapter(configs[0]).execute_ingest("AAPL"))[
        "vendor"
    ] == "yfinance"
    assert (await ResilientNewsAdapter(configs[1]).execute_ingest("AAPL"))[
        "vendor"
    ] == "alphavantage"
    assert (await ResilientFundamentalAdapter(configs[2]).execute_ingest("AAPL"))[
        "vendor"
    ] == "fmp"


@pytest.mark.asyncio
async def test_all_adapters_ingested_at_field():
    configs = [
        {
            "vendor": "yfinance",
            "id": "ing_p",
            "cadence": "1min",
            "schema_type": "price",
        },
        {
            "vendor": "alphavantage",
            "id": "ing_n",
            "cadence": "daily",
            "schema_type": "news",
        },
        {
            "vendor": "fmp",
            "id": "ing_f",
            "cadence": "daily",
            "schema_type": "fundamental",
        },
    ]

    for cfg, Adapter in [
        (configs[0], ResilientPriceAdapter),
        (configs[1], ResilientNewsAdapter),
        (configs[2], ResilientFundamentalAdapter),
    ]:
        result = await Adapter(cfg).execute_ingest("AAPL")
        assert "ingested_at" in result


# logging & validation test
@pytest.mark.asyncio
async def test_adapter_logs_to_correct_directory():
    from marketpilot.utils.mode_manager import get_mode_manager

    config = {
        "vendor": "yfinance",
        "id": "test_log_001",
        "cadence": "1min",
        "schema_type": "price",
    }

    adapter = ResilientPriceAdapter(config)
    _ = await adapter.execute_ingest("AAPL")

    manager = get_mode_manager()
    log_dir = manager.get_log_dir() / "adapters"
    log_files = list(log_dir.glob("*.jsonl"))

    assert len(log_files) > 0


@pytest.mark.asyncio
async def test_schema_validation_happens():
    from marketpilot.utils.mode_manager import get_mode_manager

    config = {
        "vendor": "yfinance",
        "id": "test_validation_001",
        "cadence": "1min",
        "schema_type": "price",
    }

    adapter = ResilientPriceAdapter(config)
    _ = await adapter.execute_ingest("AAPL")

    manager = get_mode_manager()
    log_dir = manager.get_log_dir() / "adapters"

    found = False
    for file in log_dir.glob("*.jsonl"):
        with open(file) as f:
            for line in f:
                if "Schema validation passed" in line:
                    found = True
                    break
        if found:
            break

    assert found, "Schema validation not logged"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
