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
OPENAI_PROMPT="Extract an audiobook-ready transcript from a PDF and return segmented JSON for text-to-speech...."
OPENAI_RESPONSES_MODEL=gpt-5-mini
OPENAI_VOICE_MODEL=gpt-4o-mini-tts
OPENAI_VOICE=alloy
OUTPUT_DIR=./output
```

You can customize these defaults anytime — for example, swap the `OPENAI_VOICE_MODEL` or change the `OUTPUT_DIR`.

---

## 🚀 Usage

### 🗂️ Step 1: Extract the text
```bash
python main.py load path/to/document.pdf
```
This uploads the PDF, sends it to the OpenAI Responses API with your chosen prompt, and saves a structured JSON transcript to:
```
./output/<document-name>/output.txt
```

---

### 🔊 Step 2: Generate the audiobook
```bash
python main.py listen path/to/document.pdf
```
This reads the JSON transcript and streams generated MP3 files for each text chunk into:
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
```
Then play the generated audio in your favorite media player 🎧

---

## 🧠 Notes

- The Responses API may take several minutes for large PDFs.  
- Each TTS segment is capped at ~4,000 characters for `gpt-4o-mini-tts`.  
- Output is structured as chapters → sections → segments for clarity.  

---

## 🪶 License

MIT © 2025 Trinity Arcand
