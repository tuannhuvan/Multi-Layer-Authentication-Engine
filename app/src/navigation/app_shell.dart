import 'package:flutter/material.dart';
import 'screens/auth/auth_sso_screen.dart';
import 'screens/attendance/attendance_screen.dart';
import 'screens/grades/grades_screen.dart';
import 'screens/payment/payment_screen.dart';
import 'services/mocker_api_service.dart';

class AuthShieldMobileShell extends StatefulWidget {
  const AuthShieldMobileShell({super.key});

  @override
  State<AuthShieldMobileShell> createState() => _AuthShieldMobileShellState();
}

class _AuthShieldMobileShellState extends State<AuthShieldMobileShell> {
  final AuthShieldMockerService _api = AuthShieldMockerService();
  int _currentIndex = 0;

  void _showNotification(String title, String detail, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: isError ? Colors.red.shade900 : Colors.teal.shade900,
        behavior: SnackBarBehavior.floating,
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
            ),
            const SizedBox(height: 2),
            Text(detail, style: const TextStyle(fontSize: 12)),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      AuthSsoScreen(
        api: _api,
        onStateChanged: () => setState(() {}),
        onNotify: _showNotification,
      ),
      AttendanceScreen(api: _api, onNotify: _showNotification),
      GradesScreen(api: _api, onNotify: _showNotification),
      PaymentAndLmsScreen(api: _api, onNotify: _showNotification),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFF020617),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F172A),
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'AuthShield-LMS Mobile',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            Text(
              'TCVN 11930 Cấp Độ 3 · SSO S1/S2/S3 · Anti-IDOR',
              style: TextStyle(fontSize: 11, color: Colors.white60),
            ),
          ],
        ),
      ),
      body: pages[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (idx) => setState(() => _currentIndex = idx),
        type: BottomNavigationBarType.fixed,
        backgroundColor: const Color(0xFF0F172A),
        selectedItemColor: Colors.lightBlueAccent,
        unselectedItemColor: Colors.white54,
        selectedFontSize: 11,
        unselectedFontSize: 11,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.shield_outlined),
            label: 'SSO & Switcher',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.fact_check_outlined),
            label: 'Điểm Danh',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.grade_outlined),
            label: 'Điểm & Ký S3',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.account_balance_wallet_outlined),
            label: 'LMS & Học Phí',
          ),
        ],
      ),
    );
  }
}
