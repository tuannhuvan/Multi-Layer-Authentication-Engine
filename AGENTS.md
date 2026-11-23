# AGENTS.md — Quy ước dự án AuthShield-LMS (Quy trình AI-Agent V2.1)

> **Lưu ý an toàn (§4, §10)**: File này là quy ước dự án (< 200 dòng) hỗ trợ định hướng cho Agent — **không phải cơ chế phân quyền**. Quyền thực thi thực tế nằm ở môi trường cô lập, sandbox và `.agent-policy/<role>.json`.

## 1. Tổng quan & Kiến trúc
- **Dự án**: `Multi-Layer-Authentication-Engine` (AuthShield-LMS) — Hệ thống Xác thực Đa tầng & Quản lý Học đường theo chuẩn Zero Trust / TCVN 11930:2017 Cấp độ 3.
- **Quy trình vận hành**: **V2.1** (`P0 Dựng nền` → `P1 Phân tích (G1)` → `P2 Thiết kế (G2)` → `P3 Viết test trước` → `P4 Hiện thực (G3)` → `P5 Review chéo (G4)` → `P6 Phát hành (G5)`).
- **Chủ sở hữu**:
  - **Product Owner (PO)**: Ng Tuân (Chịu trách nhiệm nghiệp vụ, duyệt G1, đồng ký G4 cho story rủi ro cao).
  - **Tech Lead / Architect**: Ng Tuân (Kiêm nhiệm pilot — Chịu trách nhiệm kiến trúc, duyệt G2, đồng ký G4 cho story rủi ro cao).
  - **QA Owner**: Ng Tuân (Kiêm nhiệm pilot — Chính sách kiểm thử, P3 baseline).
  - **Release Owner**: Ng Tuân (Kiêm nhiệm pilot — Duyệt phát hành G5).

## 2. Nguyên tắc bắt buộc (§1.2)
1. **Nguồn sự thật có phiên bản**: Nghiệp vụ (`docs/spec/`), API (`api/openapi.yaml`), test (`tests/acceptance/`) và UI baseline (`docs/design/ui-baseline.md`) đều có ID và SHA-256 checksum trong `.pipeline/baseline-manifest.json`.
2. **Agent viết không tự duyệt**: Reviewer (`BIZ`, `SEC`) chạy phiên độc lập, không đọc phần tự biện hộ của agent viết.
3. **Gate dựa trên bằng chứng**: Agent không tự ghi `PASS` thay kết quả CI; `.pipeline/state.json` chỉ là bản xuất để quan sát.
4. **PASS gắn với đúng đầu vào**: Đổi spec, contract, test hoặc SHA làm mất hiệu lực (chuyển `STALE`) các kết quả chịu ảnh hưởng.
5. **Quản lý thay đổi bằng Change Request**: Khi thiếu/sai spec, API, test hoặc UI token, agent tạo `requests/<task-id>/<request-id>.json` theo schema Phụ lục C — tuyệt đối không tự sửa baseline ngoài phạm vi.
6. **Review có trần (§8)**:
   - Thường (`NORMAL`): Cơ bản **2**, tối đa **4** lượt.
   - Trung bình (`MEDIUM`): Cơ bản **4**, tối đa **6** lượt.
   - Cao (`HIGH`): Cơ bản **5**, tối đa **9** lượt (bắt buộc PO + Tech Lead ký xác nhận ở G4).
   - Mọi vòng sửa `CODE` mặc định dùng **kiểm delta (`DELTA`)**. Chỉ chạy `FULL` khi Controller xác định: (a) diff sửa > 30% hoặc chạm ngoài `checked_scope`, (b) đổi baseline ảnh hưởng BR, hoặc (c) sửa finding `CRITICAL` đổi luồng xác thực/phân quyền.
   - Review LLM chỉ chạy trên MR (`merge_request_event`); nhánh chính chỉ chạy `verify-review-evidence`.

## 3. Phân quyền ghi theo vai trò (§3)
| Vai trò | Đường dẫn được phép ghi | Cấm ghi / Ràng buộc |
| :--- | :--- | :--- |
| **BA** | `docs/spec/**` | Không sửa baseline đã duyệt; **không dùng Bash** |
| **Architect** | `docs/adr/**`, `api/**`, `docs/design/**`, `docs/trace/**` | Chỉ sửa thiết kế nháp / đề xuất thay đổi |
| **Tester** | `tests/acceptance/**`, `tests/fixtures/**`, `tests/plans/**` | Baseline do Controller niêm phong phát hành |
| **BE Dev** | `backend/**`, `src/**`, `requests/**` | Cấm sửa `docs/**`, `api/**`, `tests/acceptance/**`, `.agent-policy/**` |
| **FE Dev** | `frontend/**`, `app/**`, `requests/**` | Dùng mock sinh từ contract (`api/openapi.yaml`), test lại với BE thật |
| **DevOps** | `infra/**`, `docs/operations/**` | Không giữ credential production |
| **Biz / Sec Reviewer** | `reports/review-*.json` (qua Controller) | Chỉ xuất JSON theo `review.schema.json`; không shell tùy ý |
| **Controller** | `.pipeline/**`, `reports/**`, `reviews/**` | Code tất định (`tools/workflow_controller/controller.py`), không code tính năng |

## 4. Đường dẫn nhạy cảm tự động nâng mức rủi ro lên `HIGH` (§11)
Mọi thay đổi chạm vào các đường dẫn sau tự động nâng `risk_level = HIGH`:
- `backend/authenticator-service/**`, `backend/api-gateway/**`, `**/security/**`
- `backend/database/**`, `**/db/migration/**`
- Các module tính điểm, xếp loại, chữ ký số S3, phân quyền đơn vị (`school-service/**/grades/**`).

## 5. Lệnh làm việc chuẩn
- **Kiểm tra trạng thái Controller**: `python tools/workflow_controller/controller.py status --story <STORY_ID>`
- **Chạy Contract Mocker (FE/BE)**: `python tools/mocker/contract_mocker.py --spec api/openapi.yaml --validate`
- **Chạy kiểm thử âm quy trình (§17.2)**: `python tools/workflow_controller/test_negative_gates.py`
