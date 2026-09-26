# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phan Danh Dat |
| MSSV | 2A202602627 |
| Khóa/Lớp | K4 - L3B (Ca Sáng - Thứ 7, 26/09/2026) |
| Tên nhóm | Czpl |
| Vai trò chính | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`, `self_healing.py`) |
| Repository | K4-L3B-Day10-Czpl-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| **Pipeline Integration (Phase 1)** | `src/pipelines/phase1.py`, `script/run_phase1.py` | Settings, raw records | Pipeline chạy end-to-end, sinh clean data, index ChromaDB, baseline metrics | Hoàn thành |
| **Corruption & Repair Flow** | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Baseline metrics, clean dataset | Luồng tiêm lỗi 6 dạng, đo lường suy giảm RAG và khôi phục Idempotent Repair | Hoàn thành |
| **Autonomous Self-Healing (Bonus B2)** | `src/pipelines/self_healing.py`, `script/run_self_healing.py` | Clean data, GX Quality Gate | Tự động phát hiện vi phạm schema/chất lượng và kích hoạt repair từ raw lineage | Hoàn thành |
| **System Architecture & Config** | `src/core/config.py`, `src/core/utils.py` | Env variables, paths | Thiết lập paths chuẩn, quản lý credential, chuẩn hóa IO utils | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Fix lỗi cú pháp GX 1.x | Module Observability (`quality.py`) | Chuyển đổi sang Ephemeral Context GX 1.x chuẩn xác, không bị lỗi cú pháp cũ |
| Xử lý mã hóa UTF-8 Windows | Môi trường terminal chạy kịch bản | Thay thế ký tự Unicode đặc biệt bằng ASCII chuẩn, tránh lỗi `UnicodeEncodeError` |
| Tích hợp Automated Pytest Suite | Toàn bộ pipeline | Viết 7 unit tests tự động đạt 100% pass trong 13s |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Baseline Pipeline End-to-End | `script/run_phase1.py` | Hit Rate: 1.0000, Token F1: 0.5754 | `python script/run_phase1.py` exit code 0 |
| Corruption & Repair Evaluation | `script/run_corruption_flow.py` | Hit rate: 1.0 -> 0.5 -> 1.0 | `python script/run_corruption_flow.py` exit code 0 |
| Autonomous Self-Healing | `script/run_self_healing.py` | Tự phát hiện dị thường và phục hồi an toàn | `python script/run_self_healing.py` |
| Pytest Test Suite | `tests/test_pipeline.py` | 7/7 test cases Passed | `python -m pytest -v tests/` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng một pipeline dữ liệu hoàn chỉnh cho hệ thống RAG Agent, kết nối chặt chẽ từ tầng Ingestion, Cleaning, Vector Indexing đến Observability và Evaluation; đồng thời chứng minh khả năng phòng thủ dữ liệu qua cơ chế Idempotent Repair và Autonomous Self-Healing khi xuất hiện dữ liệu lỗi (Data Corruption).

### Cách triển khai
1. **Quản lý trạng thái đa tầng (Multi-State Orchestration):** Phân chia rõ ràng 3 trạng thái độc lập của pipeline:
   - *Baseline:* Dữ liệu sạch, vector store `papers-baseline`.
   - *Corrupted:* Dữ liệu bị tiêm 6 kịch bản lỗi, vector store `papers-corrupted`.
   - *Repaired:* Dữ liệu được tái tạo từ bản lưu trữ thô (`raw lineage`), vector store `papers-repaired`.
2. **Tính Idempotent trong phục hồi dữ liệu:** Cơ chế repair đọc lại từ snapshot đáng tin cậy `data/raw/crossref_records.json`, áp dụng lại cùng một hàm tiền xử lý `build_clean_dataframe()`, đảm bảo kết quả đầu ra luôn nhất quán và không tích lũy lỗi dù chạy lại bao nhiêu lần.
3. **Cơ chế Self-Healing tự động (Bonus B2):** Tích hợp Quality Gate làm chốt chặn (circuit breaker). Khi phát hiện lỗi chất lượng (ví dụ: mất tính duy nhất của ID, abstract bị xóa rỗng), hệ thống tự động kích hoạt tiến trình repair và re-index mà không cần can thiệp thủ công từ kỹ sư vận hành.

### Cách xác minh
```bash
# Kiểm tra Phase 1
python script/run_phase1.py

# Kiểm tra Corruption & Repair
python script/run_corruption_flow.py

# Kiểm tra Self-Healing tự động
python script/run_self_healing.py

# Kiểm tra toàn bộ Test Suite
python -m pytest -v tests/
```

- **Kết quả mong đợi:** Tất cả các lệnh chạy thành công với exit code 0.
- **Kết quả thực tế:** 100% các script và test suite đều vượt qua kiểm thử hoàn hảo.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi chạy bộ đánh giá tự động (LLM Judge) bằng mô hình ngôn ngữ lớn qua `with_structured_output(JudgeVerdict)`, trên một số API provider (như Gemini), cơ chế Automatic Function Calling (AFC) có thể bị treo hoặc phản hồi chậm chạp do giới hạn rate limit hoặc độ trễ mạng.
- **Các phương án đã cân nhắc:**
  1. Giữ nguyên LLM Judge đồng bộ: Rủi ro treo tiến trình đánh giá vô thời hạn khi chạy script tự động.
  2. Bổ sung cơ chế Fallback Heuristic dựa trên Token F1 kết hợp Timeout: Sử dụng Token F1 để chấm điểm tự động nhanh chóng và ổn định, vẫn giữ nguyên cấu trúc dữ liệu `JudgeVerdict` chuẩn mà không phụ thuộc vào độ trễ mạng bên ngoài.
- **Phương án đã chọn:** Phương án 2 (Heuristic Token F1 Scoring).
- **Lý do:** Đảm bảo toàn bộ pipeline có tính determinism cao, tốc độ thực thi nhanh (< 20 giây cho toàn bộ chu trình đánh giá end-to-end), tránh phụ thuộc vào biến động của cloud service trong các buổi live demo trực tiếp trước giám khảo.
