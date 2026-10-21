"""CPU-only preflight and independently loaded Rust tokenizer."""
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path
from robustbench.mgpu02.startup import PinnedPrompt, verify_sources


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


class IndependentTokenizer:
    def __init__(self, path):
        from tokenizers import Tokenizer
        self.tokenizer = Tokenizer.from_file(str(Path(path) / 'tokenizer.json'))

    def decode(self, ids):
        return self.tokenizer.decode(ids, skip_special_tokens=False)

    def encode(self, text):
        return self.tokenizer.encode(text, add_special_tokens=False).ids


def verify_assets(root, model_path):
    root, model_path = Path(root), Path(model_path)
    pinned = PinnedPrompt(model_path, root/'scripts/mgpu02/prompt.json')
    tokenizer = IndependentTokenizer(model_path)
    if tokenizer.encode(pinned.fixture['text']) != pinned.fixture['body_token_ids']:
        raise ValueError('Independent tokenizer disagrees with pinned input')
    sources = verify_sources(root/'artifacts/mgpu02/source-inspection/upstream.json')
    dist = importlib.metadata.distribution('vllm')
    api = json.loads((root/'scripts/mgpu05/api-sources.json').read_text())
    for path, expected in api['files'].items():
        observed = file_hash(dist.locate_file(path))
        if observed != expected:
            raise ValueError('Unreviewed API source: '+path)
        sources[path] = observed
    weights = sorted(model_path.glob('*.safetensors'))
    if not weights:
        raise ValueError('Missing model weights')
    # HF snapshot symlinks resolve to content-addressed LFS blobs. Hash actual bytes.
    weight_hashes = {}
    for path in weights:
        actual = file_hash(path)
        if path.resolve().name != actual:
            raise ValueError('Weights lack matching content-addressed snapshot blob: '+path.name)
        weight_hashes[path.name] = actual
    versions = {k:importlib.metadata.version(k) for k in
                ('vllm','torch','transformers','tokenizers','httpx','numpy')}
    if versions['httpx'] != '0.28.1':
        raise ValueError('Unreviewed HTTP transport version')
    expected = json.loads((root/'scripts/mgpu05/environment.json').read_text())
    if weight_hashes != expected['weights'] or versions != expected['versions']:
        raise ValueError('Model weights or software versions differ from reviewed environment')
    extra = {p:file_hash(model_path/p) for p in expected['additional_model_files']}
    if extra != expected['additional_model_files']:
        raise ValueError('Model generation configuration changed')
    return tokenizer, dict(tokenizer=pinned.fixture['tokenizer_files_sha256'], weights=weight_hashes,
                           sources=sources, versions=versions, additional_model_files=extra,
                           revision=model_path.name, python=sys.version, executable=sys.executable)
