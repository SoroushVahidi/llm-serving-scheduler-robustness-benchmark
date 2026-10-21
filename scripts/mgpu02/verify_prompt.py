#!/usr/bin/env python3
"""Offline CPU check of the saved token fixture; no server or GPU execution."""
import argparse
import hashlib
import json
from pathlib import Path
from transformers import AutoTokenizer
from robustbench.mgpu02.startup import PinnedPrompt

parser = argparse.ArgumentParser()
parser.add_argument('--model-path', type=Path, required=True)
args = parser.parse_args()
fixture = Path(__file__).with_name('prompt.json')
pinned = PinnedPrompt(args.model_path, fixture)
actual = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)
ids = actual.encode(pinned.fixture['text'], add_special_tokens=False)
assert ids == pinned.fixture['body_token_ids']
assert (ids * (128 // len(ids) + 1))[:128] == pinned.fixture['prompt_token_ids']
print(json.dumps({'status': 'PASS', 'comparison': 'actual pinned tokenizer vs frozen token IDs',
                  'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
                  'body_ids': ids, 'prompt_tokens': 128}))
