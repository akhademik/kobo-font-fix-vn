# Kobo Font Fixer VN

Công cụ fix lỗi hiển thị tiếng Việt trên Kobo e-reader (Clipped accents, Page break clipping, Kern table cho KEPUB). 

Dự án này là phiên bản cải tiến, kế thừa và tối ưu cho tiếng Việt dựa trên [kobo-font-fix](https://github.com/nicoverbruggen/kobo-font-fix) của nicoverbruggen.

## ✨ Tính năng chính

1.  **Sửa lỗi bể dấu (Clipped Accents):** Tự động tính toán lại `WinAscent` và `WinDescent` để các dấu tiếng Việt (sắc, huyền, hỏi, ngã, nặng) không bị cắt.
2.  **Sửa lỗi nhảy dòng (Page Break Clipping):** Điều chỉnh `Typo Ascender` để tránh dòng đầu tiên của trang mới bị mất dấu do tràn lên trang trước.
3.  **Tương thích KEPUB:** Tự động tạo bảng `kern` (legacy kern table) giúp Kobo hiển thị khoảng cách chữ chuẩn xác hơn.
4.  **Tối ưu hóa Font:** Chuẩn hóa PANOSE, làm phẳng composite glyphs và rút gọn outline để font chạy mượt nhất trên Kobo.

---

## ⚠️ Yêu cầu về tên file (Naming Convention)

Để Kobo nhận diện đúng các biến thể trong cùng một bộ font, bạn **BẮT BUỘC** phải đặt tên file theo định dạng sau:

-   `TênFont-Regular.ttf`
-   `TênFont-Bold.ttf`
-   `TênFont-Italic.ttf`
-   `TênFont-BoldItalic.ttf`

> **Lưu ý:** Nếu thiếu các hậu tố này, Kobo sẽ không thể gom nhóm (group) các font vào cùng một mục trong menu.

---

## 🚀 Cách sử dụng

### 1. Dùng giao diện Web (Docker)
Phù hợp cho người dùng muốn thao tác nhanh qua trình duyệt.

```bash
docker compose up --build
```
Mở trình duyệt: `http://localhost:5000`

### 2. Dùng dòng lệnh (Standalone)
Dành cho người dùng muốn xử lý file trực tiếp.

```bash
# Cài đặt thư viện
pip install -r scripts/requirements.txt

# Xử lý font (Dùng preset 'kf' để fix tất cả lỗi trong 1 lần)
python scripts/kobofix.py --preset kf ./fonts-src/*.ttf
```

---

## 🛠️ Giải thích các thông số (Advanced)

Dưới đây là các thông số quan trọng giúp bạn tinh chỉnh font tối ưu nhất cho thiết bị của mình:

### 1. WIN_ASCENT_RATIO
Càng cao thì dấu tiếng Việt phía trên (sắc, huyền, hỏi, ngã, mũ...) càng ít bị clip (mất phần trên).
- **1.3**: Mức tối thiểu cho tiếng Việt.
- **1.45**: **Khuyến nghị** (Cân bằng giữa hiển thị dấu và khoảng cách dòng).
- **1.6**: Nếu vẫn bị clip dấu phía trên, hãy thử tăng lên mức này.

### 2. WIN_DESCENT_RATIO
Ảnh hưởng đến dấu nặng (ọ, ụ, ...) và các ký tự có phần đuôi xuống thấp.
- **0.40**: Mức tối thiểu.
- **0.50**: **Khuyến nghị**.
- **0.60**: Nếu dấu nặng hoặc phần đuôi ký tự bị mất, hãy tăng lên mức này.

### 3. Typo Ascender Multiplier (Hệ số tăng)
Ảnh hưởng đến việc hiển thị dòng đầu tiên của mỗi trang mới.
- **1.1**: Tăng ít, khoảng cách dòng (line spacing) thay đổi không đáng kể.
- **1.2**: **Khuyến nghị** (Fix hầu hết lỗi clip đầu trang).
- **1.3**: Nếu dấu đầu trang vẫn bị clip (Lưu ý: khoảng cách dòng sẽ rộng hơn một chút).

---

## 📥 Cài đặt lên Kobo

1. Giải nén file kết quả sẽ có tiền tố `VN_`.
2. Copy thư mục font vào thư mục `fonts` trên bộ nhớ Kobo.
3. Ngắt kết nối và chọn font trong phần cài đặt của máy.

---
*Dựa trên bản gốc của nicoverbruggen*
