from __future__ import annotations

import argparse
import base64
import binascii
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openai import OpenAI, OpenAIError


# Batch defaults. These are the first places to edit for avatar generation.
ENV_FILE = Path(__file__).with_name("image_model.env")
OUTPUT_DIR = Path(__file__).with_name("generated")
PROMPTS_FILE = Path(__file__).with_name("avatar_prompts.txt")
RESPONSE_MODEL_NAME = "gpt-5"
DEFAULT_IMAGE_MODEL_NAME = "gpt-image-1"
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "low"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_BACKGROUND = "opaque"


@dataclass(frozen=True, slots=True)
class ImageConfig:
    api_url: str
    api_key: str
    image_model_name: str


def load_env_file(path: Path) -> ImageConfig:
    if not path.exists():
        raise RuntimeError(f"Missing env file: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    api_url = values.get("API_BASE_URL") or values.get("API_URL")
    api_key = values.get("API_KEY")
    image_model_name = values.get("IMAGE_MODEL_NAME") or values.get("MODEL_NAME") or DEFAULT_IMAGE_MODEL_NAME
    missing = [name for name, value in (("API_URL", api_url), ("API_KEY", api_key)) if not value]
    if missing:
        raise RuntimeError(f"env file missing required keys: {', '.join(missing)}")

    return ImageConfig(
        api_url=str(api_url).rstrip("/"),
        api_key=str(api_key),
        image_model_name=str(image_model_name),
    )


def load_prompts(path: Path) -> list[str]:
    if not path.exists():
        raise RuntimeError(f"Missing prompts file: {path}")
    prompts = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not prompts:
        raise RuntimeError(f"No prompts found in {path}")
    return prompts


def sanitize_stem(index: int, prompt: str) -> str:
    letters = []
    for char in prompt.lower():
        if char.isascii() and char.isalnum():
            letters.append(char)
        elif char in {" ", "-", "_"}:
            letters.append("-")
    compact = "".join(letters).strip("-")
    while "--" in compact:
        compact = compact.replace("--", "-")
    suffix = compact[:40] or "avatar"
    return f"{index:03d}-{suffix}"


def extract_image_base64(response: object) -> str:
    output = getattr(response, "output", None) or []
    for item in output:
        if getattr(item, "type", None) == "image_generation_call" and getattr(item, "result", None):
            return str(item.result)
    raise RuntimeError("Responses output did not contain an image_generation_call result.")


def decode_image(image_base64: str) -> bytes:
    try:
        return base64.b64decode(image_base64)
    except binascii.Error as exc:
        raise RuntimeError("Image result was not valid base64.") from exc


def generate_one(
    *,
    client: OpenAI,
    response_model_name: str,
    image_model_name: str,
    prompt: str,
    size: str,
    quality: str,
    output_format: str,
    background: str,
) -> bytes:
    response = client.responses.create(
        model=response_model_name,
        input=prompt,
        tools=[
            {
                "type": "image_generation",
                "model": image_model_name,
                "size": size,
                "quality": quality,
                "output_format": output_format,
                "background": background,
            }
        ],
        tool_choice={"type": "image_generation"},
    )
    return decode_image(extract_image_base64(response))


def write_images(
    *,
    client: OpenAI,
    prompts: Iterable[str],
    output_dir: Path,
    response_model_name: str,
    image_model_name: str,
    size: str,
    quality: str,
    output_format: str,
    background: str,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []
    for index, prompt in enumerate(prompts, start=1):
        image_bytes = generate_one(
            client=client,
            response_model_name=response_model_name,
            image_model_name=image_model_name,
            prompt=prompt,
            size=size,
            quality=quality,
            output_format=output_format,
            background=background,
        )
        output_path = output_dir / f"{sanitize_stem(index, prompt)}.{output_format}"
        output_path.write_bytes(image_bytes)
        written_paths.append(output_path)
        print(f"[{index}] wrote {output_path.name}")
    return written_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate avatar images with the Responses API.")
    parser.add_argument("--env-file", type=Path, default=ENV_FILE)
    parser.add_argument("--prompts-file", type=Path, default=PROMPTS_FILE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--response-model", default=RESPONSE_MODEL_NAME)
    parser.add_argument("--image-model", default=None)
    parser.add_argument("--size", default=DEFAULT_SIZE)
    parser.add_argument("--quality", default=DEFAULT_QUALITY)
    parser.add_argument("--output-format", default=DEFAULT_OUTPUT_FORMAT)
    parser.add_argument("--background", default=DEFAULT_BACKGROUND)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_env_file(args.env_file)
    prompts = load_prompts(args.prompts_file)

    # Responses API needs a text-capable response model. The image model is configured
    # on the image_generation tool, not in the top-level response model field.
    image_model_name = args.image_model or config.image_model_name
    client = OpenAI(api_key=config.api_key, base_url=config.api_url)

    try:
        written_paths = write_images(
            client=client,
            prompts=prompts,
            output_dir=args.output_dir,
            response_model_name=args.response_model,
            image_model_name=image_model_name,
            size=args.size,
            quality=args.quality,
            output_format=args.output_format,
            background=args.background,
        )
    except OpenAIError as exc:
        print(f"request failed: {exc}")
        return 1
    except RuntimeError as exc:
        print(f"request failed: {exc}")
        return 1

    print(f"done: {len(written_paths)} image(s) -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
