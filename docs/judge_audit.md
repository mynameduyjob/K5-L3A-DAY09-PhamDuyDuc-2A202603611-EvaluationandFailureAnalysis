# Đánh giá Judge (Judge Audit)

Lệnh replay: `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5`.

| Tiêu chí | n | κ | Precision | Recall | Đạt sàn κ≥0.6, P≥0.8, R≥0.7? | Quyết định |
|---|---:|---:|---:|---:|---|---|
| `tone_ok` | 100 | 0.757 | 0.857 | 0.800 | Đạt | Chỉ dùng sau khi khóa rubric; không bao giờ dùng để xác minh tiền hoặc phê duyệt. |
| `helpful` | 100 | 0.375 | 1.000 | 0.300 | Không đạt | Loại khỏi gate: bỏ sót 21 trên 30 trường hợp con người đánh FAIL. |

## 5 trường hợp bất đồng tone_ok

Đây là 5 trường hợp bất đồng đầu tiên theo thứ tự CSV. Nhãn con người là tham chiếu replay; nhãn sản xuất sẽ cần đánh giá độc lập.

| Mã | Judge | Con người | Đúng theo nhãn replay | Ghi chú |
|---|---|---|---|---|
| H-008 | PASS | FAIL | Con người | Cách dùng "em/anh" quá thân mật; rubric cần tính đến mức độ trang trọng với khách hàng. |
| H-017 | PASS | FAIL | Con người | "Bạn ơi… nha" không phù hợp trong bối cảnh chăm sóc khách hàng. |
| H-029 | PASS | FAIL | Con người | Yêu cầu khách hàng chờ mà không giải thích tiến trình hoặc bước tiếp theo. |
| H-042 | FAIL | PASS | Con người | Phản hồi lịch sự, cụ thể và phù hợp; judge quá nghiêm khắc. |
| H-051 | FAIL | PASS | Con người | Từ tiếng Anh "refund" không làm cho câu trả lời lịch sự, rõ ràng trở nên không phù hợp. |

## Tại sao loại bỏ helpful

Ma trận nhầm lẫn: TP=9, FP=0, FN=21, TN=70. Hiệu chỉnh Rogan–Gladen điều chỉnh tỷ lệ lỗi quan sát từ 0.09 lên 0.30 sử dụng recall 0.30 và specificity 1.0. Judge chỉ đánh FAIL các ví dụ cực đoan, nên tỷ lệ false-negative quá cao cho cổng release. Precision hoàn hảo không bù đắp được recall kém.

Đây là phán quyết từ CSV replay công khai, không phải đánh giá độc lập mới. Trước khi sử dụng tone judge làm cổng, cần: ẩn judge, thu thập mẫu held-out mới, hai người dán nhãn, và giải quyết bất đồng theo rubric viết sẵn. Không bao giờ dùng LLM judge cho phê duyệt, quyền sở hữu, hoặc tính đúng sai của tiền.
