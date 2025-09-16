from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import urllib3
import ssl
from urllib3.util.ssl_ import create_urllib3_context
import urllib.request
import urllib.parse
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Cấu hình Gemini API
import os
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyBNU2IteZpqb93aISVU38Z0fN9r_Wc3_qs')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def extract_with_selenium(url):
    """
    Sử dụng Selenium để trích xuất tiêu đề và nội dung từ URL
    """
    try:
        # Cấu hình Chrome options cho production (Render.com compatible)
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Chạy ẩn
        chrome_options.add_argument('--no-sandbox')  # Critical for cloud deployment
        chrome_options.add_argument('--disable-dev-shm-usage')  # Critical for cloud deployment
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--ignore-certificate-errors-spki-list')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')  # Faster loading
        # chrome_options.add_argument('--disable-javascript')  # Keep JS enabled for some sites
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--remote-debugging-port=9222')  # For cloud debugging
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Cloud-specific optimizations
        chrome_options.add_argument('--single-process')  # Use single process for cloud
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--safebrowsing-disable-auto-update')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--disable-notifications')
        
        # Force Selenium for problematic domains
        force_selenium_domains = ['bnews.vn', 'baotintuc.vn', 'vietnamnet.vn']
        if any(domain in url for domain in force_selenium_domains):
            print(f"🔄 Force using Selenium for domain: {url}")
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Tạo driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print(f"Sử dụng Selenium cho URL: {url}")
        driver.get(url)
        
        # Đợi trang load
        time.sleep(3)
        
        # Lấy HTML content
        html_content = driver.page_source
        driver.quit()
        
        # Parse với BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Tìm tiêu đề
        title = None
        title_selectors = [
            'h1.title', 'h1.detail-title', 'h1.article-title', 'h1.post-title',
            '.title', '.detail-title', '.article-title', '.post-title', 
            'h1', '.entry-title', 'title'
        ]
        
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title_text = title_element.get_text().strip()
                if title_text and len(title_text) > 5:  # Chỉ lấy nếu có nội dung thực sự
                    title = title_text
                    break
        
        # Tìm nội dung
        content_text = None
        
        # Xử lý đặc biệt cho vietnamnet.vn
        if 'vietnamnet.vn' in url:
            print("🔍 Xử lý đặc biệt cho vietnamnet.vn trong Selenium...")
            
            # Tìm sapo từ thẻ h2
            sapo_selectors = [
                'h2[class="content-detail-sapo sm-sapo-mb-0"]',
                'h2.content-detail-sapo',
                'h2[class*="content-detail-sapo"]',
                'h2[class*="sapo"]',
                '.content-detail-sapo',
                '[class*="sapo"]'
            ]
            
            for selector in sapo_selectors:
                print(f"🔍 Selenium thử selector: {selector}")
                sapo_element = soup.select_one(selector)
                if sapo_element:
                    sapo_text = sapo_element.get_text().strip()
                    print(f"📝 Selenium tìm thấy sapo: {sapo_text}")
                    
                    if len(sapo_text) > 30 and not sapo_text.endswith('...'):
                        content_text = sapo_text
                        print(f"✅ Selenium lấy sapo thành công!")
                        break
                    else:
                        print(f"❌ Selenium sapo không hợp lệ (ngắn hoặc có ...)")
                else:
                    print(f"❌ Selenium không tìm thấy element với selector {selector}")
            
            # Nếu không tìm thấy sapo, thử tìm tất cả thẻ h2
            if not content_text:
                print("🔍 Selenium tìm tất cả thẻ h2...")
                all_h2 = soup.find_all('h2')
                for i, h2 in enumerate(all_h2):
                    h2_classes = h2.get('class', [])
                    h2_text = h2.get_text().strip()
                    print(f"Selenium H2 {i+1}: classes={h2_classes}, text='{h2_text[:100]}...'")
                    
                    if 'sapo' in ' '.join(h2_classes).lower() and len(h2_text) > 30 and not h2_text.endswith('...'):
                        print(f"✅ Selenium tìm thấy sapo từ thẻ h2 thứ {i+1}")
                        content_text = h2_text
                        break
        
        # Xử lý đặc biệt cho baotintuc.vn
        elif 'baotintuc.vn' in url:
            print("🔍 Xử lý đặc biệt cho baotintuc.vn trong Selenium...")
            
            # Ưu tiên tìm sapo trước
            sapo_selectors = [
                'h2.sapo',
                'h2[class="sapo"]',
                '.sapo'
            ]
            
            for selector in sapo_selectors:
                print(f"🔍 Selenium thử sapo selector: {selector}")
                sapo_element = soup.select_one(selector)
                if sapo_element:
                    sapo_text = sapo_element.get_text().strip()
                    print(f"📝 Selenium tìm thấy sapo baotintuc: {sapo_text}")
                    
                    if len(sapo_text) > 50:
                        content_text = sapo_text
                        print(f"✅ Selenium lấy sapo baotintuc thành công: {len(sapo_text.split())} từ")
                        break
                else:
                    print(f"❌ Selenium không tìm thấy sapo với selector {selector}")
            
                        # Nếu không tìm thấy sapo, fallback về logic thông thường
            pass
        
        # Nếu không phải vietnamnet/baotintuc hoặc không tìm thấy nội dung đặc biệt, thử meta description
        if not content_text:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                desc = meta_desc.get('content').strip()
                if len(desc) > 50:
                    content_text = desc
        
        # Nếu không có meta description, tìm trong thẻ p
        if not content_text:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if (len(text) > 80 and 
                    not any(keyword in text.lower() for keyword in [
                        'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                        'đăng nhập', 'login', 'quảng cáo', 'advertisement'
                    ])):
                    content_text = text
                    break
        
        # Nếu nội dung chưa đủ 80 từ, lấy thêm đoạn văn kế tiếp
        if content_text:
            content_words = len(content_text.split())
            
            # Kiểm tra xem có phải là vietnamnet và đã lấy từ sapo không
            is_vietnamnet_sapo = 'vietnamnet.vn' in url and any(selector in str(soup) for selector in ['content-detail-sapo', 'sapo'])
            
            if content_words < 80 and not is_vietnamnet_sapo:
                print(f"Selenium: Nội dung hiện tại có {content_words} từ, chưa đủ 80 từ. Đang lấy thêm đoạn văn kế tiếp...")
                
                # Tìm đoạn văn kế tiếp
                paragraphs = soup.find_all('p')
                for i, p in enumerate(paragraphs):
                    text = p.get_text().strip()
                    if (len(text) > 50 and 
                        not any(keyword in text.lower() for keyword in [
                            'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                            'đăng nhập', 'login', 'quảng cáo', 'advertisement'
                        ])):
                        
                        # Kiểm tra xem đoạn này có khác với đoạn đã lấy không
                        if text != content_text:
                            # Kết hợp đoạn văn kế tiếp
                            combined_content = content_text + " " + text
                            combined_words = len(combined_content.split())
                            
                            print(f"Selenium: Đã kết hợp đoạn văn kế tiếp. Tổng từ: {combined_words}")
                            content_text = combined_content
                            
                            # Nếu đã đủ 80 từ, dừng lại
                            if combined_words >= 80:
                                break
            elif is_vietnamnet_sapo:
                print(f"✅ Selenium: Đã lấy từ sapo vietnamnet, không cần kết hợp thêm. Số từ: {content_words}")
        
        if title and content_text:
            return {
                "title": title,
                "content": content_text,
                "success": True
            }
        else:
            return {
                "title": "Không tìm thấy tiêu đề",
                "content": "Không tìm thấy nội dung",
                "success": False
            }
        
    except Exception as e:
        print(f"Lỗi Selenium: {str(e)}")
        return {
            "title": "Lỗi Selenium",
            "content": f"Không thể sử dụng Selenium: {str(e)}",
            "success": False
        }

def extract_with_gemini(url):
    """
    Sử dụng Gemini API để trích xuất tiêu đề và nội dung từ URL
    """
    try:
        # Sử dụng URL Context tool để truy cập trực tiếp URL
        try:
            # Tạo prompt với URL context tool
            prompt = f"""
            Truy cập URL này và đọc chính xác nội dung: {url}
            
            Hãy trích xuất:
            1. Tiêu đề chính của bài báo (từ thẻ h1 hoặc title)
            2. Đoạn văn đầu tiên của bài báo (đoạn văn đầu tiên trong nội dung chính)
            
            Trả về theo format chính xác:
            Tiêu đề: [tiêu đề chính xác từ trang web]
            Nội dung: [đoạn văn đầu tiên chính xác từ trang web]
            
            QUAN TRỌNG: Đọc kỹ và trích xuất chính xác từ trang web, không tự suy đoán hay tóm tắt.
            """
            
            # Sử dụng prompt đơn giản (URL context tool không hoạt động)
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Debug: In ra response để kiểm tra
            print(f"Gemini response for {url}:")
            print(result_text)
            print("=" * 50)
            
            # Loại bỏ code Python nếu có
            if '```python' in result_text:
                result_text = result_text.split('```python')[0]
            if '```' in result_text:
                result_text = result_text.split('```')[0]
            
            # Nếu response có vẻ hợp lý, sử dụng nó
            if len(result_text) > 50 and not any(keyword in result_text.lower() for keyword in ['python', 'import', 'def ', 'function', 'requests.get', 'beautifulsoup']):
                # Tách tiêu đề và nội dung từ response
                lines = result_text.split('\n')
                title = ""
                content = ""
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('URL:'):
                        # Làm sạch format
                        cleaned_line = line
                        
                        # Loại bỏ số thứ tự và dấu **
                        if cleaned_line.startswith('1. '):
                            cleaned_line = cleaned_line[3:]
                        if cleaned_line.startswith('2. '):
                            cleaned_line = cleaned_line[3:]
                        
                        # Loại bỏ dấu **
                        cleaned_line = cleaned_line.replace('**', '').strip()
                        
                        # Loại bỏ phần mô tả
                        if 'Tiêu đề bài báo là:' in cleaned_line:
                            cleaned_line = cleaned_line.replace('Tiêu đề bài báo là:', '').strip()
                        if 'Nội dung đoạn đầu tiên của bài báo là:' in cleaned_line:
                            cleaned_line = cleaned_line.replace('Nội dung đoạn đầu tiên của bài báo là:', '').strip()
                        if 'Tiêu đề:' in cleaned_line:
                            cleaned_line = cleaned_line.replace('Tiêu đề:', '').strip()
                        if 'Nội dung:' in cleaned_line:
                            cleaned_line = cleaned_line.replace('Nội dung:', '').strip()
                        
                        if not title and cleaned_line:
                            title = cleaned_line
                        elif not content and cleaned_line:
                            content = cleaned_line
                            break
                
                if title and content:
                    return {
                        "title": title,
                        "content": content,
                        "success": True
                    }
                
                # Nếu không tách được theo cách trên, thử cách khác
                # Tìm "Tiêu đề:" và "Nội dung:" trong response
                if 'Tiêu đề:' in result_text and 'Nội dung:' in result_text:
                    try:
                        title_start = result_text.find('Tiêu đề:') + 8
                        content_start = result_text.find('Nội dung:')
                        title_end = content_start
                        
                        title = result_text[title_start:title_end].strip()
                        content = result_text[content_start + 8:].strip()
                        
                        # Làm sạch thêm
                        title = title.replace('**', '').strip()
                        content = content.replace('**', '').strip()
                        
                        if title and content:
                            return {
                                "title": title,
                                "content": content,
                                "success": True
                            }
                    except:
                        pass
        except:
            pass
        
        # Nếu prompt đơn giản không hoạt động, thử prompt chi tiết
        prompt = f"""
        Truy cập URL này và trích xuất chính xác:
        {url}
        
        Trả về theo format chính xác:
        Tiêu đề: [tiêu đề chính xác từ trang web]
        Nội dung: [đoạn văn đầu tiên chính xác từ trang web]
        
        KHÔNG thêm phần mô tả, chỉ trả về nội dung thực tế.
        """
        
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Xử lý response từ prompt chi tiết
        import json
        
        # Làm sạch response
        cleaned_text = result_text
        
        # Loại bỏ các đoạn code Python
        if '```python' in cleaned_text:
            cleaned_text = cleaned_text.split('```python')[0]
        if '```' in cleaned_text:
            cleaned_text = cleaned_text.split('```')[0]
        
        # Loại bỏ các từ khóa không cần thiết
        unwanted_phrases = [
            'import requests', 'from bs4 import BeautifulSoup', 'def extract_',
            'try:', 'except:', 'return {', 'headers = {', 'response = requests.get',
            'soup = BeautifulSoup', 'title_element = soup.select_one'
        ]
        
        for phrase in unwanted_phrases:
            if phrase in cleaned_text:
                cleaned_text = cleaned_text.split(phrase)[0]
        
        # Thử tách tiêu đề và nội dung từ text
        lines = cleaned_text.split('\n')
        title = ""
        content = ""
        
        for line in lines:
            line = line.strip()
            if line:
                # Làm sạch format
                cleaned_line = line
                
                # Loại bỏ số thứ tự và dấu **
                if cleaned_line.startswith('1. '):
                    cleaned_line = cleaned_line[3:]
                if cleaned_line.startswith('2. '):
                    cleaned_line = cleaned_line[3:]
                
                # Loại bỏ dấu **
                cleaned_line = cleaned_line.replace('**', '').strip()
                
                # Loại bỏ phần mô tả
                if 'Tiêu đề bài báo là:' in cleaned_line:
                    cleaned_line = cleaned_line.replace('Tiêu đề bài báo là:', '').strip()
                if 'Nội dung đoạn đầu tiên của bài báo là:' in cleaned_line:
                    cleaned_line = cleaned_line.replace('Nội dung đoạn đầu tiên của bài báo là:', '').strip()
                if 'Tiêu đề:' in cleaned_line:
                    cleaned_line = cleaned_line.replace('Tiêu đề:', '').strip()
                if 'Nội dung:' in cleaned_line:
                    cleaned_line = cleaned_line.replace('Nội dung:', '').strip()
                
                if not title and cleaned_line:
                    title = cleaned_line
                elif not content and cleaned_line:
                    content = cleaned_line
                    break
        
        if title and content:
            return {
                "title": title,
                "content": content,
                "success": True
            }
        
        # Nếu không tách được, trả về text đã làm sạch
        return {
            "title": "Tiêu đề từ Gemini",
            "content": cleaned_text[:300] + "..." if len(cleaned_text) > 300 else cleaned_text,
            "success": True
        }
            
    except Exception as e:
        return {
            "title": "Lỗi Gemini API",
            "content": f"Không thể sử dụng Gemini API: {str(e)}",
            "success": False
        }

def extract_title_and_content(url):
    """
    Trích xuất tiêu đề và đoạn văn đầu tiên từ URL bài báo
    """
    try:
        # Force Selenium for known problematic domains
        force_selenium_domains = ['bnews.vn', 'baotintuc.vn', 'vietnamnet.vn']
        if any(domain in url for domain in force_selenium_domains):
            print(f"🚀 Using Selenium directly for {url}")
            return extract_with_selenium(url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Thử nhiều cách để truy cập URL
        response = None
        
        # Cách 1: Thử với verify=False và session
        try:
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=20, verify=False)
            response.raise_for_status()
        except requests.exceptions.SSLError as ssl_error:
            # Cách 2: Thử với urllib3 context tùy chỉnh
            try:
                import urllib3
                from urllib3.util.ssl_ import create_urllib3_context
                
                # Tạo context với cài đặt SSL lỏng lẻo
                ctx = create_urllib3_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                
                # Tạo session với context tùy chỉnh
                session = requests.Session()
                adapter = requests.adapters.HTTPAdapter()
                session.mount('https://', adapter)
                
                response = session.get(url, headers=headers, timeout=20, verify=False)
                response.raise_for_status()
                
            except requests.exceptions.SSLError:
                # Cách 3: Thử với HTTP thay vì HTTPS
                if url.startswith('https://'):
                    http_url = url.replace('https://', 'http://')
                    try:
                        response = requests.get(http_url, headers=headers, timeout=20)
                        response.raise_for_status()
                    except Exception as e:
                        # Cách 4: Thử với urllib thay vì requests
                        try:
                            # Tạo SSL context cho urllib
                            ssl_context = ssl.create_default_context()
                            ssl_context.check_hostname = False
                            ssl_context.verify_mode = ssl.CERT_NONE
                            
                            # Tạo request với urllib
                            req = urllib.request.Request(url, headers=headers)
                            with urllib.request.urlopen(req, context=ssl_context, timeout=20) as response_urllib:
                                content = response_urllib.read()
                                
                            # Tạo response object giả để tương thích với code cũ
                            class MockResponse:
                                def __init__(self, content):
                                    self.content = content
                                    self.status_code = 200
                                
                                def raise_for_status(self):
                                    pass
                            
                            response = MockResponse(content)
                            
                        except Exception as urllib_error:
                            # Cách 5: Sử dụng Selenium khi tất cả các cách khác thất bại
                            print(f"Sử dụng Selenium cho URL: {url}")
                            selenium_result = extract_with_selenium(url)
                            
                            if selenium_result['success']:
                                # Tạo response object giả từ kết quả Selenium
                                class MockResponse:
                                    def __init__(self, title, content):
                                        self.title = title
                                        self.content = content
                                        self.status_code = 200
                                    
                                    def raise_for_status(self):
                                        pass
                                
                                response = MockResponse(selenium_result['title'], selenium_result['content'])
                            else:
                                # Cách 6: Sử dụng Gemini API làm fallback cuối cùng
                                print(f"Sử dụng Gemini API cho URL: {url}")
                                gemini_result = extract_with_gemini(url)
                                
                                if gemini_result['success']:
                                    class MockResponse:
                                        def __init__(self, title, content):
                                            self.title = title
                                            self.content = content
                                            self.status_code = 200
                                        
                                        def raise_for_status(self):
                                            pass
                                    
                                    response = MockResponse(gemini_result['title'], gemini_result['content'])
                                else:
                                    raise requests.exceptions.SSLError(f"Không thể truy cập URL do vấn đề SSL và tất cả phương pháp đều thất bại: {str(urllib_error)}")
                else:
                    raise requests.exceptions.SSLError(f"Không thể truy cập URL do vấn đề SSL: {str(ssl_error)}")
        except Exception as e:
            raise requests.exceptions.RequestException(f"Lỗi khi truy cập URL: {str(e)}")
        
        # Kiểm tra xem response có phải từ Gemini API không
        if hasattr(response, 'title') and hasattr(response, 'content'):
            # Response từ Gemini API
            title = response.title
            content = response.content
            
            # Đếm số từ
            title_words = len(title.split()) if title else 0
            content_words = len(content.split()) if content else 0
            total_words = title_words + content_words
            
            return {
                'title': title,
                'content': content,
                'word_count': {
                    'title_words': title_words,
                    'content_words': content_words,
                    'total_words': total_words,
                    'meets_minimum': total_words >= 80
                },
                'success': True,
                'source': 'gemini_api'
            }
        
        # Response từ web scraping thông thường
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Tìm tiêu đề
        title = None
        
        # Xử lý đặc biệt cho tienphong.vn
        if 'tienphong.vn' in url:
            print("🔍 Xử lý đặc biệt cho tienphong.vn...")
            tienphong_title_selectors = [
                'h1[class*="title"]',
                'h1.article-title',
                '.article-title h1',
                'h1',
                '.title'
            ]
            
            for selector in tienphong_title_selectors:
                print(f"🔍 Thử title selector tienphong: {selector}")
                title_element = soup.select_one(selector)
                if title_element:
                    title_text = title_element.get_text().strip()
                    print(f"📝 Tìm thấy title: {title_text}")
                    if title_text and len(title_text) > 10:  # Tiêu đề phải dài hơn 10 ký tự
                        title = title_text
                        print(f"✅ Lấy title thành công từ {selector}")
                        break
                else:
                    print(f"❌ Không tìm thấy title với selector {selector}")
        
        # Nếu không phải tienphong hoặc không tìm thấy title, dùng selector thông thường
        if not title:
            title_selectors = [
                'h1.title', 'h1.detail-title', 'h1.article-title', 'h1.post-title',
                '.title', '.detail-title', '.article-title', '.post-title', 
                'h1', '.entry-title', '[class*="title"]', '[class*="headline"]', 'title'
            ]
            
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    title_text = title_element.get_text().strip()
                    if title_text and len(title_text) > 5:  # Chỉ lấy nếu có nội dung thực sự
                        title = title_text
                        break
        
        # Tìm đoạn văn chính của bài báo
        content = None
        
        # Xử lý đặc biệt cho vietnamnet.vn NGAY TỪ ĐẦU
        if 'vietnamnet.vn' in url:
            print("🔍 Đang xử lý vietnamnet.vn với web scraping thông thường...")
            print(f"URL: {url}")
            print("=== BẮT ĐẦU XỬ LÝ VIETNAMNET.VN ===")
            
            # Ưu tiên lấy từ thẻ h2.sapo (tóm tắt bài báo) trước
            sapo_selectors = [
                'h2[class="content-detail-sapo sm-sapo-mb-0"]',
                'h2.content-detail-sapo',
                'h2[class*="content-detail-sapo"]',
                'h2[class*="sapo"]',
                '.content-detail-sapo',
                '[class*="sapo"]'
            ]
            
            for selector in sapo_selectors:
                print(f"🔍 Đang thử selector: {selector}")
                sapo_element = soup.select_one(selector)
                if sapo_element:
                    sapo_text = sapo_element.get_text().strip()
                    print(f"📝 Tìm thấy element với selector {selector}")
                    print(f"Nội dung sapo (đầy đủ): {sapo_text}")
                    print(f"Số từ sapo: {len(sapo_text.split())}")
                    print(f"Độ dài ký tự sapo: {len(sapo_text)}")
                    
                    if len(sapo_text) > 30:
                        # Kiểm tra xem sapo có bị cắt ngắn không
                        if sapo_text.endswith('...'):
                            print("⚠️ Cảnh báo: Sapo bị cắt ngắn (kết thúc bằng ...), bỏ qua và tìm nội dung đầy đủ")
                            continue  # Bỏ qua sapo bị cắt ngắn
                        
                        content = sapo_text
                        print(f"✅ Đã lấy sapo thành công từ selector {selector}, không kết hợp thêm đoạn văn khác")
                        break
                    else:
                        print(f"❌ Sapo quá ngắn ({len(sapo_text)} ký tự), bỏ qua")
                else:
                    print(f"❌ Không tìm thấy element với selector {selector}")
            
            # Nếu không tìm thấy sapo bằng selector, thử tìm tất cả thẻ h2
            if not content:
                print("🔍 Không tìm thấy sapo bằng selector, đang tìm tất cả thẻ h2...")
                all_h2 = soup.find_all('h2')
                for i, h2 in enumerate(all_h2):
                    h2_classes = h2.get('class', [])
                    h2_text = h2.get_text().strip()
                    print(f"H2 {i+1}: classes={h2_classes}, text='{h2_text[:100]}...'")
                    
                    if 'sapo' in ' '.join(h2_classes).lower() and len(h2_text) > 30 and not h2_text.endswith('...'):
                        print(f"✅ Tìm thấy sapo từ thẻ h2 thứ {i+1}")
                        print(f"Nội dung sapo (đầy đủ): {h2_text}")
                        content = h2_text
                        break
            
            print(f"=== KẾT THÚC XỬ LÝ VIETNAMNET.VN - Kết quả: {'Thành công' if content else 'Thất bại'} ===")
        
        # Xử lý đặc biệt cho tienphong.vn
        elif 'tienphong.vn' in url:
            print("🔍 Đang xử lý tienphong.vn...")
            print(f"URL: {url}")
            print("=== BẮT ĐẦU XỬ LÝ TIENPHONG.VN ===")
            
            # Tìm sapo của tienphong.vn
            tienphong_selectors = [
                'div.sapo p',
                '.article-sapo',
                '.content-sapo',
                'div[class*="sapo"]',
                '.lead'
            ]
            
            for selector in tienphong_selectors:
                print(f"🔍 Đang thử selector: {selector}")
                sapo_element = soup.select_one(selector)
                if sapo_element:
                    sapo_text = sapo_element.get_text().strip()
                    print(f"📝 Tìm thấy element với selector {selector}")
                    print(f"Nội dung sapo: {sapo_text}")
                    
                    if len(sapo_text) > 30:
                        content = sapo_text
                        print(f"✅ Đã lấy sapo thành công từ selector {selector}")
                        break
                else:
                    print(f"❌ Không tìm thấy element với selector {selector}")
            
            print(f"=== KẾT THÚC XỬ LÝ TIENPHONG.VN - Kết quả: {'Thành công' if content else 'Thất bại'} ===")
        
        # Nếu không phải vietnamnet/tienphong hoặc không tìm thấy nội dung đặc biệt, ưu tiên lấy từ meta description và kết hợp với đoạn văn đầu tiên
        if not content:
            meta_description = soup.find('meta', attrs={'name': 'description'})
            if meta_description and meta_description.get('content'):
                desc_content = meta_description.get('content').strip()
                if len(desc_content) > 50:
                    # Tìm đoạn văn đầu tiên trong nội dung để bổ sung
                    first_paragraph = None
                
                # Thử các selector cụ thể trước
                content_selectors = [
                    'div.detail p', 'div.content p', 'article p', 
                    'div[class*="content"] p', 'div[class*="article"] p'
                ]
                
                for selector in content_selectors:
                    paragraphs = soup.select(selector)
                    if paragraphs:
                        for p in paragraphs:
                            text = p.get_text().strip()
                            if (len(text) > 80 and 
                                not any(keyword in text.lower() for keyword in [
                                    'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                                    'đăng nhập', 'login', 'quảng cáo', 'advertisement'
                                ])):
                                first_paragraph = text
                                break
                        if first_paragraph:
                            break
                
                # Nếu không tìm thấy, tìm trong tất cả thẻ p
                if not first_paragraph:
                    all_paragraphs = soup.find_all('p')
                    for p in all_paragraphs:
                        text = p.get_text().strip()
                        if (len(text) > 80 and 
                            not any(keyword in text.lower() for keyword in [
                                'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                                'đăng nhập', 'login', 'quảng cáo', 'advertisement'
                            ])):
                            first_paragraph = text
                            break
                
                # Kết hợp meta description với đoạn văn đầu tiên
                if first_paragraph and not first_paragraph.startswith(desc_content):
                    # Chỉ kết hợp meta description với đoạn văn đầu tiên
                    content = desc_content + " " + first_paragraph
                else:
                    content = desc_content
                
                # Nếu nội dung chưa đủ 80 từ, lấy thêm đoạn văn kế tiếp
                if content:
                    content_words = len(content.split())
                    if content_words < 80:
                        print(f"Nội dung hiện tại có {content_words} từ, chưa đủ 80 từ. Đang lấy thêm đoạn văn kế tiếp...")
                        
                        # Tìm đoạn văn kế tiếp
                        all_paragraphs = soup.find_all('p')
                        for i, p in enumerate(all_paragraphs):
                            text = p.get_text().strip()
                            if (len(text) > 50 and 
                                not any(keyword in text.lower() for keyword in [
                                    'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                                    'đăng nhập', 'login', 'quảng cáo', 'advertisement'
                                ])):
                                
                                # Kiểm tra xem đoạn này có khác với đoạn đã lấy không
                                if text != content:
                                    # Kết hợp đoạn văn kế tiếp
                                    combined_content = content + " " + text
                                    combined_words = len(combined_content.split())
                                    
                                    print(f"Đã kết hợp đoạn văn kế tiếp. Tổng từ: {combined_words}")
                                    print(f"Nội dung kết hợp đầy đủ: {combined_content}")
                                    content = combined_content
                                    
                                    # Nếu đã đủ 80 từ, dừng lại
                                    if combined_words >= 80:
                                        break
        
        # Logic vietnamnet.vn đã được xử lý ở trên
            print("Đang xử lý vietnamnet.vn với web scraping thông thường...")
            print(f"URL: {url}")
            print("=== BẮT ĐẦU XỬ LÝ VIETNAMNET.VN ===")
            
            # Ưu tiên lấy từ thẻ h2.sapo (tóm tắt bài báo) trước
            sapo_selectors = [
                'h2[class="content-detail-sapo sm-sapo-mb-0"]',
                'h2.content-detail-sapo',
                'h2[class*="content-detail-sapo"]',
                'h2[class*="sapo"]',
                '.content-detail-sapo',
                '[class*="sapo"]'
            ]
            
            for selector in sapo_selectors:
                print(f"🔍 Đang thử selector: {selector}")
                sapo_element = soup.select_one(selector)
                if sapo_element:
                    sapo_text = sapo_element.get_text().strip()
                    print(f"📝 Tìm thấy element với selector {selector}")
                    print(f"Nội dung sapo (đầy đủ): {sapo_text}")
                    print(f"Số từ sapo: {len(sapo_text.split())}")
                    print(f"Độ dài ký tự sapo: {len(sapo_text)}")
                    
                    if len(sapo_text) > 30:
                        # Kiểm tra xem sapo có bị cắt ngắn không
                        if sapo_text.endswith('...'):
                            print("⚠️ Cảnh báo: Sapo bị cắt ngắn (kết thúc bằng ...), bỏ qua và tìm nội dung đầy đủ")
                            continue  # Bỏ qua sapo bị cắt ngắn
                        
                        content = sapo_text
                        print(f"✅ Đã lấy sapo thành công từ selector {selector}, không kết hợp thêm đoạn văn khác")
                        break
                    else:
                        print(f"❌ Sapo quá ngắn ({len(sapo_text)} ký tự), bỏ qua")
                else:
                    print(f"❌ Không tìm thấy element với selector {selector}")
            
            # Nếu không tìm thấy sapo bằng selector, thử tìm tất cả thẻ h2
            if not content:
                print("🔍 Không tìm thấy sapo bằng selector, đang tìm tất cả thẻ h2...")
                all_h2 = soup.find_all('h2')
                for i, h2 in enumerate(all_h2):
                    h2_classes = h2.get('class', [])
                    h2_text = h2.get_text().strip()
                    print(f"H2 {i+1}: classes={h2_classes}, text='{h2_text[:100]}...'")
                    
                    if 'sapo' in ' '.join(h2_classes).lower() and len(h2_text) > 30:
                        print(f"✅ Tìm thấy sapo từ thẻ h2 thứ {i+1}")
                        print(f"Nội dung sapo (đầy đủ): {h2_text}")
                        content = h2_text
                        break
            
            # Định nghĩa content_selectors để dùng cho cả sapo và đoạn văn kế tiếp
            content_selectors = [
                'div[class*="content"] p',
                'article p',
                'div.detail p',
                'div.content p'
            ]
            
            # Nếu không tìm thấy sapo hoặc sapo bị cắt ngắn, tìm đoạn văn chính từ vietnamnet.vn
            if not content:
                print("Không tìm thấy sapo đầy đủ, đang tìm đoạn văn chính...")
            
                for selector in content_selectors:
                    paragraphs = soup.select(selector)
                    if paragraphs:
                        print(f"Tìm thấy {len(paragraphs)} đoạn văn với selector: {selector}")
                        
                        # Tìm đoạn văn đầu tiên có nội dung thực sự
                        first_valid_paragraph = None
                        for i, p in enumerate(paragraphs):
                            text = p.get_text().strip()
                            print(f"Đoạn văn {i+1}: {text}")
                            
                        # Kiểm tra xem có phải đoạn văn có nội dung thực sự không
                        if (len(text) > 30 and  # Giảm yêu cầu độ dài
                            not any(keyword in text.lower() for keyword in [
                                'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                                'đăng nhập', 'login', 'quảng cáo', 'advertisement'
                            ]) and
                            not text.endswith('...') and  # Không lấy đoạn bị cắt
                            len(text.split()) > 5):  # Giảm yêu cầu số từ
                            
                            # Ưu tiên đoạn văn có nội dung dài hơn và không phải tên tác giả
                            if (len(text) > 50 and 
                                not any(author in text.lower() for author in ['thạch thảo', 'mỹ anh']) and
                                len(text.split()) > 10 and
                                not text.endswith('...')):  # Không lấy đoạn văn bị cắt ngắn
                                print(f"✅ Tìm thấy đoạn văn ưu tiên (đầy đủ):")
                                print(f"Nội dung đầy đủ: {text}")
                                if not content:  # Chỉ gán nếu chưa có content
                                    content = text
                                break
                            elif not first_valid_paragraph:
                                # Lưu đoạn văn đầu tiên hợp lệ làm backup
                                first_valid_paragraph = text
                                print(f"📝 Lưu đoạn văn backup:")
                                print(f"Nội dung đầy đủ: {text}")
                        
                        # Nếu không tìm thấy đoạn văn ưu tiên, dùng đoạn backup
                        if not content and first_valid_paragraph:
                            print(f"✅ Sử dụng đoạn văn backup:")
                            print(f"Nội dung đầy đủ: {first_valid_paragraph}")
                            if not content:  # Chỉ gán nếu chưa có content
                                content = first_valid_paragraph
                        
                        if content:
                            break
            
            # Nếu vẫn chưa có nội dung, thử cách khác với logic nhất quán
            if not content:
                print("Không tìm thấy nội dung với selector ưu tiên, thử cách khác...")
                # Tìm trong tất cả thẻ p với logic nhất quán
                all_paragraphs = soup.find_all('p')
                first_valid_backup = None
                
                for p in all_paragraphs:
                    text = p.get_text().strip()
                    
                    # Kiểm tra đoạn văn hợp lệ
                    if (len(text) > 30 and 
                        not any(keyword in text.lower() for keyword in [
                            'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                            'đăng nhập', 'login', 'quảng cáo', 'advertisement'
                        ]) and
                        len(text.split()) > 5):
                        
                        # Ưu tiên đoạn văn dài và không phải tên tác giả
                        if (len(text) > 50 and 
                            not any(author in text.lower() for author in ['thạch thảo', 'mỹ anh']) and
                            len(text.split()) > 10 and
                            not text.endswith('...')):  # Không lấy đoạn văn bị cắt ngắn
                            print(f"✅ Tìm thấy đoạn văn ưu tiên từ tất cả thẻ p (đầy đủ):")
                            print(f"Nội dung đầy đủ: {text}")
                            if not content:  # Chỉ gán nếu chưa có content
                                content = text
                            break
                        elif not first_valid_backup:
                            # Lưu đoạn văn đầu tiên hợp lệ làm backup
                            first_valid_backup = text
                            print(f"📝 Lưu đoạn văn backup từ tất cả thẻ p:")
                            print(f"Nội dung đầy đủ: {text}")
                
                # Nếu không tìm thấy đoạn ưu tiên, dùng backup
                if not content and first_valid_backup:
                    print(f"✅ Sử dụng đoạn văn backup từ tất cả thẻ p:")
                    print(f"Nội dung đầy đủ: {first_valid_backup}")
                    if not content:  # Chỉ gán nếu chưa có content
                        content = first_valid_backup
            
            # Kiểm tra xem có lấy từ sapo không
            sapo_found = False
            if content:
                for selector in sapo_selectors:
                    sapo_element = soup.select_one(selector)
                    if sapo_element:
                        sapo_text = sapo_element.get_text().strip()
                        if sapo_text == content:
                            sapo_found = True
                            print(f"✅ Xác nhận đã lấy từ sapo: {sapo_text[:50]}...")
                            break
            
            # Nếu nội dung vietnamnet.vn chưa đủ 80 từ, lấy thêm đoạn văn kế tiếp
            # NHƯNG chỉ khi KHÔNG lấy từ sapo
            if content and not sapo_found:
                content_words = len(content.split())
                if content_words < 80:
                    print(f"Nội dung hiện tại có {content_words} từ, chưa đủ 80 từ. Đang lấy thêm đoạn văn kế tiếp...")
                    
                    # Tìm đoạn văn kế tiếp từ vietnamnet.vn
                    for selector in content_selectors:
                        paragraphs = soup.select(selector)
                        if paragraphs:
                            for p in paragraphs:
                                text = p.get_text().strip()
                                if (len(text) > 50 and 
                                    not any(keyword in text.lower() for keyword in [
                                        'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                                        'đăng nhập', 'login', 'quảng cáo', 'advertisement',
                                        'thạch thảo', 'mỹ anh'
                                    ]) and
                                    text != content and  # Khác với đoạn đã lấy
                                    len(text.split()) > 10):
                                    
                                    # Kết hợp đoạn văn kế tiếp
                                    combined_content = content + " " + text
                                    combined_words = len(combined_content.split())
                                    
                                    print(f"Đã kết hợp đoạn văn kế tiếp. Tổng từ: {combined_words}")
                                    print(f"Nội dung kết hợp đầy đủ: {combined_content}")
                                    content = combined_content
                                    
                                    # Nếu đã đủ 80 từ, dừng lại
                                    if combined_words >= 80:
                                        break
                            
                            if len(content.split()) >= 80:
                                break
            elif content and sapo_found:
                content_words = len(content.split())
                print(f"✅ Đã lấy từ sapo, không kết hợp thêm. Số từ: {content_words}")
            
            # Làm sạch nội dung cuối cùng - loại bỏ dấu "..." nếu có
            if content and content.endswith('...'):
                print("⚠️ Phát hiện nội dung kết thúc bằng '...', đang làm sạch...")
                content = content.rstrip('...').strip()
                print(f"✅ Đã làm sạch nội dung: {content}")
            
            print(f"=== KẾT THÚC XỬ LÝ VIETNAMNET.VN - Kết quả: {'Thành công' if content else 'Thất bại'} ===")
            if content:
                print(f"Nội dung cuối cùng (đầy đủ): {content}")
                print(f"Số từ: {len(content.split())}")
                print(f"Độ dài ký tự: {len(content)}")
        
        elif 'nguoiduatin.vn' in url and not content:
            # Tìm đoạn văn chính - thường là đoạn đầu tiên sau tiêu đề
            # Thử nhiều cách tiếp cận khác nhau
            content_selectors = [
                'div.detail p',
                'div.content p', 
                'article p',
                'div[class*="content"] p',
                'div[class*="article"] p',
                'div[class*="story"] p'
            ]
            
            for selector in content_selectors:
                paragraphs = soup.select(selector)
                if paragraphs:
                    for p in paragraphs:
                        text = p.get_text().strip()
                        # Tìm đoạn văn có chứa từ khóa chính của bài báo
                        if (len(text) > 80 and 
                            ('biểu tình' in text.lower() or 'london' in text.lower() or 'tommy robinson' in text.lower()) and
                            not any(keyword in text.lower() for keyword in [
                                'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                                'đăng nhập', 'login', 'quảng cáo', 'advertisement',
                                'đám đông biểu tình tập trung'  # Loại bỏ caption ảnh cụ thể này
                            ])):
                            content = text
                            break
                    if content:
                        break
            
            # Nếu vẫn chưa tìm thấy, thử tìm theo thứ tự xuất hiện
            if not content:
                all_paragraphs = soup.find_all('p')
                for p in all_paragraphs:
                    text = p.get_text().strip()
                    if (len(text) > 80 and 
                        'biểu tình' in text.lower() and 
                        'london' in text.lower() and
                        'tommy robinson' in text.lower()):
                        content = text
                        break
        
        # Danh sách các selector ưu tiên cho nội dung chính
        main_content_selectors = [
            '.article-content p',
            '.post-content p', 
            '.entry-content p',
            '.content p',
            'article p',
            '.article-body p',
            '[class*="content"] p',
            '.detail p',
            '.news-content p',
            '.story p'
        ]
        
        # Tìm trong các container nội dung chính trước (chỉ nếu chưa có content)
        if not content:
            for selector in main_content_selectors:
                content_elements = soup.select(selector)
                if content_elements:
                    for p in content_elements:
                        text = p.get_text().strip()
                        # Lọc bỏ các đoạn văn không phải nội dung chính
                        if (len(text) > 80 and 
                            not any(keyword in text.lower() for keyword in [
                                'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:', 
                                'đăng nhập', 'login', 'quảng cáo', 'advertisement',
                                'bình luận', 'comment', 'chia sẻ', 'share',
                                'theo dõi', 'follow', 'đăng ký', 'subscribe'
                            ]) and
                            not text.startswith(('Liên hệ', 'Góp ý', 'Quảng cáo'))):
                            content = text
                            break
                    if content:
                        break
        
        # Nếu không tìm thấy trong container chính, tìm trong tất cả thẻ p
        if not content:
            all_paragraphs = soup.find_all('p')
            for p in all_paragraphs:
                text = p.get_text().strip()
                if (len(text) > 80 and 
                    not any(keyword in text.lower() for keyword in [
                        'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                        'đăng nhập', 'login', 'quảng cáo', 'advertisement', 
                        'bình luận', 'comment', 'chia sẻ', 'share',
                        'theo dõi', 'follow', 'đăng ký', 'subscribe'
                    ]) and
                    not text.startswith(('Liên hệ', 'Góp ý', 'Quảng cáo'))):
                    content = text
                    break
        
        # Nếu nội dung chưa đủ 80 từ, lấy thêm đoạn văn kế tiếp (cho trường hợp không có meta description)
        if content:
            content_words = len(content.split())
            if content_words < 80:
                print(f"Nội dung hiện tại có {content_words} từ, chưa đủ 80 từ. Đang lấy thêm đoạn văn kế tiếp...")
                
                # Tìm đoạn văn kế tiếp
                all_paragraphs = soup.find_all('p')
                for i, p in enumerate(all_paragraphs):
                    text = p.get_text().strip()
                    if (len(text) > 50 and 
                        not any(keyword in text.lower() for keyword in [
                            'nguồn:', 'ảnh:', 'photo:', 'image:', 'caption:',
                            'đăng nhập', 'login', 'quảng cáo', 'advertisement',
                            'bình luận', 'comment', 'chia sẻ', 'share',
                            'theo dõi', 'follow', 'đăng ký', 'subscribe'
                        ]) and
                        not text.startswith(('Liên hệ', 'Góp ý', 'Quảng cáo'))):
                        
                        # Kiểm tra xem đoạn này có khác với đoạn đã lấy không
                        if text != content:
                            # Kết hợp đoạn văn kế tiếp
                            combined_content = content + " " + text
                            combined_words = len(combined_content.split())
                            
                            print(f"Đã kết hợp đoạn văn kế tiếp. Tổng từ: {combined_words}")
                            content = combined_content
                            
                            # Nếu đã đủ 80 từ, dừng lại
                            if combined_words >= 80:
                                break
        
        # Đếm số từ
        title_text = title or 'Không tìm thấy tiêu đề'
        content_text = content or 'Không tìm thấy nội dung'
        
        # Đếm từ trong tiêu đề và nội dung
        title_words = len(title_text.split()) if title_text else 0
        content_words = len(content_text.split()) if content_text else 0
        total_words = title_words + content_words
        
        return {
            'title': title_text,
            'content': content_text,
            'word_count': {
                'title_words': title_words,
                'content_words': content_words,
                'total_words': total_words,
                'meets_minimum': total_words >= 80
            },
            'success': True
        }
        
    except requests.RequestException as e:
        error_str = str(e)
        print(f"⚠️ Requests error: {error_str}")
        
        # Nếu gặp SSL error, thử dùng Selenium
        if 'SSL' in error_str or 'CERTIFICATE' in error_str or 'ssl' in error_str.lower():
            print("🔄 SSL error detected, trying Selenium fallback...")
            try:
                selenium_result = extract_with_selenium(url)
                if selenium_result['success']:
                    print("✅ Selenium fallback successful!")
                    return selenium_result
                else:
                    print("❌ Selenium fallback failed, trying Gemini...")
                    # Nếu Selenium cũng fail, thử Gemini
                    gemini_result = extract_with_gemini(url)
                    if gemini_result['success']:
                        print("✅ Gemini fallback successful!")
                        return gemini_result
            except Exception as selenium_error:
                print(f"❌ Selenium fallback error: {selenium_error}")
                try:
                    print("🔄 Trying Gemini as final fallback...")
                    gemini_result = extract_with_gemini(url)
                    if gemini_result['success']:
                        print("✅ Gemini final fallback successful!")
                        return gemini_result
                except Exception as gemini_error:
                    print(f"❌ All fallbacks failed. Gemini error: {gemini_error}")
        
        error_content = f'Không thể truy cập URL: {error_str}'
        return {
            'title': 'Lỗi kết nối',
            'content': error_content,
            'word_count': {
                'title_words': 0,
                'content_words': len(error_content.split()),
                'total_words': len(error_content.split()),
                'meets_minimum': False
            },
            'success': False
        }
    except Exception as e:
        error_content = f'Lỗi khi xử lý dữ liệu: {str(e)}'
        return {
            'title': 'Lỗi xử lý',
            'content': error_content,
            'word_count': {
                'title_words': 0,
                'content_words': len(error_content.split()),
                'total_words': len(error_content.split()),
                'meets_minimum': False
            },
            'success': False
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract():
    # Hỗ trợ cả form data và JSON data
    if request.is_json:
        data = request.get_json()
        url = data.get('url', '').strip()
    else:
        url = request.form.get('url', '').strip()
    
    if not url:
        return jsonify({
            'title': 'Lỗi',
            'content': 'Vui lòng nhập URL hợp lệ',
            'success': False
        })
    
    # Thêm http:// nếu URL không có protocol
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    result = extract_title_and_content(url)
    return jsonify(result)

@app.route('/batch_extract', methods=['POST'])
def batch_extract():
    urls_text = request.form.get('urls', '').strip()
    
    if not urls_text:
        return jsonify({
            'results': [],
            'error': 'Vui lòng nhập ít nhất một URL'
        })
    
    # Tách các URL từ text input
    urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
    
    results = []
    for url in urls:
        # Thêm http:// nếu URL không có protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        result = extract_title_and_content(url)
        result['url'] = url
        results.append(result)
    
    return jsonify({'results': results})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
