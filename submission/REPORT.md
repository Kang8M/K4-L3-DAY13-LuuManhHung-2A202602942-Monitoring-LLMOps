# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Lưu Mạnh Hùng
- **MSSV:** 2A202602942
- **Lớp:** K4-L3A
- **Repository URL:** [github.com/Kang8M/K4-L3-DAY13-LuuManhHung-2A202602942-Monitoring-LLMOps](https://github.com/Kang8M/K4-L3-DAY13-LuuManhHung-2A202602942-Monitoring-LLMOps)
- **Commit SHA cuối:**
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602942`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.


| Evidence            | Đường dẫn                         |
| --------------------- | --------------------------------------- |
| Pytest cuối        | `evidence/01-pytest.png`              |
| Log validator       | `evidence/02-log-validator.png`       |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log      | `evidence/04-structured-log.png`      |
| PII redaction       | `evidence/05-pii-redaction.png`       |
| Trace list          | `evidence/06-trace-list.png`          |
| Trace waterfall     | `evidence/07-trace-waterfall.png`     |
| Trace metadata      | `evidence/08-trace-metadata.png`      |
| Prompt versions     | `evidence/09-prompt-versions.png`     |
| Prompt rollback     | `evidence/10-prompt-rollback.png`     |
| Dashboard runtime   | `evidence/11-dashboard-overview.png`  |
| Incident metric     | `evidence/12-incident-metric.png`     |
| Incident log        | `evidence/13-incident-log.png`        |
| Incident trace      | `evidence/14-incident-trace.png`      |

## 3. Kết quả kỹ thuật


| Nội dung               | Baseline                                                                                                      | Kết quả cuối | Nhận xét                                                                                                                     |
| ------------------------- | --------------------------------------------------------------------------------------------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `validate_logs.py`      | 30/100 (45 records, 40 thiếu field bắt buộc, 40 thiếu enrichment, 0 correlation ID duy nhất, 0 PII leak) | 100/100 (21 records, 0 thiếu field, 0 thiếu enrichment, 10 correlation ID duy nhất, 0 PII leak) | CP1: middleware sinh/nhận `x-request-id`, bind context vào structlog, PII scrubber chạy trước khi ghi file |
| `validate_dashboard.py` | 6/6 panel hợp lệ theo contract                                                                              | 6/6            | Contract panel đã đủ từ đầu, chưa cần sửa CP2                                                                        |
| `pytest`                | 22 passed                                                                                                     | 25 passed      | Thêm 3 test PII (cccd, credit_card, passport_vn) ở CP1                                                                |
| Số traces hợp lệ     | 0                                                                                                             | ≥ 25 (10 từ load_test + 4 từ demo prompt version/promote/rollback + các lần chạy lại)               | Mỗi trace có root span `lab-agent-run` + child `retrieve-context` (retriever) + child `llm-generate` (generation)          |
| Số PII leak            | 0                                                                                                             | 0               | Input/output của span generation được scrub qua `scrub_text` trước khi gửi Langfuse                                    |
| Latency P95 / TTFT P95  | chưa đo (load_test baseline chỉ log latency tổng, không tách TTFT)                                      | P95 ≈ 921ms / TTFT P95 = 50ms (đo qua dashboard Streamlit trên cửa sổ 60 phút)                | Dưới threshold 3000ms trong `config/dashboard.yaml` và SLO                                                                |
| Retrieval success rate  | chưa đo                                                                                                     | 100% (không có `tool_success=false` trong cửa sổ đo)                                            | Trên ngưỡng guardrail 90% trong `config/slo.yaml`                                                                         |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `CorrelationIdMiddleware` (`app/middleware.py`) xóa contextvars cũ mỗi request, đọc header `x-request-id` nếu có, ngược lại sinh `req-<8-hex>` (`uuid.uuid4().hex[:8]`), bind vào `structlog.contextvars` và lưu vào `request.state.correlation_id`; trả lại qua header `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** trong `POST /chat` (`app/main.py`), trước log `request_received` gọi `bind_contextvars(user_id_hash=hash_user_id(...), session_id, feature, model=agent.model, env)`; các field này tự động merge vào mọi log sau đó nhờ `merge_contextvars`.
- **Cách bảo đảm PII được scrub trước khi ghi:** processor `scrub_event` (`app/logging_config.py`) được đăng ký trước `JsonlFileProcessor` trong pipeline structlog, scrub cả `event` và mọi giá trị string trong `payload` bằng `scrub_text` (`app/pii.py`) — regex cho email, SĐT VN, CCCD, thẻ thanh toán, hộ chiếu — trước khi ghi ra `data/logs.jsonl`.
- **Cách kiểm chứng kết quả:** xóa `data/logs.jsonl` cũ, restart API, chạy `scripts/load_test.py` rồi `scripts/validate_logs.py` → 100/100 (0 missing field, 0 missing enrichment, 10 correlation ID duy nhất, 0 PII leak); `pytest -q` 25 passed gồm test mới cho CCCD/thẻ/hộ chiếu.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** dùng key `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` của project `day13-k4-l3a-<MSSV>` trong `.env`; toàn bộ trace chỉ xuất hiện khi gọi `app/main.py` qua chính API trên máy cá nhân, xác nhận bằng cách so khớp `correlation_id` trong `data/logs.jsonl` với metadata trace trên Langfuse UI.
- **Cấu trúc root/retrieval/generation observations:** root span `lab-agent-run` (`as_type="agent"`, đặt trong `LabAgent.run`) → child `retrieve-context` (`as_type="retriever"`, input là câu hỏi đã scrub, output `{doc_count}`) → child `llm-generate` (`as_type="generation"`, có `model`, `input`/`output` đã scrub bằng `scrub_text`, `usage_details={input, output}` và `cost_details={total}`). Implement tại `app/agent.py`.
- **Cách nối trace với log:** `correlation_id` được truyền vào `metadata` của root span (`propagate_attributes(metadata={"correlation_id": ...})`) và của cả hai child observation; cùng giá trị này cũng là `correlation_id` trong mọi dòng log JSONL của request đó, nên có thể tra chéo log ↔ trace bằng một ID duy nhất.
- **Prompt name:** `day13-chat` (biến `LANGFUSE_PROMPT_NAME`).
- **Version/label baseline:** version 1, labels `baseline` + `production` (mặc định) — template gốc 3 biến `feature/docs/message`.
- **Version/label candidate:** version 2, label `candidate` — thêm chỉ dẫn "trả lời tối đa 3 câu" so với v1.
- **Trace ID của mỗi version:** `req-4c8c5b14` (label `baseline` → v1), `req-62f1650b` (label `candidate` → v2), `req-a2fdb835` (sau khi promote `production` → v2), `req-119b9193` (sau khi rollback `production` → v1, xác nhận bằng `prompt_source=langfuse` không còn fallback).
- **Cách promote và rollback `production`:** dùng `langfuse_client.update_prompt(name="day13-chat", version=2, new_labels=["candidate","production"])` để promote v2 lên `production` (không tạo version mới, chỉ gán lại label), rồi `update_prompt(..., version=1, new_labels=["baseline","production"])` để rollback về v1. Mỗi lần đổi label, request tiếp theo phản ánh đúng version qua `prompt_version`/`prompt_source` trong trace metadata.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `scripts/dashboard_app.py` (Streamlit, chạy bằng `streamlit run scripts/dashboard_app.py`) đọc trực tiếp `data/logs.jsonl` theo đúng contract `config/dashboard.yaml` (time range 60 phút, refresh 30s qua `st.fragment(run_every=...)`): panel Latency (P50/P95/P99 + TTFT P95), Traffic (count + req/phút), Errors (error rate % + retrieval success %), Cost (tổng theo phút), Tokens (input/output), Quality (mean). Mỗi panel hiển thị kèm threshold và trạng thái OK/BREACH.
- **SLO và lý do chọn:** `config/slo.yaml` giữ SLO `fast_successful_requests` (good = `response_sent` với `latency_ms <= 3000`, target 99.5%/28 ngày). Baseline đo được P95 ≈ 921ms, error rate 0%, retrieval success 100%, quality trung bình 0.86 — đều nằm sâu trong ngưỡng nên giữ nguyên threshold 3000ms và các guardrail (`error_rate_pct_max=2`, `daily_cost_usd_max=2.5`, `quality_score_avg_min=0.75`, `retrieval_success_rate_pct_min=90`) thay vì siết chặt hơn, để còn biên độ cho tải thực tế cao hơn load test.
- **Cách tính error budget:** `error_budget_percent = 100% - target_percent = 100% - 99.5% = 0.5%`; trong cửa sổ 28 ngày, số request "xấu" (lỗi hoặc latency > 3000ms) được phép tối đa là 0.5% tổng số request trước khi vi phạm SLO.
- **Ba alert và runbook tương ứng:** cấu hình tại `config/alert_rules.yaml`, chi tiết kiểm tra/mitigation tại `docs/alerts.md`:
  1. `HighLatencyP95` — `latency_p95_ms > 3000` trong 5m, severity `critical`, owner `on-call-backend`, runbook `docs/alerts.md#alert-1`.
  2. `ElevatedErrorRate` — `error_rate_pct > 2` trong 5m, severity `critical`, owner `on-call-backend`, runbook `docs/alerts.md#alert-2`.
  3. `CostBudgetBurn` — tổng `cost_usd` trong 5 phút vượt 0.50 USD, duy trì 10m, severity `warning`, owner `on-call-platform`, runbook `docs/alerts.md#alert-3`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (cohort K4, incident `rag_slow`, `affected_feature=monitoring`, `latency_threshold_ms=2000`).
- **Khoảng thời gian điều tra:** incident bật lúc `2026-09-29T09:35:50Z`; chạy `python scripts/load_test.py --challenge --concurrency 5` ngay sau đó, 5 request hoàn tất trong khoảng `09:35:56Z` – `09:36:10Z` (16:35:56 – 16:36:10 giờ local).
- **Triệu chứng từ metrics:** panel Latency trên dashboard (`evidence/12-incident-metric.png`) cho thấy P50/P95/P99 nhảy đồng loạt lên **~2654–2655ms**, tăng gấp ~3 lần so với baseline (~387–921ms) — tuy chưa chạm ngưỡng panel 3000ms nhưng đã vượt hẳn `latency_threshold_ms=2000` riêng của challenge.
- **Log line và correlation ID liên quan:** lọc `data/logs.jsonl` theo `feature == "monitoring"` thấy cả 5 request đều có `latency_ms≈2654`. Lấy một request cụ thể: `correlation_id=req-e201ce43`, `session_id=k4-l3a-challenge-s01`, `latency_ms=2654`, `tool_success=true` (evidence `13-incident-log.png`).
- **Trace ID và span gây ảnh hưởng:** trace `8686a6744715754953c31a1197b975ff` (cùng `correlation_id=req-e201ce43`) — span `retrieve-context` mất **2.50s**, span `llm-generate` chỉ mất **0.15s**, trong tổng thời gian trace **2.65s**. Span retrieval chiếm ~94% tổng thời gian (evidence `14-incident-trace.png`).
- **Root cause:** incident `rag_slow` bật flag `STATE["rag_slow"]=True` trong `app/incidents.py`, khiến `retrieve()` (`app/mock_rag.py`) chủ động `time.sleep(2.5)` trước khi trả kết quả — retrieval trở thành điểm nghẽn duy nhất, không phải do LLM hay hạ tầng khác.
- **Fix action:** đã tắt incident bằng `python scripts/inject_incident.py --disable` (đọc lại `config/challenge.json` để xác định đúng incident `rag_slow` cần tắt) ngay sau khi thu thập đủ evidence; xác nhận `GET /health` trả `rag_slow: false`.
- **Preventive measure:** (1) thêm timeout/circuit-breaker quanh bước retrieval để một dependency chậm không kéo dài toàn bộ request; (2) alert `HighLatencyP95` (`config/alert_rules.yaml`) đã cấu hình sẵn để cảnh báo khi P95 > 3000ms trong 5 phút, nên cân nhắc thêm ngưỡng cảnh báo sớm hơn (ví dụ >1500ms) riêng cho span retrieval; (3) vì handler `/chat` gọi `retrieve()`/`FakeLLM.generate()` đồng bộ (blocking) trong async endpoint, nhiều request đồng thời bị dồn tuần tự (`--concurrency 5` cho thấy độ trễ phía client tới 13s dù `latency_ms` nội bộ chỉ ~2.65s) — nên chuyển các bước I/O sang non-blocking/threadpool để tránh nghẽn cả event loop khi một dependency chậm.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** khi làm prompt versioning, dùng `langfuse_client.update_prompt(name, version, new_labels)` để gán lại label `production` cho version có sẵn thay vì gọi `create_prompt` tạo version mới. Lý do: đúng ngữ nghĩa "rollback" (quay về trạng thái cũ) thay vì "roll-forward" (tạo v3 giống hệt v1), giữ lịch sử version sạch và dễ audit.
- **Một lỗi/blocker đã gặp:** lần chạy `load_test.py` đầu tiên sau khi thêm child observation, uvicorn log báo `Prompt 'day13-chat' with label 'production' not found` (404) — vì prompt chưa từng được tạo trên Langfuse, app tự fallback về template local nên vẫn chạy được nhưng `prompt_source=local-fallback`.
- **Cách tìm nguyên nhân và xử lý:** đọc trực tiếp log uvicorn thấy rõ thông báo lỗi kèm status code 404 từ Langfuse API; viết một script nhỏ dùng `client.create_prompt(...)` để tạo v1 (`baseline`+`production`) và v2 (`candidate`) trước, sau đó chạy lại request thì `prompt_source` chuyển thành `langfuse` và không còn fallback.
- **Cách hiểu luồng Metrics → Logs → Traces:** áp dụng trực tiếp ở CP3 — dashboard (metric) cho biết *có vấn đề gì* (P95 tăng vọt) và *khoảng thời gian nào*; lọc `data/logs.jsonl` theo thời gian/feature cho ra `correlation_id` của *request cụ thể* bị ảnh hưởng; mở trace cùng `correlation_id` trên Langfuse cho biết *span nào* (retrieval) là nguyên nhân. Ba tín hiệu này không thay thế nhau mà thu hẹp phạm vi điều tra theo từng bước.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** prompt version cho phép thử thay đổi (candidate) mà không ảnh hưởng người dùng thật (production), và rollback tức thì nếu candidate tệ hơn — không cần deploy lại code. Theo dõi token/cost giúp phát hiện sớm việc chi phí tăng bất thường (ví dụ do output token tăng đột biến như incident `cost_spike`). SLO/error budget biến "hệ thống có ổn không" thành một con số định lượng, làm cơ sở khách quan để quyết định có nên triển khai thay đổi rủi ro hay không.
- **Điều quan trọng nhất đã học:** `correlation_id` là "chìa khóa" duy nhất xuyên suốt cả ba tín hiệu quan sát (log, trace, và cả response header) — nếu không truyền nhất quán một ID qua toàn bộ request thì không thể nối metric → log → trace lại với nhau khi điều tra sự cố.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** dashboard được tự viết bằng Streamlit (đọc trực tiếp `data/logs.jsonl`) thay vì dùng Grafana/công cụ BI chuẩn, nên chưa có tính năng lưu lịch sử dài hạn hay alerting tự động thực sự (alert rules mới ở dạng cấu hình + runbook, chưa nối vào một hệ thống cảnh báo thật). Ngoài ra, handler `/chat` vẫn gọi retrieval/LLM đồng bộ (blocking) trong async endpoint — đã ghi nhận là preventive measure ở mục 7 nhưng chưa sửa code vì nằm ngoài phạm vi TODO bắt buộc của lab.

## 9. Checklist trước khi nộp

- [ ]  Kết quả và evidence thuộc commit SHA cuối. *(cần commit + điền SHA trước khi nộp)*
- [x]  Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x]  Incident evidence nối đúng metric → log → trace.
- [x]  Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret (chỉ hiện public key, không hiện secret key).
- [x]  Repository chạy lại được theo README (`pytest`, `validate_logs.py`, `validate_dashboard.py` đều pass trên commit hiện tại).
- [x]  Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác (`.env`, `config/challenge.json`, `data/logs.jsonl` đều trong `.gitignore`).
- [ ]  URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs. *(học viên tự nộp)*
