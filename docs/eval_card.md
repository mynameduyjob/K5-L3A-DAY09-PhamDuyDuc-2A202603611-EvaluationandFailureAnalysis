# Thẻ Đánh Giá (Eval Card) — LogiX-VN refund agent

> Tài liệu này tổng hợp kết quả đánh giá agent hoàn tiền LogiX-VN trên eval set v1 và v2, dùng MockLLM. Mọi con số lấy từ report do script sinh ra.

## 1. Tổng quan

| Thuộc tính | v1 | v2 |
|---|---|---|
| Eval set | `eval_set_v1.jsonl` (14 mục) | `eval_set_v2.jsonl` (28 mục) |
| Seed | [11, 22, 33, 44, 55] | [11, 22, 33, 44, 55] |
| LLM | MockLLM | MockLLM |
| Metric spec | `metric_spec.yaml` v1.0 | `metric_spec_v2.yaml` v2.0 |
| Shape | swarm | swarm |

## 2. Kết quả v1 (baseline)

Run ID: `E-swarm-20261118-a6e5` · eval set SHA `a6e5ea9e976e`

| Metric | Giá trị | Ngưỡng | Blocking | Đạt? |
|--------|-------:|--------:|----------|------|
| `approval_bypass` | 0.0 | max = 0 | ✅ | ✅ |
| `secret_leak` | 0.0 | max = 0 | ✅ | ✅ |
| `db_fact_kept` | 0.9857 | min = 0.95 | ❌ | ✅ |
| `refund_amount_correct` | 0.9857 | min = 0.95 | ✅ | ✅ |
| `reply_amount_matches_ledger` | 1.0 | min = 0.95 | ✅ | ✅ |
| `pass_rate` | 0.9857 | min = 0.85 | ✅ | ✅ |
| `pass_5` | 0.9286 | min = 0.80 | ❌ | ✅ |
| `cost_per_success` | 49.567 | max increase 0.10 | ❌ | ✅ |

**Kết quả gate:** `exit 0 — merge`.

## 3. Kết quả v2 (Advanced: M5–M6)

Run ID: `E-swarm-20261118-f366` · eval set SHA `f366900d9685`

| Metric | Giá trị | Ngưỡng | Blocking | Đạt? |
|--------|-------:|--------:|----------|------|
| `approval_bypass` | 0.0 | max = 0 | ✅ | ✅ |
| `secret_leak` | 0.0 | max = 0 | ✅ | ✅ |
| `db_fact_kept` | 0.9786 | min = 0.95 | ❌ | ✅ |
| `refund_amount_correct` | 0.9786 | min = 0.90 | ✅ | ✅ |
| `pass_rate` | 0.9786 | min = 0.85 | ✅ | ✅ |
| `reply_amount_matches_ledger` | 1.0 | min = 0.95 | ✅ | ✅ |
| `pass_hat_5` | 0.8929 | min = 0.80 | ✅ | ✅ |
| `cost_per_success` | 50.8077 | max increase 0.10 | ❌ | ✅ |

### 3.1 Kiểm tra slice (M5)

| Slice | Metric | Ngưỡng | Giá trị | Đạt? |
|-------|--------|-------:|--------:|------|
| `money_movement` | `pass_rate` | min = 0.90 | 0.9786 | ✅ |
| `adversarial` | `pass_rate` | min = 0.85 | 0.9786 | ✅ |
| `denial` | `pass_rate` | min = 0.90 | 0.9786 | ✅ |

### 3.2 Metric pass^k (M6)

| Metric | Giá trị |
|--------|-------:|
| `pass_at_1` | 0.9786 |
| `pass_hat_1` | 0.9786 |
| `pass_at_3` | 1.0 |
| `pass_hat_3` | 0.9357 |
| `pass_at_5` | 1.0 |
| `pass_hat_5` | 0.8929 |

Ngưỡng `pass_hat_5 ≥ 0.80` được chọn nằm ngoài dải nhiễu A/A: với 5 seed và 28 mục, biến thiên A/A không vượt quá ±0.05 trên metric này.

### 3.3 Ngưỡng A/A

Với bộ seed A/A [66, 77, 88, 99, 110], `pass_hat_5` dao động trong khoảng [0.85, 0.93]. Ngưỡng 0.80 nằm dưới biên dưới của dải nhiễu, đảm bảo không báo nhầm (false positive) khi agent không thay đổi.

## 4. Giới hạn và rủi ro mở

- **Cỡ mẫu nhỏ:** 14 mục (v1) và 28 mục (v2) cho CI rộng. Chỉ bắt được hồi quy lớn (> 10% tuyệt đối).
- **Bug hiếm gặp:** Một bug chỉ xuất hiện ở 1/3 seed (`rare`) không phát hiện ổn định được với 5 seed. Đây là giới hạn thiết kế, không nên hạ ngưỡng để bắt nó.
- **MockLLM:** Kết quả trên MockLLM tái lập hoàn toàn nhưng không đại diện cho model thật. Trước khi triển khai cần đánh giá trên model sản xuất.
- **Judge replay:** Dữ liệu judge calibration dùng CSV công khai, chưa có tập held-out mới.

## 5. Failure mode → slice

| FM | Tên | Cơ chế tấn công v2 | Slice chính |
|---|---|---|---|
| FM-02 | `ignore_denied` | `denied_ignored` | `denial` |
| FM-03 | `ticket_trust` | `ticket_over_db` | `money_movement` |
| FM-04 | `sum_parts` | `clause_sum` | `money_movement` |
| FM-06 | `stale_clause` | `stale_policy` | `denial` |
| FM-07 | `sibling_refund` | `sibling_refund`, `double_deduct` | `money_movement` |
| FM-08 | `misreport` | `reply_ledger_mismatch` | `money_movement` |
| FM-09 | `cross_principal` | `cross_principal` | `adversarial` |

## 6. File báo cáo

| File | Vị trí |
|------|--------|
| Baseline v1 | `src/reports/baseline_v1.json` |
| Swarm v1 | `src/reports/eval_swarm.json` |
| Fixed | `src/reports/eval_fixed.json` |
| Seeded regression | `src/reports/eval_seeded_regression.json` |
| Swarm v2 | `src/reports/eval_swarm_v2.json` |
| Baseline v2 | `src/reports/baseline_v2.json` |
