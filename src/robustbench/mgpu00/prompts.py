"""Frozen RQ6 prompt construction, copied unchanged from commit
703a752762348bd911c9d93f17731fa5244b38f9 (project MIT license).
Used only BEFORE timed injection. The caller rejects token-length round-trip
mismatches; no truncation/substitution is performed during replay.
"""
from typing import Any, List

_SENTENCE_BANK = [
    "The request scheduler assigns incoming jobs to available GPU workers.",
    "Each worker maintains a key-value cache that grows during decoding.",
    "Batching multiple requests together can improve overall throughput.",
    "A scheduling policy decides the order in which requests are served.",
    "Prefill computes the initial hidden state for the full input prompt.",
    "Decoding produces one output token at a time using the cached state.",
    "Admission control can reject requests when the system is overloaded.",
    "Latency service-level objectives constrain how long a request may wait.",
    "Preemption allows a scheduler to pause one request to serve another.",
    "Throughput and tail latency are often in tension with each other.",
    "A simulator can replay traffic traces to compare scheduling policies.",
    "Token generation speed depends on batch size and sequence length.",
    "Streaming responses let a client observe output as it is produced.",
    "Fairness across tenants is one goal of a multi-tenant serving system.",
    "Cache eviction policies determine which sequences are dropped first.",
]

def build_exact_length_prompt(tokenizer: Any, target_tokens: int, seed: int) -> str:
    """Deterministically build prompt text whose tokenizer-encoded length
    (`len(tokenizer.encode(text, add_special_tokens=False))`) is exactly
    `target_tokens`, for any `target_tokens >= 1`.

    Method: walk a deterministic, seed-rotated stream of words drawn from
    `_SENTENCE_BANK`, tokenizing incrementally, until the accumulated token
    id list reaches at least `target_tokens`; then hard-truncate the id list
    to exactly `target_tokens` and decode it back to text. This is exact by
    construction on the *id* axis. The returned *text*, if re-tokenized, is
    verified by the caller (see `verify_exact_length_prompt`) to round-trip
    to the same length for the plain-ASCII sentence bank used here; a
    request where it does not is a real, disclosed approximation, not a
    silently-accepted one.
    """
    if target_tokens < 1:
        raise ValueError(f"target_tokens must be >= 1, got {target_tokens}")

    start = seed % len(_SENTENCE_BANK)

    def _words_upto(n_sentences: int) -> List[str]:
        words: List[str] = []
        for i in range(n_sentences):
            words.extend(_SENTENCE_BANK[(start + i) % len(_SENTENCE_BANK)].split())
        return words

    # Coarse jump: estimate the word count needed from this tokenizer's
    # observed tokens-per-word ratio on the sentence bank itself, then do a
    # small number of doubling top-ups if the estimate undershoots. This
    # keeps cost near O(log target_tokens) encode() calls instead of
    # O(target_tokens) (re-encoding the whole growing string once per word
    # does not scale to the ~29k-token prompts seen in the frozen traces).
    bank_words = " ".join(w for s in _SENTENCE_BANK for w in s.split())
    bank_word_count = len(bank_words.split())
    bank_token_count = len(tokenizer.encode(bank_words, add_special_tokens=False))
    tokens_per_word = max(bank_token_count / bank_word_count, 1e-6)

    n_sentences = max(1, int(target_tokens / tokens_per_word / 8) + 1)  # ~8 words/sentence
    words = _words_upto(n_sentences)
    ids = tokenizer.encode(" ".join(words), add_special_tokens=False)
    while len(ids) < target_tokens:
        n_sentences *= 2
        words = _words_upto(n_sentences)
        ids = tokenizer.encode(" ".join(words), add_special_tokens=False)

    truncated_ids = ids[:target_tokens]
    return tokenizer.decode(truncated_ids)
