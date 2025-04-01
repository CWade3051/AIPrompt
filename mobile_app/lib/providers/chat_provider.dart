import 'package:flutter/material.dart';
import '../models/chat_message.dart';
import '../services/ai_service.dart';
import '../services/lm_studio_service.dart';
import '../services/openai_service.dart';
import 'package:provider/provider.dart';
import 'settings_provider.dart';

class ChatProvider extends ChangeNotifier {
  AIService? _aiService;
  List<ChatMessage> _messages = [];
  List<Map<String, dynamic>> _chatHistory = [];
  String _currentChatId = '';
  String _shellType = 'zsh';
  bool _isLoading = false;
  String? _error;

  List<ChatMessage> get messages => _messages;
  List<Map<String, dynamic>> get chatHistory => _chatHistory;
  String get shellType => _shellType;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> initializeService(String provider, String apiKey, String serverUrl) async {
    _error = null;
    notifyListeners();

    try {
      _aiService?.dispose();
      _aiService = provider == 'lmstudio'
          ? LMStudioService(serverUrl: serverUrl)
          : OpenAIService(apiKey: apiKey);

      await _aiService?.initialize();
      notifyListeners();
    } catch (e) {
      _error = 'Failed to initialize service: $e';
      notifyListeners();
    }
  }

  Future<List<String>> getAvailableModels() async {
    if (_aiService == null) {
      throw Exception('Service not initialized');
    }
    return await _aiService!.getModels();
  }

  void setShellType(String type) {
    _shellType = type;
    notifyListeners();
  }

  void createNewChat() {
    _currentChatId = DateTime.now().millisecondsSinceEpoch.toString();
    _messages = [];
    _error = null;
    notifyListeners();
  }

  void loadChat(String chatId) {
    final chat = _chatHistory.firstWhere((chat) => chat['id'] == chatId);
    _currentChatId = chatId;
    _messages = (chat['messages'] as List)
        .map((msg) => ChatMessage.fromJson(msg))
        .toList();
    _error = null;
    notifyListeners();
  }

  Future<void> sendMessage(String content) async {
    if (_aiService == null) {
      _error = 'Service not initialized';
      notifyListeners();
      return;
    }

    final settings = Provider.of<SettingsProvider>(navigatorKey.currentContext!, listen: false);
    if (settings.selectedModel.isEmpty) {
      _error = 'No model selected';
      notifyListeners();
      return;
    }

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final userMessage = ChatMessage(
        content: content,
        isUser: true,
      );
      _messages.add(userMessage);

      final response = await _aiService!.sendPrompt(
        settings.selectedModel,
        content,
        _shellType,
      );

      _messages.add(ChatMessage(
        content: response,
        isUser: false,
      ));

      _updateChatHistory();
    } catch (e) {
      _error = 'Failed to send message: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void _updateChatHistory() {
    final chatIndex = _chatHistory.indexWhere((chat) => chat['id'] == _currentChatId);
    final chatData = {
      'id': _currentChatId,
      'messages': _messages.map((msg) => msg.toJson()).toList(),
      'lastUpdated': DateTime.now().toIso8601String(),
    };

    if (chatIndex >= 0) {
      _chatHistory[chatIndex] = chatData;
    } else {
      _chatHistory.add(chatData);
    }
    notifyListeners();
  }

  void clearChat() {
    _messages = [];
    _error = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _aiService?.dispose();
    super.dispose();
  }
}

final navigatorKey = GlobalKey<NavigatorState>(); 