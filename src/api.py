# src/api.py
import os
import base64
from dotenv import load_dotenv
import litellm
from openai import OpenAI

load_dotenv()

API_BASE = os.getenv("THUCCHIEN_API_BASE", "https://api.thucchien.ai")
API_KEY = os.getenv("THUCCHIEN_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
DEFAULT_TEMP = float(os.getenv("TEMPERATURE", "1.0"))

# set the API base ON the client
litellm.api_base = API_BASE

# Initialize OpenAI client for image generation
openai_client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE
)


def chat_completions(messages, model=None, temperature=None, use_web_search=False):
    """
    Call /chat/completions with optional web_search_options.
    If use_web_search=True, adds {"search_context_size": "medium"}.
    Otherwise, no web_search_options are sent.
    """
    kwargs = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "temperature": DEFAULT_TEMP if temperature is None else temperature,
        "api_key": API_KEY,
        "api_base": API_BASE,  # explicit
        "custom_llm_provider": "openai",  # force OpenAI-compatible route
    }

    # ✅ only include this if user toggled web search
    if use_web_search:
        kwargs["web_search_options"] = {"search_context_size": "medium"}

    resp = litellm.completion(**kwargs)
    content = getattr(resp.choices[0].message, "content", str(resp))

    return {"raw": resp, "content": content}


def generate_image(prompt, model="gemini-2.5-flash-image-preview", aspect_ratio="1:1", n=1, image_context=None):
    """
    Generate an image using the OpenAI library with chat completions API.
    
    Args:
        prompt (str): The text prompt for image generation
        model (str): The model to use for image generation (default: imagen-4)
        aspect_ratio (str): The aspect ratio of the generated image (default: "1:1")
        n (int): Number of images to generate (default: 1)
        image_context (list): List of image data bytes to use as context
    
    Returns:
        dict: Contains the generated image data and metadata
    """
    try:
        # Build message content with optional image context
        content = [{"type": "text", "text": prompt}]
        
        # Add image context if provided
        if image_context:
            for img_data in image_context:
                img_b64 = base64.b64encode(img_data).decode('utf-8')
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_b64}"
                    }
                })
        
        # Use OpenAI client with chat completions for image generation
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            modalities=["image"]
        )
        
        # Process the response
        if response and response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if hasattr(message, 'images') and message.images:
                # Get the base64 string from the response
                base64_string = message.images[0].get("image_url", {}).get("url", "")
                
                if base64_string:
                    # Handle data URL format (data:image/png;base64,...)
                    if ',' in base64_string:
                        header, encoded = base64_string.split(',', 1)
                    else:
                        encoded = base64_string
                    
                    image_data = base64.b64decode(encoded)
                    
                    return {
                        "success": True,
                        "image_data": image_data,
                        "b64_json": encoded,
                        "prompt": prompt,
                        "model": model,
                        "aspect_ratio": aspect_ratio
                    }
                else:
                    return {
                        "success": False,
                        "error": "No base64 image data in response"
                    }
            else:
                return {
                    "success": False,
                    "error": "No images in response message"
                }
        else:
            return {
                "success": False,
                "error": "No choices in response"
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def save_image(image_data, filename):
    """
    Save image data to a file.
    
    Args:
        image_data (bytes): The image data in bytes
        filename (str): The filename to save the image as
    
    Returns:
        str: The path to the saved image
    """
    os.makedirs("generated_images", exist_ok=True)
    filepath = os.path.join("generated_images", filename)
    
    with open(filepath, "wb") as f:
        f.write(image_data)
    
    return filepath
