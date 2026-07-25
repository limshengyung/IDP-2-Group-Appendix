import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sms_sender/sms_sender.dart';
import 'package:permission_handler/permission_handler.dart';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MATLAB SMS Gateway',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF4F46E5),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF7F7FB),
      ),
      home: const SmsServerPage(),
    );
  }
}

class LogEntry {
  final String message;
  final bool isError;
  final bool isSuccess;
  final DateTime time;
  LogEntry(this.message, {this.isError = false, this.isSuccess = false})
      : time = DateTime.now();
}

class SmsServerPage extends StatefulWidget {
  const SmsServerPage({super.key});
  @override
  State<SmsServerPage> createState() => _SmsServerPageState();
}

class _SmsServerPageState extends State<SmsServerPage> {
  String? ipAddress;
  bool serverRunning = false;
  bool permissionGranted = false;
  final List<LogEntry> logs = [];

  final phoneController = TextEditingController();
  final messageController = TextEditingController(text: 'Test alert from app');

  void _log(String msg, {bool isError = false, bool isSuccess = false}) {
    debugPrint((isError ? '❌ ' : 'ℹ️ ') + msg);
    setState(() {
      logs.insert(0, LogEntry(msg, isError: isError, isSuccess: isSuccess));
      if (logs.length > 50) logs.removeLast();
    });
  }

  void _showSnack(String msg, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: isError ? Colors.red.shade600 : Colors.green.shade600,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        duration: const Duration(seconds: 3),
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    _log('Requesting SMS permission...');
    var smsStatus = await Permission.sms.request();
    var phoneStatus = await Permission.phone.request();
    permissionGranted = smsStatus.isGranted && phoneStatus.isGranted;
    _log('SMS: $smsStatus · Phone: $phoneStatus', isError: !permissionGranted);

    for (var iface in await NetworkInterface.list()) {
      for (var addr in iface.addresses) {
        if (!addr.isLoopback && addr.type == InternetAddressType.IPv4) {
          ipAddress = addr.address;
        }
      }
    }
    _log('Local IP detected: ${ipAddress ?? "not found"}');

    if (!permissionGranted) {
      _log('Cannot start server — permission denied. Enable it in Settings > Apps > Permissions.',
          isError: true);
      setState(() {});
      return;
    }

    _startServer();
  }

  Future<void> _startServer() async {
    try {
      final server = await HttpServer.bind(InternetAddress.anyIPv4, 8080);
      setState(() => serverRunning = true);
      _log('Server started successfully', isSuccess: true);

      await for (HttpRequest request in server) {
        if (request.method == 'POST' && request.uri.path == '/sendsms') {
          try {
            final content = await utf8.decoder.bind(request).join();
            final data = jsonDecode(content);
            final String phone = data['phone'];
            final String message = data['message'];

            _log('Request received → $phone: "$message"');
            await SmsSender.sendSms(phoneNumber: phone, message: message);
            _log('SMS sent to $phone', isSuccess: true);

            request.response
              ..statusCode = 200
              ..headers.contentType = ContentType.json
              ..write(jsonEncode({'status': 'sent'}));
          } catch (e) {
            _log('SMS send failed: $e', isError: true);
            request.response
              ..statusCode = 500
              ..headers.contentType = ContentType.json
              ..write(jsonEncode({'status': 'error', 'detail': e.toString()}));
          }
        } else {
          request.response.statusCode = 404;
        }
        await request.response.close();
      }
    } catch (e) {
      _log('Failed to start server: $e', isError: true);
    }
  }

  Future<void> _sendTestSms() async {
    if (phoneController.text.isEmpty) {
      _showSnack('Enter a phone number first', isError: true);
      return;
    }
    try {
      _log('Manual test → ${phoneController.text}');
      await SmsSender.sendSms(
        phoneNumber: phoneController.text,
        message: messageController.text,
      );
      _log('Manual test SMS sent successfully', isSuccess: true);
      _showSnack('SMS sent successfully');
    } catch (e) {
      _log('Manual test failed: $e', isError: true);
      _showSnack('Failed: $e', isError: true);
    }
  }

  IconData _iconFor(LogEntry e) {
    if (e.isError) return Icons.error_rounded;
    if (e.isSuccess) return Icons.check_circle_rounded;
    return Icons.info_rounded;
  }

  Color _colorFor(LogEntry e) {
    if (e.isError) return Colors.red.shade600;
    if (e.isSuccess) return Colors.green.shade600;
    return Colors.blueGrey.shade400;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 120,
            pinned: true,
            backgroundColor: const Color(0xFF4F46E5),
            flexibleSpace: FlexibleSpaceBar(
              titlePadding: const EdgeInsets.only(left: 20, bottom: 16),
              title: const Text('SMS Gateway',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20)),
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFF4F46E5), Color(0xFF7C3AED)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Status card
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.05),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: serverRunning
                                    ? Colors.green.shade50
                                    : Colors.orange.shade50,
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                serverRunning ? Icons.cloud_done_rounded : Icons.cloud_sync_rounded,
                                color: serverRunning ? Colors.green.shade600 : Colors.orange.shade600,
                                size: 26,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    serverRunning ? 'Server Online' : 'Starting up…',
                                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                                  ),
                                  const SizedBox(height: 2),
                                  Row(
                                    children: [
                                      Icon(
                                        permissionGranted ? Icons.verified_user_rounded : Icons.gpp_bad_rounded,
                                        size: 14,
                                        color: permissionGranted ? Colors.green : Colors.red,
                                      ),
                                      const SizedBox(width: 4),
                                      Text(
                                        permissionGranted ? 'Permissions OK' : 'Permission denied',
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: permissionGranted ? Colors.green.shade700 : Colors.red,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        if (ipAddress != null) ...[
                          const SizedBox(height: 16),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF3F3FB),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.lan_rounded, size: 18, color: Colors.indigo),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: SelectableText(
                                    '$ipAddress:8080',
                                    style: const TextStyle(
                                      fontFamily: 'monospace',
                                      fontWeight: FontWeight.w600,
                                      fontSize: 14,
                                    ),
                                  ),
                                ),
                                IconButton(
                                  visualDensity: VisualDensity.compact,
                                  icon: const Icon(Icons.copy_rounded, size: 18),
                                  onPressed: () {
                                    Clipboard.setData(ClipboardData(text: '$ipAddress:8080'));
                                    _showSnack('IP copied to clipboard');
                                  },
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Test SMS card
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.05),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: const [
                            Icon(Icons.send_rounded, size: 18, color: Colors.indigo),
                            SizedBox(width: 8),
                            Text('Send Test SMS',
                                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                          ],
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: phoneController,
                          keyboardType: TextInputType.phone,
                          decoration: InputDecoration(
                            labelText: 'Phone number',
                            hintText: '+60123456789',
                            prefixIcon: const Icon(Icons.phone_rounded, size: 20),
                            filled: true,
                            fillColor: const Color(0xFFF7F7FB),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: BorderSide.none,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: messageController,
                          maxLines: 2,
                          decoration: InputDecoration(
                            labelText: 'Message',
                            prefixIcon: const Icon(Icons.message_rounded, size: 20),
                            filled: true,
                            fillColor: const Color(0xFFF7F7FB),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: BorderSide.none,
                            ),
                          ),
                        ),
                        const SizedBox(height: 14),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            style: FilledButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10),
                              ),
                            ),
                            onPressed: _sendTestSms,
                            icon: const Icon(Icons.send_rounded, size: 18),
                            label: const Text('Send Now'),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  Row(
                    children: [
                      const Icon(Icons.history_rounded, size: 18, color: Colors.black54),
                      const SizedBox(width: 6),
                      const Text('Activity Log',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                      const Spacer(),
                      TextButton.icon(
                        onPressed: () => setState(() => logs.clear()),
                        icon: const Icon(Icons.delete_outline_rounded, size: 16),
                        label: const Text('Clear'),
                        style: TextButton.styleFrom(foregroundColor: Colors.black54),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                ],
              ),
            ),
          ),

          // Log list
          logs.isEmpty
              ? const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: Column(
                  children: [
                    Icon(Icons.inbox_rounded, size: 40, color: Colors.black26),
                    SizedBox(height: 8),
                    Text('No activity yet', style: TextStyle(color: Colors.black38)),
                  ],
                ),
              ),
            ),
          )
              : SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
            sliver: SliverList(
              delegate: SliverChildBuilderDelegate(
                    (context, index) {
                  final entry = logs[index];
                  final t = entry.time;
                  final timeStr =
                      '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}:${t.second.toString().padLeft(2, '0')}';
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(_iconFor(entry), size: 18, color: _colorFor(entry)),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                entry.message,
                                style: const TextStyle(fontSize: 13.5),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                timeStr,
                                style: const TextStyle(fontSize: 11, color: Colors.black38),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                },
                childCount: logs.length,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
