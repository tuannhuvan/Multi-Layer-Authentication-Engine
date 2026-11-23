# CLAUDE.md — Hướng dẫn nhanh cho Claude Code / AI Runtime

Dự án này vận hành theo **Quy trình AI-Agent tự động hóa dự án phần mềm — V2.1**.
Toàn bộ quy ước dự án, bảng phân quyền 8 vai trò + Controller, trần số lượt review (4 / 6 / 9), quy tắc kiểm delta và hợp đồng script CI được định nghĩa tại:

- Xem chi tiết: [AGENTS.md](./AGENTS.md)
- Cấu hình schema & policy vùng tin cậy: `.agent-policy/`
- Trạng thái xuất quan sát: `.pipeline/state.json`
- CLI Điều phối viên (Workflow Controller): `python tools/workflow_controller/controller.py`
