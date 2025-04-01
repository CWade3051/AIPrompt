abstract class AIService {
  Future<void> initialize();
  Future<List<String>> getModels();
  Future<String> sendPrompt(String model, String prompt, String shellType);
  void dispose();
} 