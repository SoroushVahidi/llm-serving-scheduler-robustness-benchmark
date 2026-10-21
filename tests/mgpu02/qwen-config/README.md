`config.json` is the configuration-only fixture from the immutable
[Qwen/Qwen2.5-0.5B-Instruct revision](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/blob/7ae557604adf67be50417f59c2c2f167def9a775/config.json).
Its SHA-256 is also pinned in `scripts/mgpu02/prompt.json`. No model weights or
inference are used by these scheduler tests. The tests instantiate the real
installed vLLM scheduler and KV manager on CPU, with synthetic runner outputs.
