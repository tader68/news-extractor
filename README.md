# News Extractor - Trích xuất tin tức

Flask web application để trích xuất tiêu đề và nội dung từ các trang tin tức Việt Nam.

## 🚀 Tính năng

- ✅ Trích xuất tiêu đề và nội dung từ URL tin tức
- ✅ Xử lý batch nhiều URL cùng lúc
- ✅ Đếm số từ và kiểm tra >= 80 từ
- ✅ Tự động gán category (Trong nước: số 1-7, Quốc tế: số 8-12)
- ✅ Xuất file DOC với format tùy chỉnh
- ✅ Hỗ trợ nhiều trang báo VN
- ✅ Xử lý SSL errors với Selenium + Gemini API backup

## 🛠️ Cài đặt

```bash
pip install -r requirements.txt
python app.py
```

## 🌐 Deploy lên Render

### Docker Deployment (Recommended)
1. Push code lên GitHub
2. Tạo Web Service trên [render.com](https://render.com)
3. Chọn **Docker** environment
4. Render sẽ tự động build image với Chrome

### Environment Variables
- `CHROME_BIN`: `/usr/bin/google-chrome`
- `GEMINI_API_KEY`: Your Gemini API key
- `DISPLAY`: `:99` (for headless Chrome)

### Memory Optimization
- Docker image với Chrome optimized cho low memory
- Single worker để tránh memory overflow
- Auto cleanup Selenium drivers

## 📝 Supported News Sites

- vietnamnet.vn
- bnews.vn  
- baotintuc.vn
- tienphong.vn
- baoxaydung.vn
- nguoiduatin.vn
- baoquocte.vn

## 🔑 Environment Variables

- `GEMINI_API_KEY`: API key cho Google Gemini (backup cho SSL errors)
# news-extractor
