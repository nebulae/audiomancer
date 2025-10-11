import json
import os
from typing import Iterable, List, Tuple

from .models import TextResponse

DEFAULT_OUTPUT_DIR = os.getenv("OUTPUT_DIR", "../.output")

def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def file_stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]

def build_output_dir(input_path: str, prefix: str = "", base_dir: str | None = None) -> str:
    base = base_dir or DEFAULT_OUTPUT_DIR
    return os.path.join(base, prefix, file_stem(input_path))

def write_json_textresponse(dest_dir: str, data: TextResponse) -> str:
    ensure_dir(dest_dir)
    out_path = os.path.join(dest_dir, "output.txt")
    with open(out_path, "w") as f:
        f.write(data.model_dump_json(indent=2))
    return out_path

def read_textresponse(input_dir: str) -> TextResponse:
    input_path = os.path.join(input_dir, "output.txt")
    if not os.path.exists(input_path):
        raise ValueError(f"Input file {input_path} does not exist")
    with open(input_path, "r") as f:
        raw = json.load(f)
    return TextResponse.model_validate(raw)

def list_audio_by_ctime(dir_path: str) -> List[str]:
    files = [(fn, os.path.join(dir_path, fn)) for fn in os.listdir(dir_path)]
    files = sorted(files, key=lambda x: os.path.getctime(x[1]))
    return [f for f, full in files if f.endswith(".mp3")]
