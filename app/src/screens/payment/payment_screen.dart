import 'package:flutter/material.dart';
import '../../services/mocker_api_service.dart';

class PaymentAndLmsScreen extends StatefulWidget {
  final AuthShieldMockerService api;
  final void Function(String title, String detail, {bool isError}) onNotify;

  const PaymentAndLmsScreen({
    super.key,
    required this.api,
    required this.onNotify,
  });

  @override
  State<PaymentAndLmsScreen> createState() => _PaymentAndLmsScreenState();
}

class _PaymentAndLmsScreenState extends State<PaymentAndLmsScreen> {
  int _attempts = 1;
  final int _maxAttempts = 3;
  bool _tuitionPaid = false;

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
                Text(
                  'PH5 · UC-20 / UC-STU-07 · Nộp Bài Tập & Phạt Muộn (Lượt $_attempts/$_maxAttempts)',
                  style: const TextStyle(
                    color: Colors.lightBlueAccent,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Bài tập #45: Tích phân & Ứng dụng · Nộp trễ 30 phút tự động gắn cờ is_late=TRUE, trừ 10% điểm và băm SHA-256 lên MinIO/S3 (Hình 9).',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.sky.shade600,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: () {
                      if (_attempts >= _maxAttempts) {
                        widget.onNotify(
                          'HTTP 400 MAX_ATTEMPTS_EXCEEDED',
                          'Đã hết số lượt nộp bài cho phép (3/3 lượt)! (Hình 9 Bước 7)',
                          isError: true,
                        );
                        return;
                      }
                      setState(() => _attempts++);
                      widget.onNotify(
                        '200 OK · Nộp bài lần $_attempts/$_maxAttempts thành công!',
                        'Ghi nhận nộp muộn 30 phút (-10% điểm: 9.0 -> 8.1) kèm mã băm SHA-256 trên S3.',
                      );
                    },
                    icon: const Icon(Icons.upload_file),
                    label: Text('Nộp Bài Tập Lần ${_attempts + 1} (Test Phạt Muộn)'),
                  ),
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
                  'PH5 · UC-21 / UC-STU-11..13 · Thanh Toán Học Phí VNPAY / MoMo',
                  style: TextStyle(
                    color: Colors.greenAccent,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  _tuitionPaid
                      ? 'Trạng thái: ĐÃ HOÀN TẤT HỌC PHÍ HK1 · Biên lai điện tử: EREC-VNPAY-2026-8812'
                      : 'Hóa đơn INV-2026-HK1-HS001 · Còn nợ: 1,500,000 VNĐ · Đối soát Webhook HMAC-SHA256.',
                  style: const TextStyle(color: Colors.white70, fontSize: 12),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green.shade600,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: _tuitionPaid
                        ? null
                        : () {
                            setState(() => _tuitionPaid = true);
                            widget.onNotify(
                              'UC-STU-12..13 · Thanh toán VNPAY thành công!',
                              'Đã xác thực Webhook HMAC-SHA256 và cấp Biên lai điện tử EREC-VNPAY-2026-8812.',
                            );
                          },
                    icon: const Icon(Icons.payment),
                    label: Text(
                      _tuitionPaid
                          ? 'Đã Xuất Biên Lai Điện Tử'
                          : 'Thanh Toán 1,500,000 VNĐ Qua VNPAY / MoMo',
                    ),
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
