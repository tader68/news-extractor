from flask import Flask, render_template, request, jsonify
import requests
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import urllib3
import ssl
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import google.generativeai as genai

# Tắt cảnh báo SSL không an toàn
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# --- Cấu hình Gemini API ---
try:
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini API configured successfully.")
    else:
        model = None
        print("⚠️ GEMINI_API_KEY not set. Gemini fallback will be disabled.")
except Exception as e:
    model = None
    print(f"❌ Error configuring Gemini API: {e}")


def parse_html_content(html_content, url):
    """
    Tách logic trích xuất tiêu đề và nội dung từ HTML.
    """
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        
        # --- Trích xuất tiêu đề ---
        title = None
        
        # Xử lý riêng cho tienphong.vn
        if 'tienphong.vn' in url:
            title_element = soup.find('h1', class_='detail-title')
            if title_element:
                title = title_element.get_text(strip=True)
        
        # Fallback cho các trang khác
        if not title:
            title_selectors = [
                'h1.detail-title',
                'h1.article-title',
                'h1.title',
                'h1.post-title',
                'h1[class*="title"]',
                'h1'
            ]
            
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    title = title_element.get_text(strip=True)
                    break
        
        # --- Trích xuất nội dung ---
        content = ""
        
        # Xử lý riêng cho vietnamnet.vn
        if 'vietnamnet.vn' in url:
            sapo_element = soup.find('h2', class_='content-detail-sapo')
            if sapo_element:
                sapo_text = sapo_element.get_text(strip=True)
                if not sapo_text.endswith('...'):
                    content = sapo_text
        
        # Xử lý riêng cho baotintuc.vn
        elif 'baotintuc.vn' in url:
            sapo_element = soup.find('h2', class_='sapo')
            if sapo_element:
                content = sapo_element.get_text(strip=True)
        
        # Xử lý riêng cho tienphong.vn
        elif 'tienphong.vn' in url:
            sapo_element = soup.find('h2', class_='sapo')
            if sapo_element:
                content = sapo_element.get_text(strip=True)
        
        # Nếu chưa có content hoặc chưa đủ 80 từ, tìm thêm
        if not content or len(content.split()) < 80:
            content_selectors = [
                'div.detail-content p',
                'div.article-content p',
                'div.content p',
                'div.post-content p',
                'div[class*="content"] p',
                'p'
            ]
            
            paragraphs = []
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    for p in elements:
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            paragraphs.append(text)
                    break
            
            # Kết hợp với content hiện tại nếu có
            if content:
                all_content = [content] + paragraphs
            else:
                all_content = paragraphs
            
            # Kết hợp cho đến khi đạt 80 từ
            combined_content = ""
            for paragraph in all_content:
                if len((combined_content + " " + paragraph).split()) <= 200:  # Giới hạn tối đa
                    combined_content += " " + paragraph if combined_content else paragraph
                    if len(combined_content.split()) >= 80:
                        break
            
            content = combined_content.strip()
        
        # Làm sạch content
        if content:
            content = content.replace('...', '').strip()
        
        return title, content
        
    except Exception as e:
        print(f"❌ Error parsing HTML: {e}")
        return None, ""


def extract_with_selenium(url):
    """
    Sử dụng Selenium để trích xuất nội dung (Phiên bản ổn định cho Cloud).
    """
    print(f"🚀 Attempting Selenium extraction for: {url}")
    
    # --- Cấu hình Chrome Options Tối ưu cho Cloud ---
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    # QUAN TRỌNG: Không chỉ định --user-data-dir, để Selenium tự quản lý profile tạm.
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(15) # Tăng thời gian chờ ngầm
        
        print(f"✅ Driver created. Navigating to URL...")
        driver.get(url)
        time.sleep(3)
        
        html_content = driver.page_source
        if not html_content or len(html_content) < 500: # Kiểm tra nội dung có hợp lệ không
             raise ValueError("Page source is too short or empty.")

        # Sử dụng parse_html_content function để trích xuất
        title, content = parse_html_content(html_content, url)
        
        if title and content:
            print("✅ Selenium extraction successful!")
            return {"title": title, "content": content, "success": True}
        
        print("⚠️ Selenium did not find enough content.")
        return {"title": title or "Không tìm thấy tiêu đề", "content": "Không tìm thấy nội dung", "success": False}

    except Exception as e:
        print(f"❌ Selenium Error: {str(e)}")
        return {"title": "Lỗi Selenium", "content": f"Không thể sử dụng Selenium: {str(e)}", "success": False}
    finally:
        if driver:
            driver.quit()
            print("✅ Chrome driver closed.")


def extract_with_gemini(url):
    """
    Sử dụng Gemini API làm phương án dự phòng cuối cùng.
    """
    if not model:
        return {"title": "Lỗi Gemini", "content": "Gemini API chưa được cấu hình.", "success": False}
        
    print(f"🔄 Falling back to Gemini API for: {url}")
    try:
        prompt = f"""
        Truy cập URL sau và trích xuất thông tin: {url}
        Hãy thực hiện các yêu cầu sau:
        1.  Trích xuất TIÊU ĐỀ CHÍNH của bài báo.
        2.  Trích xuất ĐOẠN VĂN ĐẦU TIÊN (sapo hoặc đoạn mở đầu) của bài báo. Đảm bảo nội dung đầy đủ, không bị cắt ngắn.
        
        Chỉ trả lời với định dạng JSON sau, không thêm bất cứ giải thích nào:
        {{
          "title": "tiêu đề bài báo ở đây",
          "content": "đoạn văn đầu tiên ở đây"
        }}
        """
        response = model.generate_content(prompt)
        
        # Xử lý response để lấy JSON
        import json
        clean_response = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_response)
        
        if data.get("title") and data.get("content"):
            print("✅ Gemini extraction successful!")
            data["success"] = True
            return data
        else:
            raise ValueError("Invalid JSON structure from Gemini.")
            
    except Exception as e:
        print(f"❌ Gemini API Error: {str(e)}")
        return {"title": "Lỗi Gemini API", "content": f"Không thể xử lý URL bằng Gemini: {str(e)}", "success": False}


def extract_title_and_content(url):
    """
    Hàm chính điều phối việc trích xuất, thử các phương pháp khác nhau.
    """
    print(f"\nProcessing URL: {url}")
    
    # --- PHƯƠNG PHÁP 1: Dùng Requests (Nhanh nhất) ---
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        
        # Sử dụng parse_html_content function để trích xuất
        title, content = parse_html_content(response.content.decode('utf-8'), url)
        
        if title and content:
            print("✅ Requests extraction successful!")
            return build_success_response(title, content)

    except requests.RequestException as e:
        print(f"⚠️ Requests failed: {e}. Trying Selenium.")

    # --- PHƯƠNG PHÁP 2: Dùng Selenium (Fallback) ---
    selenium_result = extract_with_selenium(url)
    if selenium_result['success']:
        return build_success_response(selenium_result['title'], selenium_result['content'])

    # --- PHƯƠNG PHÁP 3: Dùng Gemini (Fallback cuối cùng) ---
    gemini_result = extract_with_gemini(url)
    if gemini_result['success']:
        return build_success_response(gemini_result['title'], gemini_result['content'])

    # Nếu tất cả đều thất bại
    print("❌ All extraction methods failed.")
    return build_error_response("Không thể trích xuất nội dung từ URL này sau nhiều lần thử.")


def build_success_response(title, content):
    """Tạo response thành công và tính toán số từ."""
    word_count = {
        'title_words': len(title.split()),
        'content_words': len(content.split()),
        'total_words': len(title.split()) + len(content.split()),
        'meets_minimum': (len(title.split()) + len(content.split())) >= 80
    }
    return {'title': title, 'content': content, 'word_count': word_count, 'success': True}


def build_error_response(message):
    """Tạo response lỗi."""
    return {'title': 'Lỗi', 'content': message, 'word_count': {'total_words': 0, 'meets_minimum': False}, 'success': False}


async def extract_title_and_content_async(session, url):
    """
    Async version với hệ thống fallback 3 tầng: aiohttp -> Selenium -> Gemini API
    """
    print(f"\n🔍 Starting async extraction for: {url}")
    
    # --- PHƯƠNG PHÁP 1: Dùng aiohttp (Nhanh nhất) ---
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        async with session.get(url, ssl=False, timeout=aiohttp.ClientTimeout(total=30), headers=headers) as response:
            html_content = await response.text()
            title, content = parse_html_content(html_content, url)
            
            if title and content:
                print("✅ Aiohttp extraction successful!")
                return build_success_response(title, content)

    except Exception as e:
        print(f"⚠️ Aiohttp failed: {e}. Trying Selenium.")

    # --- PHƯƠNG PHÁP 2: Dùng Selenium (Fallback) ---
    selenium_result = extract_with_selenium(url)
    if selenium_result['success']:
        return build_success_response(selenium_result['title'], selenium_result['content'])

    # --- PHƯƠNG PHÁP 3: Dùng Gemini (Fallback cuối cùng) ---
    gemini_result = extract_with_gemini(url)
    if gemini_result['success']:
        return build_success_response(gemini_result['title'], gemini_result['content'])

    # Nếu tất cả đều thất bại
    print("❌ All extraction methods failed.")
    return build_error_response("Không thể trích xuất nội dung từ URL này sau nhiều lần thử.")


async def batch_extract_async(urls):
    """
    Async batch processing với song song hoá hoàn toàn
    """
    print(f"🚀 Starting async batch extraction for {len(urls)} URLs")
    
    async with aiohttp.ClientSession() as session:
        # Tạo tasks cho tất cả URLs đồng thời
        tasks = [extract_title_and_content_async(session, url) for url in urls]
        
        # Chờ tất cả hoàn thành đồng thời
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Xử lý kết quả và exception
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = build_error_response(f"Lỗi xử lý: {str(result)}")
                error_result['url'] = urls[i]
                processed_results.append(error_result)
            else:
                result['url'] = urls[i]
                processed_results.append(result)
        
        return processed_results


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return {'status': 'healthy', 'service': 'news-extractor'}, 200

@app.route('/extract', methods=['POST'])
def extract():
    url = (request.get_json() or {}).get('url') or request.form.get('url', '')
    if not url:
        return jsonify(build_error_response('Vui lòng nhập URL hợp lệ.'))
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    result = extract_title_and_content(url)
    return jsonify(result)


@app.route('/batch_extract', methods=['POST'])
def batch_extract():
    urls_text = request.form.get('urls', '')
    if not urls_text:
        return jsonify({'results': [], 'error': 'Vui lòng nhập ít nhất một URL.'})
    
    urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
    full_urls = [url if url.startswith(('http://', 'https://')) else 'https://' + url for url in urls]
    
    # Sử dụng async batch processing
    results = asyncio.run(batch_extract_async(full_urls))
        
    return jsonify({'results': results})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
