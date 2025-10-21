import os
from typing import Callable, Tuple

import typer
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputFileParam

from .models import TextResponse, ReadingNote
from .io_utils import (
    build_output_dir,
    ensure_dir,
    write_json_textresponse,
    read_textresponse,
    list_audio_by_ctime,
    write_reading_note,
)

from .backends import run_oss_transcript

# Load env once per process
load_dotenv()

OSS_ENABLED = os.getenv("OSS_ENABLED", "0") == "1"
OSS_DEFAULT_MODEL = os.getenv("OSS_MODEL_ID", "openai/gpt-oss-20b")

# Environment/config
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

PROMPT_CONVERT = os.getenv("OPENAI_CONVERT_PROMPT")
if not PROMPT_CONVERT:
    raise ValueError("OPENAI_CONVERT_PROMPT environment variable not set")

PROMPT_CONDENSE = os.getenv("OPENAI_CONDENSE_PROMPT")
if not PROMPT_CONDENSE:
    raise ValueError("OPENAI_CONDENSE_PROMPT environment variable not set")

PROMPT_READING_NOTE = os.getenv("OPENAI_READING_NOTE_PROMPT")
if not PROMPT_READING_NOTE:
    raise ValueError("OPENAI_READING_NOTE_PROMPT environment variable not set")

RESPONSES_MODEL = os.getenv("OPENAI_RESPONSES_MODEL", "gpt-5-mini")
VOICE_MODEL = os.getenv("OPENAI_VOICE_MODEL", "gpt-4o-mini-tts")
VOICE_FLAVOR = os.getenv("OPENAI_VOICE", "alloy")

# Chunk limit for tts (leave a little headroom)
TTS_MAX_CHARS = 4000

_client = OpenAI(api_key=API_KEY)

def _upload_pdf(path: str):
    return _client.files.create(file=open(path, "rb"), purpose="assistants")

def _make_input(pdf_id: str, prompt: str) -> EasyInputMessageParam:
    input_pdf: ResponseInputFileParam = {"type": "input_file", "file_id": pdf_id}
    return {
        "role": "user",
        "content": [{"type": "input_text", "text": prompt}, input_pdf],
    }


def transcript(prompt: str, path: str, prefix: str, *, backend: str = "api",
               oss_model_id: str | None = None, oss_max_new_tokens: int = 2048,
               oss_device_map: str = "auto", oss_torch_dtype: str = "auto") -> TextResponse:
    if backend == "oss":
        typer.echo(f"[oss] running local transcript with {oss_model_id or OSS_DEFAULT_MODEL}")
        data = run_oss_transcript(
            pdf_path=path,
            convert_prompt=prompt,
            model_id=oss_model_id or OSS_DEFAULT_MODEL,
            max_new_tokens=oss_max_new_tokens,
            device_map=oss_device_map,
            torch_dtype=oss_torch_dtype,
        )
        out_dir = build_output_dir(path, prefix=prefix)
        ensure_dir(out_dir)
        write_json_textresponse(out_dir, data)
        typer.echo(f"[oss] wrote structured JSON to {out_dir}/output.txt")
        return data

    # === existing API path remains unchanged ===
    typer.echo(f"Loading file at {path}")
    pdf = _upload_pdf(path)
    typer.echo(f"Uploaded file, id: {pdf.id}")

    input_message = _make_input(pdf.id, prompt)
    typer.echo("Transcribing...")

    with typer.progressbar(length=100) as bar:
        resp = _client.responses.parse(
            model=RESPONSES_MODEL,
            input=[input_message],
            text_format=TextResponse,
        )
        bar.update(100)

    data = resp.output_parsed
    typer.echo(f"Got response with {len(data.chapters)} chapters")
    typer.echo(f"Token usage: {resp.usage.model_dump_json(indent=2)}")

    out_dir = build_output_dir(path, prefix=prefix)
    ensure_dir(out_dir)
    write_json_textresponse(out_dir, data)
    return data


def create_reading_note(path: str, prefix: str, *, backend: str = "api") -> ReadingNote:
    if backend != "api":
        raise ValueError("Reading note generation currently requires backend='api'")

    typer.echo(f"Loading file at {path}")
    pdf = _upload_pdf(path)
    typer.echo(f"Uploaded file, id: {pdf.id}")

    input_message = _make_input(pdf.id, PROMPT_READING_NOTE)
    typer.echo("Drafting reading note...")

    with typer.progressbar(length=100) as bar:
        resp = _client.responses.parse(
            model=RESPONSES_MODEL,
            input=[input_message],
            text_format=ReadingNote,
        )
        bar.update(100)

    note = resp.output_parsed
    typer.echo(f"Token usage: {resp.usage.model_dump_json(indent=2)}")

    out_dir = build_output_dir(path, prefix=prefix)
    ensure_dir(out_dir)
    md_path, json_path = write_reading_note(out_dir, note)
    typer.echo(f"Wrote reading note to {md_path}")
    typer.echo(f"Wrote structured JSON to {json_path}")

    # Rough word count for operator awareness
    parts = [note.citation, note.argument, note.assessment]
    parts.extend(note.main_points)
    parts.extend(note.evidence)
    approx_words = sum(len(p.split()) for p in parts)
    typer.echo(f"Approximate word count: {approx_words} words")

    return note

def text_to_speech_for_dir(input_pdf_path: str, prefix: str) -> str:
    filename = os.path.basename(input_pdf_path)
    out_dir = build_output_dir(input_pdf_path, prefix=prefix)

    if not os.path.exists(out_dir):
        raise ValueError(f"Directory {out_dir} does not exist")

    # Read structured text
    data = read_textresponse(out_dir)
    typer.echo(f"Loaded {len(data.chapters)} chapters")

    def process(text: str, index: int) -> Tuple[str, int, str]:
        file_path = os.path.join(out_dir, f"{filename}-{index}.mp3")
        typer.echo(f"Processing chunk {index} with {len(text)} characters")
        with typer.progressbar(length=100) as bar:
            with _client.audio.speech.with_streaming_response.create(
                model=VOICE_MODEL, voice=VOICE_FLAVOR, input=text
            ) as response:
                response.stream_to_file(file_path)
            bar.update(100)
        return "", index + 1, file_path

    # Gather chunks
    chunk = ""
    idx = 0

    for chapter in data.chapters:
        line = f"Chapter: {chapter.title}\n"
        if len(chunk) + len(line) > TTS_MAX_CHARS:
            chunk, idx, _ = process(chunk, idx)
        chunk += line

        for section in chapter.sections:
            line = f"  Section: {section.title}\n"
            if len(chunk) + len(line) > TTS_MAX_CHARS:
                chunk, idx, _ = process(chunk, idx)
            chunk += line

            for segment in section.segments:
                text = f"{segment.text}\n"
                if len(chunk) + len(text) > TTS_MAX_CHARS:
                    chunk, idx, _ = process(chunk, idx)
                chunk += text

    if chunk:
        process(chunk, idx)

    return out_dir

def write_playlist(input_pdf_path: str, prefix: str) -> str:
    stem = os.path.splitext(os.path.basename(input_pdf_path))[0]
    out_dir = build_output_dir(input_pdf_path, prefix=prefix)
    if not os.path.exists(out_dir):
        raise ValueError(f"Directory {out_dir} does not exist")

    playlist = list_audio_by_ctime(out_dir)
    playlist_path = os.path.join(out_dir, f"{stem}.m3u")
    with open(playlist_path, "w") as f:
        for item in playlist:
            f.write(f"{item}\n")
    return playlist_path

def smash_into_one(input_pdf_path: str, prefix: str) -> str:
    from pydub import AudioSegment

    stem = os.path.splitext(os.path.basename(input_pdf_path))[0]
    out_dir = build_output_dir(input_pdf_path, prefix=prefix)
    if not os.path.exists(out_dir):
        raise ValueError(f"Directory {out_dir} does not exist")

    combined = AudioSegment.empty()
    files = list_audio_by_ctime(out_dir)
    for f in files:
        typer.echo(f"Adding {f} to combined audio")
        combined += AudioSegment.from_mp3(os.path.join(out_dir, f))

    output_path = os.path.join(out_dir, f"{stem}-full.mp3")
    combined.export(output_path, format="mp3")
    typer.echo(f"Wrote combined audio to {output_path}")

    # remove the smaller chunks
    for f in files:
        full = os.path.join(out_dir, f)
        if not f.endswith("-full.mp3"):
            os.remove(full)
            typer.echo(f"Deleted {f}")

    return output_path

# High-level flows (used by CLI)
def convert_flow(path: str, into_one_mp3: bool, **backend_kwargs) -> None:
    transcript(PROMPT_CONVERT, path, prefix="converted", **backend_kwargs)
    text_to_speech_for_dir(path, prefix="converted")
    if into_one_mp3:
        smash_into_one(path, prefix="converted")
    else:
        p = write_playlist(path, prefix="converted")
        typer.echo(f"Wrote playlist to {p}")

def summarize_flow(path: str, into_one_mp3: bool, **backend_kwargs) -> None:
    transcript(PROMPT_CONDENSE, path, prefix="condensed", **backend_kwargs)
    text_to_speech_for_dir(path, prefix="condensed")
    if into_one_mp3:
        smash_into_one(path, prefix="condensed")
    else:
        p = write_playlist(path, prefix="condensed")
        typer.echo(f"Wrote playlist to {p}")
