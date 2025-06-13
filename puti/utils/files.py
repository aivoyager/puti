import base64
import mimetypes


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
