# src/api.py
import os
import base64
import time
import requests
import json
import imghdr
from dotenv import load_dotenv
import litellm
from openai import OpenAI

load_dotenv()

API_BASE = os.getenv("THUCCHIEN_API_BASE", "https://api.thucchien.ai")
API_KEY = os.getenv("THUCCHIEN_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Google Gemini key
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
DEFAULT_TEMP = float(os.getenv("TEMPERATURE", "1.0"))

# Configure LiteLLM client base
litellm.api_base = API_BASE

# OpenAI-compatible client for image generation via /chat/completions
openai_client = OpenAI(api_key=API_KEY, base_url=API_BASE)


def chat_completions(messages, model=None, temperature=None, use_web_search=False):
    """
    Call /chat/completions with optional web_search_options.
    If use_web_search=True, adds {"search_context_size": "medium"}.
    """
    kwargs = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "temperature": DEFAULT_TEMP if temperature is None else temperature,
        "api_key": API_KEY,
        "api_base": API_BASE,
        "custom_llm_provider": "openai",
    }
    if use_web_search:
        kwargs["web_search_options"] = {"search_context_size": "medium"}

    resp = litellm.completion(**kwargs)
    content = getattr(resp.choices[0].message, "content", str(resp))
    return {"raw": resp, "content": content}


def generate_image(
    prompt,
    model="gemini-2.5-flash-image-preview",
    aspect_ratio="1:1",
    n=1,
    image_context=None
):
    """
    Generate an image using the OpenAI-compatible chat completions API.
    (Reverted to the previous working flow that posts a user message with
     optional image data URLs, and reads back a base64 image from response.)
    """
    try:
        # Build message content with optional image context
        content = [{"type": "text", "text": prompt}]
        if image_context:
            for img_data in image_context:
                img_b64 = base64.b64encode(img_data).decode("utf-8")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}"
                        },
                    }
                )

        # Use OpenAI client with chat completions for image generation
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            modalities=["image"],
        )

        # Process the response
        if response and response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if hasattr(message, "images") and message.images:
                # Expect a data URL in image_url.url
                base64_string = message.images[0].get("image_url", {}).get("url", "")
                if base64_string:
                    encoded = base64_string.split(",", 1)[1] if "," in base64_string else base64_string
                    image_data = base64.b64decode(encoded)
                    return {
                        "success": True,
                        "image_data": image_data,
                        "b64_json": encoded,
                        "prompt": prompt,
                "model": model,
                "resolution": resolution_to_use,
                        "aspect_ratio": aspect_ratio,
                    }
                else:
                    return {"success": False, "error": "No base64 image data in response"}
            else:
                return {"success": False, "error": "No images in response message"}
        else:
            return {"success": False, "error": "No choices in response"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_image(image_data, filename):
    os.makedirs("generated_images", exist_ok=True)
    filepath = os.path.join("generated_images", filename)
    with open(filepath, "wb") as f:
        f.write(image_data)
    return filepath


def _b64(img_bytes: bytes) -> str:
    return base64.b64encode(img_bytes).decode("utf-8")


def _detect_mime(img_bytes: bytes) -> str:
    """
    Best-effort MIME detection for images — Veo expects bytesBase64Encoded and mimeType.
    """
    kind = imghdr.what(None, h=img_bytes)
    mapping = {
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "rgb": "image/x-rgb",
        "pbm": "image/x-portable-bitmap",
        "pgm": "image/x-portable-graymap",
        "ppm": "image/x-portable-pixmap",
        "rast": "image/x-cmu-raster",
        "xbm": "image/x-xbitmap",
        "webp": "image/webp",
    }
    return mapping.get(kind, "image/png")  # safe default if unknown


def _image_obj(img_bytes: bytes) -> dict:
    """
    Veo image part object with both bytesBase64Encoded and mimeType.
    """
    return {
        "bytesBase64Encoded": _b64(img_bytes),
        "mimeType": _detect_mime(img_bytes),
    }


def generate_video_api_call(
    prompt,
    model='veo-3.0-generate-001',
    negative_prompt='blurry, low quality',
    aspect_ratio='16:9',
    resolution='1080p',
    person_generation='allow_all',
    duration_seconds=8,
    reference_images=None,              # list[bytes] (max 3)
    first_frame_image_data=None,        # bytes
    last_frame_image_data=None,         # bytes
):
    """
    Calls the ThucChien AI video generation API.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")
    if not prompt and not first_frame_image_data and not reference_images:
        raise ValueError("Provide at least a prompt or some images (reference/first frame).")

    # Step 1: Start video generation
    step1_url = f'{API_BASE}/gemini/v1beta/models/{model}:predictLongRunning'

    # ---- instances[0] ----
    instance = {'prompt': prompt or ""}

    # first frame goes on the instance as 'image'
    if first_frame_image_data:
        instance["image"] = _image_obj(first_frame_image_data)

    # ---- parameters ----
    parameters = {
        'negativePrompt': negative_prompt,
        'aspectRatio': aspect_ratio,
        'resolution': resolution,
        'personGeneration': person_generation,
        'durationSeconds': int(duration_seconds)
    }

    # last frame for interpolation
    if last_frame_image_data:
        parameters["lastFrame"] = {"image": _image_obj(last_frame_image_data)}

    # up to 3 reference images
    if reference_images:
        parameters["referenceImages"] = [{"image": _image_obj(b)} for b in reference_images[:3]]

    step1_payload = {
        'instances': [instance],
        'parameters': parameters
    }

    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': GEMINI_API_KEY
    }

    print(f"Video Generation Request URL: {step1_url}")
    print(f"Video Generation Request Payload: {json.dumps(step1_payload, indent=2)}")
    print(f"Video Generation Request Headers: {json.dumps(headers, indent=2)}")

    response1 = requests.post(step1_url, json=step1_payload, headers=headers)
    
    if response1.status_code != 200:
        print(f"Video Generation Step 1 Error: {response1.status_code} - {response1.text}")
        response1.raise_for_status() # Raise an exception for HTTP errors

    operation_name = response1.json().get('name')
    if not operation_name:
        raise ValueError('No operation name returned from video generation start.')

    # Step 2: Poll for completion (with timeout)
    max_attempts = 60  # 5 minutes with 5-second intervals
    attempt = 0

    while attempt < max_attempts:
        step2_url = f'{API_BASE}/gemini/v1beta/{operation_name}'
        print(f"Polling URL: {step2_url}")
        response2 = requests.get(step2_url, headers=headers)
        
        if response2.status_code != 200:
            print(f"Video Generation Step 2 Error: {response2.status_code} - {response2.text}")
            response2.raise_for_status()

        result = response2.json()
        print(f"Polling Result: {json.dumps(result, indent=2)}")

        if result.get('done'):
            try:
                if "response" in result and "generateVideoResponse" in result["response"] and result["response"]["generateVideoResponse"]["generatedSamples"]:
                    video_uri = result['response']['generateVideoResponse']['generatedSamples'][0]['video']['uri']
                else:
                    raise ValueError("No 'generateVideoResponse' found in the completion payload.")

                video_id = video_uri.split('/files/')[1].split(':')[0]
                return {"video_id": video_id, "video_uri": video_uri}
            except (KeyError, IndexError) as e:
                print("Unexpected API response:", json.dumps(result, indent=2))
                raise ValueError(f"Invalid response format from video generation status: {e}")

        attempt += 1
        time.sleep(5)

    raise TimeoutError('Video generation timeout.')


def download_video_api_call(video_id):
    """
    Downloads a video given its video_id. Returns raw bytes.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")

    download_url = f"{API_BASE}/gemini/download/v1beta/files/{video_id}:download?alt=media"
    headers = {"x-goog-api-key": GEMINI_API_KEY}
    response = requests.get(download_url, headers=headers, stream=True)
    response.raise_for_status()
    return response.content


def generate_video(prompt, model='veo-3.0-generate-001', aspect_ratio='16:9', duration=8, negative_prompt='blurry, low quality',
                            person_generation='allow_all', reference_images=None, first_frame_image_data=None, last_frame_image_data=None):
    """
    Orchestrates the video generation and download process.
    
    Args:
        prompt (str): The text prompt for video generation.
        model (str): The model to use for video generation.
        aspect_ratio (str): The aspect ratio of the generated video.
        duration (int): The duration of the video in seconds.
        negative_prompt (str): The negative prompt for video generation.
        person_generation (str): Person generation setting.
        reference_images (list): List of reference image data bytes.
        first_frame_image_data (bytes): First frame image data bytes.
        last_frame_image_data (bytes): Last frame image data bytes.
        
    Returns:
        dict: Contains the generated video data and metadata, or an error.
    """
    try:
        # Simple resolution heuristic
        if aspect_ratio == "16:9":
            resolution_to_use = "1080p"
        else:
            resolution_to_use = "720p"
        
        video_gen_result = generate_video_api_call(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            resolution=resolution_to_use,
            duration_seconds=duration,
            negative_prompt=negative_prompt,
            person_generation=person_generation,
            reference_images=reference_images,
            first_frame_image_data=first_frame_image_data,
            last_frame_image_data=last_frame_image_data,
        )
        
        if video_gen_result and "video_id" in video_gen_result:
            video_id = video_gen_result["video_id"]
            video_data = download_video_api_call(video_id)
            
            return {
                "success": True,
                "video_data": video_data,
                "video_id": video_id,
                "prompt": prompt,
                "model": model,
                "resolution": resolution_to_use,
                "aspect_ratio": aspect_ratio,
                "duration": duration,
                "negative_prompt": negative_prompt,
                "reference_images": bool(reference_images),
                "first_frame_present": bool(first_frame_image_data),
                "last_frame_present": bool(last_frame_image_data),
            }
        else:
            return {
                "success": False,
                "error": video_gen_result.get("error", "Unknown error during video generation start.")
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def text_to_speech(
    input_text: str,
    model: str = "gemini-2.5-flash-preview-tts",
    voice: str = "Zephyr",
    audio_format: str = "mp3",   # only used to hint the filename if server returns generic type
    filename: str | None = None,
    timeout: int = 120,
):
    """
    Convert text to speech via ThucChien AI gateway and save the audio locally.

    Args:
        input_text: Text to synthesize.
        model: TTS model id. Example: "gemini-2.5-flash-preview-tts".
        voice: Voice preset. Example: "Zephyr".
        audio_format: Expected file extension fallback (e.g., "mp3", "wav", "ogg").
        filename: Optional output filename (without path). If None, one is generated.
        timeout: Request timeout in seconds.

    Returns:
        dict:
            {
                "success": True/False,
                "path": "/full/path/to/file.mp3" (when success),
                "content_type": "audio/mpeg",
                "status_code": 200,
                "bytes": <int>,
                "error": "..." (when failed),
            }
    """
    if not API_KEY:
        return {"success": False, "error": "THUCCHIEN_API_KEY is not set.", "status_code": 0}

    url = f"{API_BASE}/audio/speech"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": model,
        "input": input_text,
        "voice": voice,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout, stream=True)
        status = resp.status_code
        content_type = resp.headers.get("Content-Type", "")

        # If server sends JSON error or meta
        if not content_type.startswith("audio/"):
            # Try to parse JSON for diagnostics
            try:
                data = resp.json()
            except Exception:
                data = {"message": resp.text[:500]}
            return {
                "success": False,
                "status_code": status,
                "content_type": content_type,
                "error": data.get("error") or data.get("message") or "Unexpected non-audio response.",
            }

        # Prepare output path
        os.makedirs("generativeAudios", exist_ok=True)

        # Pick extension from content-type when possible
        ext_map = {
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/ogg": "ogg",
            "audio/opus": "opus",
            "audio/webm": "webm",
            "audio/aac": "aac",
            "audio/flac": "flac",
        }
        ext = ext_map.get(content_type.lower(), audio_format.lower() if audio_format else "mp3")

        if not filename:
            safe_voice = "".join(c for c in voice if c.isalnum() or c in ("-", "_")).strip() or "voice"
            ts = int(time.time())
            filename = f"tts_{safe_voice}_{ts}.{ext}"
        elif not filename.lower().endswith(f".{ext}"):
            # ensure extension matches what we think we're saving
            filename = f"{filename}.{ext}"

        out_path = os.path.join("generativeAudios", filename)

        # Write bytes
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        file_size = os.path.getsize(out_path)
        return {
            "success": True,
            "status_code": status,
            "content_type": content_type,
            "path": out_path,
            "bytes": file_size,
            "model": model,
            "voice": voice,
        }
    except requests.RequestException as e:
        return {"success": False, "error": str(e), "status_code": 0}
