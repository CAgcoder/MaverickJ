"""Compile-time checks for supply-chain graph wiring (no LLM)."""

from maverickj.llm.router import ModelRouter
from maverickj.schemas.config import DebateEngineConfig
from maverickj.supply_chain.builder import build_supply_chain_graph


def test_supply_chain_graph_compiles():
    router = ModelRouter(DebateEngineConfig())
    app = build_supply_chain_graph(router)
    assert app is not None
