import base64
import mimetypes
import json
from typing import List, Dict, Any
from pathlib import Path


def encode_image(image_path: str) -> str:
    """
    Encodes an image file to a base64 data URI with a dynamic MIME type.

    Args:
        image_path: The path to the image file.

    Returns:
        The base64-encoded data URI string of the image (e.g., "data:image/jpeg;base64,...").
    
    Raises:
        ValueError: If the file type is not a recognizable image.
    """
    # Guess the MIME type of the image based on the file extension
    mime_type, _ = mimetypes.guess_type(image_path)
    
    if not mime_type or not mime_type.startswith('image'):
        raise ValueError(f"Cannot determine a valid image type for the file: {image_path}")

    with open(image_path, "rb") as image_file:
        base64_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    return f"data:{mime_type};base64,{base64_string}"


def save_texts_to_file(texts: List[str], file_path: Path):
    with open(file_path, 'w', encoding='utf-8') as f:
        for text in texts:
            f.write(text + '\n')


def load_texts_from_file(file_path: Path) -> List[str]:
    if not file_path.exists():
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def save_json(data: Dict[str, Any], file_path: str):
    """
    Save a dictionary to a JSON file.

    Args:
        data (Dict[str, Any]): The dictionary to save.
        file_path (str): The path to the JSON file.
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load a dictionary from a JSON file.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        Dict[str, Any]: The loaded dictionary.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
