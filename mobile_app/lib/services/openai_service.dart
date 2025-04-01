import 'dart:convert';
import 'package:http/http.dart' as http;
import 'ai_service.dart';

class OpenAIService implements AIService {
  final String apiKey;
  http.Client? _client;

  OpenAIService({required this.apiKey});

  @override
  Future<void> initialize() async {
    _client = http.Client();
  }

  @override
  Future<List<String>> getModels() async {
    try {
      final response = await _client?.get(
        Uri.parse('https://api.openai.com/v1/models'),
        headers: {
          'Authorization': 'Bearer $apiKey',
          'Content-Type': 'application/json',
        },
      );

      if (response == null) throw Exception('HTTP client not initialized');
      if (response.statusCode != 200) {
        throw Exception('Failed to fetch models: ${response.statusCode}');
      }

      final data = json.decode(response.body);
      if (data['data'] == null) return [];

      return (data['data'] as List)
          .map((model) => model['id'] as String)
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch models: $e');
    }
  }

  @override
  Future<String> sendPrompt(String model, String prompt, String shellType) async {
    try {
      final response = await _client?.post(
        Uri.parse('https://api.openai.com/v1/chat/completions'),
        headers: {
          'Authorization': 'Bearer $apiKey',
          'Content-Type': 'application/json',
        },
        body: json.encode({
          'model': model,
          'messages': [
            {
              'role': 'system',
              'content': 'You are a helpful assistant that provides commands for $shellType.'
            },
            {'role': 'user', 'content': prompt}
          ],
          'temperature': 0.7,
        }),
      );

      if (response == null) throw Exception('HTTP client not initialized');
      if (response.statusCode != 200) {
        throw Exception('Failed to send prompt: ${response.statusCode}');
      }

      final data = json.decode(response.body);
      if (data['choices'] == null || data['choices'].isEmpty) {
        throw Exception('No response from model');
      }

      return data['choices'][0]['message']['content'] as String;
    } catch (e) {
      throw Exception('Failed to send prompt: $e');
    }
  }

  @override
  void dispose() {
    _client?.close();
    _client = null;
  }
} 