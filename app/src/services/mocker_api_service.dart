import 'dart:convert';
import 'dart:io';

/// Dịch vụ gọi API Contract Mocker cho Flutter Mobile App (Android Studio)
/// - Tự động dùng `http://10.0.2.2:18080` khi chạy trên Android Emulator
///   hoặc `http://127.0.0.1:18080` trên Desktop/Windows.
/// - Tự động đính kèm Header:
///   `Authorization: Bearer <JWT>`, `X-Workspace-Context`, `X-Auth-ACR`, `X-Assigned-Classes`
/// - Có sẵn chế độ Offline Fallback tất định để chạy mượt ngay cả khi chưa bật server Python.
class AuthShieldMockerService {
  static String get baseUrl {
    try {
      if (Platform.isAndroid) {
        return 'http://10.0.2.2:18080';
      }
    } catch (_) {}
    return 'http://127.0.0.1:18080';
  }

  String username = 'gv_kiem_pho_ht_01';
  String fullName = 'TS. Nguyễn Văn Minh (Phó HT kiêm GV Toán)';
  List<String> roles = ['ROLE_BOARD', 'ROLE_TEACHER'];
  String activeScope = 'TEACHER';
  String currentAcr = 'S2';
  List<String> assignedClasses = ['12A1', '10A1'];
  String studentCode = 'HS001';

  Future<Map<String, dynamic>> switchWorkspace(String targetScope) async {
    final roleMap = {
      'BOARD': 'ROLE_BOARD',
      'TEACHER': 'ROLE_TEACHER',
      'STUDENT': 'ROLE_STUDENT',
      'ADMIN': 'ROLE_ADMIN',
    };
    final reqRole = roleMap[targetScope];
    if (reqRole != null && !roles.contains(reqRole)) {
      return {
        'ok': false,
        'status': 403,
        'title': 'Workspace Switch Denied (PEP Guard)',
        'detail':
            'Tài khoản "$username" không sở hữu quyền $reqRole để chuyển sang góc $targetScope.',
        'error_code': 'WORKSPACE_ROLE_MISSING',
        'traceId': 'tr-flutter-403-ws',
      };
    }

    activeScope = targetScope;
    return {
      'ok': true,
      'status': 200,
      'active_scope': activeScope,
      'message':
          'UC-04: Đã chuyển sang góc làm việc $targetScope (X-Workspace-Context: $targetScope)',
    };
  }

  Future<Map<String, dynamic>> stepUpAcrS3(String method, String pin) async {
    currentAcr = 'S3';
    return {
      'ok': true,
      'status': 200,
      'current_acr': 'S3',
      's3_signature': 'S3-$method-FIDO2-VERIFIED',
      'message':
          'UC-02: Đã xác thực sinh trắc học / Soft-HSM PIN và nâng cấp phiên lên ACR=S3!',
    };
  }

  Future<Map<String, dynamic>> checkTeacherClassScope(String targetClassId) async {
    try {
      final client = HttpClient();
      client.connectionTimeout = const Duration(milliseconds: 1200);
      final req = await client.putUrl(
        Uri.parse('$baseUrl/api/v1/classes/$targetClassId/grades'),
      );
      req.headers.set('Content-Type', 'application/json');
      req.headers.set('X-Workspace-Context', activeScope);
      req.headers.set('X-Auth-ACR', currentAcr);
      req.headers.set('X-Assigned-Classes', assignedClasses.join(','));
      req.add(utf8.encode(jsonEncode({
        'student_code': 'HS001',
        'class_id': targetClassId,
        'tx1': 8.5,
        'tx2': 8.0,
        'midterm': 8.5,
        'final_exam': 9.0,
      })));
      final resp = await req.close();
      final body = await resp.transform(utf8.decoder).join();
      final data = jsonDecode(body) as Map<String, dynamic>;
      return {'ok': resp.statusCode == 200, 'status': resp.statusCode, ...data};
    } catch (_) {
      // Deterministic Fallback matching BR-031 & Anti-IDOR
      if (!assignedClasses.contains(targetClassId)) {
        return {
          'ok': false,
          'status': 403,
          'title': 'Anti-IDOR Data Scope Blocked (Hình 7 Bước 26)',
          'detail':
              'Chặn Anti-IDOR: Giáo viên không được phân công giảng dạy lớp $targetClassId!',
          'error_code': 'UNIT_SCOPE_FORBIDDEN',
          'traceId': 'tr-idor-12a2-blocked',
        };
      }
      return {
        'ok': true,
        'status': 200,
        'class_id': targetClassId,
        'average_score': 8.6,
        'academic_rank': 'GIOI',
      };
    }
  }
}
