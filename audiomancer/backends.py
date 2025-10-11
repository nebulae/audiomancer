from __future__ import annotations
import os, json, math
from pathlib import Path
from typing import List, Dict, Any, Optional

import typer
from pydantic import ValidationError

# lazy import torch/transformers so API users don't need them installed
def _lazy_import_transformers():
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    import torch
    return AutoModelForCausalLM, AutoTokenizer, pipeline, torch

from .models import TextResponse

DEFAULT_OSS_MODEL = os.getenv("OSS_MODEL_ID", "openai/gpt-oss-20b")  # or 120b if you have the VRAM
TTS_MAX_CHARS = 4000  # keep consistent with your TTS headroom

def read_pdf_text(path: str) -> str:
    # lightweight extraction; swap for your preferred extractor if needed
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("Install pypdf for OSS mode: pip install pypdf") from e
    reader = PdfReader(path)
    typer.echo(f"[oss] PDF has {len(reader.pages)} pages")
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def chunk_text(s: str, max_len: int = 10_000) -> List[str]:
    # naive chunker; keeps prompts manageable for local models
    out, buf = [], []
    total = 0
    for line in s.splitlines():
        if total + len(line) + 1 > max_len:
            out.append("\n".join(buf))
            buf, total = [line], len(line) + 1
        else:
            buf.append(line)
            total += len(line) + 1
    if buf:
        out.append("\n".join(buf))
    return out

def _json_only_prompt(schema_hint: str) -> str:
    return (
        "You are a careful JSON generator. "
        "Respond with VALID JSON ONLY, no markdown fences, no commentary. "
        "The JSON must follow this schema:\n"
        f"{schema_hint}\n"
        "Do not include fields not in the schema. Ensure lists and strings are properly escaped."
    )

_SCHEMA_HINT = """
{
  "chapters": [
    {
      "title": "string",
      "sections": [
        {
          "title": "string",
          "segments": [
            {"text": "string", "approx_words": 123}
          ]
        }
      ]
    }
  ]
}
""".strip()

def _apply_chat_template(tokenizer, system: str, user: str) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    # GPT-OSS expects the “harmony” chat format via Transformers chat templates
    # (this applies the right bos/eos and tool prefixes automatically). :contentReference[oaicite:0]{index=0}
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

def run_oss_transcript(pdf_path: str, convert_prompt: str, model_id: Optional[str] = None,
                       max_new_tokens: int = 2048, device_map: str = "auto",
                       torch_dtype: str = "auto") -> TextResponse:
    AutoModelForCausalLM, AutoTokenizer, pipeline, torch = _lazy_import_transformers()
    model_id = model_id or DEFAULT_OSS_MODEL

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    dtype = getattr(torch, torch_dtype) if torch_dtype != "auto" else "auto"
    typer.echo(f"[oss] loading model {model_id} with dtype={dtype} device_map={device_map}")

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map=device_map,
        torch_dtype=dtype,
    )
    gen = pipeline("text-generation", model=model, tokenizer=tokenizer)

    pdf_text = read_pdf_text(pdf_path)
    chunks = chunk_text(pdf_text, max_len=9500)
    typer.echo(f"[oss] PDF text is {len(pdf_text)} chars, split into {len(chunks)} chunks")

    system = _json_only_prompt(_SCHEMA_HINT)
    # feed each chunk, then merge JSON progressively (model may output partials per chunk)
    merged: Dict[str, Any] = {"chapters": []}

    for i, chunk in enumerate(chunks):
        typer.echo(f"[oss] processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
        user = (
            f"{convert_prompt}\n\n"
            f"Document excerpt {i+1}/{len(chunks)}:\n"
            f"{chunk}\n\n"
            "Produce JSON for just the content seen so far (skip duplicates)."
        )
        formatted = _apply_chat_template(tokenizer, system, user)
        out = gen(formatted, max_new_tokens=max_new_tokens, do_sample=False)[0]["generated_text"]
        # Strip the prompt prefix returned by text-generation pipeline
        completion = out[len(formatted):].strip()

        # try to load and merge
        try:
            piece = json.loads(completion)
            if "chapters" in piece and isinstance(piece["chapters"], list):
                merged["chapters"].extend(piece["chapters"])
        except json.JSONDecodeError:
            # If it failed, try a minimal repair: find first/last braces
            start = completion.find("{")
            end = completion.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    piece = json.loads(completion[start:end+1])
                    if "chapters" in piece and isinstance(piece["chapters"], list):
                        merged["chapters"].extend(piece["chapters"])
                except Exception:
                    typer.echo("[oss] warning: could not parse model JSON for one chunk")

    # validate against your Pydantic model
    try:
        return TextResponse.model_validate(merged)
    except ValidationError as e:
        # fall back to a minimal shell if validation fails
        typer.echo(f"[oss] validation failed, returning minimal structure: {e}")
        return TextResponse(chapters=[])
