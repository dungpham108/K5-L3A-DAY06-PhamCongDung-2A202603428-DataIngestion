# Starter · PostgreSQL + pgvector / Qdrant Persistent Store

Thư mục `starter/` chứa toàn bộ mã nguồn thực thi pipeline Data Ingestion Engineering và đánh giá Benchmark cho 3 chiến lược **A**, **B**, **C**. Hỗ trợ cả hai chế độ lưu trữ vector bền vững:
1. **Qdrant Persistent Local Store (`qdrant_local` / `auto`)**: Lưu trực tiếp xuống đĩa tại `results/qdrant_storage/`, chạy độc lập không cần Docker daemon.
2. **PostgreSQL 16 + pgvector (`pgvector`)**: Chạy qua Docker Compose (`docker-compose.yml` + `init.sql`).

## Cấu trúc

```text
starter/
├── docker-compose.yml               # PostgreSQL 16 + pgvector, chỉ mở cổng local 127.0.0.1:55433
├── init.sql                         # Bật extension vector khi tạo database mới
├── requirements.txt                 # Dependencies cố định phiên bản (pypdf, model2vec, qdrant-client, psycopg, ...)
├── .env.example                     # Cấu hình mẫu; copy thành .env
├── scripts/
│   ├── check_setup.py               # Kiểm tra hạ tầng vector store & mô hình embedding
│   ├── build_corpus.py              # Tạo 3 file PDF corpus (33 trang nội dung hợp lệ) + manifest.json
│   ├── build_benchmark.py           # Tạo và xác thực 20 câu hỏi benchmark (15 dev / 5 test)
│   └── generate_manual_audits.py    # Xuất bảng chấm thủ công Tiêu chí 2, 3, 4
├── src/
│   ├── models.py                    # Cấu trúc dữ liệu DocumentPage, Chunk, BenchmarkQuestion
│   ├── ingestion.py                 # Đọc PDF, lọc trang bìa/mục lục/trắng/tham khảo, chuẩn hóa text
│   ├── chunking.py                  # Chia chunk fixed_size (A) và by_paragraph (B, C)
│   ├── embeddings.py                # MyEmbedder dùng minishlab/potion-multilingual-128M (256 chiều)
│   ├── store.py                     # PgVectorStore & QdrantLocalStore (upsert idempotent, xóa chunk cũ, filter)
│   ├── evaluation.py                # Đánh giá truy xuất Hit@1, Evidence Hit@3, Filter Compliance
│   └── run.py                       # Pipeline chính chạy thực nghiệm A/B/C và xuất kết quả
├── data/                            # Bản sao corpus PDF, manifest.json và benchmark.json
└── results/                         # Bản sao đầy đủ các file trace, metrics và manual audit
```

## 1. Cài đặt môi trường và kiểm tra hạ tầng

Từ thư mục `starter/`:

```powershell
cd starter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/check_setup.py
```

Nếu dùng PostgreSQL + pgvector qua Docker Desktop:

```powershell
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

Nếu không bật Docker Desktop, `VECTOR_STORE_MODE=auto` sẽ tự động sử dụng **Qdrant Persistent Local Store** và báo `Setup OK`.

## 2. Chạy Pipeline và Benchmark

Từ thư mục `starter/`:

```powershell
python -m src.run
python scripts/generate_manual_audits.py
```

Kết quả được ghi đồng thời vào `../results/` (thư mục gốc của repo) và `starter/results/`.
