# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighLatencyP95
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack (#day13-oncall)
- SLI/SLO liên quan: `primary_slo.fast_successful_requests` (`config/slo.yaml`) — request tính là "good" khi `latency_ms <= 3000`; panel `latency` trong `config/dashboard.yaml` có threshold P95 `<= 3000ms`.
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000` liên tục trong `5m`.
- Ảnh hưởng tới người dùng: câu trả lời chậm rõ rệt, có thể gây timeout ở client hoặc trải nghiệm chờ đợi kém, ăn vào error budget của SLO.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel `latency` để xác nhận P95/P99 tăng và khoảng thời gian bắt đầu.
  2. Lọc `data/logs.jsonl` theo `event == "response_sent"` và `latency_ms` cao, lấy `correlation_id` của một request chậm.
  3. Mở trace Langfuse cùng `correlation_id`, so sánh thời lượng span `retrieve-context` và `llm-generate` để xác định span nào chậm.
- Mitigation tạm thời: nếu span retrieval chậm (giống scenario `rag_slow`), tắt incident bằng `python scripts/inject_incident.py --scenario rag_slow --disable`; nếu do tải cao, giảm `--concurrency` của load test hoặc scale thêm worker.
- Owner: on-call-backend

## Alert 2

- Tên: ElevatedErrorRate
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack (#day13-oncall)
- SLI/SLO liên quan: guardrail `error_rate_pct_max: 2` và `retrieval_success_rate_pct_min: 90` trong `config/slo.yaml`; panel `errors` (error rate và `tool_success_rate_pct`) trong `config/dashboard.yaml`.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` liên tục trong `5m`.
- Ảnh hưởng tới người dùng: một phần request trả lỗi 500, người dùng không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel `errors`, xem `error_rate_pct` và breakdown `error_type` để biết loại lỗi chiếm đa số.
  2. Lọc log theo `event == "request_failed"`, lấy `correlation_id` và `error_type` (ví dụ `RuntimeError` từ retrieval tool).
  3. Mở trace cùng `correlation_id` trên Langfuse, xem span nào (`retrieve-context` hay `llm-generate`) kết thúc bằng lỗi/exception.
- Mitigation tạm thời: nếu do retrieval tool lỗi (giống scenario `tool_fail`), tắt incident `python scripts/inject_incident.py --scenario tool_fail --disable`; đồng thời cân nhắc bật fallback trả lời chung chung thay vì lỗi cứng cho người dùng.
- Owner: on-call-backend

## Alert 3

- Tên: CostBudgetBurn
- Severity: warning
- Duration: 10m
- Kênh thông báo: Slack (#day13-oncall)
- SLI/SLO liên quan: guardrail `daily_cost_usd_max: 2.5` trong `config/slo.yaml`; panel `cost` (tổng `cost_usd` theo phút) trong `config/dashboard.yaml`.
- Điều kiện và thời gian duy trì: tổng `cost_usd` trong cửa sổ 5 phút (`cost_usd_sum_5m`) vượt `0.50` USD, duy trì `10m`.
- Ảnh hưởng tới người dùng: không ảnh hưởng trực tiếp ngay lập tức, nhưng báo hiệu chi phí vận hành tăng bất thường (ví dụ output token tăng đột biến) có thể dẫn tới cắt giảm ngân sách hoặc rate-limit khẩn cấp.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel `cost` và `tokens`, xác nhận `tokens_out` tăng bất thường so với baseline.
  2. Lọc log `event == "response_sent"` có `cost_usd` cao, lấy `correlation_id`.
  3. Mở trace cùng `correlation_id`, kiểm tra `usage_details`/`cost_details` trên span `llm-generate` để xác nhận số token output tăng (giống scenario `cost_spike`).
- Mitigation tạm thời: tắt incident `python scripts/inject_incident.py --scenario cost_spike --disable`; nếu là traffic thật, cân nhắc giới hạn `max_output_tokens` hoặc bật rate-limit tạm thời.
- Owner: on-call-platform
