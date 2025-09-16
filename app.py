from flask import Flask, render_template, request, jsonify
import requests
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

        soup = BeautifulSoup(html_content, 'html.parser')
        
        # (Logic trích xuất tiêu đề và nội dung giữ nguyên)
        title, content = None, None
        title_selectors = ['h1.title', 'h1.detail-title', 'h1', '.entry-title', 'title']
        for selector in title_selectors:
            if title_element := soup.select_one(selector):
                if len(title_element.get_text(strip=True)) > 10:
                    title = title_element.get_text(strip=True)
                    break
        
        # Các logic tìm content có thể thêm vào đây
        # Ưu tiên meta description
        if meta_desc := soup.find('meta', attrs={'name': 'description'}):
            if len(meta_desc.get('content', '')) > 50:
                content = meta_desc.get('content', '').strip()

        # Nếu không có, tìm trong các thẻ <p>
        if not content:
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 80 and 'login' not in text.lower() and 'đăng nhập' not in text.lower():
                    content = text
                    break
        
        # Nếu content < 80 từ, lấy thêm đoạn văn kế tiếp (tất cả trang đều áp dụng)
        if content and len(content.split()) < 80:
            print(f"Selenium: Content has {len(content.split())} words, adding more paragraphs...")
            all_paragraphs = soup.find_all('p')
            for p in all_paragraphs:
                text = p.get_text(strip=True)
                if (len(text) > 30 and 
                    'login' not in text.lower() and 
                    'đăng nhập' not in text.lower() and
                    'nguồn:' not in text.lower() and
                    'ảnh:' not in text.lower() and
                    'photo:' not in text.lower() and
                    'image:' not in text.lower() and
                    text not in content):
                    content += " " + text
                    print(f"Selenium: Combined content now has {len(content.split())} words")
                    if len(content.split()) >= 80:
                        print("✅ Selenium: Content combined successfully to meet 80-word minimum.")
                        break
        
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
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Logic trích xuất tương tự Selenium
        title, content = None, None
        
        # Xử lý đặc biệt cho các trang cụ thể
        if 'vietnamnet.vn' in url:
            print("🔍 Applying specific logic for vietnamnet.vn")
            if sapo := soup.select_one('h2.content-detail-sapo, [class*="sapo"]'):
                sapo_text = sapo.get_text(strip=True)
                if len(sapo_text) > 30 and not sapo_text.endswith('...'):
                    content = sapo_text
                    print(f"✅ VietnamNet sapo extracted: {len(sapo_text.split())} words")
        elif 'tienphong.vn' in url:
            print("🔍 Applying specific logic for tienphong.vn")
            if sapo := soup.select_one('div.sapo p, .article-sapo'):
                sapo_text = sapo.get_text(strip=True)
                if len(sapo_text) > 30:
                    content = sapo_text
                    print(f"✅ TienPhong sapo extracted: {len(sapo_text.split())} words")
        elif 'baotintuc.vn' in url:
            print("🔍 Applying specific logic for baotintuc.vn")
            if sapo := soup.select_one('h2.sapo, [class="sapo"]'):
                sapo_text = sapo.get_text(strip=True)
                if len(sapo_text) > 50:
                    content = sapo_text
                    print(f"✅ BaoTinTuc sapo extracted: {len(sapo_text.split())} words")

        # Logic chung
        title_selectors = ['h1.title', 'h1.detail-title', 'h1', '.entry-title', 'title']
        for selector in title_selectors:
            if title_element := soup.select_one(selector):
                if len(title_element.get_text(strip=True)) > 10:
                    title = title_element.get_text(strip=True)
                    break
        
        if not content:
            if meta_desc := soup.find('meta', attrs={'name': 'description'}):
                if len(meta_desc.get('content', '')) > 50:
                    content = meta_desc.get('content', '').strip()

        if not content:
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 80 and 'login' not in text.lower() and 'đăng nhập' not in text.lower():
                    content = text
                    break
        
        # Nếu content < 80 từ, lấy thêm đoạn văn kế tiếp (tất cả trang đều áp dụng)
        if content and len(content.split()) < 80:
            print(f"Requests: Content has {len(content.split())} words, adding more paragraphs...")
            all_paragraphs = soup.find_all('p')
            for p in all_paragraphs:
                text = p.get_text(strip=True)
                if (len(text) > 30 and 
                    'login' not in text.lower() and 
                    'đăng nhập' not in text.lower() and
                    'nguồn:' not in text.lower() and
                    'ảnh:' not in text.lower() and
                    'photo:' not in text.lower() and
                    'image:' not in text.lower() and
                    text not in content):
                    content += " " + text
                    print(f"Requests: Combined content now has {len(content.split())} words")
                    if len(content.split()) >= 80:
                        print("✅ Content combined successfully to meet 80-word minimum.")
                        break
        
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
    results = []
    for url in urls:
        full_url = url if url.startswith(('http://', 'https://')) else 'https://' + url
        result = extract_title_and_content(full_url)
        result['url'] = full_url
        results.append(result)
        
    return jsonify({'results': results})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
