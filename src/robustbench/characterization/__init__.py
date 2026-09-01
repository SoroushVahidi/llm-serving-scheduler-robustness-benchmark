"""Outcome-blind workload-distribution-characterization pipeline.

Everything in this package computes source-native (or deterministically
derived) workload descriptors and cross-source/within-source distribution-
shift statistics. Nothing here runs a scheduler policy, computes a policy
outcome, or is imported by anything in `robustbench.policies`,
`robustbench.simulator`, or `robustbench.evaluation` -- this package is
intentionally decoupled from the (frozen) Stage-0 scheduler-discriminability
pipeline. See docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md.
"""
