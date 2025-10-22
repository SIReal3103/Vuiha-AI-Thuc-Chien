import os
import logging
import litellm
import requests
from bs4 import BeautifulSoup
import codecs

def unescape_unicode(s: str) -> str:
    # Chỉ decode khi có pattern \uXXXX để tránh “phá” chuỗi bình thường
    if "\\u" in s:
        try:
            return codecs.decode(s, "unicode_escape")
        except Exception:
            pass
    return s

# ======================
# Cấu hình Logging (UTF-8)
# ======================
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("national_day_analysis")
logger.setLevel(logging.INFO)
logger.handlers.clear()

# Ghi file UTF-8 (không lưu timestamp nếu bạn không muốn — ở đây tắt timestamp)
file_handler = logging.FileHandler(os.path.join(log_dir, "analysis.log"), encoding="utf-8")
file_formatter = logging.Formatter("%(message)s")  # chỉ ghi message (plain), không thời gian/mức log
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# (tùy chọn) in ra console cho dễ debug, vẫn UTF-8
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)

# ======================
# Cấu hình API
# ======================
litellm.api_base = "https://api.thucchien.ai"
API_KEY = "sk-TOcGVBs-iLLtm6mcRiw3fw"  # KHÔNG hardcode trên máy thật

def analyze_national_day_activities(query: str) -> str:
    """
    Gọi LLM để phân tích. Trả về CHUỖI kết quả thuần (plain text),
    không kèm thời gian/nguồn tham khảo.
    """
    try:
        resp = litellm.completion(
            custom_llm_provider="openai",   # ép dùng OpenAI-compatible, tránh Vertex
            model="gemini-2.5-flash",       # tên model phía thucchien.ai hỗ trợ
            api_key=API_KEY,
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý ảo chuyên tổng hợp và phân tích thông tin từ các nguồn tin tức."},
                {"role": "user", "content": query},
            ],
            # Tham số mở rộng đặt trong extra_body (nếu cần web search)
            extra_body={
                "web_search_options": {"search_context_size": "medium"}
            },
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Lỗi khi gọi LiteLLM: {e}"

def extract_images_from_url(url: str):
    """
    Trả về danh sách URL ảnh. Chỉ lọc theo từ khóa đơn giản trong src.
    Không ghi thời gian vào log.
    """
    image_urls = []
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/117.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for img_tag in soup.find_all("img"):
            src = img_tag.get("src")
            if not src:
                continue
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = requests.compat.urljoin(url, src)

            # Lọc nhanh theo từ khóa
            if any(k in (src or "").lower() for k in ["quoc_khanh", "bo_doi", "viet_nam", "ky_niem", "2_9"]):
                image_urls.append(src)
    except Exception as e:
        logger.info(f"Lỗi khi truy cập/phân tích {url}: {e}")
    return image_urls

if __name__ == "__main__":
    # 1) Phân tích (ghi ra log CHỈ nội dung tiếng Việt, không timestamp)
    query = "Tổng kết, phân tích các hoạt động chào mừng kỷ niệm 80 năm quốc khánh dịp 2/9/2025 trên cả nước."
    analysis = analyze_national_day_activities(query)
    analysis = unescape_unicode(analysis)

    logger.info("=== KẾT QUẢ PHÂN TÍCH ===")
    logger.info(analysis.strip())
    logger.info("")  # dòng trống

    # 2) Khai thác ảnh (ghi danh sách URL ảnh dạng plain)
    news_websites = [
        "https://dangcongsan.vn/",
        "https://baochinhphu.vn/",
        "https://vtv.vn/",
    ]
    logger.info("=== ẢNH TRÍCH XUẤT ===")
    for site in news_websites:
        imgs = extract_images_from_url(site)
        logger.info(f"Từ {site}:")
        if imgs:
            for u in imgs:
                logger.info(f"- {u}")
        else:
            logger.info("- Không tìm thấy hình ảnh liên quan hoặc có lỗi khi truy cập.")
        logger.info("")  # dòng trống

    # 3) Gợi ý cuối (plain)
    logger.info("Lưu ý: đặt API key qua biến môi trường THUCCHIEN_API_KEY.")
    logger.info("Cài đặt: pip install litellm requests beautifulsoup4")
    logger.info("Chạy: python national_day_analysis.py")
