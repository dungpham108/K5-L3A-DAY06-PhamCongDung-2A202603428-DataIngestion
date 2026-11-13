# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **Học viên: Phạm Công Dũng (`2A202603428` · Lớp `L3A`)**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu (`data/pdfs/`) | 🧩 Chiến lược (`starter/src/`) | 🎯 Benchmark (`benchmark/questions.json`) |
|---|---|---|
| **33 trang nội dung hợp lệ** (trên 43 trang vật lý, 3 PDF) | **3 cấu hình (`A`, `B`, `C`)** cùng model & vector store | **20 câu hỏi** (`15 dev` / `5 test`, gồm `6` câu có metadata filter) |

---

## Cách cài đặt và chạy tái lập (Quick Reproduction)

### 1. Cài đặt môi trường Python (`Python 3.11–3.14`)

Từ thư mục gốc của repository:

```powershell
# Tạo môi trường ảo (nếu chưa có)
python -m venv starter/.venv

# Cài đặt dependencies
starter\.venv\Scripts\python.exe -m pip install -r starter/requirements.txt
```

Cấu hình biến môi trường (tùy chọn copy từ `.env.example`):

```powershell
Copy-Item starter/.env.example starter/.env
```

> **Lưu ý về Vector Store & Embedding Model:**
> - **Embedding Model:** Mặc định sử dụng mô hình semantic đa ngôn ngữ chạy local **`minishlab/potion-multilingual-128M`** (`256` chiều, chắt lọc từ `BAAI/bge-m3`, hỗ trợ tiếng Việt, chuẩn hóa L2) thông qua thư viện `model2vec`. Không cần API key trả phí và không dùng vector giả lập (mock).
> - **Vector Store:** Hỗ trợ **2 chế độ lưu trữ bền vững (persistent)** trong [`starter/src/store.py`](starter/src/store.py):
>   - `VECTOR_STORE_MODE=auto` / `qdrant_local`: Lưu trữ bền vững trên đĩa bằng **Qdrant Local Persistent Store** tại `results/qdrant_storage/` (chạy ngay không cần Docker daemon).
>   - `VECTOR_STORE_MODE=pgvector`: Lưu trữ trên **PostgreSQL 16 + pgvector** (`docker compose -p day6_student_starter up -d --wait` trong `starter/`).

### 2. Kiểm tra hạ tầng (Setup Check)

```powershell
starter\.venv\Scripts\python.exe starter/scripts/check_setup.py
```

### 3. (Tùy chọn) Tái tạo Corpus PDF và bộ câu hỏi Benchmark

Corpus và benchmark đã được tạo sẵn trong `data/` và `benchmark/`. Nếu muốn chạy lại script khởi tạo:

```powershell
starter\.venv\Scripts\python.exe starter/scripts/build_corpus.py
starter\.venv\Scripts\python.exe starter/scripts/build_benchmark.py
```

### 4. Chạy toàn bộ Pipeline (Ingestion $\rightarrow$ Chunking $\rightarrow$ Embedding $\rightarrow$ Store $\rightarrow$ Benchmark A/B/C)

Có thể chạy từ thư mục gốc hoặc từ thư mục `starter/`:

```powershell
# Cách 1: Chạy từ thư mục gốc của repo
starter\.venv\Scripts\python.exe -m starter.src.run

# Cách 2: Chạy từ thư mục starter/
cd starter
.\.venv\Scripts\python.exe -m src.run
cd ..
```

### 5. Xuất bảng kiểm định thủ công (Manual Audit cho Tiêu chí 2, 3, 4)

```powershell
starter\.venv\Scripts\python.exe starter/scripts/generate_manual_audits.py
```

---

## Cấu trúc thư mục & Đường dẫn dữ liệu / kết quả

```text
.
├── STUDENT.md                                    # Thông tin học viên
├── README.md                                     # Hướng dẫn cài đặt, chạy và đường dẫn dữ liệu
├── data/
│   ├── manifest.json                             # Manifest corpus (3 PDF, 43 trang vật lý, 33 trang hợp lệ)
│   └── pdfs/
│       ├── doc_01_academic_handbook_2025.pdf     # Sổ tay Học vụ 2025 (16 trang vật lý, 12 trang hợp lệ)
│       ├── doc_02_academic_handbook_2026.pdf     # Sổ tay Học vụ 2026 (14 trang vật lý, 11 trang hợp lệ)
│       └── doc_03_ai_data_governance_2026.pdf    # Quy chuẩn AI & Dữ liệu 2026 (13 trang vật lý, 10 trang hợp lệ)
├── benchmark/
│   └── questions.json                            # 20 câu hỏi (15 dev: q01..q15, 5 test: q16..q20)
├── starter/
│   ├── requirements.txt                          # Danh sách thư viện và phiên bản cố định
│   ├── .env.example                              # Mẫu cấu hình môi trường (không chứa secret)
│   ├── scripts/
│   │   ├── check_setup.py                        # Kiểm tra kết nối store & model
│   │   ├── build_corpus.py                       # Sinh bộ PDF corpus và manifest.json
│   │   ├── build_benchmark.py                    # Sinh và kiểm chứng trích dẫn benchmark/questions.json
│   │   └── generate_manual_audits.py             # Chấm và xuất bảng audit thủ công (coherence, metadata, grounding)
│   └── src/
│       ├── models.py                             # Dataclasses: DocumentPage, Chunk, BenchmarkQuestion
│       ├── ingestion.py                          # Đọc PDF, lọc trang loại trừ, chuẩn hóa văn bản & ghép hyphenation
│       ├── chunking.py                           # Chiến lược fixed_size (A) và by_paragraph (B, C)
│       ├── embeddings.py                         # MyEmbedder (minishlab/potion-multilingual-128M, 256d)
│       ├── store.py                              # PgVectorStore & QdrantLocalStore (upsert idempotent, xóa chunk cũ, filter)
│       ├── evaluation.py                         # Tính Hit@1, Evidence Hit@3, Filter Compliance và tổng hợp metrics
│       └── run.py                                # Điểm vào chạy thực nghiệm A/B/C và kiểm chứng nạp lại (re-ingestion)
├── results/
│   ├── metrics_summary.json                      # Tổng hợp kết quả định lượng A, B, C trên dev và test
│   ├── traces_all.json                           # Full top-3 retrieval traces của cả 3 chiến lược (60 truy vấn)
│   ├── traces_dev.json                           # Top-3 traces trên tập dev (15 câu/chiến lược)
│   ├── traces_test.json                          # Top-3 traces trên tập test (5 câu/chiến lược)
│   ├── ingestion_log.json                        # Nhật ký nạp và lọc từng trang PDF
│   ├── reingestion_check.json                    # Bằng chứng nạp lại không nhân đôi (98->98) & xóa chunk cũ (98->92->98)
│   ├── manual_audit_coherence.json               # Chấm độ mạch lạc 10 vị trí cùng nội dung (Tiêu chí 2)
│   ├── manual_audit_metadata.json                # Chấm 15 chunk & 6 câu hỏi có metadata filter (Tiêu chí 3)
│   └── manual_audit_grounding.json               # Chấm chất lượng grounding trên 5 câu test (Tiêu chí 4)
├── artifacts/
│   └── experiment_log.csv                        # Nhật ký thực nghiệm các cấu hình A, B, C
└── report/
    └── individual/
        ├── 2A202603428_PhamCongDung.md           # Báo cáo cá nhân hoàn chỉnh
        └── MSSV_HoTen.md                         # Bản sao đồng bộ với báo cáo cá nhân
```

---

## Tóm tắt kết quả thực nghiệm

| Chiến lược | Cấu hình | Số chunk | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 | Coherence (10 mẫu) | Filter Compliance (Dev / Test) | Grounding (Test) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **A** | `fixed_size` (`size=500`, `overlap=50`), không filter | 126 | `1/15` (6.67%) | `3/15` (20.00%) | `0/5` (0.00%) | `1/5` (20.00%) | `0.80 / 2.00` | `0/4` / `0/2` (0%) | `1.20 / 2.00` |
| **B** | `by_paragraph` (`max_size=750`), không filter | 98 | `9/15` (60.00%) | `14/15` (93.33%) | `2/5` (40.00%) | `3/5` (60.00%) | `2.00 / 2.00` | `0/4` / `0/2` (0%) | `1.60 / 2.00` |
| **C (Chọn)** | `by_paragraph` (`max_size=750`) + Metadata Filter (`year`, `source`, ...) | 98 | **`9/15` (60.00%)** | **`15/15` (100.00%)** | **`2/5` (40.00%)** | **`4/5` (80.00%)** | **`2.00 / 2.00`** | **`4/4` / `2/2` (100%)** | **`1.80 / 2.00`** |

Xem phân tích chi tiết, ví dụ lỗi cụ thể và lập luận đánh đổi trong báo cáo cá nhân: [`report/individual/2A202603428_PhamCongDung.md`](report/individual/2A202603428_PhamCongDung.md).

---

## Tài liệu hướng dẫn gốc của Lab

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector & Qdrant | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |
