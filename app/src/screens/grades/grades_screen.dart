import 'package:flutter/material.dart';
import '../../services/mocker_api_service.dart';

class GradesScreen extends StatelessWidget {
  final AuthShieldMockerService api;
  final void Function(String title, String detail, {bool isError}) onNotify;

  const GradesScreen({
    super.key,
    required this.api,
    required this.onNotify,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          color: const Color(0xFF0F172A),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'PH4 · Bảng Điểm BR-031, Chặn Anti-IDOR & Phúc Khảo Maker-Checker',
                  style: TextStyle(
                    color: Colors.amberAccent,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Kiểm tra thực tế chốt chặn Anti-IDOR (Hình 7): Giáo viên được phân công dạy 12A1 (200 OK), thử truy cập 12A2 sẽ bị chặn 403 Forbidden.',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.emerald.shade600,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () async {
                          final res = await api.checkTeacherClassScope('12A1');
                          onNotify(
                            '200 OK · Lớp 12A1 (Hợp lệ Data Scope)',
                            'ĐTBm chuẩn BR-031 HALF_UP: ${res['average_score']} · Xếp loại: ${res['academic_rank']}',
                          );
                        },
                        child: const Text('Nhập Điểm 12A1 (200 OK)'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.red.shade700,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () async {
                          final res = await api.checkTeacherClassScope('12A2');
                          onNotify(
                            'HTTP ${res['status']} ${res['title']}',
                            '${res['detail']} (traceId: ${res['traceId']})',
                            isError: true,
                          );
                        },
                        child: const Text('Thử Lớp 12A2 (Chặn 403)'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          color: const Color(0xFF0F172A),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'UC-18 & UC-11 · Phúc Khảo Sửa Điểm Maker-Checker (GA-2026-089)',
                  style: TextStyle(
                    color: Colors.purpleAccent,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'HS002 Trần Minh Châu · Điểm thi HK: 6.5 -> 8.0 · Ràng buộc SoD-02: CHECK (maker_id != checker_id) & Mở khóa đúng 24 giờ.',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.purple.shade600,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: () {
                      if (api.currentAcr != 'S3') {
                        onNotify(
                          'HTTP 403 STEP_UP_S3_REQUIRED',
                          'Vui lòng sang tab SSO-MFA để xác thực FIDO2/Soft-HSM nâng cấp lên ACR=S3 trước khi ký duyệt!',
                          isError: true,
                        );
                        return;
                      }
                      onNotify(
                        'UC-BRD-06 · Đã Ký Duyệt Mở Khóa Sửa Điểm 24 Giờ',
                        'Đã lưu chữ ký kép (Maker Sig + Checker Sig S3) vào kho nhật ký bất biến WORM Audit.',
                      );
                    },
                    icon: const Icon(Icons.verified_user),
                    label: const Text('Duyệt Mở Khóa 24h (Yêu cầu ACR=S3)'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
