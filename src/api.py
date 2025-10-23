# src/api.py
import os
import time
import requests
import json
from dotenv import load_dotenv
import litellm

load_dotenv()

API_BASE = os.getenv("THUCCHIEN_API_BASE", "https://api.thucchien.ai")
API_KEY = os.getenv("THUCCHIEN_API_KEY")
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') # New API key for video generation
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
DEFAULT_TEMP = float(os.getenv("TEMPERATURE", "1.0"))

# set the API base ON the client
litellm.api_base = API_BASE


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


def generate_video_api_call(prompt, model='veo-3.0-generate-001', negative_prompt='blurry, low quality',
                            aspect_ratio='16:9', resolution='700p', person_generation='allow_all'):
    """
    Calls the ThucChien AI video generation API.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")
    if not prompt:
        raise ValueError("Prompt is required for video generation.")

    # Step 1: Start video generation
    step1_url = f'{API_BASE}/gemini/v1beta/models/{model}:predictLongRunning'

    instance = {'prompt': prompt}

    step1_payload = {
        'instances': [instance],
        'parameters': {
            'negativePrompt': negative_prompt,
            'aspectRatio': aspect_ratio,
            'resolution': resolution,
            'personGeneration': person_generation
        }
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
                video_uri = result['response']['generateVideoResponse']['generatedSamples'][0]['video']['uri']
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
    Downloads a video given its video_id.
    Returns the content of the video.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")

    download_url = f'{API_BASE}/gemini/download/v1beta/files/{video_id}:download?alt=media'
    headers = {
        'x-goog-api-key': GEMINI_API_KEY
    }
    response = requests.get(download_url, headers=headers, stream=True)
    response.raise_for_status()
    return response.content
