"""XGrammar loader for Cluster 1 constrained decoding."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class CompiledGrammar:
    """Small wrapper around the backend-compiled grammar object."""

    def __init__(self, backend_grammar: Any, grammar_path: str, vocab_fingerprint: str):
        self.backend_grammar = backend_grammar
        self.grammar_path = grammar_path
        self.vocab_fingerprint = vocab_fingerprint


_TOKENIZER_IDS_BY_FINGERPRINT: dict[str, str] = {}


def load_compiled_grammar(grammar_path: str, tokenizer_id: str) -> CompiledGrammar:
    """Load and cache a compiled XGrammar grammar for a tokenizer vocabulary."""

    fingerprint = _vocab_fingerprint(tokenizer_id)
    _TOKENIZER_IDS_BY_FINGERPRINT[fingerprint] = tokenizer_id
    return _load_compiled_grammar_cached(str(Path(grammar_path)), fingerprint)


@lru_cache(maxsize=8)
def _load_compiled_grammar_cached(
    grammar_path: str,
    vocab_fingerprint: str,
) -> CompiledGrammar:
    tokenizer_id = _TOKENIZER_IDS_BY_FINGERPRINT[vocab_fingerprint]
    grammar_text = Path(grammar_path).read_text(encoding="utf-8")
    backend_grammar = _compile_xgrammar(grammar_text, tokenizer_id)
    return CompiledGrammar(
        backend_grammar=backend_grammar,
        grammar_path=grammar_path,
        vocab_fingerprint=vocab_fingerprint,
    )


def _vocab_fingerprint(tokenizer_id: str) -> str:
    tokenizer = _load_tokenizer(tokenizer_id)
    vocab = tokenizer.get_vocab()
    ordered_vocab = [
        {"token": token, "id": token_id}
        for token, token_id in sorted(vocab.items(), key=lambda item: item[1])
    ]
    payload = {
        "vocab_size": len(vocab),
        "ordered_vocab": ordered_vocab,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _load_tokenizer(tokenizer_id: str):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(tokenizer_id)


def _compile_xgrammar(grammar_text: str, tokenizer_id: str):
    """Compile GBNF text with XGrammar.

    The exact XGrammar API has changed across releases, so this adapter keeps the
    public Cluster 1 loader stable while still failing loudly if no compatible API
    exists in the installed package.
    """

    import xgrammar as xgr

    tokenizer_info = _build_tokenizer_info(xgr, tokenizer_id)
    compiler = xgr.GrammarCompiler(tokenizer_info)
    if hasattr(compiler, "compile_grammar"):
        grammar = _build_xgrammar_grammar(xgr, grammar_text)
        return compiler.compile_grammar(grammar)
    if hasattr(compiler, "compile_grammar_from_string"):
        return compiler.compile_grammar_from_string(grammar_text)
    raise AttributeError("XGrammar GrammarCompiler has no GBNF compile method")


def _build_xgrammar_grammar(xgr, grammar_text: str):
    grammar_cls = getattr(xgr, "Grammar", None)
    if grammar_cls is None or not hasattr(grammar_cls, "from_ebnf"):
        return grammar_text
    return grammar_cls.from_ebnf(grammar_text, root_rule_name="root")


def _build_tokenizer_info(xgr, tokenizer_id: str):
    from transformers import AutoTokenizer

    if not hasattr(xgr, "TokenizerInfo"):
        raise AttributeError("xgrammar.TokenizerInfo is unavailable")

    tokenizer_info = xgr.TokenizerInfo
    if hasattr(tokenizer_info, "from_huggingface"):
        try:
            return tokenizer_info.from_huggingface(tokenizer_id)
        except (TypeError, ValueError, AttributeError):
            tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
            return tokenizer_info.from_huggingface(tokenizer)

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
    if hasattr(tokenizer_info, "from_huggingface_tokenizer"):
        return tokenizer_info.from_huggingface_tokenizer(tokenizer)
    raise AttributeError("xgrammar.TokenizerInfo has no HuggingFace constructor")
