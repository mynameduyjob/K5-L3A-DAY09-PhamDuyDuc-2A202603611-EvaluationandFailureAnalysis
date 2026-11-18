# Trace case: quyết định sai đầu tiên trên C-002

Lệnh (chạy từ `src/`):

```bash
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 55
python -m lab9.trace_case --shape fixed --claim C-002 --seed 55
```

| Trường | Phát hiện |
|---|---|
| Thử nghiệm | `seeded_regression C-002@55`, report `E-seeded_regression-20261118-a6e5`; eval set SHA prefix `a6e5`. |
| Triệu chứng | Grader Lab 8 báo `status resolved != denied`; ledger ghi hoàn tiền 20.000đ và count 1, trong khi nhãn mong đợi hoàn tiền 0 và count 0. |
| Bước sai đầu tiên | Sự kiện 3, `model_override`: `{"delay_days": 5}`. Sự kiện 2 (Investigator) đã đọc đơn hàng chính xác từ DB. |
| Tại sao là bước đầu tiên | Sự kiện 1–2 thiết lập handoff và đơn hàng DB. Sự kiện 3 thay thế thời gian trễ 5 ngày từ ticket. Sự kiện 4 báo giá 20.000đ và sự kiện 5 cam kết một hoàn tiền. Sự kiện 6 phản hồi cùng số tiền, nên phản hồi không phải nguồn sai lệch của thử nghiệm này. |
| Failure mode | FM-03 `ticket_trust`. |
| Phản thực (counterfactual) | Với `fixed` trên cùng claim và seed, sự kiện 3 `quote` là `no_entitlement`, trạng thái bị từ chối (denied), và ledger hoàn tiền/count đều bằng 0. Không xảy ra `model_override`. |
| Kiểm tra hồi quy | `DbFactKept` trả false khi trace chứa `model_override`; `RefundAmountCorrect` trả false khi ledger và nhãn khác nhau. `tests/test_lab9_graders.py` kiểm thử các hợp đồng grader đó. Lệnh trên xác nhận fail trên mutant và pass trên `fixed`. |
| Chưa rõ | Trace cho thấy sự thay thế quan sát được và tác động; nó không xác định được tại sao model tin ticket. |

Trace không chứa sự kiện phản hồi với số tiền sai trong trường hợp này: phản hồi khớp với 20.000đ trong ledger, mặc dù bản thân hoàn tiền không được phê duyệt bởi kết quả mong đợi. Đây là lý do FM-03 phải được phát hiện qua grader DB-fact và outcome, trong khi FM-08 cần một assertion riêng so sánh phản hồi với ledger.
