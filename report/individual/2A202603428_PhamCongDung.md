# Báo cáo cá nhân — Day 6

- **Họ và tên:** Phạm Công Dũng
- **MSSV:** `2A202603428`
- **Lớp:** `L3A`
- **Thời điểm chạy thực nghiệm:** `2026-11-13T10:32:54Z` (`2026-11-13 17:32:54 +07:00`)

---

## Dữ liệu và pipeline

- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - **Chủ đề hẹp:** Bộ Quy chế Học vụ, Tuyển sinh, Đào tạo Tín chỉ Đại học và Quy định Kỹ thuật Quản trị Dữ liệu / Hạ tầng Vector AI nội bộ giai đoạn 2025–2026.
  - **Nguồn và giấy phép:** Gồm 3 tài liệu PDF (`doc_01_academic_handbook_2025.pdf`, `doc_02_academic_handbook_2026.pdf`, `doc_03_ai_data_governance_2026.pdf`) được biên찬 và phát hành mở theo giấy phép **CC0-1.0 Public Domain Dedication** (tài liệu học thuật/kỹ thuật mở phục vụ thực hành Data Ingestion Engineering, được phép lưu trữ và tái phân phối trên repository, cam kết **không chứa thông tin định danh cá nhân — PII** hay dữ liệu mật). Chi tiết từng tệp, mã băm `SHA-256`, thời điểm truy cập và danh sách trang được khai báo đầy đủ tại [`data/manifest.json`](../../data/manifest.json).
  - **Số trang vật lý và số trang nội dung hợp lệ:**
    - Tổng số trang PDF vật lý: **43 trang** trên 3 tệp PDF:
      1. `handbook-2025` (`data/pdfs/doc_01_academic_handbook_2025.pdf`): **16 trang vật lý** $\rightarrow$ **12 trang nội dung hợp lệ** (trang 3–14, gồm `18.374` ký tự chuẩn hóa); loại trừ **4 trang** (trang 1: trang bìa, trang 2: mục lục, trang 15: trang trống `0` ký tự mô phỏng lỗi bản quét/in, trang 16: tài liệu tham khảo).
      2. `handbook-2026` (`data/pdfs/doc_02_academic_handbook_2026.pdf`): **14 trang vật lý** $\rightarrow$ **11 trang nội dung hợp lệ** (trang 3–13, gồm `16.922` ký tự chuẩn hóa); loại trừ **3 trang** (trang 1: trang bìa, trang 2: mục lục, trang 14: tài liệu tham khảo).
      3. `ai-governance-2026` (`data/pdfs/doc_03_ai_data_governance_2026.pdf`): **13 trang vật lý** $\rightarrow$ **10 trang nội dung hợp lệ** (trang 3–12, gồm `16.213` ký tự chuẩn hóa); loại trừ **3 trang** (trang 1: trang bìa, trang 2: mục lục, trang 13: tài liệu tham khảo).
    - **Tổng cộng toàn corpus:** **33 trang nội dung hữu ích hợp lệ** (vượt yêu cầu tối thiểu $\ge 30$ trang nội dung), tổng cộng **`51.509` ký tự** văn bản sau chuẩn hóa; **10 trang bị loại trừ** được ghi vết tự động vào [`results/ingestion_log.json`](../../results/ingestion_log.json).
  - **Quy tắc tính trang:** Chỉ tính các trang PDF vật lý thực sự chứa nội dung quy chế/tiêu chuẩn kỹ thuật (`status="accepted"`, độ dài $\ge 50$ ký tự sau chuẩn hóa). Loại trừ hoàn toàn: (1) trang bìa (`cover_page`), (2) trang mục lục (`toc_page`), (3) trang trống hoặc trang lỗi trích xuất dưới 50 ký tự (`empty_or_unreadable_page`), và (4) trang chỉ chứa danh mục tài liệu tham khảo (`references_page`).

- **Chuẩn hóa, lỗi và giới hạn:**
  - **Quy trình đọc và chuẩn hóa (`starter/src/ingestion.py`):**
    1. Sử dụng `pypdf` (`v6.21.4`) trích xuất văn bản từng trang vật lý, giữ nguyên số thứ tự trang (`page` đánh số từ `1`).
    2. Chuẩn hóa Unicode về dạng dựng sẵn **`NFC`** (`unicodedata.normalize("NFC", text)`) để đồng nhất dấu tiếng Việt giữa tài liệu và câu hỏi truy vấn.
    3. Loại bỏ các ký tự điều khiển ẩn (`U+200B` zero-width space, `U+FEFF` BOM, `U+00AD` soft hyphen), chuyển khoảng trắng không ngắt dòng (`U+00A0`) thành khoảng trắng chuẩn và chuẩn hóa các ký tự ghép PDF (`ﬁ` $\rightarrow$ `fi`, `ﬂ` $\rightarrow$ `fl`).
    4. Khôi phục cấu trúc đoạn văn: nối các dòng bị ngắt mềm do khổ giấy PDF A4 trong cùng một điều khoản, đồng thời bảo toàn ranh giới đoạn văn (`\n\n`) tại các đầu mục (`Chương`, `Phần`, `Điều X.Y`, `[Mã tài liệu: ...]`).
  - **Ghi nhận lỗi và giới hạn xử lý tài liệu:**
    - Phát hiện và ghi log chính xác **trang 15 của `handbook-2025`** là trang rỗng (`0` ký tự, `reason="empty_or_unreadable_page"`) cùng 9 trang bìa/mục lục/tham khảo trong [`results/ingestion_log.json`](../../results/ingestion_log.json).
    - **Giới hạn:** `pypdf` hoạt động tốt trên PDF có lớp văn bản gốc (digital-born PDF) nhưng không tự đọc được ảnh quét (scanned image) nếu không tích hợp OCR (như Tesseract/PaddleOCR), và việc nối dòng dựa trên biểu thức chính quy (`_PARAGRAPH_START_RE`) được thiết kế phù hợp với văn bản quy chế có cấu trúc `Chương / Phần / Điều`.

- **Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:**
  - **Embedding Model:**
    - **Provider:** Local HuggingFace / `model2vec` (`v0.10.0`, `tokenizers==0.23.3`, `safetensors==0.8.0`).
    - **Tên và phiên bản model:** `minishlab/potion-multilingual-128M` (mô hình semantic embedding đa ngữ hỗ trợ 101 ngôn ngữ bao gồm tiếng Việt, được chưng cất từ mô hình ngữ nghĩa `BAAI/bge-m3`).
    - **Số chiều vector:** `256` chiều (`float32`).
    - **Cách xử lý Document và Query:** Cả văn bản chunk (`embed_documents`) và câu hỏi (`embed_query`) đều được mã hóa qua cùng không gian ngữ nghĩa 256 chiều và chuẩn hóa độ dài đơn vị $L_2$ (`L2-normalization`) để tích vô hướng tương đương chính xác với độ tương đồng Cosine. Hệ thống kiểm tra nghiêm ngặt kích thước vector đầu ra và **báo lỗi dừng ngay (`RuntimeError`) nếu mô hình gặp sự cố, tuyệt đối không fallback sang vector ngẫu nhiên hay mock**.
  - **Vector Store:**
    - **Hệ lưu trữ sử dụng:** **Qdrant Persistent Local Store** (`qdrant-client==1.20.0`) lưu trữ bền vững trực tiếp trên đĩa tại `results/qdrant_storage/` (collection `day06_knowledge_chunks`). Mã nguồn trong [`starter/src/store.py`](../../starter/src/store.py) đồng thời hiện thực đầy đủ cả hai lớp **`QdrantLocalStore`** và **`PgVectorStore`** (`psycopg[binary]==3.3.8`, PostgreSQL 16 + `pgvector 0.8.7`), cho phép chuyển đổi qua biến môi trường `VECTOR_BACKEND=qdrant` hoặc `VECTOR_BACKEND=pgvector`.
    - **Metric và chế độ tìm kiếm:** **Cosine Similarity (`Distance.COSINE`)**, chế độ **Exact Search** (`SearchParams(exact=True)`) đảm bảo không có sai số xấp xỉ giữa 3 chiến lược.
    - **Kiểm tra nạp lại không trùng (Idempotent Re-ingestion) & xóa chunk lỗi thời:** Mỗi chunk được ánh xạ sang mã định danh tất định (`UUIDv5` từ `day06:{strategy}:{chunk_id}`). Khi nạp lại lần 2 cùng phiên bản corpus, số lượng bản ghi của cả 3 chiến lược giữ nguyên tuyệt đối (`A: 126 -> 126`, `B: 98 -> 98`, `C: 98 -> 98`). Khi kiểm thử thu gọn một tài liệu từ 3 chunk xuống 2 chunk, hàm `upsert` tự động xóa chunk dư thừa (`3 -> 2`). Minh chứng lưu tại [`results/reingestion_check.json`](../../results/reingestion_check.json).
  - **Lệnh chạy tái lập và chi phí:**
    ```powershell
    # Từ thư mục gốc của repo:
    starter\.venv\Scripts\python.exe starter/scripts/build_corpus.py
    starter\.venv\Scripts\python.exe starter/scripts/build_benchmark.py
    starter\.venv\Scripts\python.exe starter/scripts/check_setup.py
    starter\.venv\Scripts\python.exe -m starter.src.run
    starter\.venv\Scripts\python.exe starter/scripts/generate_manual_audits.py
    ```
  - **Chi phí thực tế:** **`0,00 USD`** (chạy 100% bằng mô hình semantic embedding cục bộ và Qdrant lưu trữ trên đĩa local).

- **Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:**
  - **Metadata bắt buộc trên mọi chunk:**
    - `document_id` (`string`): Mã định danh tài liệu (`handbook-2025`, `handbook-2026`, `ai-governance-2026`).
    - `source` (`string`): Đường dẫn tương đối tới tệp PDF gốc (`data/pdfs/doc_01_academic_handbook_2025.pdf`, ...).
    - `page` (`integer`): Số trang vật lý thực tế trong tệp PDF (`3` đến `14`).
  - **Các trường metadata bổ sung phục vụ lọc và truy vết:**
    - `year` (`integer`: `2025` hoặc `2026`): Trích xuất trực tiếp bằng biểu thức chính quy từ dòng tiêu đề chuẩn `[Năm ban hành: YYYY]` in trên từng trang PDF. **Lý do chọn:** Giúp phân biệt chính xác quy chế học vụ năm 2025 và bản cập nhật năm 2026 khi hai văn bản có cùng cấu trúc chương mục và thuật ngữ nhưng thay đổi định mức (hạn nộp hồ sơ, đơn giá học phí, lệ phí phúc khảo, số tín chỉ tốt nghiệp).
    - `section` (`string`: `tuyen_sinh`, `hoc_phi_hoc_bong`, `danh_gia_diem`, `tot_nghiep`, `ho_tro_sinh_vien`, `pipeline_ingestion`, ...): Trích xuất trực tiếp từ trường `[Chuyên mục: <section>]` trên trang PDF. **Lý do chọn:** Thu hẹp phạm vi tìm kiếm vào đúng chuyên mục nghiệp vụ mà người dùng đang tra cứu.
    - `category` (`string`: `hoc_vu` hoặc `quan_tri_du_lieu_ai`), `audience` (`string`: `sinh_vien` hoặc `ky_su_va_nghien_cuu`), `version` (`string`: `2025.1`, `2026.1`, `2026.2`): Trích xuất trực tiếp từ tiêu đề trang PDF, không tự suy đoán bất kỳ giá trị nào.

---

## Cấu hình và benchmark

- **A / B / C (tham số cụ thể, khác biệt duy nhất B–C):**
  - **Chiến lược A (`fixed_size` — Baseline):** Chia văn bản từng trang theo cửa sổ ký tự cố định `size = 500` ký tự, `overlap = 50` ký tự (bước nhảy `450` ký tự). Lưu đầy đủ metadata nhưng **không áp dụng bộ lọc metadata** khi truy xuất (`apply_filter = False`). Sinh ra **126 chunks** (độ dài trung bình `445,4` ký tự, min `60`, max `500`).
  - **Chiến lược B (`by_paragraph` — Structure-aware):** Chia văn bản theo ranh giới đoạn văn / điều khoản (`\n\n`), gắn tiêu đề Chương/Phần ở đầu mỗi điều khoản để giữ ngữ cảnh và giới hạn `max_size = 750` ký tự (`overlap = 0`). Giữ nguyên toàn bộ metadata và **không áp dụng bộ lọc metadata** khi truy xuất (`apply_filter = False`). Sinh ra **98 chunks** (độ dài trung bình `519,6` ký tự, min `310`, max `729`). **Khác biệt duy nhất giữa A và B là thuật toán chia chunk.**
  - **Chiến lược C (`by_paragraph` + `metadata_filter`):** Sử dụng **cùng thuật toán chia chunk và cùng tập 98 chunks giống hệt Chiến lược B** (`max_size = 750`, `overlap = 0`), nhưng **bật bộ lọc metadata (`apply_filter = True`)** đối với các câu hỏi có cung cấp ngữ cảnh lọc (`year`, `section`, `category`). Với các câu hỏi không có filter (`filter: null`), Chiến lược C chạy truy xuất không lọc. **Khác biệt duy nhất giữa B và C là việc kích hoạt bộ lọc metadata trước khi xếp hạng Cosine.**

- **$\ge 20$ câu: phân chia $\ge 15$ dev / $\ge 5$ test, câu metadata filter và cách kiểm chứng evidence:**
  - **Quy mô và phân chia:** Bộ benchmark tại [`benchmark/questions.json`](../../benchmark/questions.json) gồm **20 câu hỏi**, được thiết kế và khóa cứng trước khi chạy thử nghiệm thành **15 câu `dev`** (`q01`–`q15`) và **5 câu `test`** (`q16`–`q20`).
  - **Phân bố loại câu hỏi:** Bao phủ cả 3 tài liệu nguồn và 4 nhóm câu hỏi: câu hỏi trực tiếp (`truc_tiep`), câu hỏi diễn đạt lại (`dien_dat_lai`), câu hỏi có điều kiện/ngoại lệ (`dieu_kien_ngoai_le`), và câu hỏi kiểm tra bộ lọc metadata (`metadata_filter`).
  - **Câu hỏi kiểm tra Metadata Filter (6 câu: 4 câu dev, 2 câu test — vượt mức tối thiểu $\ge 3$ câu và $\ge 1$ câu test):**
    - Tập `dev` (4 câu): `q01` (`year=2025, section='tuyen_sinh'`), `q04` (`year=2025, section='danh_gia_diem'`), `q09` (`year=2026, section='hoc_phi_hoc_bong'`), `q14` (`category='quan_tri_du_lieu_ai', section='pipeline_ingestion'`).
    - Tập `test` (2 câu): `q16` (`year=2025, section='ho_tro_sinh_vien'`), `q17` (`year=2026, section='tot_nghiep'`).
    - **Nguyên tắc chống gian lận filter:** Giá trị filter là **ngữ cảnh phiên làm việc giả định được cung cấp trước khi truy xuất** (ví dụ sinh viên đang chọn tra cứu quy chế năm 2025 hoặc năm 2026 trên cổng thông tin); tuyệt đối không đưa `gold_source_id`, `gold_page` hay đáp án vào câu hỏi hoặc filter.
  - **Cách kiểm chứng Evidence:** Trước khi chạy truy xuất, hàm `_verify_benchmark_evidence()` trong `starter/src/run.py` tự động đối chiếu từng `evidence_quote` của cả 20 câu hỏi với văn bản đã chuẩn hóa trên đúng `(gold_source_id, gold_page)`, xác nhận `20/20` đoạn bằng chứng tồn tại nguyên văn 100% (lưu log xác minh trong [`results/ingestion_log.json`](../../results/ingestion_log.json)).

- **Tiêu chí chọn chiến lược đã chốt trước khi xem test:**
  1. **Ưu tiên 1:** Đạt **Evidence Hit@3** cao nhất trên tập `dev` (15 câu) và đạt ngưỡng tối thiểu $\ge 80\%$.
  2. **Ưu tiên 2:** Đạt **Hit@1** trên tập `dev` cao hơn và **Filter Compliance** trên các câu có filter của tập `dev` đạt `100%` (`4/4`).
  3. **Ưu tiên 3:** Đạt điểm trung bình **Chunk Coherence** (`/2`) trên 10 vị trí nguồn cao hơn, sau đó xét đến thời gian và tài nguyên lưu trữ.

---

## Kết quả

### Bảng 1: Độ chính xác truy xuất (Retrieval Accuracy) và Tài nguyên theo Chiến lược & Split

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---:|---:|---:|---:|---:|
| **A** (`fixed_size`, 500/50, không lọc) | `dev` | `1/15` (6,67%) | `3/15` (20,00%) | 126 | Ingest: `0,5923s` / Query (20 câu): `0,0948s` (Tổng: `0,6871s`) | `0,00 USD` |
| **A** (`fixed_size`, 500/50, không lọc) | `test` | `0/5` (0,00%) | `1/5` (20,00%) | 126 | Như trên | `0,00 USD` |
| **B** (`by_paragraph`, max 750, không lọc) | `dev` | `9/15` (60,00%) | `14/15` (93,33%) | 98 | Ingest: `0,5786s` / Query (20 câu): `0,0907s` (Tổng: `0,6693s`) | `0,00 USD` |
| **B** (`by_paragraph`, max 750, không lọc) | `test` | `2/5` (40,00%) | `3/5` (60,00%) | 98 | Như trên | `0,00 USD` |
| **C** (`by_paragraph`, max 750 + lọc metadata) | `dev` | `9/15` (60,00%) | **`15/15` (100,00%)** | 98 | Ingest: `0,5218s` / Query (20 câu): `0,1043s` (Tổng: `0,6261s`) | `0,00 USD` |
| **C** (`by_paragraph`, max 750 + lọc metadata) | `test` | `2/5` (40,00%) | **`4/5` (80,00%)** | 98 | Như trên | `0,00 USD` |

*(Ghi chú chẩn đoán: Ở Chiến lược A, dù **Page Hit@3** — tỷ lệ tìm đúng trang nguồn trong top-3 — đạt tới `13/15` trên `dev` và `5/5` trên `test`, nhưng **Evidence Hit@3** chỉ đạt `3/15` và `1/5` vì có tới **`10/15` câu dev** và **`4/5` câu test** bị lỗi **cắt đôi đoạn bằng chứng (`evidence_split_across_chunks_error`)** qua hai chunk 500 ký tự liên tiếp).*

### Bảng 2: Tổng hợp Audit Thủ công (Coherence, Metadata Usefulness và Grounding Quality)

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---:|---:|---:|---:|
| **A** | **`0,80 / 2,00`** (`n = 10`: 2 mức 0, 8 mức 1, 0 mức 2) | **`15/15`** (100% khớp trang nguồn PDF) | Dev: `0/4` (0%) \| Test: `0/2` (0%) | `0 / 4 / 1` (0 câu mức 0; 4 câu mức 1; 1 câu mức 2) — TB: **`1,20 / 2,00`** |
| **B** | **`2,00 / 2,00`** (`n = 10`: 0 mức 0, 0 mức 1, 10 mức 2) | **`15/15`** (100% khớp trang nguồn PDF) | Dev: `0/4` (0%) \| Test: `0/2` (0%) | `0 / 2 / 3` (0 câu mức 0; 2 câu mức 1; 3 câu mức 2) — TB: **`1,60 / 2,00`** |
| **C** | **`2,00 / 2,00`** (`n = 10`: 0 mức 0, 0 mức 1, 10 mức 2) | **`15/15`** (100% khớp trang nguồn PDF) | Dev: **`4/4` (100%)** \| Test: **`2/2` (100%)** | `0 / 1 / 4` (0 câu mức 0; 1 câu mức 1; 4 câu mức 2) — TB: **`1,80 / 2,00`** |

### Đường dẫn trace, nhãn thủ công và cách chọn mẫu

- **Đường dẫn dữ liệu và kết quả thực nghiệm:**
  - Manifest dữ liệu (nguồn, giấy phép, quy tắc tính trang): [`data/manifest.json`](../../data/manifest.json)
  - Bộ câu hỏi Benchmark (15 dev / 5 test, gold evidence): [`benchmark/questions.json`](../../benchmark/questions.json)
  - Nhật ký thí nghiệm 3 chiến lược: [`artifacts/experiment_log.csv`](../../artifacts/experiment_log.csv)
  - Log đọc PDF và loại trừ 10 trang không hợp lệ: [`results/ingestion_log.json`](../../results/ingestion_log.json)
  - Kiểm chứng nạp lại chống trùng & xóa chunk cũ: [`results/reingestion_check.json`](../../results/reingestion_check.json)
  - Tổng hợp thống kê chunk, thời gian, chi phí và Hit@1/Hit@3: [`results/metrics_summary.json`](../../results/metrics_summary.json)
  - Trace truy xuất top-3 đầy đủ (Dev / Test / All): [`results/traces_dev.json`](../../results/traces_dev.json), [`results/traces_test.json`](../../results/traces_test.json), [`results/traces_all.json`](../../results/traces_all.json)
  - Bảng nhãn chấm thủ công Chunk Coherence (10 vị trí): [`results/manual_audit_coherence.json`](../../results/manual_audit_coherence.json) & [`results/manual_audit_coherence.csv`](../../results/manual_audit_coherence.csv)
  - Bảng kiểm tra thủ công Metadata (5 câu test × top-3 = 15 bản ghi/chiến lược): [`results/manual_audit_metadata.json`](../../results/manual_audit_metadata.json)
  - Bảng chấm thủ công Grounding Quality (5 câu test/chiến lược): [`results/manual_audit_grounding.json`](../../results/manual_audit_grounding.json) & [`results/manual_audit_grounding.csv`](../../results/manual_audit_grounding.csv)

- **Cách chọn mẫu và quy trình chấm thủ công:**
  - **Chunk Coherence (10 vị trí nguồn cố định):** Chọn trước khi xem điểm theo quy tắc tất định: lấy đúng **10 `page_id` hợp lệ đầu tiên sau khi sắp xếp từ điển** (`ai-governance-2026_p03` đến `ai-governance-2026_p12`), neo tại điều khoản giữa trang (`Điều X.2`). Ở Chiến lược A, `8/10` vị trí bị cắt mất tiêu đề/chủ ngữ ở đầu chunk và dính tiêu đề điều sau ở cuối chunk (đạt `1/2`), còn `2/10` vị trí (`pos_07` tại trang 9 và `pos_09` tại trang 11) bị cắt đứt ngay giữa mệnh đề điều kiện và mệnh đề hành động làm không hiểu được quy định nếu đọc đơn lẻ (đạt `0/2`), trung bình **`0,80/2,00`**. Ở Chiến lược B và C, cả `10/10` vị trí đều giữ nguyên vẹn điều khoản kèm tiêu đề Phần (đạt **`2,00/2,00`**).
  - **Metadata Usefulness (15 bản ghi top-3 trên tập test mỗi chiến lược):** Đối chiếu thủ công từng bản ghi trong `5 câu test × 3 kết quả = 15 bản ghi` với trang PDF gốc: cả 3 chiến lược đều đạt **`15/15` bản ghi có `source`, `page`, `year`, `section`, `category` đúng thực tế trang nguồn**. Tuy nhiên, xét về **tỷ lệ tuân thủ filter** trên các câu có yêu cầu lọc (`q16` yêu cầu `year=2025, section='ho_tro_sinh_vien'` và `q17` yêu cầu `year=2026, section='tot_nghiep'`), Chiến lược A và B đạt **`0/2`** trên test (và `0/4` trên dev) do luôn trả về lẫn các chunk của năm khác trong top-3; chỉ có Chiến lược C đạt **`2/2` (100%)** trên test và **`4/4` (100%)** trên dev.
  - **Grounding Quality (5 câu test mỗi chiến lược):** Chấm thủ công mức độ đầy đủ bằng chứng của tập top-3 trên `q16`–`q20` (độc lập với câu trả lời LLM):
    - `q16`: A đạt `1/2` (bị cắt giữa từ `"Lệ phí phúc khả"` và lẫn phí 70.000đ năm 2026 ở Top-3); B đạt `2/2` (Top-1 có trọn vẹn Điều 12.2 năm 2025); C đạt `2/2` (cả 3 chunk đều thuộc đúng trang 14 năm 2025).
    - `q17`: A đạt `1/2` (Top-1 nhầm năm 2025, Top-2 năm 2026 bị cắt mất điều kiện vi phạm AI); B đạt `1/2` (Top-1 và Top-3 bị chiếm bởi năm 2025, đẩy Điều 10.1 năm 2026 khỏi top-3); C đạt `2/2` (lọc sạch năm 2025, Top-1 có Điều 10.3 và Top-2 có Điều 10.1 năm 2026).
    - `q18`: A, B, C đều đạt `1/2` (nêu được chuẩn IELTS 6.0 và mã `AIDL-2026`, nhưng thiếu ngưỡng điểm `75/100` ở Điều 8.2).
    - `q19`: A đạt `1/2` (điều kiện và SLA 15 phút / 2 giờ bị tách làm 2 chunk rời); B và C đạt `2/2` (Top-1 chứa trọn vẹn Điều 7.2 trang 9).
    - `q20`: A, B, C đều đạt `2/2` (top-3 chứa đủ SLA P95 `150ms/800ms` và ngân sách API `5,00 USD/tháng` tại trang 11).

---

## Phân tích và kết luận

- **So sánh A–B và B–C; 2 ví dụ sai có ID câu và nguồn:**
  - **So sánh có kiểm soát A và B (Tác động của Chunking):**
    - Thay đổi từ chia cố định 500 ký tự (`A`) sang chia theo cấu trúc đoạn/điều khoản giới hạn 750 ký tự (`B`) giúp giảm 22,2% số lượng chunk (`126` xuống `98` chunks, giảm tổng ký tự lưu trữ từ `56.116` xuống `50.919` do không lặp overlap 50 ký tự), đồng thời tăng vọt **Hit@1 trên dev từ `1/15` (6,67%) lên `9/15` (60,00%)**, **Evidence Hit@3 trên dev từ `3/15` (20,00%) lên `14/15` (93,33%)**, và **Chunk Coherence từ `0,80/2` lên `2,00/2`**. Nguyên nhân cốt lõi là văn bản quy chế có các điều khoản dài 450–650 ký tự chứa điều kiện và ngoại lệ ở cuối câu; cửa sổ cố định 500 ký tự của A cắt đôi điều khoản ở `10/15` câu dev và `4/5` câu test.
  - **So sánh có kiểm soát B và C (Tác động của Metadata Filter):**
    - Giữ nguyên tập 98 chunks của B và chỉ bật bộ lọc metadata (`year`, `section`, `category`) khi câu hỏi có filter giúp tăng **Evidence Hit@3 trên dev từ `14/15` (93,33%) lên `15/15` (100,00%)**, tăng **Evidence Hit@3 trên test từ `3/5` (60,00%) lên `4/5` (80,00%)**, tăng **Grounding Quality từ `1,60/2` lên `1,80/2`** và nâng **Filter Compliance từ `0%` lên `100%`** (`4/4` trên dev, `2/2` trên test) mà không làm tăng chi phí hay số lượng chunk.
  - **Hai ví dụ lỗi cụ thể kèm ID câu hỏi, chunk ID và nguồn:**
    1. **Ví dụ lỗi 1 — Nhiễu chéo phiên bản năm khi thiếu Metadata Filter và lỗi cắt chunk (`q17` trên tập `test`, nguồn chuẩn: `handbook-2026`, trang 12, `section="tot_nghiep"`):**
       - *Câu hỏi `q17`:* Hỏi tổng số tín chỉ tích lũy tối thiểu để xét tốt nghiệp chuẩn và các trường hợp khiến sinh viên Xuất sắc/Giỏi bị hạ một bậc bằng (ngữ cảnh tra cứu: `filter = {"year": 2026, "section": "tot_nghiep"}`).
       - *Lỗi ở Chiến lược A và B:* Do câu hỏi không gõ chữ `"năm 2026"` vào chuỗi văn bản truy vấn, Chiến lược B (không lọc) xếp hạng `handbook-2025_p12_para_03` (`year=2025`, score `0,7783`) ở **Top-1** và `handbook-2025_p09_para_02` (`year=2025`, score `0,6393`) ở **Top-3**. Hai chunk năm 2025 này đã chiếm chỗ và đẩy `handbook-2026_p12_para_01` (chứa quy định chuẩn `132 tín chỉ` của năm 2026) ra khỏi top-3, khiến `Evidence Hit@3 = 0`. Ở Chiến lược A, ngoài việc Top-1 lấy nhầm năm 2025 (`handbook-2025_p12_fix_03`), chunk Top-2 của năm 2026 (`handbook-2026_p12_fix_03`) còn bị cắt cụt ở chữ `"...vượt quá 5% tổng số tín chỉ toàn khó"`, làm mất hoàn toàn điều kiện hạ bậc thứ 3 (vi phạm Quy chế AI tạo sinh).
       - *Khắc phục ở Chiến lược C:* Khi bật `filter = {"year": 2026, "section": "tot_nghiep"}`, toàn bộ các chunk năm 2025 bị loại bỏ trước khi xếp hạng; kết quả trả về `handbook-2026_p12_para_03` ở Top-1 và `handbook-2026_p12_para_01` ở Top-2 (`Evidence Hit@3 = 1`, `Grounding = 2/2`). (Hiện tượng tương tự cũng xảy ra ở câu **`q09` tập `dev`** tại `handbook-2026` trang 5, nơi Chiến lược B bị hai chunk `handbook-2025_p05_para_01` và `_para_02` đẩy chunk học phí `850.000 đồng` của năm 2026 khỏi top-3).
    2. **Ví dụ lỗi 2 — Sai lệch thứ hạng do nhiễu từ khóa cùng chủ đề trong câu hỏi đa điều kiện (`q18` trên tập `test`, nguồn chuẩn: `handbook-2026`, trang 10, `Điều 8.2`):**
       - *Câu hỏi `q18`:* *"Từ năm 2026, bên cạnh chuẩn đầu ra tiếng Anh IELTS Academic tối thiểu 6.0 đối với hệ tiêu chuẩn, sinh viên tất cả các ngành còn bắt buộc phải đạt thêm chứng chỉ năng lực gì và với mức điểm bao nhiêu trước khi xét tốt nghiệp?"* (`filter = null`).
       - *Lỗi ở cả Chiến lược B và C (`Evidence Hit@3 = 0`, `Grounding = 1/2`):* Vì câu hỏi nhắc đến cụm từ `"chuẩn đầu ra tiếng Anh IELTS Academic tối thiểu 6.0"` và `"xét tốt nghiệp"`, mô hình dense embedding `minishlab/potion-multilingual-128M` đã chấm điểm tương đồng cao nhất cho 3 chunk chứa nhiều từ khóa về IELTS và tốt nghiệp nhất:
         - **Rank 1:** `handbook-2026_p10_para_01` (trang 10, `Điều 8.1` — quy định về IELTS Academic 6.0, score `0,8012`).
         - **Rank 2:** `handbook-2026_p03_para_02` (trang 3, `Điều 1.2` — quy đổi IELTS Academic 6.5/6.0 trong tuyển sinh, score `0,7709`).
         - **Rank 3:** `handbook-2026_p12_para_01` (trang 12, `Điều 10.1` — điều kiện xét tốt nghiệp nhắc tới `"đạt chuẩn ngoại ngữ IELTS 6.0 và chứng chỉ AIDL-2026"`, score `0,7350`).
       - Trong khi đó, đoạn bằng chứng chuẩn **`handbook-2026_p10_para_02` (`Điều 8.2` tại trang 10)** — nơi quy định tên đầy đủ của chứng chỉ `AIDL-2026` và ngưỡng điểm **`từ 75/100 điểm trở lên`** — không chứa chữ `"IELTS Academic tối thiểu 6.0"` nên bị tụt xuống hạng 4 (ngoài top-3). Hệ quả là top-3 chỉ cho biết mã chứng chỉ `AIDL-2026` (nhờ Rank 3 ở trang 12) nhưng thiếu mức điểm `75/100`.

- **Chiến lược chọn, đánh đổi, điều kiện áp dụng:**
  - **Chiến lược được chọn:** **Chiến lược C (`by_paragraph` giới hạn 750 ký tự + `metadata_filter` khi có ngữ cảnh lọc)**, được chọn dựa trên tiêu chí đã chốt trước trên tập `dev` (đạt `15/15 = 100%` Evidence Hit@3, `9/15 = 60%` Hit@1, `4/4 = 100%` Filter Compliance và `2,00/2` Coherence trên tập `dev`), và sau đó được xác nhận trên tập `test` độc lập với `4/5 = 80%` Evidence Hit@3 và `1,80/2` Grounding Quality.
  - **Các đánh đổi (Trade-offs):**
    1. *Chi phí thiết kế parser cấu trúc vs. chia cố định:* Chiến lược B và C đòi hỏi văn bản sau chuẩn hóa phải giữ được ranh giới đoạn văn (`\n\n`) và cấu trúc tiêu đề (`Chương / Phần / Điều`); nếu tài liệu nguồn là văn bản thô bị mất hoàn toàn dấu xuống dòng thì `by_paragraph` sẽ suy biến về việc cắt theo câu ở ngưỡng `max_size`.
    2. *Độ nhạy của Metadata Filter (Precision vs. Recall risk):* Bộ lọc cứng (`exact match filter`) ở Chiến lược C đảm bảo độ chính xác phạm vi 100% khi metadata nguồn và filter đầu vào đúng, nhưng nếu người dùng hoặc tầng phân tích ý định (Query Router) gắn sai giá trị filter (ví dụ người dùng hỏi quy chế mới năm 2026 nhưng giao diện giữ bộ lọc mặc định `year=2025`), hệ thống sẽ trả về 0 kết quả đúng (rủi ro mất hoàn toàn Recall).
  - **Điều kiện áp dụng:** Phù hợp cho kho văn bản quy chế, chính sách, tài liệu kỹ thuật có cấu trúc điều khoản rõ ràng và có nhiều phiên bản theo năm/danh mục cần phân tách ngữ cảnh. **Không suy rộng kết luận này thành quy luật tổng quát cho mọi loại dữ liệu phi cấu trúc ngoài phạm vi corpus đã thử nghiệm.**

- **Hạn chế của dữ liệu, nhãn, test nhỏ, đo thời gian/chi phí:**
  - **Hạn chế của dữ liệu:** Corpus gồm 33 trang nội dung hợp lệ (43 trang vật lý) là các tài liệu PDF chuẩn hóa sạch có cấu trúc điều khoản rõ ràng và tiêu đề metadata nhất quán; chưa đại diện cho các tài liệu PDF bảng biểu phức tạp nhiều cột, công thức toán học dày đặc hoặc bản quét OCR nhiễu nặng.
  - **Sai số do kích thước tập Test nhỏ:** Tập `test` chỉ gồm **5 câu hỏi** (trong đó có 2 câu có filter), nên **mỗi câu đúng/sai làm thay đổi tới `20%` điểm phần trăm** trên tập test (và `50%` trên chỉ số Filter Compliance của tập test). Do đó kết quả trên tập test chỉ mang tính minh họa kiểm증, không dùng để tuyên bố độ chính xác thống kê diện rộng.
  - **Nguy cơ thiên lệch người chấm (Self-evaluation bias) và sử dụng công cụ AI:** Việc thiết kế câu hỏi và chấm điểm thủ công (Chunk Coherence, Metadata, Grounding Quality) do chính tác giả bài làm thực hiện nên có nguy cơ thiên lệch xác nhận. Để minh bạch, toàn bộ quy tắc chọn mẫu 10 vị trí đầu tiên, tiêu chí chọn chiến lược và toàn văn các chunk top-3 đều được lưu công khai trong `results/`. Trong quá trình thực hiện, tác giả có sử dụng AI Assistant (Antigravity) để hỗ trợ viết mã nguồn khung pipeline và định dạng bảng báo cáo; toàn bộ mã nguồn, kết quả chạy thực tế, đoạn trích bằng chứng (`evidence_quote`) và nhãn audit đều đã được chạy kiểm chứng trực tiếp bằng lệnh thực thi và đối chiếu với trang PDF gốc.
  - **Hạn chế đo thời gian và chi phí:** Thời gian ingest (~`0,52s`–`0,59s`) và query (~`0,09s`–`0,10s` cho 20 câu) được đo trên máy cá nhân với quy mô 98–126 chunks dùng mô hình tĩnh `model2vec` và Qdrant local; khi mở rộng lên hàng trăm nghìn trang hoặc gọi API qua mạng, độ trễ và chi phí token sẽ tăng tuyến tính theo quy mô.

- **Nếu làm lại hoặc mở rộng, cải tiến gì?**
  1. **Mở rộng Hybrid Retrieval (Dense + BM25 Lexical Search):** Như đã phân tích ở lỗi câu `q18`, việc kết hợp điểm tương đồng vector ngữ nghĩa (`minishlab/potion-multilingual-128M`) với tìm kiếm từ khóa `BM25` (hoặc `Reciprocal Rank Fusion - RRF`) sẽ giúp bắt trúng các cụm danh từ đặc thù trong phần câu hỏi chính (`"bắt buộc phải đạt thêm chứng chỉ năng lực gì"`, `"với mức điểm bao nhiêu"`) thay vì bị lấn át bởi cụm từ mở đầu `"IELTS Academic tối thiểu 6.0"`.
  2. **Tăng `top_k` kết hợp Cross-Encoder Reranker:** Truy xuất ứng viên rộng hơn (`top_k = 10`) từ Vector Store rồi dùng mô hình Reranker chấm điểm cặp `(question, chunk)` để chọn ra `top-3` cuối cùng; trên câu `q18`, chunk đúng `handbook-2026_p10_para_02` nằm ngay ở hạng 4 nên `top_k = 10` + Reranker sẽ đưa chunk này vào top-3.
  3. **Bổ sung Parent-Child Chunking (Small-to-Big Retrieval):** Đánh chỉ mục vector trên từng điều khoản nhỏ để tối ưu độ chính xác so khớp, nhưng khi trả về ngữ cảnh cho tầng Grounding thì trả kèm các điều khoản liền kề trong cùng một Chương/Trang để tránh thiếu thông tin bổ trợ giữa `Điều 10.1` và `Điều 10.3` (như ở câu `q17`).
