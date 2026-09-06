"""Dependency-free adapter checks, also collected by pytest."""

import json
import unittest
from dataclasses import replace

from econ_agent_sim.economy_0_2 import canonical_population
from econ_agent_sim.economy_0_4 import Economy04Config, run_economy_0_4
from econ_agent_sim.playground import apply_transfer, playground_data


class PlaygroundTests(unittest.TestCase):
    def setUp(self):
        self.population = canonical_population()
        self.action = {
            "kind": "redistribute",
            "id": "test-1",
            "revision": 0,
            "sender": "Agent 1",
            "receiver": "Agent 2",
            "amount": 0.1,
        }

    def test_valid_transfer_uses_existing_engine_without_mutating_population(self):
        updated = apply_transfer(self.population, self.action, 0)
        self.assertAlmostEqual(updated[0].y, 0.1)
        self.assertAlmostEqual(updated[1].y, 1.9)
        self.assertEqual(self.population[0].y, 0.2)
        self.assertAlmostEqual(
            sum(a.y for a in updated), sum(a.y for a in self.population)
        )

    def test_rejects_nonfinite_invalid_and_overdrawn_amounts(self):
        for amount in (float("nan"), float("inf"), -1, 0, 0.001, True, "0.1", None, 1):
            with self.subTest(amount=amount), self.assertRaises((ValueError, TypeError)):
                apply_transfer(self.population, {**self.action, "amount": amount}, 0)

    def test_rejects_stale_or_malformed_actions(self):
        for action in (
            None,
            {},
            {**self.action, "revision": -1},
            {**self.action, "revision": False},
            {**self.action, "id": ""},
            {**self.action, "kind": "reset"},
            {**self.action, "sender": "missing"},
            {**self.action, "receiver": "Agent 1"},
            {**self.action, "sender": []},
        ):
            with self.subTest(action=action), self.assertRaises((ValueError, TypeError)):
                apply_transfer(self.population, action, 0)

    def test_payload_matches_model_trade_and_balance_records(self):
        result = run_economy_0_4()
        payload = playground_data(result, 0, 0)
        json.dumps(payload, allow_nan=False)
        self.assertEqual(payload["opening"], result.periods[0].opening_stocks)
        self.assertEqual(payload["closing"], result.periods[0].closing_stocks)
        self.assertEqual(payload["trades"][0]["payment"], result.trades[0].payment)
        self.assertTrue(all(payload["checks"].values()))

    def test_old_result_and_latest_transfer_population_are_distinct(self):
        updated = apply_transfer(self.population, self.action, 0)
        result = run_economy_0_4(
            Economy04Config(period_populations=(self.population, updated))
        )
        old = playground_data(result, 0, 1, self.action)
        latest = playground_data(result, 1, 1, self.action)
        self.assertEqual(old["agents"][0]["y"], updated[0].y)
        self.assertEqual(old["opening"]["Agent 1"]["Y"], self.population[0].y)
        self.assertIsNone(old["last_transfer"])
        self.assertEqual(latest["last_transfer"], self.action)
        self.assertEqual(latest["previous_price"], result.periods[0].prices["X"])

    def test_opening_money_is_reset_and_does_not_change_real_result(self):
        updated = apply_transfer(self.population, self.action, 0)
        config = Economy04Config(period_populations=(self.population, updated))
        a = run_economy_0_4(config)
        b = run_economy_0_4(replace(config, opening_money_per_agent=100.0))
        for left, right in zip(a.periods, b.periods, strict=True):
            self.assertEqual(left.prices, right.prices)
            self.assertEqual(left.desired_bundles, right.desired_bundles)
            self.assertTrue(
                all(s["Money"] == 100 for s in right.opening_stocks.values())
            )


if __name__ == "__main__":
    unittest.main()
