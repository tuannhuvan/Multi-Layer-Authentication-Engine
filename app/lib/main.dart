import 'package:flutter/material.dart';
import '../src/navigation/app_shell.dart';

/// Điểm khởi chạy chuẩn của Flutter trong Android Studio (`lib/main.dart`)
void main() {
  runApp(const AuthShieldMobileApp());
}

class AuthShieldMobileApp extends StatelessWidget {
  const AuthShieldMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AuthShield-LMS Mobile',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0284C7),
          brightness: Brightness.dark,
        ),
      ),
      home: const AuthShieldMobileShell(),
    );
  }
}
