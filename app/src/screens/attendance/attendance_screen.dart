import 'package:flutter/material.dart';
import '../../services/mocker_api_service.dart';

class AttendanceScreen extends StatefulWidget {
  final AuthShieldMockerService api;
  final void Function(String title, String detail, {bool isError}) onNotify;

  const AttendanceScreen({
    super.key,
    required this.api,
    required this.onNotify,
  });

  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  final Map<String, String> _attendance = {
    'HS001 - Nguyễn Hải An': 'PRESENT',
    'HS002 - Trần Minh Châu': 'PRESENT',
    'HS003 - Lê Quốc Bảo': 'EXCUSED_ABSENT',
  };

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
                  'PH3 · UC-14 / UC-TCH-01 · Điểm Danh Tiết Học & Sổ Đầu Bài',
                  style: TextStyle(
                    color: Colors.tealAccent,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Lớp 12A1 · Tiết 2: Nguyên hàm & Tích phân · Kiểm soát Anti-IDOR theo bảng phân công chuyên môn (teaching_assignments).',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
                const SizedBox(height: 12),
                ..._attendance.entries.map((entry) {
                  return ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      entry.key,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                    ),
                    trailing: DropdownButton<String>(
                      dropdownColor: const Color(0xFF1E293B),
                      value: entry.value,
                      style: const TextStyle(color: Colors.cyanAccent, fontSize: 12),
                      items: const [
                        DropdownMenuItem(value: 'PRESENT', child: Text('Có mặt')),
                        DropdownMenuItem(value: 'EXCUSED_ABSENT', child: Text('Nghỉ có phép')),
                        DropdownMenuItem(value: 'UNEXCUSED_ABSENT', child: Text('Nghỉ không phép')),
                        DropdownMenuItem(value: 'LATE', child: Text('Đi muộn')),
                      ],
                      onChanged: (val) {
                        if (val != null) {
                          setState(() => _attendance[entry.key] = val);
                        }
                      },
                    ),
                  );
                }),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.teal.shade600,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: () {
                      widget.onNotify(
                        'UC-TCH-01 & 03 · Đã lưu Điểm danh & Ký Sổ Đầu Bài 12A1',
                        'Sĩ số: 44/45 · Đã đồng bộ thông báo chuyên cần tới Phụ huynh qua Zalo ZNS / SMS Brandname.',
                      );
                    },
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('Lưu Điểm Danh & Ký Sổ Đầu Bài (ACR=S2)'),
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
