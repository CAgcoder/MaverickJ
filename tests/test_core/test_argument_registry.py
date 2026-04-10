"""Tests for ArgumentRegistry."""
import pytest

from maverickj.core.argument_registry import ArgumentRegistry
from maverickj.schemas.arguments import (
    Argument,
    ArgumentStatus,
    FactCheck,
    FactCheckVerdict,
    Rebuttal,
)


class TestArgumentRegistry:
    def setup_method(self):
        self.registry = ArgumentRegistry()

    def test_register_argument(self):
        arg = Argument(
            id="ADV-R1-01",
            claim="Go deployment cost is low",
            reasoning="Small memory footprint",
            status=ArgumentStatus.ACTIVE,
        )
        self.registry.register(arg, round_num=1, agent="advocate")
        active = self.registry.get_active_arguments()
        assert len(active) == 1
        assert active[0].argument.id == "ADV-R1-01"
        assert active[0].raised_by == "advocate"

    def test_update_status(self):
        arg = Argument(
            id="ADV-R1-01",
            claim="Go deployment cost is low",
            reasoning="Small memory footprint",
        )
        self.registry.register(arg, 1, "advocate")
        self.registry.update_status("ADV-R1-01", ArgumentStatus.REBUTTED, "Rebutted")

        active = self.registry.get_active_arguments()
        assert len(active) == 0

        record = self.registry.to_dict()["ADV-R1-01"]
        assert record.argument.status == ArgumentStatus.REBUTTED
        assert "Rebutted" in record.modification_history

    def test_add_rebuttal(self):
        arg = Argument(id="ADV-R1-01", claim="test", reasoning="test")
        self.registry.register(arg, 1, "advocate")

        rebuttal = Rebuttal(
            target_argument_id="ADV-R1-01",
            counter_claim="Incorrect",
            reasoning="Because...",
        )
        self.registry.add_rebuttal("ADV-R1-01", rebuttal)

        record = self.registry.to_dict()["ADV-R1-01"]
        assert len(record.rebuttals) == 1

    def test_add_fact_check_flawed(self):
        arg = Argument(id="ADV-R1-01", claim="test", reasoning="test")
        self.registry.register(arg, 1, "advocate")

        check = FactCheck(
            target_argument_id="ADV-R1-01",
            verdict=FactCheckVerdict.FLAWED,
            explanation="Logical fallacy",
        )
        self.registry.add_fact_check("ADV-R1-01", check)

        record = self.registry.to_dict()["ADV-R1-01"]
        assert record.argument.status == ArgumentStatus.REBUTTED
        assert len(record.fact_checks) == 1

    def test_add_fact_check_valid(self):
        arg = Argument(id="ADV-R1-01", claim="test", reasoning="test")
        self.registry.register(arg, 1, "advocate")

        check = FactCheck(
            target_argument_id="ADV-R1-01",
            verdict=FactCheckVerdict.VALID,
            explanation="Logically sound",
        )
        self.registry.add_fact_check("ADV-R1-01", check)

        record = self.registry.to_dict()["ADV-R1-01"]
        assert record.argument.status == ArgumentStatus.ACTIVE

    def test_filter_by_side(self):
        arg1 = Argument(id="ADV-R1-01", claim="Pro argument", reasoning="test")
        arg2 = Argument(id="CRT-R1-01", claim="Con argument", reasoning="test")
        self.registry.register(arg1, 1, "advocate")
        self.registry.register(arg2, 1, "critic")

        adv_args = self.registry.get_active_arguments(side="advocate")
        crt_args = self.registry.get_active_arguments(side="critic")
        assert len(adv_args) == 1
        assert len(crt_args) == 1

    def test_survivor_stats(self):
        arg1 = Argument(id="ADV-R1-01", claim="t1", reasoning="t")
        arg2 = Argument(id="ADV-R1-02", claim="t2", reasoning="t")
        arg3 = Argument(id="CRT-R1-01", claim="t3", reasoning="t")
        self.registry.register(arg1, 1, "advocate")
        self.registry.register(arg2, 1, "advocate")
        self.registry.register(arg3, 1, "critic")

        self.registry.update_status("ADV-R1-02", ArgumentStatus.REBUTTED)

        stats = self.registry.get_survivor_stats()
        assert stats["total_raised"] == 3
        assert stats["survived"] == 2
        assert stats["rebutted"] == 1
        assert stats["conceded"] == 0
