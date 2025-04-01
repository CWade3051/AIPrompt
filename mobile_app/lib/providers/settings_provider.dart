import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import '../services/ai_service.dart';
import '../services/lm_studio_service.dart';
import '../services/openai_service.dart';

class SettingsProvider extends ChangeNotifier {
  String _aiProvider = 'lmstudio';
  String _serverUrl = 'http://localhost:1234';
  String _apiKey = '';
  String? _selectedModel;
  List<String> _models = [];
  bool _isLoadingModels = false;
  String? _error;
  AIService? _service;

  // Getters
  String get aiProvider => _aiProvider;
  String get serverUrl => _serverUrl;
  String get apiKey => _apiKey;
  String? get selectedModel => _selectedModel;
  List<String> get models => _models;
  bool get isLoadingModels => _isLoadingModels;
  String? get error => _error;

  // Setters
  void setAIProvider(String provider) {
    _aiProvider = provider;
    _selectedModel = null;
    _models = [];
    notifyListeners();
  }

  void setServerUrl(String url) {
    _serverUrl = url;
    notifyListeners();
  }

  void setApiKey(String key) {
    _apiKey = key;
    notifyListeners();
  }

  void setSelectedModel(String model) {
    _selectedModel = model;
    notifyListeners();
  }

  // Initialize or update the AI service
  Future<void> _initializeService() async {
    _service?.dispose();
    
    if (_aiProvider == 'lmstudio') {
      _service = LMStudioService(serverUrl: _serverUrl);
    } else {
      _service = OpenAIService(apiKey: _apiKey);
    }

    await _service?.initialize();
  }

  // Refresh available models
  Future<void> refreshModels(BuildContext context) async {
    _isLoadingModels = true;
    _error = null;
    notifyListeners();

    try {
      // Check local network permission for LM Studio
      if (_aiProvider == 'lmstudio') {
        final status = await Permission.localNetwork.status;
        if (status.isDenied) {
          final result = await Permission.localNetwork.request();
          if (result.isDenied) {
            throw Exception('Local network permission required');
          }
        }
      }

      // Initialize service
      await _initializeService();

      // Get models
      _models = await _service?.getModels() ?? [];
      if (_models.isNotEmpty && _selectedModel == null) {
        _selectedModel = _models.first;
      }
    } catch (e) {
      _error = e.toString();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: ${e.toString()}')),
      );
    } finally {
      _isLoadingModels = false;
      notifyListeners();
    }
  }

  // Check local network permission
  Future<bool> get hasLocalNetworkPermission async {
    final status = await Permission.localNetwork.status;
    return status.isGranted;
  }

  // Open app settings
  Future<void> openAppSettings() async {
    await openAppSettings();
  }

  @override
  void dispose() {
    _service?.dispose();
    super.dispose();
  }
} 