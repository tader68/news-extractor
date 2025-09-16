# 🎯 Deployment Checklist - 100% Quality Assurance

## ✅ **Pre-Deployment Checklist**

### 1. **Environment Configuration**
- [ ] `GEMINI_API_KEY` correctly set in environment variables
- [ ] `PYTHON_VERSION = 3.11.0` set
- [ ] Chrome environment variables configured
- [ ] `PORT` variable handled dynamically

### 2. **Code Quality**
- [ ] All imports working correctly
- [ ] No hardcoded API keys in code
- [ ] Error handling for all scenarios
- [ ] Logging configured properly

### 3. **Selenium Configuration**
- [ ] Chrome options optimized for cloud deployment
- [ ] `--no-sandbox` and `--disable-dev-shm-usage` flags present
- [ ] Single process mode enabled for cloud
- [ ] Headless mode working
- [ ] SSL bypass options configured

### 4. **Fallback Systems**
- [ ] Primary: Direct web scraping with requests
- [ ] Fallback 1: Selenium for SSL errors
- [ ] Fallback 2: Gemini API for complex cases
- [ ] Error messages informative

---

## 🚀 **Post-Deployment Verification**

### Test URLs (Critical):
Test these URLs on deployed version to ensure 100% accuracy:

1. **SSL Challenge**: `https://bnews.vn/vn-index-tang-nhe-phien-sang-15-9-co-phieu-chung-khoan-ban-le-the-p-dan-song/387604.html`
2. **VietnamNet**: `https://vietnamnet.vn/toan-canh-14km-hai-ben-song-to-lich-truoc-khi-lot-xac-thanh-cong-vien-2441880.html`
3. **BaoTinTuc**: `https://baotintuc.vn/the-gioi/trung-quoc-cao-buoc-tap-doan-nvidia-vi-pham-luat-chong-doc-quyen-20250915163348500.htm`
4. **TienPhong**: `https://tienphong.vn/tong-bi-thu-to-lam-du-hoi-nghi-toan-quoc-quan-triet-4-nghi-quyet-quan-trong-cua-bo-chinh-tri-post1778552.tpo`

### Expected Results:

#### ✅ **Must Have Features Working:**
- [ ] Title extraction 100% accurate
- [ ] Content extraction matching exact source
- [ ] Word count calculation correct
- [ ] Auto category selection (1-7: Trong nước, 8-12: Quốc tế)
- [ ] Number selection (1-15 buttons)
- [ ] DOC file generation with correct format
- [ ] Newspaper name mapping working
- [ ] URL clickable hyperlinks

#### ✅ **Quality Standards:**
- [ ] No "..." truncation in content
- [ ] No Python code in responses
- [ ] No technical error messages in UI
- [ ] Content combines paragraphs if <80 words
- [ ] Specific site handlers working (vietnamnet, bnews, etc.)

#### ✅ **Performance Checks:**
- [ ] Page loads within 5 seconds
- [ ] Single extraction < 15 seconds
- [ ] Batch extraction < 30 seconds per URL
- [ ] No memory leaks or crashes
- [ ] Chrome driver properly closes

---

## 🛠️ **Troubleshooting Guide**

### Common Issues & Solutions:

#### **Issue**: Chrome/Selenium not working
```bash
# Check if Chrome is installed
google-chrome --version

# Check ChromeDriver
chromedriver --version

# Test minimal Selenium
python -c "
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)
driver.get('https://google.com')
print('Title:', driver.title)
driver.quit()
"
```

#### **Issue**: Gemini API not working
```python
# Test Gemini API
import google.generativeai as genai
genai.configure(api_key='your-api-key')
model = genai.GenerativeModel('gemini-2.5-flash')
response = model.generate_content('Hello')
print(response.text)
```

#### **Issue**: Memory problems
- Add swap file to VPS
- Use single process Chrome
- Reduce worker count

#### **Issue**: Build timeout
- Increase build timeout in platform settings
- Pre-install Chrome in Docker image

---

## 📊 **Performance Benchmarks**

### Local vs. Cloud Performance:

| Metric | Local | Render.com | Target |
|--------|-------|------------|---------|
| Page Load | 1-2s | 3-5s | <5s |
| Single Extract | 3-8s | 8-15s | <15s |
| Batch 5 URLs | 15-30s | 30-60s | <60s |
| Memory Usage | 200-500MB | 500MB-1GB | <1GB |

### Success Rate Targets:
- **Direct scraping**: 70%+
- **Selenium fallback**: 95%+
- **Gemini fallback**: 99%+
- **Overall success**: 99%+

---

## 🔍 **Quality Verification Commands**

Run these on deployed app:

```bash
# Test single extraction
curl -X POST https://your-app.onrender.com/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://bnews.vn/test-url"}'

# Test batch extraction
curl -X POST https://your-app.onrender.com/batch_extract \
  -F "urls=https://bnews.vn/test1
https://vietnamnet.vn/test2"

# Check health
curl https://your-app.onrender.com/
```

---

## ✅ **Final Checklist**

Before marking deployment as "100% quality":

- [ ] All test URLs working perfectly
- [ ] Auto category selection functioning
- [ ] DOC file generation correct format
- [ ] No errors in console logs
- [ ] SSL fallback working
- [ ] Gemini fallback working
- [ ] UI responsive on mobile
- [ ] All buttons functional
- [ ] LocalStorage persistence working
- [ ] Word count accurate
- [ ] Newspaper mapping correct

**🎯 Only mark complete when ALL items are checked!**
