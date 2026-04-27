from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from maverickj.schemas.debate import DebateConfig, DebateMetadata, DebateState, DebateStatus
from maverickj.schemas.supply_chain_engine import MarketDataConfig, SupplyChainConfig
from maverickj.supply_chain.nodes.data_warmup import data_warmup_node


@pytest.mark.asyncio
async def test_data_warmup_records_warmup_tool_calls() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    data_dir = repo_root / "maverickj" / "supply_chain" / "data"
    sc = SupplyChainConfig(
        data_path=str(data_dir),
        market_data=MarketDataConfig(offline_mode=False),
    )
    state = DebateState(
        id="t1",
        question="Should we dual-source SKU-A21?",
        config=DebateConfig(),
        metadata=DebateMetadata(started_at=datetime.now()),
        current_round=1,
        status=DebateStatus.RUNNING,
        supply_chain_config=sc,
    )
    out = await data_warmup_node(state, MagicMock())
    tc = out["tool_calls"]
    assert len(tc) >= 5
    assert all(v.get("source") == "warmup" for v in tc.values())
    pack = out["current_round_data_pack"]
    assert pack["sku_focus"] == "SKU-A21"
    assert "baseline_eoq" in pack and "baseline_mc" in pack
    assert "local_supplier" in pack["baseline_tco"]
