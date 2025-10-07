# AI Processing Workflow

## Tổng quan
Workflow này được thiết kế để xử lý tài liệu với AI và cho phép người dùng chọn các sections để tạo test cases.

## Workflow Steps

### Step 1: Upload/Review
- Người dùng upload file (.docx, .pdf) hoặc nhập link
- Document được lưu với status `pending`
- Hiển thị button "Start AI Processing"

### Step 2: AI Extract
- Khi người dùng click "Start AI Processing":
  - Status chuyển thành `processing`
  - AI xử lý document trong background thread
  - Tạo mock sections (API endpoints, functions, etc.)
  - Status chuyển thành `completed` khi xong
- Hiển thị button "Check Status" để theo dõi tiến trình

### Step 3: Choose Sections
- Khi AI processing hoàn thành:
  - Hiển thị button "Select Sections"
  - Chuyển đến trang section selection
  - Người dùng chọn sections muốn tạo test cases
  - Lưu selections vào database

## Models

### ProjectDocument
- `ai_processing_status`: pending/processing/completed/failed
- `ai_processed_at`: thời gian hoàn thành
- `ai_error_message`: lỗi nếu có

### DocumentSection
- `section_title`: tiêu đề section
- `section_content`: nội dung section
- `section_type`: loại (api_endpoint, function, class, etc.)
- `is_selected`: user có chọn section này không

## API Endpoints

- `POST /project/<uuid>/ai/start/` - Bắt đầu AI processing
- `GET /project/<uuid>/ai/status/` - Kiểm tra trạng thái
- `GET /project/<uuid>/sections/` - Hiển thị section selection
- `POST /project/<uuid>/sections/update/` - Cập nhật selections

## Frontend Features

- Step wizard hiển thị tiến trình
- Real-time status updates
- AJAX calls cho async processing
- Responsive UI với Bootstrap
- Interactive section selection với checkboxes

## Next Steps

1. Tích hợp với AI service thực tế (thay thế mock data)
2. Thêm step 4: AI Test Case Generation
3. Thêm step 5: Report Generation
4. Cải thiện error handling
5. Thêm progress bar cho AI processing
