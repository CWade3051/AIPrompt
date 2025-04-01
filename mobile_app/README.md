# AIPrompt Mobile

A mobile application that provides an intuitive interface for interacting with AI language models through both OpenAI's API and LM Studio's local server.

## Features

- 🔄 Support for both OpenAI API and LM Studio local models
- 📱 Cross-platform mobile support (iOS and Android)
- 💬 Chat history management with persistent storage
- 🖥️ Shell type selection (ZSH/PowerShell)
- 🔍 Model selection and refresh capabilities
- 🔒 Secure API key handling
- 🌓 Dark mode support

## Installation

### Prerequisites

- Flutter SDK (latest version)
- iOS development tools (Xcode, CocoaPods) for iOS
- Android development tools (Android Studio, Android SDK) for Android

### Building from Source

1. Clone the repository and switch to the mobile branch:
   ```bash
   git clone https://github.com/yourusername/AIPrompt.git
   cd AIPrompt
   git checkout mobile
   ```

2. Navigate to the mobile app directory:
   ```bash
   cd mobile_app
   ```

3. Install dependencies:
   ```bash
   flutter pub get
   ```

4. Run the app:
   ```bash
   flutter run
   ```

## Usage

### Setting up AI Providers

#### OpenAI
1. Select "OpenAI" from the AI Provider dropdown in Settings
2. Enter your OpenAI API key
3. Click "Refresh Models" to load available models
4. Select your desired model from the dropdown

#### LM Studio
1. Start LM Studio and load your desired model
2. Select "LM Studio" from the AI Provider dropdown in Settings
3. Ensure the Server URL is set to `http://localhost:1234` (default)
4. Click "Refresh Models" to load available models
5. Select your desired model from the dropdown

### Working with Chats

1. **New Chat**: Tap the menu icon and select "New Chat" or use the button in the drawer
2. **Chat History**: Access previous chats from the drawer menu
3. **Delete Chats**: Use the clear button in the app bar to clear the current chat
4. **Shell Type**: Toggle between ZSH and PowerShell using the segmented button at the top

## Data Storage

- iOS: Chat history and settings are stored in the app's documents directory
- Android: Chat history and settings are stored in the app's internal storage

## Development

### Project Structure

```
mobile_app/
├── lib/
│   ├── models/         # Data models
│   ├── providers/      # State management
│   ├── screens/        # UI screens
│   ├── services/       # AI service implementations
│   ├── theme/          # App theming
│   ├── widgets/        # Reusable widgets
│   └── main.dart       # App entry point
├── ios/               # iOS-specific files
├── android/           # Android-specific files
└── pubspec.yaml       # Dependencies and assets
```

### Adding New Features

1. Create new models in the `models` directory
2. Implement services in the `services` directory
3. Add state management in the `providers` directory
4. Create UI components in the `screens` and `widgets` directories

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
