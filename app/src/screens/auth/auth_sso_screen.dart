import 'package:flutter/material.dart';
import '../../services/mocker_api_service.dart';

class AuthSsoScreen extends StatelessWidget {
  final AuthShieldMockerService api;
  final VoidCallback onStateChanged;
  final void Function(String title, String detail, {bool isError}) onNotify;

  const AuthSsoScreen({
    super.key,
    required this.api,
    required this.onStateChanged,
    required this.onNotify,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF0284C7), Color(0xFF4F46E5)],
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'PH1 · CỔNG XÁC THỰC ĐA TẦNG SSO-MFA',
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                api.fullName,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  Chip(
                    label: Text('Scope: ${api.activeScope}'),
                    backgroundColor: Colors.black26,
                    labelStyle: const TextStyle(color: Colors.white, fontSize: 12),
                  ),
                  Chip(
                    label: Text('ACR: ${api.currentAcr}'),
                    backgroundColor: api.currentAcr == 'S3'
                        ? Colors.purple.shade700
                        : Colors.teal.shade700,
                    labelStyle: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Card(
          color: const Color(0xFF0F172A),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'UC-04 · Chuyển Đổi Góc Làm Việc (Workspace Switcher)',
                  style: TextStyle(
                    color: Colors.lightBlueAccent,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Tài khoản kiêm nhiệm sở hữu đồng thời ROLE_BOARD và ROLE_TEACHER (Không nhân bản Role rác).',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: ['TEACHER', 'BOARD', 'STUDENT', 'ADMIN'].map((scope) {
                    final isCurrent = api.activeScope == scope;
                    return ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: isCurrent
                            ? Colors.sky.shade600
                            : const Color(0xFF1E293B),
                        foregroundColor: Colors.white,
                      ),
                      onPressed: () async {
                        final res = await api.switchWorkspace(scope);
                        onStateChanged();
                        if (res['ok'] == true) {
                          onNotify('UC-04 Workspace Switcher', res['message']);
                        } else {
                          onNotify(
                            'HTTP 403 ${res['title']}',
                            '${res['detail']} (traceId: ${res['traceId']})',
                            isError: true,
                          );
                        }
                      },
                      child: Text('Góc $scope'),
                    );
                  }).toList(),
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
                  'UC-02 · Sinh Trắc Học FIDO2 / Soft-HSM Step-Up (ACR = S3)',
                  style: TextStyle(
                    color: Colors.purpleAccent,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Nâng cấp phiên xác thực từ S2 lên S3 để ký khóa bảng điểm hoặc phê duyệt mở khóa sửa điểm Maker-Checker.',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.purple.shade600,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () async {
                          final res = await api.stepUpAcrS3('FIDO2_BIOMETRIC', '888888');
                          onStateChanged();
                          onNotify('UC-02 Step-Up S3', res['message']);
                        },
                        icon: const Icon(Icons.fingerprint),
                        label: const Text('Ký Số FIDO2 / FaceID (S3)'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.redAccent,
                      ),
                      onPressed: () {
                        onNotify(
                          'HTTP 423 Account Locked (UC-01)',
                          'Tài khoản bị khóa lũy tiến 15 phút do nhập sai mật khẩu quá 5 lần (traceId: tr-lockout-423).',
                          isError: true,
                        );
                      },
                      child: const Text('Test 423 Lockout'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
