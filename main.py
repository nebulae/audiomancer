import json
import os
import typer
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputFileParam

load_dotenv()  # reads .env into os.environ

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

api_convert_prompt = os.getenv("OPENAI_CONVERT_PROMPT")
if not api_convert_prompt:
    raise ValueError("OPENAI_CONVERT_PROMPT environment variable not set")

api_condense_prompt = os.getenv("OPENAI_CONDENSE_PROMPT")
if not api_condense_prompt:
    raise ValueError("OPENAI_CONDENSE_PROMPT environment variable not set")

responses_model = os.getenv("OPENAI_RESPONSES_MODEL", "gpt-5-mini")
voice_model = os.getenv("OPENAI_VOICE_MODEL", "gpt-4o-mini-tts")
voice_flavor = os.getenv("OPENAI_VOICE", "alloy")
output_dir = os.getenv("OUTPUT_DIR", "./output")

client = OpenAI(api_key=api_key)
app = typer.Typer()

# defining the structure of the response we expect
# this is a nested structure of chapters, sections, and segments
class Segment(BaseModel):
    text: str
    approx_words: int

class Section(BaseModel):
    title: str
    segments: list[Segment]

class Chapter(BaseModel):
    title: str
    sections: list[Section]

class TextResponse(BaseModel):
    chapters: list[Chapter]


# load a pdf file, send it to the API, get the response, and save it to a file
@app.command()
def load(path: str, prefix: str = ""):
    get_transcript(api_convert_prompt, path, prefix)

@app.command()
def condense(path: str, prefix: str = ""):
    get_transcript(api_condense_prompt, path, prefix)


def get_transcript(prompt: str, path: str, prefix: str = ''):
    typer.echo(f"Loading file at {path}")
    pdf = client.files.create(
        file=open(path, "rb"),
        purpose="assistants"
    )
    typer.echo(f"Uploaded file, got id: {pdf.id}")

    input_pdf: ResponseInputFileParam = {
        "type": "input_file",
        "file_id": pdf.id,
    }

    input_message: EasyInputMessageParam = {
        "role": "user",
        "content": [
            {"type": "input_text", "text": prompt},
            input_pdf
        ],
    }

    typer.echo(f"Transcribing.... please have patience, this may take a while")

    with typer.progressbar(length=100) as bar:
        resp = client.responses.parse(
            model=responses_model,
            input=[input_message],
            text_format=TextResponse
        )
        bar.update(100)

    event = resp.output_parsed
    typer.echo(f"Got response with {len(event.chapters)} chapters")
    # print out the token usage
    typer.echo(f"Token usage: {resp.usage.model_dump_json(indent=2)}")

    # make a directory with the name of the file without extension
    dirname = os.path.join(output_dir, prefix, os.path.splitext(os.path.basename(path))[0])
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    # write the output to a file in that directory
    output_path = os.path.join(dirname, "output.txt")
    with open(output_path, "w") as f:
        f.write(event.model_dump_json(indent=2))


@app.command()
def listen(path: str, prefix: str = ""):
    filename = os.path.basename(path)
    dirname = os.path.join(output_dir, prefix, os.path.splitext(filename)[0])

    def process(text: str, index: int) -> (str, int, str):
        file_path = os.path.join(dirname, f"{filename}-{index}.mp3")
        typer.echo(f"Processing chunk {index} with {len(text)} characters")
        with typer.progressbar(length=100) as bar:
            with client.audio.speech.with_streaming_response.create(
                    model=voice_model,
                    voice=voice_flavor,
                    input=text
            ) as response:
                response.stream_to_file(file_path)
            bar.update(100)
        return "", index + 1, file_path


    # load the json file at path we saved it to
    typer.echo(f"Converting text to speech for {path}")

    if not os.path.exists(dirname):
        raise ValueError(f"Directory {dirname} does not exist")

    input_path = os.path.join(dirname, "output.txt")

    if not os.path.exists(input_path):
        raise ValueError(f"Input file {input_path} does not exist")

    # load this as a json object
    with open(input_path, "r") as f:
        data: TextResponse = json.load(f)
    if not data:
        raise ValueError(f"Could not load data from {input_path}")

    typer.echo(f"Loaded {len(data['chapters'])} chapters")

    # collect and chunk everything into a max of 4096 characters
    chunk = ""
    idx = 0
    # playlist = []
    for chapter in data["chapters"]:
        if len(chunk) > 4000: # max context length for gpt-4o-mini-tts is 4096
            chunk, idx, saved_file = process(chunk, idx)
            # playlist.append(saved_file)
        chunk += f"Chapter: {chapter['title']}\n"
        # typer.echo(f"Chapter: {chapter['title']}")
        for section in chapter["sections"]:
            if len(chunk) + len(section["title"]) > 4000:
                chunk, idx, saved_file = process(chunk, idx)
                # playlist.append(saved_file)
            chunk += f"  Section: {section['title']}\n"
            for segment in section["segments"]:
                if len(chunk) + len(segment["text"]) > 4000:
                    chunk, idx, saved_file = process(chunk, idx)
                    # playlist.append(saved_file)
                chunk += f"{segment['text']}\n"

    chunk, idx, saved_file = process(chunk, idx)
    # playlist.append(saved_file)

    # write a playlist file
    # playlist_path = f"{dirname}.m3u"
    # with open(playlist_path, "w") as f:
    #     for item in playlist:
    #         f.write(f"{item}\n")
    # typer.echo(f"Wrote playlist to {playlist_path}")

    typer.echo(f"Wrote {idx+1} audio files to {dirname}")

###
# generate a playlist file for the given directory, using the created at time to order the files
###
@app.command()
def playlist(path: str, prefix: str = ""):

    filename =  os.path.splitext(os.path.basename(path))[0]
    dirname = os.path.join(output_dir, prefix, os.path.splitext(filename)[0])

    if not os.path.exists(dirname):
        raise ValueError(f"Directory {dirname} does not exist")

    playlist = []
    files = [(file, os.path.join(dirname, file)) for file in os.listdir(dirname)]
    for file, full_path in sorted(files, key=lambda x: os.path.getctime(x[1])):
        if file.endswith(".mp3"):
            playlist.append(file)

    # write a playlist file
    playlist_path = os.path.join(dirname, f"{filename}.m3u")
    with open(playlist_path, "w") as f:
        for item in playlist:
            f.write(f"{item}\n")
    typer.echo(f"Wrote playlist to {playlist_path}")

@app.command()
def convert(path: str):
    load(path, "converted")
    listen(path, "converted")
    playlist(path, "converted")

@app.command()
def summarize(path: str):
    condense(path, "condensed")
    listen(path, "condensed")
    playlist(path, "condensed")


if __name__ == "__main__":
    app()