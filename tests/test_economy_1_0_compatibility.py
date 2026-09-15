"""A released file and its future stay on the original Economy 1.0 engine.

The fixture and continuation fingerprints were captured before adding flexible
consumption targets. Do not regenerate them when developing a newer economy.
"""

import json
from dataclasses import replace
from pathlib import Path

from econ_agent_sim.competition_experiments import dump_experiment, load_experiment
from econ_agent_sim.economy_1_0 import advance_competition_period

FIXTURE = Path(__file__).parent / "fixtures" / "economy_1_0_released_workspace.json"
CONTINUATION_DIGESTS = (
    "6fa6cc0c4907d8c7ca375cc4644929937cab61ffa2a53f7c7a8030f1e1e707f7",
    "7b751cadcd9ab3efc58939cfc9b2105f05d579f001867f0edc5b96f7ac83a818",
    "57221d944506328e9f307ebb8909f3ea984b14a2a44657fa936a4b929ff8b24f",
    "01df3263fb9b3077f9eec6b9c92c913bed27a2a4b6b181695972a38a3a9d6665",
    "ad82d878c9859bacf0df89eee25e07d94d6729ea52a936db37e49023f250d374",
    "0490c0e70b877ec5abde450aa9cf3df372aa315c02828eb485f0e87ed4469bed",
    "51fde02ca0acbdaf16bb96aaeb4127fe73b66ba63b66456715ea0b91abcfac82",
    "f6562df5544de1eb7289bc8a523b864f9baa3203818e79c355ec600959b40e74",
    "7fd138bd99a9391f10ca0ac21cdd5554188a0acb4825a2fe50fec694a686eaaa",
)


def test_released_10_file_keeps_run_draft_baseline_and_original_results():
    encoded = FIXTURE.read_bytes().rstrip(b"\n")
    restored = load_experiment(encoded)
    current = restored.current
    assert len(current.periods) == 3
    assert len(restored.baseline.periods) == 2
    assert current.draft_households != current.periods[0].households
    assert current.draft_firms != current.periods[0].firms
    assert (current.selected_period, current.report_scope, current.selected_firm) == (
        2, "Cumulative", "firm_b",
    )
    assert dump_experiment(current, baseline=restored.baseline) == encoded


def test_released_10_file_continues_with_identical_full_snapshot_fingerprints():
    restored = load_experiment(FIXTURE.read_bytes())
    periods = list(restored.current.periods)
    for _ in CONTINUATION_DIGESTS:
        previous = periods[-1]
        periods.append(advance_competition_period(
            previous.households, previous.firms, previous,
        ))
    continued = replace(restored.current, periods=tuple(periods))
    saved = json.loads(dump_experiment(continued, baseline=restored.baseline))
    assert saved["engine_version"] == "two-firms-1.0.0"
    assert tuple(saved["current"]["run"]["period_digests"][3:]) == CONTINUATION_DIGESTS
    assert saved["baseline"] == json.loads(FIXTURE.read_text())["baseline"]
