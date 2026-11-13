"""Create and verify the 20-question benchmark (15 dev / 5 test) before running experiments.
Also pre-registers the strategy selection criteria and leakage control rules.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = ROOT_DIR / "benchmark"
STARTER_DATA_DIR = ROOT_DIR / "starter" / "data"


BENCHMARK_METADATA: dict[str, Any] = {
    "benchmark_name": "Day 06 Data Ingestion Retrieval Benchmark (20 Questions: 15 Dev / 5 Test)",
    "created_before_run": True,
    "split_methodology": (
        "Phân chia cố định trước khi chạy thí nghiệm theo tỷ lệ 15 câu dev (q01–q15) và 5 câu test (q16–q20), "
        "phân tầng (stratified) theo cả 3 tài liệu nguồn (handbook-2025, handbook-2026, ai-governance-2026) "
        "và theo 4 nhóm câu hỏi: trực tiếp (truc_tiep), diễn đạt lại (dien_dat_lai), điều kiện/ngoại lệ (dieu_kien_ngoai_le), "
        "và kiểm tra bộ lọc metadata (metadata_filter). Có tổng cộng 6 câu gắn metadata filter (4 câu ở dev, 2 câu ở test)."
    ),
    "leakage_risk_and_mitigation": (
        "Nguy cơ rò rỉ (Data Leakage Risk): Các tài liệu handbook-2025 và handbook-2026 có cấu trúc chương mục tương đồng, "
        "nên nếu câu hỏi không nêu năm hoặc nếu chỉnh sửa tham số dựa trên tập test sẽ gây hiện tượng quá khớp (overfitting). "
        "Biện pháp kiểm soát: (1) Khóa cứng 5 câu test (q16–q20) trước khi chạy pipeline, chỉ dùng 15 câu dev để chọn cấu hình; "
        "(2) Không bao giờ đưa gold_source_id, gold_page hay đáp án vào câu hỏi hoặc vào filter; "
        "(3) Giá trị filter (year, section, category) đóng vai trò là ngữ cảnh phiên tra cứu của người dùng được cung cấp trước khi truy xuất."
    ),
    "pre_registered_selection_criteria": (
        "Tiêu chí chọn chiến lược đã chốt trước khi xem tập test: "
        "(1) Ưu tiên 1: Điểm Evidence Hit@3 trên tập dev cao nhất; "
        "(2) Ưu tiên 2: Nếu Evidence Hit@3 bằng nhau, chọn chiến lược có Hit@1 trên tập dev cao hơn và tỷ lệ tuân thủ filter đạt 100%; "
        "(3) Ưu tiên 3: Điểm trung bình Chunk Coherence (/2) và Grounding Quality (/2) cao hơn, chi phí và thời gian hợp lý."
    ),
}


QUESTIONS: list[dict[str, Any]] = [
    # ==================== DEV SPLIT (15 QUESTIONS: q01 - q15) ====================
    {
        "id": "q01",
        "split": "dev",
        "type": "metadata_filter",
        "question": "Thời hạn đóng cổng nộp hồ sơ xét tuyển đại học chính quy đợt 1 và mức lệ phí đăng ký cho mỗi nguyện vọng là bao nhiêu?",
        "expected_answer": "Theo quy chế năm 2025, hạn nộp hồ sơ xét tuyển trực tuyến đợt 1 là trước 17h00 ngày 30 tháng 6 năm 2025 và lệ phí là 150.000 đồng/nguyện vọng.",
        "gold_source_id": "handbook-2025",
        "gold_page": 3,
        "evidence_quote": "Thí sinh đăng ký xét tuyển đại học chính quy đợt 1 năm 2025 phải hoàn thành nộp hồ sơ trực tuyến và tải lên minh chứng trước 17h00 ngày 30 tháng 6 năm 2025. Lệ phí đăng ký xét tuyển năm 2025 được quy định ở mức cố định là 150.000 đồng cho mỗi nguyện vọng",
        "filter": {"year": 2025, "section": "tuyen_sinh"},
        "filter_context_note": "Ngữ cảnh giả định cung cấp trước: Thí sinh đang tra cứu tại Cổng lưu trữ quy chế khóa tuyển sinh năm 2025, chuyên mục Tuyển sinh (year=2025, section='tuyen_sinh').",
    },
    {
        "id": "q02",
        "split": "dev",
        "type": "dieu_kien_ngoai_le",
        "question": "Sinh viên rút học phần nhận điểm W từ tuần thứ 3 đến tuần thứ 8 trong năm học 2025 phải thỏa mãn điều kiện tín chỉ tối thiểu nào và chịu bao nhiêu phần trăm học phí?",
        "expected_answer": "Được rút tối đa 2 học phần mỗi kỳ với điều kiện tổng số tín chỉ còn lại sau khi rút không thấp hơn 14 tín chỉ, và sinh viên vẫn phải nộp 50% học phí của học phần đó (sau tuần 8 bị từ chối trừ trường hợp tai nạn cấp cứu có xác nhận bệnh viện).",
        "gold_source_id": "handbook-2025",
        "gold_page": 4,
        "evidence_quote": "Từ tuần thứ 3 đến hết tuần thứ 8 của học kỳ chính, sinh viên được phép nộp đơn xin rút bớt tối đa 2 học phần mỗi học kỳ với điều kiện tổng số tín chỉ còn lại sau khi rút không được thấp hơn ngưỡng tối thiểu 14 tín chỉ. Học phần rút trong giai đoạn này được nhận điểm W trên bảng điểm, không tính vào điểm trung bình học kỳ (GPA) nhưng sinh viên vẫn phải nộp 50% học phí của học phần đó.",
        "filter": None,
    },
    {
        "id": "q03",
        "split": "dev",
        "type": "dieu_kien_ngoai_le",
        "question": "Trong năm học 2025, những trường hợp ngoại lệ nào khiến sinh viên dù đạt GPA trên 3,85 vẫn không được đưa vào danh sách xét cấp học bổng Khuyến khích học tập (KKHT)?",
        "expected_answer": "Sinh viên đang trong thời gian chịu kỷ luật từ mức khiển trách trở lên, hoặc có bất kỳ học phần nào đăng ký học lại, học cải thiện điểm trong học kỳ đang xét sẽ không được xét học bổng KKHT.",
        "gold_source_id": "handbook-2025",
        "gold_page": 5,
        "evidence_quote": "Sinh viên đang trong thời gian chịu kỷ luật từ mức khiển trách trở lên, hoặc sinh viên có bất kỳ học phần nào đăng ký học lại, học cải thiện điểm trong học kỳ đang xét sẽ không được đưa vào danh sách xét cấp học bổng KKHT của học kỳ đó, kể cả khi điểm GPA đạt trên 3,85.",
        "filter": None,
    },
    {
        "id": "q04",
        "split": "dev",
        "type": "metadata_filter",
        "question": "Trọng số điểm đánh giá quá trình, điểm thi kết thúc học phần và ngưỡng điểm liệt bài thi cuối kỳ được quy định như thế nào?",
        "expected_answer": "Theo quy chế năm 2025, điểm quá trình chiếm 40%, điểm thi kết thúc học phần chiếm 60%, và ngưỡng điểm liệt bài thi cuối kỳ là dưới 3,0/10,0 (sẽ bị quy về điểm F).",
        "gold_source_id": "handbook-2025",
        "gold_page": 6,
        "evidence_quote": "Điểm tổng kết học phần năm 2025 được tính theo thang điểm 10 (làm tròn đến một chữ số thập phân) từ hai thành phần: điểm đánh giá quá trình chiếm trọng số 40% và điểm thi kết thúc học phần chiếm trọng số 60%. Tuy nhiên, nếu điểm thi kết thúc học phần đạt dưới 3,0/10,0 (ngưỡng điểm liệt bài thi cuối kỳ năm 2025), điểm tổng kết học phần sẽ bị quy về điểm F",
        "filter": {"year": 2025, "section": "danh_gia_diem"},
        "filter_context_note": "Ngữ cảnh giả định cung cấp trước: Sinh viên khóa 2025 tra cứu mục Đánh giá điểm áp dụng cho năm 2025 (year=2025, section='danh_gia_diem').",
    },
    {
        "id": "q05",
        "split": "dev",
        "type": "dieu_kien_ngoai_le",
        "question": "Sinh viên xin nghỉ học tạm thời vì nhu cầu cá nhân năm 2025 cần đáp ứng đồng thời ba điều kiện gì và khác gì so với nghỉ học do điều trị bệnh hoặc nghĩa vụ quân sự?",
        "expected_answer": "Nghỉ vì lý do cá nhân cần: (1) đã học ít nhất 1 học kỳ chính, (2) CPA từ 2,00/4,00 trở lên, (3) không bị kỷ luật hoặc cảnh báo học vụ mức 2 trở lên, và thời gian nghỉ tính vào thời gian học tối đa. Ngược lại, nghỉ do điều trị bệnh dài ngày hoặc nghĩa vụ quân sự không áp dụng ngưỡng CPA 2,00 và không tính vào thời gian đào tạo tối đa.",
        "gold_source_id": "handbook-2025",
        "gold_page": 8,
        "evidence_quote": "Sinh viên xin nghỉ học tạm thời vì lý do cá nhân (không phải lý do y tế hay nghĩa vụ quân sự) bắt buộc phải thỏa mãn đồng thời ba điều kiện: (1) đã học tại trường ít nhất 1 học kỳ chính hoàn chỉnh; (2) điểm trung bình chung tích lũy (CPA) tại thời điểm nộp đơn đạt từ 2,00/4,00 trở lên; và (3) không đang trong thời gian bị xem xét kỷ luật hoặc bị cảnh báo học vụ mức 2 trở lên.",
        "filter": None,
    },
    {
        "id": "q06",
        "split": "dev",
        "type": "dien_dat_lai",
        "question": "Nếu sinh viên năm 2025 đã tích lũy đủ 112 tín chỉ nhưng điểm CPA chỉ nằm trong khoảng từ 2,00 đến dưới 2,20 thì hoàn thành khối lượng tốt nghiệp cuối khóa bằng cách nào?",
        "expected_answer": "Sinh viên không được làm Đồ án tốt nghiệp mà phải đăng ký học 3 học phần chuyên ngành thay thế (tổng cộng 10 tín chỉ) kết hợp viết Chuyên đề tổng hợp cuối khóa.",
        "gold_source_id": "handbook-2025",
        "gold_page": 9,
        "evidence_quote": "Sinh viên đã tích lũy đủ 112 tín chỉ nhưng có CPA đạt từ 2,00 đến dưới 2,20 sẽ không được làm Đồ án tốt nghiệp mà phải đăng ký học 3 học phần chuyên ngành thay thế (tổng cộng 10 tín chỉ) kết hợp viết Chuyên đề tổng hợp cuối khóa",
        "filter": None,
    },
    {
        "id": "q07",
        "split": "dev",
        "type": "truc_tiep",
        "question": "Tỷ lệ trùng lặp toàn văn tối đa cho phép trên hệ thống Turnitin đối với đồ án tốt nghiệp năm 2025 là bao nhiêu và hành vi thi hộ bị xử lý thế nào?",
        "expected_answer": "Tỷ lệ trùng lặp (Similarity Index) trên Turnitin không được vượt quá 20% (không tính tài liệu tham khảo). Hành vi nhờ thi hộ hoặc thi hộ bị Đình chỉ học tập 1 năm ở lần đầu và Buộc thôi học nếu tái phạm.",
        "gold_source_id": "handbook-2025",
        "gold_page": 11,
        "evidence_quote": "Báo cáo thực tập, tiểu luận và đồ án tốt nghiệp năm 2025 phải được kiểm tra qua hệ thống đối sánh văn bản Turnitin với tỷ lệ trùng lặp toàn văn (Similarity Index) không vượt quá 20% (không tính phần danh mục tài liệu tham khảo). Hành vi nhờ người khác thi hộ hoặc thi hộ người khác bị xử lý kỷ luật Đình chỉ học tập 1 năm ở lần vi phạm đầu tiên và Buộc thôi học nếu tái phạm.",
        "filter": None,
    },
    {
        "id": "q08",
        "split": "dev",
        "type": "dieu_kien_ngoai_le",
        "question": "Để đăng ký học chương trình thứ hai (song bằng) năm 2025, sinh viên cần tích lũy tối thiểu bao nhiêu tín chỉ và khi nào bị buộc dừng học ngành thứ hai?",
        "expected_answer": "Phải hoàn thành tối thiểu 2 học kỳ chính của ngành thứ nhất, tích lũy ít nhất 32 tín chỉ, CPA đạt từ 2,50 (kèm đạt ngưỡng đầu vào ngành hai) hoặc từ 2,80 trở lên. Nếu trong quá trình học mà CPA ngành thứ nhất tụt xuống dưới 2,00/4,00 thì buộc phải dừng học chương trình ngành thứ hai.",
        "gold_source_id": "handbook-2025",
        "gold_page": 13,
        "evidence_quote": "Sinh viên được nộp hồ sơ đăng ký học thêm chương trình đào tạo ngành thứ hai khi đã hoàn thành tối thiểu 2 học kỳ chính của ngành thứ nhất, tích lũy ít nhất 32 tín chỉ",
        "filter": None,
    },
    {
        "id": "q09",
        "split": "dev",
        "type": "metadata_filter",
        "question": "Đơn giá học phí mỗi tín chỉ và số tín chỉ tích lũy tối thiểu trong học kỳ để được xét Học bổng Khuyến khích Học tập (KKHT) là bao nhiêu?",
        "expected_answer": "Theo quy chế cập nhật năm 2026, đơn giá học phí là 850.000 đồng/tín chỉ và sinh viên phải tích lũy tối thiểu 16 tín chỉ tính điểm lần đầu trong học kỳ xét cấp (không có điểm dưới B, rèn luyện từ 82 trở lên).",
        "gold_source_id": "handbook-2026",
        "gold_page": 5,
        "evidence_quote": "Trong năm học 2026, đơn giá học phí chương trình tiêu chuẩn ngành Công nghệ Thông tin, Khoa học Dữ liệu và Trí tuệ Nhân tạo được điều chỉnh lên mức 850.000 đồng cho mỗi tín chỉ học phí",
        "filter": {"year": 2026, "section": "hoc_phi_hoc_bong"},
        "filter_context_note": "Ngữ cảnh giả định cung cấp trước: Sinh viên đang tra cứu chính sách áp dụng cho năm học 2026 tại chuyên mục Học phí - Học bổng (year=2026, section='hoc_phi_hoc_bong').",
    },
    {
        "id": "q10",
        "split": "dev",
        "type": "dieu_kien_ngoai_le",
        "question": "Theo quy chế năm 2026, sinh viên lần đầu chạm ngưỡng Cảnh báo học vụ mức 3 (buộc thôi học) được phép nộp đơn xin cứu xét học vụ khi thỏa mãn những điều kiện nào?",
        "expected_answer": "Phải tích lũy được tối thiểu 90 tín chỉ toàn khóa, nộp Đơn xin cứu xét học vụ có chữ ký cam kết của phụ huynh trong vòng 10 ngày làm việc; nếu được duyệt sẽ có 1 học kỳ thử thách cuối cùng và phải đạt GPA học kỳ đó từ 2,00 trở lên.",
        "gold_source_id": "handbook-2026",
        "gold_page": 7,
        "evidence_quote": "sinh viên lần đầu tiên chạm ngưỡng Cảnh báo học vụ mức 3 (ngưỡng buộc thôi học) nhưng đã tích lũy được tối thiểu 90 tín chỉ toàn khóa được phép nộp Đơn xin cứu xét học vụ có chữ ký cam kết của phụ huynh trong vòng 10 ngày làm việc. Nếu được Hội đồng Học vụ chấp thuận, sinh viên được gia hạn 1 học kỳ thử thách cuối cùng và phải đạt GPA học kỳ đó từ 2,00 trở lên",
        "filter": None,
    },
    {
        "id": "q11",
        "split": "dev",
        "type": "truc_tiep",
        "question": "Quy chế năm 2026 quy định giới hạn tỷ lệ văn bản do AI hỗ trợ biên tập trong báo cáo là bao nhiêu và xử phạt thế nào nếu có trích dẫn giả mạo do AI bịa đặt (hallucination)?",
        "expected_answer": "Tỷ lệ nội dung văn bản do AI hỗ trợ biên tập không được vượt quá 30% tổng dung lượng báo cáo và phải kèm Phụ lục Minh bạch AI. Nếu có trích dẫn giả mạo do AI bịa đặt sẽ bị trừ 50% tổng điểm ở lần vi phạm đầu tiên và nhận điểm 0 (buộc làm lại học phần) nếu có từ 3 trích dẫn giả mạo trở lên.",
        "gold_source_id": "handbook-2026",
        "gold_page": 8,
        "evidence_quote": "Tỷ lệ nội dung văn bản do AI hỗ trợ biên tập không được vượt quá 30% tổng dung lượng báo cáo.",
        "filter": None,
    },
    {
        "id": "q12",
        "split": "dev",
        "type": "dien_dat_lai",
        "question": "Sinh viên muốn quy đổi tín chỉ từ các khóa học trực tuyến MOOC quốc tế (Coursera, edX) trong năm 2026 được công nhận tối đa bao nhiêu tín chỉ và phải qua bước kiểm tra nào?",
        "expected_answer": "Được công nhận chuyển đổi tối đa 12 tín chỉ trong toàn khóa học từ các khóa MOOC đã được thẩm định, với điều kiện có chứng chỉ xác thực danh tính và vượt qua bài kiểm tra sát hạch trực tiếp (30 phút) tại bộ môn.",
        "gold_source_id": "handbook-2026",
        "gold_page": 11,
        "evidence_quote": "Sinh viên được phép đăng ký học và đề nghị công nhận chuyển đổi tối đa 12 tín chỉ trong toàn khóa học từ danh mục các khóa học MOOC quốc tế (trên nền tảng Coursera, edX) đã được Hội đồng Khoa thẩm định tương đương. Để được quy đổi điểm, sinh viên phải có chứng chỉ hoàn thành khóa học MOOC kèm xác thực danh tính và vượt qua bài kiểm tra sát hạch trực tiếp (30 phút) tại bộ môn quản lý học phần.",
        "filter": None,
    },
    {
        "id": "q13",
        "split": "dev",
        "type": "dieu_kien_ngoai_le",
        "question": "Quy định kỹ thuật năm 2026 xử lý như thế nào đối với việc nạp dữ liệu Cấp độ L4 (Tuyệt mật) và Cấp độ L3 (Hạn chế) vào cơ sở dữ liệu Vector?",
        "expected_answer": "Tuyệt đối cấm đưa dữ liệu Cấp độ L4 vào kho vector hoặc gửi qua API bên thứ ba. Với dữ liệu Cấp độ L3, chỉ được nạp vào cơ sở dữ liệu vector chạy nội bộ (on-premise) sau khi đã che giấu hoặc băm một chiều (salted SHA-256) toàn bộ các trường thông tin định danh cá nhân (PII).",
        "gold_source_id": "ai-governance-2026",
        "gold_page": 3,
        "evidence_quote": "Tuyệt đối cấm đưa bất kỳ tài liệu nào thuộc Cấp độ L4 vào kho tri thức vector hoặc gửi qua API của mô hình ngôn ngữ bên thứ ba dưới mọi hình thức. Đối với dữ liệu Cấp độ L3, kỹ sư dữ liệu chỉ được phép nạp vào cơ sở dữ liệu vector chạy nội bộ (on-premise) sau khi đã thực hiện bước che giấu hoặc băm một chiều (salted SHA-256) toàn bộ các trường thông tin định danh cá nhân (PII)",
        "filter": None,
    },
    {
        "id": "q14",
        "split": "dev",
        "type": "metadata_filter",
        "question": "Những loại trang nào phải bị loại trừ khi tính số trang nội dung hữu ích của PDF và ngưỡng ký tự tối thiểu đối với mỗi đơn vị tài liệu không phân trang là bao nhiêu?",
        "expected_answer": "Phải loại trừ 4 loại trang: (1) trang bìa, (2) trang mục lục, (3) trang trống/quét lỗi dưới 50 ký tự, và (4) trang chỉ chứa tài liệu tham khảo. Với tài liệu không phân trang (Markdown/HTML/text), mỗi đơn vị nguồn phải đạt tối thiểu 1.500 ký tự sau chuẩn hóa.",
        "gold_source_id": "ai-governance-2026",
        "gold_page": 4,
        "evidence_quote": "Khi kiểm đếm số trang nội dung hữu ích của tệp PDF, pipeline phải tự động phát hiện và loại trừ 4 loại trang không hợp lệ: (1) trang bìa (cover page); (2) trang mục lục (table of contents); (3) trang trống hoặc trang quét ảnh lỗi có độ dài văn bản sau chuẩn hóa dưới 50 ký tự; và (4) trang chỉ chứa danh mục tài liệu tham khảo ở cuối văn bản.",
        "filter": {"category": "quan_tri_du_lieu_ai", "section": "pipeline_ingestion"},
        "filter_context_note": "Ngữ cảnh giả định cung cấp trước: Kỹ sư dữ liệu đang tra cứu danh mục Quản trị dữ liệu AI, phần tiêu chuẩn Pipeline Ingestion (category='quan_tri_du_lieu_ai', section='pipeline_ingestion').",
    },
    {
        "id": "q15",
        "split": "dev",
        "type": "truc_tiep",
        "question": "Thời hạn lưu trữ tối thiểu của nhật ký truy xuất (Query Trace) là bao nhiêu ngày và trong bao lâu phải xóa vĩnh viễn vector khi tài liệu bị thu hồi quyền sử dụng?",
        "expected_answer": "Nhật ký truy xuất (Query Trace) phải được lưu trữ tối thiểu 180 ngày ở định dạng JSON hoặc JSONL; khi tài liệu bị thu hồi quyền sử dụng, toàn bộ vector và văn bản của tài liệu đó phải được xóa vĩnh viễn trong vòng 24 giờ.",
        "gold_source_id": "ai-governance-2026",
        "gold_page": 8,
        "evidence_quote": "Nhật ký truy xuất đầy đủ (bao gồm câu hỏi, danh sách top-3 chunk ID, điểm tương đồng cosine, metadata và văn bản chunk) phải được lưu trữ phục vụ kiểm toán tối thiểu 180 ngày ở định dạng JSON hoặc JSONL. Khi một tài liệu bị thu hồi quyền sử dụng, toàn bộ vector và bản ghi văn bản của tài liệu đó phải được xóa vĩnh viễn khỏi cơ sở dữ liệu vector và bản sao lưu trực tuyến trong vòng 24 giờ.",
        "filter": None,
    },

    # ==================== TEST SPLIT (5 QUESTIONS: q16 - q20) ====================
    {
        "id": "q16",
        "split": "test",
        "type": "metadata_filter",
        "question": "Thời hạn nộp đơn đề nghị phúc khảo điểm thi kết thúc học phần và mức lệ phí phúc khảo cho mỗi bài thi được quy định như thế nào?",
        "expected_answer": "Theo quy chế năm 2025, sinh viên nộp đơn phúc khảo trực tuyến trong thời hạn 7 ngày liên tục (kể cả thứ Bảy, Chủ nhật) kể từ ngày công bố điểm với lệ phí là 50.000 đồng/bài thi (hoàn trả 100% nếu điểm thay đổi từ 0,5 điểm trở lên).",
        "gold_source_id": "handbook-2025",
        "gold_page": 14,
        "evidence_quote": "Sinh viên có thắc mắc về điểm thi kết thúc học phần được quyền nộp đơn đề nghị phúc khảo trực tuyến trong thời hạn 7 ngày календар (7 ngày liên tục kể cả thứ Bảy, Chủ nhật) kể từ ngày điểm thi được công bố trên hệ thống. Lệ phí phúc khảo năm 2025 là 50.000 đồng cho mỗi bài thi tự luận hoặc trắc nghiệm",
        "filter": {"year": 2025, "section": "ho_tro_sinh_vien"},
        "filter_context_note": "Ngữ cảnh giả định cung cấp trước: Sinh viên tra cứu quy định phúc khảo áp dụng cho năm học 2025 tại mục Hỗ trợ sinh viên (year=2025, section='ho_tro_sinh_vien').",
    },
    {
        "id": "q17",
        "split": "test",
        "type": "metadata_filter",
        "question": "Tổng số tín chỉ tích lũy tối thiểu để xét công nhận tốt nghiệp đại học chuẩn là bao nhiêu và những trường hợp nào khiến sinh viên loại Xuất sắc hoặc Giỏi bị hạ một bậc xếp loại tốt nghiệp?",
        "expected_answer": "Theo quy chế cập nhật năm 2026, cần tích lũy tối thiểu 132 tín chỉ. Sinh viên đạt CPA Xuất sắc hoặc Giỏi bị hạ một bậc xếp loại nếu: (1) số tín chỉ học lại do điểm F vượt quá 5% tổng tín chỉ toàn khóa (trên 6,6 tín chỉ), hoặc (2) từng bị kỷ luật từ mức Cảnh cáo trở lên, hoặc (3) vi phạm Quy chế sử dụng AI tạo sinh bị trừ từ 50% điểm học phần trở lên.",
        "gold_source_id": "handbook-2026",
        "gold_page": 12,
        "evidence_quote": "Tổng số tín chỉ tích lũy tối thiểu để xét tốt nghiệp chương trình đại học chuẩn năm 2026 là 132 tín chỉ (tăng 2 tín chỉ so với mức 130 tín chỉ năm 2025 do bổ sung học phần Đạo đức và Pháp luật AI)",
        "filter": {"year": 2026, "section": "tot_nghiep"},
        "filter_context_note": "Ngữ cảnh giả định cung cấp trước: Sinh viên tra cứu điều kiện xét tốt nghiệp cập nhật năm 2026 (year=2026, section='tot_nghiep').",
    },
    {
        "id": "q18",
        "split": "test",
        "type": "dieu_kien_ngoai_le",
        "question": "Từ năm 2026, bên cạnh chuẩn đầu ra tiếng Anh IELTS Academic tối thiểu 6.0 đối với hệ tiêu chuẩn, sinh viên tất cả các ngành còn bắt buộc phải đạt thêm chứng chỉ năng lực gì và với mức điểm bao nhiêu trước khi xét tốt nghiệp?",
        "expected_answer": "Sinh viên tất cả các ngành bắt buộc phải hoàn thành và đạt chứng chỉ nội bộ 'Năng lực Ứng dụng AI có Trách nhiệm và Quản trị Dữ liệu' (mã chứng chỉ AIDL-2026) với điểm bài thi đánh giá thực hành đạt từ 75/100 điểm trở lên.",
        "gold_source_id": "handbook-2026",
        "gold_page": 10,
        "evidence_quote": "Kể từ năm 2026, toàn bộ sinh viên tất cả các ngành đào tạo trước khi xét tốt nghiệp bắt buộc phải hoàn thành và đạt chứng chỉ nội bộ 'Năng lực Ứng dụng AI có Trách nhiệm và Quản trị Dữ liệu' (mã chứng chỉ AIDL-2026) với điểm bài thi đánh giá thực hành đạt từ 75/100 điểm trở lên.",
        "filter": None,
    },
    {
        "id": "q19",
        "split": "test",
        "type": "dien_dat_lai",
        "question": "Khi phát hiện sự cố cấu hình sai bộ lọc metadata làm lộ các đoạn dữ liệu hạn chế của kỹ sư cho nhóm sinh viên, đội vận hành phải ngắt kết nối bộ sưu tập vector và gửi báo cáo sơ bộ trong thời hạn bao lâu?",
        "expected_answer": "Đội vận hành phải thực hiện ngắt kết nối (circuit-breaker) bộ sưu tập vector bị lỗi trong vòng tối đa 15 phút kể từ lúc phát hiện và gửi báo cáo sự cố sơ bộ cho Ban An toàn Thông tin trong vòng 2 giờ.",
        "gold_source_id": "ai-governance-2026",
        "gold_page": 9,
        "evidence_quote": "Khi phát hiện sự cố bộ lọc metadata bị cấu hình sai khiến người dùng thuộc nhóm sinh viên truy xuất được các chunk dữ liệu chỉ dành cho kỹ sư nội bộ hoặc quản trị viên, nhóm vận hành phải thực hiện ngắt kết nối (circuit-breaker) bộ sưu tập vector bị lỗi trong vòng tối đa 15 phút kể từ lúc phát hiện và gửi báo cáo sự cố sơ bộ cho Ban An toàn Thông tin trong vòng 2 giờ.",
        "filter": None,
    },
    {
        "id": "q20",
        "split": "test",
        "type": "truc_tiep",
        "question": "Cam kết độ trễ truy vấn top-3 ở phân vị thứ 95 (P95 latency SLA) đối với kho tri thức dưới 100.000 chunk và hạn mức ngân sách API thử nghiệm hàng tháng cho mỗi môi trường cá nhân là bao nhiêu?",
        "expected_answer": "Độ trễ truy vấn top-3 ở phân vị P95 không được vượt quá 150 mili-giây đối với mô hình cục bộ và không quá 800 mili-giây khi gọi API qua mạng. Hạn mức ngân sách API thử nghiệm tối đa là 5,00 USD/tháng (cảnh báo ở mức 80% tức 4,00 USD và tự động khóa nạp lại ở 100%).",
        "gold_source_id": "ai-governance-2026",
        "gold_page": 11,
        "evidence_quote": "thời gian phản hồi của một truy vấn top-3 (không tính thời gian sinh câu trả lời của LLM) ở phân vị thứ 95 (P95 latency) không được vượt quá 150 mili-giây đối với mô hình cục bộ và không vượt quá 800 mili-giây khi phải gọi API tạo vector truy vấn qua mạng.",
        "filter": None,
    },
]


def build_and_verify_benchmark() -> None:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    STARTER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        **BENCHMARK_METADATA,
        "total_questions": len(QUESTIONS),
        "dev_count": sum(1 for q in QUESTIONS if q["split"] == "dev"),
        "test_count": sum(1 for q in QUESTIONS if q["split"] == "test"),
        "filter_question_count": sum(1 for q in QUESTIONS if q.get("filter")),
        "dev_filter_count": sum(1 for q in QUESTIONS if q["split"] == "dev" and q.get("filter")),
        "test_filter_count": sum(1 for q in QUESTIONS if q["split"] == "test" and q.get("filter")),
        "questions": QUESTIONS,
    }

    out_path = BENCHMARK_DIR / "questions.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (STARTER_DATA_DIR / "benchmark.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"Saved {len(QUESTIONS)} questions ({payload['dev_count']} dev / {payload['test_count']} test, "
        f"{payload['filter_question_count']} with metadata filter) to {out_path}"
    )


if __name__ == "__main__":
    build_and_verify_benchmark()
