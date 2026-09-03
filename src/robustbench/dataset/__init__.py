"""LSSP public dataset-release schema/contract package.

Result-blind by construction: nothing in this package reads or requires a
real Phase-12 scheduler_outcomes value. It only knows how to (a) describe
the release's table/config contract, (b) validate rows against that
contract using the already-frozen Phase-10/11/12B manifests as ground
truth for identifiers, and (c) build the tables that are derivable from
those frozen manifests alone (workload_windows, workload_descriptors,
load_region_assignments, policy_registry). scheduler_outcomes/telemetry
row *values* are never fabricated here as if real; the schema is defined,
not populated, until a validated consolidated Phase-12 artifact exists.
"""
