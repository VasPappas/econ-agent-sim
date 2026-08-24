# ADR 0001 — Core architecture principles

**Status:** Accepted

## Decision

The simulator uses Python and separates economic state/logic from presentation and future persistence.

Completed economies remain runnable scenarios rather than being overwritten. Shared infrastructure may evolve, but regression tests must preserve each scenario's defined results and accounting identities.

The transaction ledger is append-only from the model's point of view. State changes happen through explicit transfers so that every change in stocks can be reconciled to flows.

Economy 0 uses no database. Persistence will be introduced only when simulation history and query volume justify it, behind a storage interface rather than inside the economic model.

## Why

This structure favors transparency, reproducibility, regression testing, and gradual scaling without forcing infrastructure complexity into the first economics lesson.
