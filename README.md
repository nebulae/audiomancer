# 🎧 Audiomancer

**Audiomancer** is a command-line tool that transforms documents (PDFs) into structured audiobook-ready transcriptions and spoken audio files.  
It uses the **OpenAI Responses API** for intelligent text extraction and **OpenAI TTS models** for natural-sounding narration.  

---

## ✨ Features

- 📄 Uploads PDFs and extracts text in logical reading order  
- 🧠 Uses OpenAI’s `Responses API` to generate clean, chaptered transcriptions  
- 🔊 Converts structured text into high-quality speech segments  
- ⚙️ Configurable models and output paths via `.env`  
- 🧰 Simple CLI built with [Typer](https://typer.tiangolo.com/)  
- 🪄 `convert` and `summarize` commands for one-step workflows  
- 
- 🎼 Generates `.m3u` playlists for seamless audiobook playback  

---

## 🧑‍💻 Installation

### 1️⃣ Clone the repository
```bash
git clone https://github.com/<your-username>/audiomancer.git
cd audiomancer
```

### 2️⃣ Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

*(If you don’t have a `requirements.txt` yet, generate one with `pip freeze > requirements.txt` after installing `typer`, `python-dotenv`, `pydantic`, and `openai`.)*

---

## ⚙️ Configuration

Generate an OpenAI API key from [platform.openai.com](https://platform.openai.com/account/api-keys) if you don’t have one.

Use the `.env.example` as the baseline, and rename it to `.env`:
```bash
cp .env.example .env
```
Create a `.env` file in the project root with your API credentials and defaults:

```bash
OPENAI_API_KEY=sk-...
OPENAI_CONVERT_PROMPT="Extract an audiobook-ready transcript from a PDF and return segmented JSON for text-to-speech."
OPENAI_CONDENSE_PROMPT="Summarize this document into concise audiobook-ready text with clear sections and key points."
OPENAI_RESPONSES_MODEL=gpt-5-mini
OPENAI_VOICE_MODEL=gpt-4o-mini-tts
OPENAI_VOICE=alloy
OUTPUT_DIR=./output
```

You can customize these defaults anytime — for example, swap the `OPENAI_VOICE_MODEL` or change the `OUTPUT_DIR`.

---

## 🚀 Usage

### 🗂️ Step 1: Extract the text
to get a structured transcript:
```bash
python main.py load path/to/document.pdf
```
or, for a condensed summary:
```bash
python main.py condense path/to/document.pdf
```

Uploads the PDF and saves a structured JSON transcript to:
```
./output/<document-name>/output.txt
```

---

### 🔊 Step 2: Generate the audiobook
```bash
python main.py listen path/to/document.pdf
```
Reads the transcript and generates MP3 files for each text chunk into:
```
./output/<document-name>/
```

Each segment is saved as:
```
<document-name>-0.mp3
<document-name>-1.mp3
<document-name>-2.mp3
...
```

---

### 🎶 Step 3: Generate the playlist
```bash
python main.py playlist path/to/document.pdf
```
Creates an `.m3u` playlist file for playback:
```
./output/<document-name>/<document-name>.m3u
```

### 🗜️ Step 4: Smash into one mp3, if desired
this will concatenate all segments into a single file, and delete the individual segments:
```bash
python main.py smash path/to/document.pdf
---
creates:
./output/<document-name>/<document-name>-full.mp3
```


### ⚡ One-step full conversion
```bash
python main.py convert path/to/document.pdf
```
Runs all steps (`load`, `listen`, and `playlist`) sequentially to create a complete audiobook.

---

to create one mp3 from all segments:
```bash
python main.py convert --into-one-mp3 path/to/document.pdf
```

### 🧭 Summarize instead of convert
```bash
python main.py summarize path/to/document.pdf
```

to create one mp3 from all segments:
```bash
python main.py summarize --into-one-mp3 path/to/document.pdf
```

Generates a **condensed audiobook** version using the `OPENAI_CONDENSE_PROMPT`.  
Perfect for executive summaries or research papers.

---

## 🧩 Project Structure

```
audiomancer/
│
├── main.py               # CLI entry point
├── .env.example          # Example environment variables
├── requirements.txt
└── output/               # Generated transcripts & audio files
```

---

## 🛠️ Dependencies

- [Typer](https://typer.tiangolo.com/) — CLI framework  
- [Pydantic](https://docs.pydantic.dev/) — typed response parsing  
- [python-dotenv](https://saurabh-kumar.com/python-dotenv/) — environment variable loader  
- [OpenAI SDK](https://github.com/openai/openai-python) — API access  

Install them manually if needed:
```bash
pip install typer python-dotenv pydantic openai
```

---

## 📚 Example Workflow

```bash
python main.py load ./samples/whitepaper.pdf
python main.py listen ./samples/whitepaper.pdf
python main.py playlist ./samples/whitepaper.pdf
```

Or, for a complete conversion in one go:
```bash
python main.py convert ./samples/whitepaper.pdf 
```

To summarize instead:
```bash
python main.py summarize ./samples/whitepaper.pdf 
```

---

## 🧠 Notes

- The Responses API may take several minutes for large PDFs.  
- Each TTS segment is capped at ~4,000 characters for `gpt-4o-mini-tts`.  
- Output is structured as chapters → sections → segments.  
- Progress bars are displayed during both transcription and audio generation.  
- All outputs are stored in subfolders under your defined `OUTPUT_DIR`.  

---

## 🪶 License

MIT © 2025 Trinity Arcand
