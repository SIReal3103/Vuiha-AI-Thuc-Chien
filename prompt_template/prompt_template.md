# Tài liệu tham khảo API

## Cấu hình Client OpenAI

Dưới đây là ví dụ về cách cấu hình và sử dụng client OpenAI với URL tùy chỉnh:

```python
from openai import OpenAI

# --- Cấu hình ---
# Thay <your_api_key> bằng API key của bạn
client = OpenAI(
  api_key="<your_api_key>",
  base_url="https://api.thucchien.ai"
)

# --- Thực thi ---
response = client.chat.completions.create(
  model="gemini-2.5-pro", # Chọn model bạn muốn
  messages=[
      {
          "role": "user",
          "content": "Explain the concept of API gateway in simple terms."
      }
  ]
)

print(response.choices[0].message.content)
```

### Tham số

- `api_key`: API key của bạn (thay `<your_api_key>` bằng key thực tế của bạn)
- `base_url`: URL cơ sở cho endpoint API (`https://api.thucchien.ai`)
- `model`: Model để sử dụng cho việc hoàn thành (ví dụ: `gemini-2.5-pro`)
- `messages`: Mảng các đối tượng tin nhắn với các trường `role` và `content`

### Lưu ý sử dụng

1. Thay `<your_api_key>` bằng API key thực tế của bạn
2. URL cơ sở trỏ đến endpoint API tùy chỉnh tại `https://api.thucchien.ai`
3. Model `gemini-2.5-pro` được chỉ định, nhưng bạn có thể sử dụng các model có sẵn khác
4. Phản hồi được truy cập thông qua `response.choices[0].message.content`

## Tạo hình ảnh

### Phương pháp 1: Sử dụng thư viện Requests

```python
import requests
import json
import base64

# --- Cấu hình ---
AI_API_BASE = "https://api.thucchien.ai/v1"
AI_API_KEY = "<your_api_key>"

# --- Gọi API để tạo hình ảnh ---
url = f"{AI_API_BASE}/images/generations"
headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {AI_API_KEY}"
}
data = {
  "model": "imagen-4",
  "prompt": "A majestic white tiger walking through a snowy forest",
  "n": 2, # Yêu cầu 2 ảnh
}

try:
  response = requests.post(url, headers=headers, data=json.dumps(data))
  response.raise_for_status()

  result = response.json()
  
  # --- Xử lý và lưu từng ảnh ---
  for i, image_obj in enumerate(result['data']):
      b64_data = image_obj['b64_json']
      image_data = base64.b64decode(b64_data)
      
      save_path = f"generated_image_{i+1}.png"
      with open(save_path, 'wb') as f:
          f.write(image_data)
      print(f"Image saved to {save_path}")

except requests.exceptions.RequestException as e:
  print(f"An error occurred: {e}")
  print(f"Response body: {response.text if 'response' in locals() else 'No response'}")
```

### Phương pháp 2: Sử dụng Client OpenAI

```python
from openai import OpenAI
import base64

# --- Cấu hình ---
AI_API_BASE = "https://api.thucchien.ai/v1"
AI_API_KEY = "<your_api_key>" # Thay bằng API key của bạn
IMAGE_SAVE_PATH = "generated_chat_image.png"

# --- Khởi tạo client ---
client = OpenAI(
  api_key=AI_API_KEY,
  base_url=AI_API_BASE,
)

# --- Bước 1: Gọi API để tạo hình ảnh ---
try:
  response = client.chat.completions.create(
      model="gemini-2.5-flash-image-preview",
      messages=[
          {
              "role": "user",
              "content": "A detailed illustration of a vintage steam train crossing a mountain bridge. High resolution, photorealistic, 8k"
          }
      ],
      modalities=["image"]  # Chỉ định trả về dữ liệu ảnh
  )

  # Trích xuất dữ liệu ảnh base64
  base64_string = response.choices[0].message.images[0].get('image_url').get("url")
  print("Image data received successfully.")

  # --- Bước 2: Giải mã và lưu hình ảnh ---
  if ',' in base64_string:
      header, encoded = base64_string.split(',', 1)
  else:
      encoded = base64_string

  image_data = base64.b64decode(encoded)

  with open(IMAGE_SAVE_PATH, 'wb') as f:
      f.write(image_data)
      
  print(f"Image saved to {IMAGE_SAVE_PATH}")

except Exception as e:
  print(f"An error occurred: {e}")
```

## Tạo video

### Bước 1: Bắt đầu tạo video

Gửi yêu cầu POST đến endpoint dành riêng cho Veo.

**Quan trọng:** Do máy chủ proxy sử dụng cơ chế pass-through tới Google AI Studio, bạn sẽ sử dụng header `x-goog-api-key` thay cho header `Authorization` tiêu chuẩn.

```bash
curl -X POST https://api.thucchien.ai/gemini/v1beta/models/veo-3.0-generate-preview:predictLongRunning \
-H "Content-Type: application/json" \
-H "x-goog-api-key: <your_api_key>" \
-d '{
  "instances": [{
    "prompt": "A cinematic shot of a hummingbird flying in slow motion"
  }]
}'
```

Nếu thành công, API sẽ trả về JSON chứa `name` của tác vụ. Lưu lại giá trị này.

```json
{
"name": "models/veo-3.0-generate-preview/operations/idrk08ltkg0a"
}
```

Trong đó:
- `operation_name`: là toàn bộ chuỗi `models/veo-3.0-generate-preview/operations/idrk08ltkg0a`
- `operation_id`: là phần định danh duy nhất của tác vụ, trong ví dụ này là `idrk08ltkg0a`. Bạn sẽ sử dụng ID này ở bước tiếp theo.

### Bước 2: Kiểm tra trạng thái

Sử dụng `operation_id` (ví dụ: `idrk08ltkg0a`) bạn nhận được ở Bước 1 để xây dựng URL và gửi yêu cầu GET để kiểm tra trạng thái.

```bash
curl https://api.thucchien.ai/gemini/v1beta/models/veo-3.0-generate-preview/operations/<operation_id> \
-H "x-goog-api-key: <your_api_key>"
```

Lặp lại yêu cầu này cho đến khi phản hồi chứa `"done": true`.

```json
{
  "name": "models/veo-3.0-generate-preview/operations/idrk08ltkg0a",
  "done": true,
  "response": {
      "@type": "type.googleapis.com/google.ai.generativelanguage.v1beta.PredictLongRunningResponse",
      "generateVideoResponse": {
          "generatedSamples": [
              {
                  "video": {
                      "uri": "https://generativelanguage.googleapis.com/v1beta/files/3j6svp4106e7:download?alt=media"
                  }
              }
          ]
      }
  }
}
```

Khi tác vụ hoàn tất (`"done": true`), phản hồi sẽ chứa trường `uri`. Từ URI này, chúng ta có thể trích xuất `video_id`, trong trường hợp này là `3j6svp4106e7`. ID này được dùng để tải video ở bước cuối cùng.

### Bước 3: Tải video

Sử dụng `video_id` (ví dụ: `3j6svp4106e7`) đã trích xuất ở Bước 2 để tạo URL tải xuống cuối cùng thông qua proxy.

```bash
# URI gốc từ Google: https://generativelanguage.googleapis.com/v1beta/files/3j6svp4106e7:download?alt=media
# Đường dẫn tương đối cần dùng: v1beta/files/3j6svp4106e7:download?alt=media
# URL tải xuống qua proxy: https://api.thucchien.ai/gemini/download/v1beta/files/3j6svp4106e7:download?alt=media

curl https://api.thucchien.ai/gemini/download/v1beta/files/<video_id>:download?alt=media \
-H "x-goog-api-key: <your_api_key>" \
--output my_generated_video.mp4
```

## Chuyển văn bản thành giọng nói (Text-to-Speech)

Các mô hình Text-to-Speech (TTS) cho phép bạn chuyển đổi văn bản thành file âm thanh có giọng nói tự nhiên.

### Các mô hình được hỗ trợ

- `gemini-2.5-flash-preview-tts` (Google Gemini)
- `gemini-2.5-pro-preview-tts` (Google Gemini)

### Endpoint

`POST /audio/speech`

### Phương pháp 1: Sử dụng curl

```bash
curl https://api.thucchien.ai/audio/speech \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <your_api_key>" \
-d '{
  "model": "gemini-2.5-flash-preview-tts",
  "input": "Xin chào, đây là một thử nghiệm chuyển văn bản thành giọng nói qua [AI Thực Chiến](https://thucchien.ai) gateway.",
  "voice": "Zephyr"
}' \
--output speech_output.mp3
```

### Phương pháp 2: Sử dụng Python (requests)

```python
import requests
import json

# --- Cấu hình ---
AI_API_BASE = "https://api.thucchien.ai"
AI_API_KEY = "<your_api_key>"

# --- Gọi API TTS ---
url = f"{AI_API_BASE}/audio/speech"
headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {AI_API_KEY}"
}
data = {
  "model": "gemini-2.5-flash-preview-tts",
  "input": "Xin chào, đây là một thử nghiệm chuyển văn bản thành giọng nói qua AI Thực Chiến gateway.",
  "voice": "Zephyr"
}

try:
  response = requests.post(url, headers=headers, data=json.dumps(data))
  response.raise_for_status()
  
  # Lưu file âm thanh
  with open("speech_output.mp3", "wb") as f:
      f.write(response.content)
  print("Audio file saved as speech_output.mp3")

except requests.exceptions.RequestException as e:
  print(f"An error occurred: {e}")
```

### Phương pháp 3: Sử dụng Python (OpenAI)

```python
from openai import OpenAI

# --- Cấu hình ---
client = OpenAI(
  api_key="<your_api_key>",
  base_url="https://api.thucchien.ai"
)

# --- Gọi API TTS ---
try:
  response = client.audio.speech.create(
    model="gemini-2.5-flash-preview-tts",
    voice="Zephyr",
    input="Xin chào, đây là một thử nghiệm chuyển văn bản thành giọng nói qua AI Thực Chiến gateway."
  )
  
  # Lưu file âm thanh
  response.stream_to_file("speech_output.mp3")
  print("Audio file saved as speech_output.mp3")

except Exception as e:
  print(f"An error occurred: {e}")
```

### Tham số

- `model`: Mô hình TTS để sử dụng (ví dụ: `gemini-2.5-flash-preview-tts`)
- `input`: Văn bản cần chuyển thành giọng nói
- `voice`: Giọng nói để sử dụng cho tổng hợp (ví dụ: `Zephyr`)

### Lưu ý sử dụng

1. Thay `<your_api_key>` bằng API key thực tế của bạn
2. Đầu ra sẽ được lưu dưới dạng file MP3
3. Các giọng nói được hỗ trợ có thể khác nhau tùy thuộc vào mô hình
4. Văn bản đầu vào có thể bao gồm định dạng markdown sẽ được xử lý đúng cách