"""Prepare a hash-pinned historical window without changing its requests."""
import hashlib
import json
from pathlib import Path

from .metadata import RequestMetadata
from .prompts import build_exact_length_prompt
from .provenance import canonical_hash
from .replay import PreparedRequest


def prepare_window(manifest_path, *, expected_file_sha256, window_id, tokenizer):
    raw = Path(manifest_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_file_sha256:
        raise ValueError("Workload manifest file hash mismatch")
    manifest = json.loads(raw)
    matches = [w for w in manifest["windows"] if w["window_id"] == window_id]
    if len(matches) != 1:
        raise ValueError("Window is missing or ambiguous")
    window = matches[0]
    prepared = []
    for row in window["requests"]:
        text = build_exact_length_prompt(tokenizer, row["input_tokens"], row["prompt_generation_seed"])
        ids = tuple(tokenizer.encode(text, add_special_tokens=False))
        if len(ids) != row["input_tokens"]:
            raise ValueError("Prompt round-trip changed input length; refusing workload substitution")
        m = RequestMetadata(row["request_id"], row["request_index"], row["class_id"],
                            row["base_relative_arrival_s"], row["base_slo_deadline_s"], row["weight"])
        prepared.append(PreparedRequest(m, ids, row["output_tokens_target"]))
    if len({r.metadata.request_id for r in prepared}) != len(prepared):
        raise ValueError("Duplicate request identity")
    return prepared, {"source": manifest["source"], "window_id": window_id,
                      "manifest_file_sha256": expected_file_sha256,
                      "historical_content_sha256": window["content_sha256"],
                      "request_records_sha256": canonical_hash(window["requests"]),
                      "preparation": "frozen prompt generator; verified lengths; no arrival/deadline scaling"}
