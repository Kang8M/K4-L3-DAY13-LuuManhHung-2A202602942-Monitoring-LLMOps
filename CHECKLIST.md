# CHECKLIST — Lab Day 13: Monitoring & LLMOps

> Dựa trên [README.md](README.md). Đánh dấu `[x]` khi hoàn thành.

## CP0 — Setup (14:00–14:30) ✅

- [x] Tạo virtualenv, cài `requirements.txt`
- [x] Copy `.env.example` → `.env`
- [x] Tạo project Langfuse riêng `day13-k4-l3a-<MSSV>`, lấy `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`, điền vào `.env`
- [x] Chạy `uvicorn app.main:app --reload --env-file .env`, kiểm tra `/health` trả `ok: true`
- [x] Chạy `python scripts/load_test.py` để tạo log baseline
- [x] Chạy baseline: `validate_logs.py` (30/100), `validate_dashboard.py` (6/6), `pytest -q` (22 passed)
- [x] Ghi kết quả baseline (chưa đạt là bình thường) vào `submission/REPORT.md`

## CP1 — Logging và PII (14:30–15:20) ✅

- [x] `app/middleware.py`: xóa context cũ; nhận `x-request-id` hoặc sinh `req-<8-hex>`; bind ID; trả ID + response time trong header
- [x] `app/main.py`: bind `user_id_hash`, `session_id`, `feature`, `model`, `env` trước log `request_received`
- [x] `app/logging_config.py`: chạy PII scrubber trước khi ghi file/render JSON
- [x] `app/pii.py`: hoàn thiện pattern + tests cho email, SĐT Việt Nam, CCCD, thẻ thanh toán (+ hộ chiếu)
- [x] Xóa/đổi tên log cũ, restart API, chạy lại `load_test.py`
- [x] `validate_logs.py` đạt ≥ 80/100 → **đạt 100/100**

## CP2 — Tracing, prompt và dashboard (15:20–16:40) ✅

### Tracing
- [x] Thêm child observation loại `retriever`/`span` cho bước retrieval
- [x] Thêm child observation loại `generation` cho LLM call (model, prompt, `input_tokens`, `output_tokens`, cost)
- [x] Đảm bảo không capture raw prompt/output chứa PII (dùng `scrub_text`)
- [x] Correlation ID xuất hiện trong trace metadata (nối trace ↔ log)
- [x] Tạo ít nhất 10 traces trên Langfuse, span tree đọc được (≥25 traces đã tạo)
- [x] Chụp evidence: `06-trace-list.png`, `07-trace-waterfall.png`, `08-trace-metadata.png`

### Prompt versioning
- [x] Liên kết trace với prompt name/label/version
- [x] Tạo prompt v1 (baseline/production) và v2 (candidate) qua Langfuse SDK
- [x] Chạy request với label baseline và candidate → 2 trace khác nhau
- [x] Promote `production` sang v2, chạy request xác nhận
- [x] Rollback `production` về v1, chạy request xác nhận (xem [docs/PROMPT_VERSIONING.md](docs/PROMPT_VERSIONING.md))
- [x] Chụp evidence: `09-prompt-versions.png`, `10-prompt-rollback.png`

### Dashboard & SLO/Alert
- [x] Dashboard Streamlit (`scripts/dashboard_app.py`) dùng `data/logs.jsonl`, đúng 6 panel trong `config/dashboard.yaml`
- [x] Panel latency có P50/P95/P99 và TTFT
- [x] Panel errors thể hiện cả retrieval success
- [x] `validate_dashboard.py` đạt 6/6
- [x] `config/slo.yaml`: đã giải thích threshold dựa trên baseline, tính error budget (0.5%)
- [x] `config/alert_rules.yaml`: 3 alert symptom-based (HighLatencyP95, ElevatedErrorRate, CostBudgetBurn) đủ duration/severity/owner/Slack/runbook
- [x] `docs/alerts.md`: cách kiểm tra và mitigation cho từng alert
- [x] Chụp evidence: `11-dashboard-overview.png`

### Evidence CP0/CP1 (đã chụp và rà soát)
- [x] `01-pytest.png` (25 passed), `02-log-validator.png` (100/100), `03-dashboard-validator.png` (6/6), `04-structured-log.png`, `05-pii-redaction.png` (email/phone/CCCD redacted)

## CP3 — Challenge chính thức (16:40–17:30) ✅

> Challenge ID: `day13-k4-l3a-monitoring-llmops-v1` (cohort K4, incident `rag_slow`)

- [x] Nhận file challenge riêng của lớp, lưu tại `config/challenge.json` (đã `.gitignore`, KHÔNG force-add/commit/push)
- [x] Chạy `python scripts/inject_incident.py`
- [x] Chạy `python scripts/load_test.py --challenge --concurrency 5`
- [x] Xem dashboard → P95 latency nhảy từ ~921ms → 2655ms (`evidence/12-incident-metric.png`)
- [x] Lọc `data/logs.jsonl` → `correlation_id=req-e201ce43`, `latency_ms=2654` (`evidence/13-incident-log.png`)
- [x] Tìm trace cùng `correlation_id` → span `retrieve-context` 2.50s / tổng 2.65s (94%) (`evidence/14-incident-trace.png`)
- [x] Ghi root cause, fix action, preventive measure vào `submission/REPORT.md` mục 7
- [x] Tắt incident sau khi thu thập evidence (`python scripts/inject_incident.py --disable`)

## CP4 — Report, evidence và kiểm tra cuối (17:30–18:00)

- [x] Hoàn thiện `submission/REPORT.md` đầy đủ (mục 1–9)
- [x] Evidence đặt trong `submission/evidence/` (14/14 ảnh):
  - [x] Ảnh dashboard có dữ liệu (`11-dashboard-overview.png`)
  - [x] Ít nhất 10 trace IDs (`06-trace-list.png`: 55 root traces)
  - [x] Một trace waterfall (`07-trace-waterfall.png`)
  - [x] Evidence prompt v1/v2 và rollback (`09-prompt-versions.png`, `10-prompt-rollback.png`)
- [x] Chạy lại toàn bộ kiểm tra trước khi nộp:
  - [x] `python -m pytest -q` → 25 passed
  - [x] `python scripts/validate_logs.py` → 100/100
  - [x] `python scripts/validate_dashboard.py` → 6/6
  - [x] `git status --short` → đã rà soát, không có secret/PII lạ
  - [ ] `git log -1 --oneline` → **chưa commit thay đổi CP1–CP4, cần commit trước khi nộp**
- [x] Không có `.env`, secret, `.venv/`, PII thô, hoặc evidence của học viên/lớp khác
- [x] Mọi ảnh trong REPORT dùng đường dẫn tương đối và mở được
- [x] Có thể demo và giải thích luồng Metrics → Logs → Traces → Root cause (đã thực hành thật ở CP3)

## Nộp bài

- [ ] **[Học viên]** Commit toàn bộ thay đổi, điền `Commit SHA cuối` vào `submission/REPORT.md` mục 1
- [ ] **[Học viên]** Đổi tên repo cá nhân theo mẫu `K4-L3-DAY13-HoVaTen-MSSV-Monitoring-LLMOps` (nếu chưa đổi)
- [ ] **[Học viên]** Không push lên repo đề bài, không dùng chung repo với học viên khác
- [ ] **[Học viên]** Nộp URL repo cá nhân + commit SHA cuối trên VLearn LMS/Codelabs (xem [docs/SUBMISSION.md](docs/SUBMISSION.md))

## Tài liệu tham khảo

- [docs/SETUP.md](docs/SETUP.md) — cài đặt, xử lý lỗi môi trường
- [docs/CHECKPOINTS.md](docs/CHECKPOINTS.md) — đầu ra & tự kiểm tra từng mốc
- [docs/GUIDE.md](docs/GUIDE.md) — gợi ý kỹ thuật khi bị kẹt
- [docs/PROMPT_VERSIONING.md](docs/PROMPT_VERSIONING.md) — prompt v1/v2, label, rollback
- [docs/DASHBOARD_SETUP.md](docs/DASHBOARD_SETUP.md) — mapping dữ liệu cho 6 panel
- [docs/RUBRIC.md](docs/RUBRIC.md), [docs/RULES.md](docs/RULES.md), [docs/SUBMISSION.md](docs/SUBMISSION.md)
- [docs/grading-evidence.md](docs/grading-evidence.md) — checklist nhanh ảnh/output cần thu thập
