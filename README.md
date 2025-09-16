# 📰 Trích xuất Tiêu đề và Nội dung Bài báo

Ứng dụng Flask đơn giản để trích xuất tiêu đề và đoạn văn đầu tiên từ các bài báo trực tuyến.

## ✨ Tính năng

- **Trích xuất đơn lẻ**: Nhập một URL để trích xuất tiêu đề và nội dung
- **Trích xuất hàng loạt**: Nhập nhiều URL cùng lúc để xử lý
- **Giao diện đơn giản**: Thiết kế thân thiện, dễ sử dụng
- **Hỗ trợ nhiều trang web**: Tương thích với các trang tin tức phổ biến

## 🚀 Cài đặt và Chạy

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Chạy ứng dụng

```bash
python app.py
```

### 3. Truy cập ứng dụng

Mở trình duyệt và truy cập: `http://localhost:5000`

## 📋 Cách sử dụng

### Trích xuất một bài báo
1. Nhập URL bài báo vào ô "URL bài báo"
2. Nhấn nút "Trích xuất"
3. Xem kết quả hiển thị ngay bên dưới

### Trích xuất nhiều bài báo
1. Nhập các URL vào ô textarea, mỗi URL một dòng
2. Nhấn nút "Trích xuất tất cả"
3. Xem kết quả cho từng bài báo

## 🔧 Cấu trúc dự án

```
news/
├── app.py              # File Flask chính
├── requirements.txt     # Dependencies
├── README.md           # Hướng dẫn này
└── templates/
    └── index.html      # Giao diện người dùng
```

## 🛠️ Công nghệ sử dụng

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Web Scraping**: BeautifulSoup4, Requests
- **Styling**: CSS3 với gradient và animations

## 📝 Ví dụ sử dụng

### URL mẫu:
```
https://nguoiduatin.vn/bieu-tinh-lon-hon-100000-nguoi-o-anh-au-da-du-doi-voi-canh-sat-204251409155802324.htm
https://vov.vn/the-gioi/thu-tuong-lam-thoi-nepal-cong-bo-uu-tien-trong-nhiem-ky-6-thang-post1229993.vov
```

### Kết quả mẫu:
- **Tiêu đề**: "Biểu tình lớn hơn 100.000 người ở Anh: Ẩu đả dữ dội với cảnh sát"
- **Nội dung**: "Một cuộc biểu tình quy mô lớn tại London (Anh) do nhà hoạt động cực hữu Tommy Robinson tổ chức đã biến thành bạo lực vào ngày 13/9."

## ⚠️ Lưu ý

- Ứng dụng chỉ trích xuất tiêu đề và đoạn văn đầu tiên
- Một số trang web có thể chặn bot, kết quả có thể không chính xác 100%
- Đảm bảo URL hợp lệ và có thể truy cập được
- Ứng dụng tự động thêm `https://` nếu URL không có protocol

## 🐛 Xử lý lỗi

- **Lỗi kết nối**: Kiểm tra URL và kết nối internet
- **Không tìm thấy nội dung**: Trang web có thể có cấu trúc HTML khác
- **Timeout**: Thử lại với URL khác hoặc kiểm tra tốc độ mạng
