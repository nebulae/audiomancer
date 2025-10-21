import os

import typer
from typing import Optional

from .core import (
    transcript,
    text_to_speech_for_dir,
    write_playlist,
    smash_into_one,
    convert_flow,
    summarize_flow,
    create_reading_note,
    PROMPT_CONVERT,
    PROMPT_CONDENSE,
)


app = typer.Typer(help="Audiomancer CLI – convert/condense PDFs to structured text and TTS audio")

def backend_opts(
    backend: str = typer.Option("api", "--backend", help="api | oss"),
    oss_model: Optional[str] = typer.Option(None, "--oss-model", help="Hugging Face model id, e.g. openai/gpt-oss-20b"),
    oss_tokens: int = typer.Option(2048, "--oss-max-new-tokens", help="Max new tokens per chunk (OSS)"),
    oss_device_map: str = typer.Option("auto", "--oss-device-map", help="Transformers device_map (e.g. auto, cuda:0)"),
    oss_torch_dtype: str = typer.Option("auto", "--oss-dtype", help="float16 | bfloat16 | auto"),
):
    return dict(backend=backend, oss_model_id=oss_model, oss_max_new_tokens=oss_tokens,
                oss_device_map=oss_device_map, oss_torch_dtype=oss_torch_dtype)

@app.callback()
def _main(verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")):
    if verbose:
        typer.echo("[verbose] on")


@app.command(help="Upload and convert PDF to structured JSON using the specified backend.")
def load(
    path: str,
    prefix: str = "",
    backend: str = "api",
    oss_model: Optional[str] = None,
    oss_max_new_tokens: int = 2048,
    oss_device_map: str = "auto",
    oss_dtype: str = "auto",
):
    transcript(
        PROMPT_CONVERT,
        path,
        prefix or "converted",
        backend=backend,
        oss_model_id=oss_model,
        oss_max_new_tokens=oss_max_new_tokens,
        oss_device_map=oss_device_map,
        oss_torch_dtype=oss_dtype,
    )


@app.command(help="Upload and condense PDF to structured JSON using the specified backend.")
def condense(
    path: str,
    prefix: str = "",
    backend: str = "api",
    oss_model: Optional[str] = None,
    oss_max_new_tokens: int = 2048,
    oss_device_map: str = "auto",
    oss_dtype: str = "auto",
):
    files = []

    # if the path is a folder, process all pdf files in it
    if os.path.isdir(path):
        for file in os.listdir(path):
            if file.lower().endswith(".pdf"):
                files.append(os.path.join(path, file))
    else:
        files.append(path)

    for path in files:
        transcript(
            PROMPT_CONDENSE,
            path,
            prefix or "condensed",
            backend=backend,
            oss_model_id=oss_model,
            oss_max_new_tokens=oss_max_new_tokens,
            oss_device_map=oss_device_map,
            oss_torch_dtype=oss_dtype,
        )


@app.command(help="Full pipeline: convert → TTS → (playlist|one MP3)")
def convert(
    path: str,
    into_one_mp3: bool = typer.Option(False, "--one", help="Combine into one MP3 instead of playlist"),
    backend: str = "api",
    oss_model: Optional[str] = None,
    oss_max_new_tokens: int = 2048,
    oss_device_map: str = "auto",
    oss_dtype: str = "auto",
):
    files = []

    # if the path is a folder, process all pdf files in it
    if os.path.isdir(path):
        for file in os.listdir(path):
            if file.lower().endswith(".pdf"):
                files.append(os.path.join(path, file))
    else:
        files.append(path)

    for path in files:
        convert_flow(
            path,
            into_one_mp3,
            backend=backend,
            oss_model_id=oss_model,
            oss_max_new_tokens=oss_max_new_tokens,
            oss_device_map=oss_device_map,
            oss_torch_dtype=oss_dtype,
        )


@app.command(help="Full pipeline: condense → TTS → (playlist|one MP3)")
def summarize(
    path: str,
    into_one_mp3: bool = typer.Option(False, "--one", help="Combine into one MP3 instead of playlist"),
    backend: str = "api",
    oss_model: Optional[str] = None,
    oss_max_new_tokens: int = 2048,
    oss_device_map: str = "auto",
    oss_dtype: str = "auto",
):
    summarize_flow(
        path,
        into_one_mp3,
        backend=backend,
        oss_model_id=oss_model,
        oss_max_new_tokens=oss_max_new_tokens,
        oss_device_map=oss_device_map,
        oss_torch_dtype=oss_dtype,
    )


@app.command(help="Create a structured reading note (≤300 words) for a PDF")
def reading_note(
    path: str,
    prefix: str = "",
    backend: str = "api",
):
    try:
        create_reading_note(
            path,
            prefix or "reading-notes",
            backend=backend,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc))

@app.command(help="Turn a previously produced structured text into MP3 chunks")
def listen(path: str, prefix: str = ""):
    out_dir = text_to_speech_for_dir(path, prefix or "converted")
    typer.echo(f"Audio written under: {out_dir}")

@app.command(help="Create a .m3u playlist from generated MP3 chunks")
def playlist(path: str, prefix: str = ""):
    p = write_playlist(path, prefix or "converted")
    typer.echo(f"Wrote playlist to {p}")

@app.command(help="Combine all MP3 chunks into a single file and delete the chunks")
def smash(path: str, prefix: str = ""):
    final_path = smash_into_one(path, prefix or "converted")
    typer.echo(f"Wrote combined audio to {final_path}")


@app.command(help="Show version")
def version():
    from importlib.metadata import version, PackageNotFoundError
    try:
        typer.echo(f"audiomancer {version('audiomancer')}")
    except PackageNotFoundError:
        typer.echo("audiomancer (uninstalled dev mode)")
