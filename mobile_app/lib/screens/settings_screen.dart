import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/settings_provider.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Consumer<SettingsProvider>(
        builder: (context, settings, _) {
          return ListView(
            padding: const EdgeInsets.all(16.0),
            children: [
              // AI Provider Selection
              Card(
                child: ListTile(
                  title: const Text('AI Provider'),
                  subtitle: DropdownButton<String>(
                    value: settings.aiProvider,
                    isExpanded: true,
                    items: const [
                      DropdownMenuItem(
                        value: 'lmstudio',
                        child: Text('LM Studio'),
                      ),
                      DropdownMenuItem(
                        value: 'openai',
                        child: Text('OpenAI'),
                      ),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        settings.setAIProvider(value);
                      }
                    },
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Server URL (for LM Studio)
              if (settings.aiProvider == 'lmstudio')
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('LM Studio Server URL'),
                        const SizedBox(height: 8),
                        TextField(
                          controller: TextEditingController(text: settings.serverUrl),
                          decoration: const InputDecoration(
                            hintText: 'http://localhost:1234',
                            border: OutlineInputBorder(),
                          ),
                          onChanged: settings.setServerUrl,
                        ),
                      ],
                    ),
                  ),
                ),

              // API Key (for OpenAI)
              if (settings.aiProvider == 'openai')
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('OpenAI API Key'),
                        const SizedBox(height: 8),
                        TextField(
                          controller: TextEditingController(text: settings.apiKey),
                          decoration: const InputDecoration(
                            hintText: 'Enter your OpenAI API key',
                            border: OutlineInputBorder(),
                          ),
                          obscureText: true,
                          onChanged: settings.setApiKey,
                        ),
                      ],
                    ),
                  ),
                ),

              const SizedBox(height: 16),

              // Model Selection
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Selected Model'),
                          IconButton(
                            icon: settings.isLoadingModels
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.refresh),
                            onPressed: settings.isLoadingModels
                                ? null
                                : () => settings.refreshModels(context),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      if (settings.error != null)
                        Text(
                          settings.error!,
                          style: const TextStyle(color: Colors.red),
                        )
                      else if (settings.models.isEmpty)
                        const Text(
                          'No models available. Try refreshing.',
                          style: TextStyle(color: Colors.grey),
                        )
                      else
                        DropdownButton<String>(
                          value: settings.selectedModel,
                          isExpanded: true,
                          items: settings.models.map((model) {
                            return DropdownMenuItem(
                              value: model,
                              child: Text(model),
                            );
                          }).toList(),
                          onChanged: (value) {
                            if (value != null) {
                              settings.setSelectedModel(value);
                            }
                          },
                        ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Local Network Permission Card
              FutureBuilder<bool>(
                future: settings.hasLocalNetworkPermission,
                builder: (context, snapshot) {
                  return Card(
                    child: ListTile(
                      title: const Text('Local Network Access'),
                      subtitle: Text(
                        snapshot.data == true
                            ? 'Enabled'
                            : 'Disabled - Required for LM Studio',
                      ),
                      trailing: IconButton(
                        icon: const Icon(Icons.open_in_new),
                        onPressed: () => settings.openAppSettings(),
                      ),
                    ),
                  );
                },
              ),
            ],
          );
        },
      ),
    );
  }
} 