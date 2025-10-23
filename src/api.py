# src/api.py
import os
import base64
import time
import requests
import json
from dotenv import load_dotenv
import litellm
from openai import OpenAI

load_dotenv()

API_BASE = os.getenv("THUCCHIEN_API_BASE", "https://api.thucchien.ai")
API_KEY = os.getenv("THUCCHIEN_API_KEY")
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Google Gemini key
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


def generate_image(prompt, model="gemini-2.5-flash-image-preview", aspect_ratio="1:1", n=1, image_context=None):
    """
    Generate an image using the OpenAI-compatible chat completions API.
    """
    try:
        content = [{"type": "text", "text": prompt}]
        if image_context:
            for img_data in image_context:
                img_b64 = base64.b64encode(img_data).decode('utf-8')
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}})

        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            modalities=["image"]
        )

        if response and response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            # Expect message.images[0].image_url.url to be a data URL
            if hasattr(message, 'images') and message.images:
                base64_string = message.images[0].get("image_url", {}).get("url", "")
                if base64_string:
                    encoded = base64_string.split(',', 1)[1] if ',' in base64_string else base64_string
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


def generate_video_api_call(
    prompt,
    model='veo-3.1-generate-preview',   # Veo 3.1 enables referenceImages + first/last frame
    negative_prompt='blurry, low quality',
    aspect_ratio='16:9',
    resolution='720p',
    duration_seconds=8,
    person_generation='allow_all',
    reference_images=None,              # list[bytes] (max 3)
    first_frame_image_data=None,        # bytes
    last_frame_image_data=None,         # bytes
):
    """
    Start Veo 3.1 generation with optional reference images and first/last frame.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")
    if not prompt and not first_frame_image_data and not reference_images:
        raise ValueError("Provide at least a prompt or some images (reference/first frame).")

    step1_url = f'{API_BASE}/gemini/v1beta/models/{model}:predictLongRunning'

    # ---- instances[0] ----
    instance = {'prompt': prompt or ""}

    # first frame goes on the instance as 'image'
    if first_frame_image_data:
        instance['image'] = {'bytesBase64Encoded': _b64(first_frame_image_data)}

    # ---- parameters ----
    parameters = {
        'aspectRatio': aspect_ratio,            # "16:9" or "9:16" etc.
        'resolution': resolution,               # "720p" or "1080p" (1080p allowed only at 8s)
        'durationSeconds': str(duration_seconds),
        'negativePrompt': negative_prompt or "",
        'personGeneration': person_generation,  # mode-dependent; we pass through
    }

    # last frame for interpolation
    if last_frame_image_data:
        parameters['lastFrame'] = {'image': {'bytesBase64Encoded': _b64(last_frame_image_data)}}

    # up to 3 reference images
    if reference_images:
        parameters['referenceImages'] = [
            {'image': {'bytesBase64Encoded': _b64(b)}} for b in reference_images[:3]
        ]

    step1_payload = {
        'instances': [instance],
        'parameters': parameters
    }

    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': GEMINI_API_KEY
    }

    response1 = requests.post(step1_url, json=step1_payload, headers=headers)
    if response1.status_code != 200:
        raise RuntimeError(f"Video start failed: {response1.status_code} - {response1.text}")

    operation_name = response1.json().get('name')
    if not operation_name:
        raise ValueError('No operation name returned from video generation start.')

    # ---- Poll for completion ----
    max_attempts = 90  # 90 * 5s = 7.5 min
    for _ in range(max_attempts):
        step2_url = f'{API_BASE}/gemini/v1beta/{operation_name}'
        r = requests.get(step2_url, headers=headers)
        if r.status_code != 200:
            raise RuntimeError(f"Polling failed: {r.status_code} - {r.text}")
        result = r.json()

        if result.get('done'):
            try:
                # response.generatedVideos[0].video.uri
                gv = result['response']['generatedVideos'][0]
                video_uri = gv['video']['uri']
                video_id = video_uri.split('/files/')[1].split(':')[0]
                return {"video_id": video_id, "video_uri": video_uri}
            except Exception as e:
                raise ValueError(f"Unexpected completion payload: {e}\n{json.dumps(result, indent=2)}")
        time.sleep(5)

    raise TimeoutError('Video generation timeout.')


def download_video_api_call(video_id):
    """
    Downloads a video given its video_id. Returns raw bytes.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")

    download_url = f'{API_BASE}/gemini/download/v1beta/files/{video_id}:download?alt=media'
    headers = {'x-goog-api-key': GEMINI_API_KEY}
    response = requests.get(download_url, headers=headers, stream=True)
    response.raise_for_status()
    return response.content


def generate_video(
    prompt,
    model='veo-3.1-generate-preview',
    aspect_ratio='16:9',
    duration=8,
    negative_prompt='blurry, low quality',
    person_generation='allow_all',
    reference_images=None,              # list[bytes]
    first_frame_image_data=None,        # bytes
    last_frame_image_data=None,         # bytes
):
    """
    Orchestrates Veo 3.1 start + download.
    """
    try:
        # Resolution heuristic
        if duration == 8 and aspect_ratio == "16:9":
            resolution_to_use = "1080p"  # allowed at 8s
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
                "aspect_ratio": aspect_ratio,
                "duration": duration,
                "negative_prompt": negative_prompt,
                "reference_images": bool(reference_images),
                "first_frame_present": bool(first_frame_image_data),
                "last_frame_present": bool(last_frame_image_data),
            }
        else:
            return {"success": False, "error": "Unknown error starting generation."}
    except Exception as e:
        return {"success": False, "error": str(e)}
