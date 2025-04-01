import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_provider.dart';
import '../widgets/chat_input.dart';
import '../widgets/chat_messages.dart';
import '../widgets/shell_toggle.dart';
import 'settings_screen.dart';

class ChatScreen extends StatelessWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AIPrompt'),
        actions: [
          // Settings button
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
          ),
          // Delete chat button
          IconButton(
            icon: const Icon(Icons.delete_outline),
            onPressed: () {
              Provider.of<ChatProvider>(context, listen: false).clearChat();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Shell toggle at the top
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: ShellToggle(),
          ),
          // Chat messages in the middle (expandable)
          const Expanded(
            child: ChatMessages(),
          ),
          // Input box at the bottom (fixed size)
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8.0),
              child: ChatInput(),
            ),
          ),
        ],
      ),
    );
  }
} 