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

1. Push code lên GitHub
2. Kết nối với Render.com
3. Deploy tự động

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
