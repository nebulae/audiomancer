# 🎧 Audiomancer

Audiomancer is a Typer-based command line tool that turns PDFs into structured transcripts and spoken audio. It can run entirely on the OpenAI platform or, if you prefer to keep things local, on an OSS stack that uses Transformers for transcription.

---

## ✨ What it does

- Extracts the text of a PDF and reshapes it into clean chapters, sections, and segments.
- Generates audiobook-ready narration using the OpenAI Text-to-Speech API.
- Produces playlists or a single merged MP3 for easy listening.
- Supports directory batching (convert/condense every PDF in a folder).
- Can run through OpenAI's Responses API (`--backend api`) or a local OSS model (`--backend oss`).

---

## 📦 Requirements

- Python 3.9+
- An OpenAI API key with access to the Responses and Audio APIs (for `--backend api`).
- Optional: CUDA-capable GPU if you plan to run the OSS workflow with large local models.

---

## 🚀 Quick start

```bash
# clone
git clone https://github.com/<your-username>/audiomancer.git
cd audiomancer

# (optional) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# install the package and its dependencies
pip install -e .
```

If you only want the API workflow you can omit GPU toolkits, but the default dependencies include `torch` and `transformers` so that the OSS backend works out of the box.

---

## 🔐 Environment configuration

Audiomancer reads its configuration from environment variables (loaded automatically from a `.env` file via `python-dotenv`). The following variables are required at startup:

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI API key used for both text and audio requests. |
| `OPENAI_CONVERT_PROMPT` | System/user instructions describing how to create full transcripts. |
| `OPENAI_CONDENSE_PROMPT` | Instructions for condensed/summarized transcripts. |
| `OPENAI_READING_NOTE_PROMPT` | Guidance for drafting 300-word reading notes following the required template. |

These have sensible defaults but can be overridden:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_RESPONSES_MODEL` | `gpt-5-mini` | Model used by the Responses API. |
| `OPENAI_VOICE_MODEL` | `gpt-4o-mini-tts` | Model used for text-to-speech. |
| `OPENAI_VOICE` | `alloy` | Voice preset for TTS. |
| `OUTPUT_DIR` | `../.output` | Root directory for generated artifacts. |
| `OSS_MODEL_ID` | `openai/gpt-oss-20b` | Default Transformers model when `--backend oss` is used. |
| `OSS_ENABLED` | unset (`False`) | Toggle used internally; set to `1` if you want to default to OSS mode. |

Create a `.env` file in the project root to keep these values together:

```env
OPENAI_API_KEY=sk-...
OPENAI_CONVERT_PROMPT="...full transcript prompt..."
OPENAI_CONDENSE_PROMPT="...summary transcript prompt..."
OPENAI_READING_NOTE_PROMPT="...reading note prompt..."
OPENAI_RESPONSES_MODEL=gpt-5-mini
OPENAI_VOICE_MODEL=gpt-4o-mini-tts
OPENAI_VOICE=alloy
OUTPUT_DIR=./output
```

> ℹ️ The prompts are intentionally long. Reuse the guidance from `.env.example` or author your own, but make sure the strings are valid JSON-safe quotes (escape inner quotes with `\`).

---

## 🛠️ CLI usage

You can invoke the CLI with either `python main.py ...`, `python -m audiomancer ...`, or the installed entry point `audiomancer ...`.

```text
Usage: audiomancer [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose  Enable verbose output
  --help         Show this message and exit.
```

### Primary commands

| Command | Description |
| --- | --- |
| `load PATH` | Run the conversion prompt against `PATH` (single PDF) and save structured JSON under `OUTPUT_DIR/converted/<stem>/output.txt`. |
| `condense PATH` | Run the condensation prompt against a PDF (or every PDF in a directory). Outputs to `OUTPUT_DIR/condensed/...`. |
| `convert PATH` | Full pipeline: transcript → TTS chunks → playlist (or single MP3 with `--one`). Works on a single PDF or directory. |
| `summarize PATH` | Full condensation pipeline: condensed transcript → audio → playlist or single MP3. |
| `reading-note PATH` | Generate a formatted reading note (Markdown + JSON + MP3) capped at roughly 300 words. |
| `listen PATH` | Convert an existing transcript directory into MP3 chunks. |
| `playlist PATH` | Build an `.m3u` playlist from generated chunks. |
| `smash PATH` | Merge MP3 chunks into `<stem>-full.mp3` and remove the smaller files. |
| `version` | Display the installed package version. |

### Shared backend options

Most commands that generate transcripts accept a common set of options:

```text
--backend [api|oss]             Which transcription backend to use (default: api)
--oss-model TEXT                Hugging Face model id for OSS mode
--oss-max-new-tokens INTEGER    Maximum new tokens per chunk (OSS mode)
--oss-device-map TEXT           Transformers device map (e.g. auto, cuda:0)
--oss-dtype TEXT                Torch dtype (auto, float16, bfloat16)
```

The OSS path relies on the packages listed in `pyproject.toml`. Expect the first run to download model weights.

### Typical flows

```bash
# Full audiobook from a single PDF using OpenAI
OPENAI_API_KEY=... audiomancer convert paper.pdf

# Condense an entire folder of PDFs into one-track MP3s using OSS backend
OSS_MODEL_ID=openai/gpt-oss-8b audiomancer summarize ./briefs --backend oss --one

# If you already have transcripts:
audiomancer listen ./output/converted/paper
```

Generated audio lives alongside the transcript under the configured `OUTPUT_DIR`, for example:

```text
OUTPUT_DIR/
├── converted/
│   └── paper/
│       ├── output.txt
│       ├── paper-0.mp3
│       ├── paper-1.mp3
│       └── paper.m3u
└── condensed/
    └── paper/
        ├── output.txt
        └── paper-full.mp3
```

---

## 🧪 Development

- Format / lint as you prefer; the project does not ship with tooling enforced in CI.
- Unit tests are not bundled yet. If you add them, run via `python -m pytest`.
- When contributing, verify that CLI commands still complete end-to-end with sample PDFs.

---

## 🪶 License

MIT © 2025 Trinity Arcand
