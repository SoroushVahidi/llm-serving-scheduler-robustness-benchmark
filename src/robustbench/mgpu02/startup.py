"""Verify pinned prompt tokens without importing/loading a second tokenizer."""
import hashlib
import importlib.metadata
import json
from pathlib import Path


def verify_sources(manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    distribution = importlib.metadata.distribution('vllm')
    if distribution.version != '0.27.1':
        raise ValueError('Unreviewed vLLM version')
    checked = {}
    for row in manifest['files']:
        relative = row['url'].split('/v0.27.1/')[1]
        if not relative.startswith('vllm/'):
            continue
        digest = hashlib.sha256(Path(distribution.locate_file(relative)).read_bytes()).hexdigest()
        if digest != row['sha256'] or digest != row['local_sha256']:
            raise ValueError('Installed source differs: ' + relative)
        checked[relative] = digest
    return checked


class PinnedPrompt:
    def __init__(self, model_path, fixture_path):
        self.fixture = json.loads(Path(fixture_path).read_text())
        if Path(model_path).name != self.fixture['revision']:
            raise ValueError('Unpinned tokenizer revision')
        for name, expected in self.fixture['tokenizer_files_sha256'].items():
            if hashlib.sha256((Path(model_path) / name).read_bytes()).hexdigest() != expected:
                raise ValueError('Tokenizer file hash mismatch: ' + name)
        ids = self.fixture['body_token_ids']
        if ((ids * (128 // len(ids) + 1))[:128] != self.fixture['prompt_token_ids']
                or not all(type(i) is int and i >= 0 for i in ids)):
            raise ValueError('Invalid pinned token fixture')

    def encode(self, text, *, add_special_tokens=False):
        if text != self.fixture['text'] or add_special_tokens:
            raise ValueError('Pinned tokenizer only supports the exact engineering fixture')
        return list(self.fixture['body_token_ids'])
