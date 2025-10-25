"""
Image utilities for AI Coder to handle vision model inputs.
"""

import base64
import os
import mimetypes
from typing import Dict, Any, List


def get_image_mime_type(file_path: str) -> str:
    """Get the MIME type for an image file."""
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type.startswith("image/"):
        return mime_type
    # Fallback to file extension
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".heic": "image/heic",
    }
    # Return the mapped MIME type or None if not supported
    return mime_map.get(ext, "application/octet-stream")  # Default to generic binary


def is_supported_image_format(file_path: str) -> bool:
    """Check if the image format is supported by vision models."""
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type.startswith("image/"):
        supported_types = [
            "image/bmp",
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/tiff",
            "image/webp",
            "image/heic",
        ]
        return mime_type in supported_types

    # If mimetypes can't determine, check file extension directly
    ext = os.path.splitext(file_path)[1].lower()
    supported_extensions = [
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".webp",
        ".tiff",
        ".tif",
        ".heic",
    ]
    return ext in supported_extensions


def encode_image_to_base64(file_path: str) -> str:
    """Encode an image file to base64 string."""
    with open(file_path, "rb") as image_file:
        binary_data = image_file.read()
        base64_encoded = base64.b64encode(binary_data).decode("utf-8")
        return base64_encoded


def create_image_content_part(file_path: str) -> Dict[str, Any]:
    """Create an image content part for the API message."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")

    if not is_supported_image_format(file_path):
        mime_type = get_image_mime_type(file_path)
        raise ValueError(
            f"Unsupported image format: {mime_type}. Supported formats: bmp, jpeg, jpg, png, tiff, webp, heic"
        )

    base64_data = encode_image_to_base64(file_path)
    mime_type = get_image_mime_type(file_path)

    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{base64_data}"},
    }


def create_text_content_part(text: str) -> Dict[str, Any]:
    """Create a text content part for the API message."""
    return {"type": "text", "text": text}


def create_multimodal_message(
    role: str, content_parts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create a multimodal message that can contain both text and images."""
    return {"role": role, "content": content_parts}


def parse_image_references(user_input: str) -> tuple[str, List[str]]:
    """
    Parse user input to extract image file paths and return clean text.

    Supports image references in these formats:
    - [image:file_path.jpg]
    - ![alt text](file_path.jpg)
    - @/path/to/image.jpg (at-sign followed by file path)

    Returns:
        tuple: (clean_text, list_of_image_paths)
    """
    import re

    # Pattern to match image references like [image:path.jpg] or ![alt](path.jpg)
    explicit_image_pattern = r"\[image:([^\]]+)\]|!\[[^\]]*\]\(([^)]+)\)"

    # Pattern to match @ followed by potential file paths (at-sign format)
    at_image_pattern = r"@(\S+\.(?:png|jpe?g|gif|bmp|webp|tiff?|heic))"

    # Find all explicit image references
    explicit_matches = re.findall(explicit_image_pattern, user_input)
    image_paths = []
    for match in explicit_matches:
        # Each match is a tuple, get the non-empty one
        path = match[0] if match[0] else match[1]
        image_paths.append(path.strip())

    # Remove explicit image references from text
    clean_text = re.sub(explicit_image_pattern, "", user_input)

    # Find all @image references
    at_matches = re.findall(at_image_pattern, clean_text)
    for path in at_matches:
        image_paths.append(path.strip())

    # Remove @image references from text
    clean_text = re.sub(at_image_pattern, "", clean_text).strip()

    return clean_text, image_paths


def create_user_message(user_input: str) -> Dict[str, Any]:
    """
    Create a user message from input that may contain image references.
    Returns either a simple text message or a multimodal message depending on whether images are present.

    Args:
        user_input: User input that may contain image references

    Returns:
        Dict containing properly formatted message for API
    """
    clean_text, image_paths = parse_image_references(user_input)

    # Filter out non-existent images
    existing_image_paths = [path for path in image_paths if os.path.exists(path)]
    missing_images = [path for path in image_paths if not os.path.exists(path)]

    if not existing_image_paths and not missing_images:
        # No images referenced at all, return regular text message
        return {"role": "user", "content": user_input}

    if not existing_image_paths and missing_images:
        # Only missing images, return error text message
        error_text = f"{clean_text} " if clean_text.strip() else ""
        error_text += " ".join(
            [f"[Error: Image file not found: {path}]" for path in missing_images]
        )
        return {"role": "user", "content": error_text.strip()}

    # We have some existing images, create multimodal message
    content_parts = []

    # Add text part if there's text
    if clean_text.strip():
        content_parts.append(create_text_content_part(clean_text))

    # Add existing image parts
    for image_path in existing_image_paths:
        try:
            image_part = create_image_content_part(image_path)
            content_parts.append(image_part)
        except Exception as e:
            # If there's an error encoding the image, add as error text
            content_parts.append(
                create_text_content_part(
                    f"[Error encoding image {image_path}: {str(e)}]"
                )
            )

    # Add missing image errors
    for missing_path in missing_images:
        content_parts.append(
            create_text_content_part(f"[Error: Image file not found: {missing_path}]")
        )

    return create_multimodal_message("user", content_parts)
