# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 - L3B (Ca Sáng - Thứ 7, 26/09/2026) |
| Tên nhóm | Czpl |
| Repository | K4-L3B-Day10-Czpl-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module / deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Phan Danh Dat | 2A202602627 | Trưởng nhóm / Thành viên | `core/`, `phase1.py`, `corruption_flow.py`, `self_healing.py`, `crossref.py`, `cleaning.py`, raw data snapshot & lineage, `retrieval/index.py`, `embeddings.py`, ChromaDB collections, `quality.py` (GX 1.x), `testset.py`, reporting, dashboard |

---

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn diện toàn bộ 7 Checkpoints (CP0 - CP6) cùng cả 3 hạng mục Bonus (B1, B2, B3) trong bài lab:

1. **Baseline Pipeline (CP0 - CP3):** Thu thập và chuẩn hóa thành công 24 tài liệu học thuật từ Crossref API. Tiền xử lý, trích xuất cấu trúc văn bản `text_for_embedding` và lập chỉ mục vào ChromaDB vector collection `papers-baseline` bằng mô hình `all-MiniLM-L6-v2`. Kết quả đánh giá trên bộ test 10 câu hỏi đạt **Retrieval Hit Rate tuyệt đối 100.0% (1.0000)** và **Mean Token F1 là 0.5754**. Hệ thống vượt qua chốt kiểm định chất lượng dữ liệu theo chuẩn Great Expectations 1.x (`PASS`) và đạt chuẩn Freshness SLA (100% bài báo dưới 180 ngày).

2. **Data Corruption & Suy giảm (CP4):** Áp dụng đồng thời 6 kịch bản làm bẩn dữ liệu tổng hợp (mất 20% bản ghi mới nhất, xóa rỗng abstract, chèn chuỗi nhiễu, cắt cụt tiêu đề, làm cũ ngày xuất bản, nhân bản bản ghi). Hệ thống Data Quality Gate lập tức phát hiện dị thường (`FAIL`). Hiệu năng RAG Agent sụt giảm nghiêm trọng: Retrieval Hit Rate rơi thẳng đứng từ **1.0000 xuống 0.5000 (-50%)**, Token F1 giảm từ **0.5754 xuống 0.3306 (-42.5%)**, minh chứng rõ nét cho hiện tượng **Silent Failure** nếu thiếu Data Observability.

3. **Idempotent Repair & Tự phục hồi (CP5 & Bonus B2):** Thực thi quy trình phục hồi dữ liệu từ bản lưu trữ gốc `data/raw/crossref_records.json`. Sau khi chạy Repair, Data Quality Gate khôi phục trạng thái `PASS`, và mọi chỉ số hiệu năng phục hồi hoàn toàn về mức Baseline (**Hit Rate 1.0000, F1 0.5754**).

4. **Bonus Vượt Chuẩn:**
   - **B1 (+5đ):** Dashboard HTML trực quan tương tác Chart.js (`data/reports/observability_dashboard.html`).
   - **B2 (+5đ):** Module tự động phát hiện vi phạm và kích hoạt phục hồi (`src/pipelines/self_healing.py`).
   - **B3 (+5đ):** Bộ test Pytest tự động 7/7 test cases đạt 100% pass (`tests/test_pipeline.py`).

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
[Crossref REST API] 
       │
       ▼ (Fetch with local snapshot fallback)
[data/raw/crossref_response.json] & [crossref_records.json]
       │
       ▼ (Cleaning, de-duplication, age_days, text_for_embedding)
[data/clean/papers_clean.csv] & [papers_clean.json]
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
[Great Expectations 1.x Quality Gate]   [ChromaDB Local Vector Store]
(4 Expectations + Freshness SLA)        (Collection: papers-baseline)
       │                                 │
       ▼                                 ▼
[data/quality/baseline_quality_report]  [Evaluation & RAG QA Engine]
                                         (10 benchmark questions)
                                         │
                                         ▼
                                        [data/results/baseline_metrics.json]
                                         │
       ┌─────────────────────────────────┘
       ▼
[Data Corruption Suite: 6 Scenarios] ──► [data/clean/papers_clean_corrupted]
       │                                         │
       ▼                                         ▼
[Quality Gate: DETECTED FAIL]            [ChromaDB: papers-corrupted]
       │                                         │
       │                                         ▼
       │                                 [Corrupted Metrics: Hit Rate drops to 0.5]
       ▼
[Idempotent Repair from Raw Snapshot] ──► [data/clean/papers_clean_repaired]
       │                                         │
       ▼                                         ▼
[Quality Gate: RECOVERED PASS]           [ChromaDB: papers-repaired]
                                                 │
                                                 ▼
                                         [Repaired Metrics: Hit Rate restored to 1.0]
                                                 │
                                                 ▼
                                         [data/reports/corruption_report.md]
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output / Artifact |
| --- | --- | --- | --- |
| **Ingestion** | Crossref REST API / Snapshot | Fetch dữ liệu, xử lý retry/fallback, parse payload JSON | `data/raw/crossref_response.json`, `crossref_records.json` |
| **Cleaning** | `list[PaperRecord]` | Khử HTML tag, khử trùng lặp theo `paper_id`, tính `age_days`, ghép `text_for_embedding` 5 phần | `data/clean/papers_clean.csv`, `papers_clean.json` |
| **Embedding / Index** | Cleaned DataFrame | Tạo vector embedding qua `all-MiniLM-L6-v2`, persist vào ChromaDB | `data/chroma/`, `data/embeddings/papers_embeddings.json` |
| **Evaluation** | Clean DataFrame + Index | Sinh 10 câu hỏi phủ 4 nhóm (`summary`, `authors`, `date`, `categories`), đo Retrieval Hit Rate và Token F1 | `data/eval/test_set.json`, `baseline_metrics.json` |
| **Observability** | DataFrame + Settings | Cấu hình GX 1.x Ephemeral Context, kiểm định 4 Expectations, giám sát Freshness SLA 180 ngày | `data/quality/*_quality_report.json`, `freshness_report.json` |
| **Corruption & Repair** | Clean DataFrame / Raw JSON | Tiêm 6 kịch bản lỗi, đo lường suy giảm RAG; khôi phục từ raw lineage | `corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json` |
| **Reporting & Dashboard** | Metrics & Quality reports | Sinh báo cáo markdown đối chiếu 3 trạng thái và dashboard HTML trực quan | `phase1_report.md`, `corruption_report.md`, `observability_dashboard.html` |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến / Cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `gemini` (hoặc `mock` khi offline) |
| `LLM_MODEL` | `gemini-3.5-flash-lite` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 records |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Random seed | 42 |

### Lệnh cài đặt môi trường

```bash
# Kích hoạt virtual environment
.venv\Scripts\activate   # Windows
# source .venv/bin/activate # Linux/macOS

# Cài đặt gói mở rộng (nếu cần)
python -m pip install -e .
python -m pip install pytest
```

### Lệnh chạy kiểm chứng từng bước

**1. Kiểm tra môi trường & Ingestion (CP0):**
```bash
python -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
```

**2. Kiểm tra Data Cleaning & Quality Check (CP1):**
```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Tín hiệu hoàn thành: Quality check status = {res[\"success\"]}')"
```

**3. Kiểm tra Test Set Generator (CP2):**
```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
```

**4. Chạy Phase 1 Pipeline End-to-End (CP3):**
```bash
python script/run_phase1.py
```

**5. Chạy Chu Trình Corruption, Repair & Báo Cáo 3 Trạng Thái (CP4 & CP5):**
```bash
python script/run_corruption_flow.py
```

**6. Chạy Bonus B2 (Self-Healing Pipeline):**
```bash
python script/run_self_healing.py
```

**7. Chạy Bonus B3 (Automated Pytest Suite):**
```bash
python -m pytest -v tests/
```

**8. Chạy Bonus B1 (Interactive Dashboard):**
```bash
python script/run_dashboard.py
```

---

## 5. Ingestion, Cleaning và Data Contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Nguồn API | Crossref Works API (`https://api.crossref.org/works`) |
| Query / Filter | `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:...,has-abstract:true` |
| Cơ chế Resilience | Tự động chuyển đổi sang Local Snapshot `data/raw/crossref_response.json` khi dính 429 hoặc mất mạng |
| Số lượng records nhận được | 24 records |

### Clean Schema & Data Modeling

| Cột | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Quy tắc tiền xử lý |
| --- | --- | --- | --- | --- |
| `paper_id` | `str` | Có | Định danh DOI bài báo | Primary key, khử trùng lặp `keep='first'` |
| `title` | `str` | Có | Tiêu đề bài báo | Loại bỏ thẻ XML JATS (`re.sub`), chuẩn hóa khoảng trắng |
| `summary` | `str` | Có | Abstract tóm tắt | Loại bỏ thẻ XML JATS, độ dài yêu cầu > 10 ký tự |
| `authors_joined` | `str` | Không | Danh sách tác giả | Ghép chuỗi từ họ + tên đệm bằng dấu `, ` |
| `categories_joined`| `str` | Không | Lĩnh vực nghiên cứu | Ghép chuỗi các môn nghiên cứu bằng dấu `, ` |
| `published` | `str` | Có | Ngày xuất bản | Định dạng chuẩn `YYYY-MM-DD` |
| `age_days` | `int` | Có | Độ tuổi tài liệu | Tính từ `(run_date - published).days` để xét Freshness SLA |
| `text_for_embedding` | `str` | Có | Văn bản hợp nhất | Ghép 5 phần có prefix: Title, Authors, Published, Categories, Summary |

---

## 6. Thiết lập đánh giá (Evaluation Setup)

- **Số lượng câu hỏi:** Đúng 10 câu hỏi đánh giá cố định trong `data/eval/test_set.json`.
- **4 Dạng nghiệp vụ phủ kín:**
  1. `summary`: Đánh giá năng lực tóm tắt và hiểu sâu nội dung bài báo.
  2. `authors`: Đánh giá năng lực truy xuất thông tin tác giả.
  3. `date`: Đánh giá năng lực nhận diện mốc thời gian xuất bản.
  4. `categories`: Đánh giá năng lực phân loại chuyên ngành.
- **Tính bất biến của Test Set:** Bộ câu hỏi test set được khởi tạo ở Pha Baseline và được **giữ cố định tuyệt đối** cho cả 3 trạng thái (Baseline, Corrupted, Repaired). Điều này tuân thủ nguyên lý khoa học thực nghiệm, đảm bảo mọi biến động về chỉ số Retrieval Hit Rate hay Token F1 chỉ phản ánh chất lượng của tầng dữ liệu (Data Layer), loại trừ sai số do bộ đề thi thay đổi.

---

## 7. Kết quả Baseline

### Artifact Checklist

- [x] `data/raw/crossref_response.json` (24 raw API responses)
- [x] `data/raw/crossref_records.json` (24 parsed raw records)
- [x] `data/clean/papers_clean.csv` & `data/clean/papers_clean.json` (24 cleaned rows)
- [x] `data/chroma/` (Vector store với collection `papers-baseline`)
- [x] `data/eval/test_set.json` (10 test questions)
- [x] `data/results/baseline_metrics.json`
- [x] `data/results/baseline_answers.json`
- [x] `data/quality/baseline_quality_report.json`
- [x] `data/quality/freshness_report.json`
- [x] `data/reports/phase1_report.md`

### Baseline Metrics

| Metric | Giá trị Baseline | Diễn giải ý nghĩa |
| --- | ---: | --- |
| `retrieval_hit_rate` | **1.0000 (100%)** | 10/10 câu hỏi truy xuất chính xác tài liệu chứa đáp án trong top-k (k=4) |
| `mean_token_f1` | **0.5754** | Mức độ trùng khớp từ vựng giữa câu trả lời trích xuất và ground-truth |
| `judge_accuracy` | **0.5000** | Tỷ lệ câu trả lời đạt điểm đánh giá chất lượng >= 3/5 |
| `mean_judge_score` | **3.20 / 5.0** | Điểm trung bình chất lượng câu trả lời |

---

## 8. Data Quality và Freshness SLA

### Cấu hình Great Expectations 1.x

Sử dụng chuẩn Ephemeral Context mới nhất của GX 1.x với 4 Expectations cốt lõi:
1. `ExpectTableRowCountToBeBetween(min_value=1, max_value=1000)`: Đảm bảo số lượng tài liệu nằm trong ngưỡng cho phép, không bị rỗng do lỗi fetch.
2. `ExpectColumnValuesToNotBeNull(column="paper_id")`: Đảm bảo mọi bài báo đều có định danh DOI.
3. `ExpectColumnValuesToBeUnique(column="paper_id")`: Ngăn ngừa nhân bản dữ liệu gây nhiễu vector index.
4. `ExpectColumnValueLengthsToBeBetween(column="summary", min_value=10, max_value=50000)`: Ngăn chặn tài liệu rỗng abstract hoặc văn bản rác quá ngắn.

### Freshness SLA

- **Ngưỡng SLA:** `freshness_threshold_days = 180` ngày.
- **Tiêu chuẩn cảnh báo:** Cảnh báo vi phạm SLA nếu tỷ lệ tài liệu quá hạn (`age_days > 180`) vượt quá 25%.
- **Kết quả Baseline:** 0/24 bài báo bị stale (0.0%). Ngày xuất bản mới nhất: `2026-09-15`, cũ nhất: `2026-04-01`. Trạng thái Freshness SLA: **PASS (`is_fresh=True`)**.

---

## 9. Kịch bản làm bẩn dữ liệu (Synthetic Data Corruption)

Để mô phỏng môi trường sản xuất thực tế khi dữ liệu bị lỗi âm thầm (Silent Failure), hệ thống áp dụng 6 kịch bản tiêm lỗi độc lập:

| STT | Kịch bản lỗi | Cách thực hiện | Bản ghi tác động | Tín hiệu phát hiện (Quality Gate) |
| :---: | --- | --- | :---: | --- |
| 1 | **Drop latest records** | Cắt bỏ 20% bản ghi mới nhất theo ngày xuất bản | 4 records | Vi phạm dữ liệu mới, có thể ảnh hưởng SLA |
| 2 | **Blank summary** | Xóa rỗng trường `summary` về chuỗi rỗng `""` | 3 records | Vi phạm `ExpectColumnValueLengthsToBeBetween` -> **FAIL** |
| 3 | **Inject noise** | Chèn chuỗi ký tự rác `@#$%^&*NOISE` vào đầu summary | 3 records | Suy giảm nghiêm trọng độ tương đồng cosine vector |
| 4 | **Truncate title** | Cắt ngắn tiêu đề bài báo xuống chỉ còn 5 ký tự | 3 records | Phá hủy tính năng exact title lookup |
| 5 | **Stale date** | Lùi ngày xuất bản về quá khứ xa (`2020-01-01`) | 3 records | Thử thách khả năng phát hiện trôi dạt của Freshness SLA |
| 6 | **Duplicate rows** | Nhân bản ngẫu nhiên 3 dòng dữ liệu và ghép vào cuối | 3 records | Vi phạm `ExpectColumnValuesToBeUnique` -> **FAIL** |

Log chi tiết về các lỗi được ghi nhận đầy đủ tại `data/results/corruption_log.json`.

---

## 10. Bảng đối chiếu 3 trạng thái: Baseline vs Corrupted vs Repaired

| Chỉ số / Tiêu chí | Baseline | Corrupted | Repaired | Thay đổi do Lỗi | Khả năng Phục hồi |
| --- | :---: | :---: | :---: | :---: | :---: |
| **Số lượng mẫu đánh giá** | 10 | 10 | 10 | Giữ nguyên | Đồng nhất thực nghiệm |
| **Retrieval Hit Rate** | **1.0000** | **0.5000** | **1.0000** | **-50.0%** (Rơi mạnh) | **100% Phục hồi** |
| **Mean Token F1** | **0.5754** | **0.3306** | **0.5754** | **-42.5%** (Mất ngữ cảnh) | **100% Phục hồi** |
| **Judge Accuracy** | **0.5000** | **0.3000** | **0.5000** | **-40.0%** | **100% Phục hồi** |
| **Mean Judge Score** | **3.20** | **2.30** | **3.20** | **-28.1%** | **100% Phục hồi** |
| **Data Quality Gate (GX 1.x)** | **PASS** | **FAIL** | **PASS** | Bắt trúng lỗi | Bảo vệ hoàn toàn |
| **Freshness SLA** | **PASS** | **PASS** | **PASS** | Trong ngưỡng 25% | Đạt SLA |

### Phân tích định lượng & Quan hệ nhân quả

1. **Hiện tượng Silent Failure:** Khi dữ liệu bị tiêm lỗi (abstract bị xóa trắng, tiêu đề bị cắt cụt, chèn ký tự nhiễu), hệ thống embedding không báo lỗi code runtime nhưng vector representation bị lệch pha hoàn toàn. Hậu quả là **Retrieval Hit Rate sụt giảm 50%**, dẫn tới câu trả lời của LLM mất căn cứ ngữ cảnh. Điều này chứng minh: nếu không có tầng **Data Observability**, hệ thống AI sẽ âm thầm trả lời sai cho người dùng cuối mà quản trị viên không hề hay biết.
2. **Năng lực phòng thủ của Great Expectations:** Chốt kiểm định chất lượng GX 1.x đã lập tức chuyển trạng thái sang **FAIL** do vi phạm tính duy nhất (`paper_id`) và độ dài tối thiểu của tóm tắt, ngăn chặn việc sử dụng dữ liệu lỗi trong sản xuất.
3. **Tính Idempotent của cơ chế Repair:** Bằng cách khôi phục lại từ nguồn gốc đáng tin cậy (`data/raw/crossref_records.json`), toàn bộ các chỉ số đã trở lại chính xác 100% như trạng thái Baseline, khẳng định tính toàn vẹn của chu trình tự chữa lành.

---

## 11. Vấn đề tích hợp kỹ thuật và cách giải quyết

Trong quá trình ghép nối các module, nhóm đã gặp và giải quyết 3 thách thức kỹ thuật:

1. **Cú pháp Great Expectations 1.x:** 
   - *Vấn đề:* GX 1.x đã loại bỏ cú pháp DataContext cũ (`add_datasource`, `create_expectation_suite` theo kiểu 0.x), gây lỗi `AttributeError`.
   - *Giải pháp:* Chuyển sang mô hình Ephemeral Context mới: `gx.get_context(mode="ephemeral")`, `data_sources.add_pandas()`, và `ValidationDefinition`.
2. **Thứ tự tham số trong hàm tiện ích `write_json`:**
   - *Vấn đề:* Hàm `write_json` trong `core/utils.py` có chữ ký `write_json(path, payload)`. Khi một số hàm gọi theo kiểu `write_json(payload, path)`, Python báo lỗi `'list' object has no attribute 'parent'`.
   - *Giải pháp:* Rà soát và chuẩn hóa toàn bộ các điểm gọi theo đúng chuẩn `write_json(path, payload)`.
3. **Mã hóa ký tự Unicode trên Windows Terminal (CP1252):**
   - *Vấn đề:* Ký tự mũi tên unicode `→` trong console log gây `UnicodeEncodeError` trên môi trường Windows mặc định.
   - *Giải pháp:* Thay thế các ký tự đồ họa đặc biệt bằng ký tự ASCII chuẩn `->` và thiết lập `PYTHONIOENCODING=utf-8`.

---

## 12. Điểm thưởng đạt được (Bonus Items)

Nhóm đã hoàn thành trọn vẹn cả 3 hạng mục Bonus:

1. **B1: Interactive Observability Dashboard (+5đ):** 
   - Đã xây dựng trang dashboard tương tác sinh tự động bằng HTML5 + Chart.js tại `data/reports/observability_dashboard.html`.
   - Chạy qua lệnh: `python script/run_dashboard.py`.
2. **B2: Automated Self-Healing Pipeline (+5đ):** 
   - Đã cài đặt module tự động giám sát chất lượng và tự kích hoạt sửa chữa an toàn trong `src/pipelines/self_healing.py`.
   - Chạy qua lệnh: `python script/run_self_healing.py`.
3. **B3: Automated Test Suite với Pytest (+5đ):**
   - Đã viết bộ test tự động gồm 7 test cases kiểm thử từ Ingestion, Cleaning, GX Quality Gate đến Retrieval và Idempotent Repair tại `tests/test_pipeline.py`.
   - Kết quả: **7 passed in 16.12s**. Chạy qua lệnh: `python -m pytest -v tests/`.

---

## 13. Checklist nghiệm thu bài nộp

- [x] `python script/run_phase1.py` chạy exit code 0 thành công
- [x] `python script/run_corruption_flow.py` chạy exit code 0 thành công
- [x] `data/reports/corruption_report.md` có bảng đối chiếu Baseline vs Corrupted vs Repaired
- [x] Có đủ các file `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`
- [x] `data/results/corruption_log.json` ghi nhận đầy đủ 6 dạng lỗi
- [x] Bộ unit test Pytest chạy pass 100% (`7 passed`)
- [x] Dashboard quan sát chất lượng dữ liệu hoạt động hoàn hảo
- [x] Module tự phục hồi (Self-Healing) tự kích hoạt khi phát hiện lỗi
- [x] File `.env` không bị commit vào Git (được bảo vệ trong `.gitignore`)
- [x] Đã hoàn thành các file báo cáo theo đúng quy chuẩn bài lab
