import platform
import requests
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import json
import os
import time
import glob
import sys
import traceback
import logging
import signal
import psutil
import openai

# Set up logging and chat directories based on platform
def setup_app_directories():
    if platform.system().lower().startswith('win'):
        # Use AppData for Windows
        base_dir = os.path.join(os.environ.get('APPDATA', ''), 'AIPrompt')
    else:
        # Use Application Support for macOS (more standard than Library)
        base_dir = os.path.expanduser("~/Library/Application Support/AIPrompt")
    
    # Create standard subdirectories
    log_dir = os.path.join(base_dir, 'Logs')
    chat_dir = os.path.join(base_dir, 'Chats')
    
    # Create directories
    for directory in [log_dir, chat_dir]:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
            logging.error(f"Error creating directory {directory}: {e}")
    
    return log_dir, chat_dir

# Set up logging
def setup_logging(log_dir):
    log_file = os.path.join(log_dir, "aiprompt.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info("Starting AIPrompt application")

# Initialize directories
LOG_DIR, CHAT_DIR = setup_app_directories()

# Redirect stdout/stderr to a file to catch crashes in --windowed mode
try:
    sys.stdout = open(os.path.join(LOG_DIR, "aiprompt_stdout.log"), "w")
    sys.stderr = open(os.path.join(LOG_DIR, "aiprompt_stderr.log"), "w")
except Exception as e:
    print(f"Failed to redirect stdout/stderr: {e}")

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Try to set TCL/TK paths with error handling
try:
    if platform.system() == 'Darwin':  # macOS
        tcl_path = '/opt/homebrew/Cellar/tcl-tk@8/8.6.16/lib/tcl8.6'
        tk_path = '/opt/homebrew/Cellar/tcl-tk@8/8.6.16/lib/tk8.6'
        
        if os.path.exists(tcl_path):
            os.environ['TCL_LIBRARY'] = tcl_path
        if os.path.exists(tk_path):
            os.environ['TK_LIBRARY'] = tk_path
except Exception as e:
    print(f"Warning: Failed to set TCL/TK paths: {e}")

class LMStudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI GUI Client")

        # Detect if we're on Windows or not
        self.is_windows = platform.system().lower().startswith('win')

        # Set icon for Windows
        if self.is_windows:
            try:
                icon_path = os.path.join(APP_ROOT, "assets", "icons", "icon.ico")
                self.root.iconbitmap(icon_path)
            except Exception as e:
                print(f"Failed to set window icon: {e}")

        if self.is_windows:
            self.shell_label = "PowerShell"
            self.shell_key = "powershell"
            # Set up temp directory for Windows
            self.log_dir = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'AIPrompt', 'Logs')
        else:
            self.shell_label = "ZSH"
            self.shell_key = "zsh"
            # Use the same log directory as the rest of the app
            self.log_dir = LOG_DIR

        # Create log directory
        os.makedirs(self.log_dir, exist_ok=True)

        # Set up logging
        log_file = os.path.join(self.log_dir, "aiprompt.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info(f"Starting AIPrompt application on {platform.system()}")

        # Redirect stdout/stderr
        try:
            sys.stdout = open(os.path.join(self.log_dir, "aiprompt_stdout.log"), "w")
            sys.stderr = open(os.path.join(self.log_dir, "aiprompt_stderr.log"), "w")
        except Exception as e:
            print(f"Failed to redirect stdout/stderr: {e}")

        # Initialize conversation history
        self.conversation_history = []
        self.current_chat_id = self.generate_chat_id()
        self.current_chat_title = "New Chat"
        self.terminal_output = []

        # Create chats directory if it doesn't exist
        os.makedirs(CHAT_DIR, exist_ok=True)

        # Default LM Studio info
        self.lmstudio_url_default = "http://localhost:1234"  # Changed to localhost
        self.server_url = tk.StringVar(master=self.root, value=self.lmstudio_url_default)
        self.openai_api_key = tk.StringVar(master=self.root, value="")

        # Track which provider is selected
        self.ai_provider = tk.StringVar(master=self.root, value="LM Studio")
        self.selected_model = tk.StringVar(master=self.root, value="")

        # Model list for either LM Studio or OpenAI
        self.models_list = []

        # Process tracking
        self.current_process = None
        self.output_running = False
        self.current_shell_command = ""

        # Create the UI
        self.create_widgets()

        # By default, use LM Studio as our client
        self.refresh_models()
        
        # Load existing chats on startup
        self.update_chat_list()

    def create_widgets(self):
        """
        Builds the entire Tkinter UI:
          1) Provider selection + server/API key configuration.
          2) Model selection.
          3) A resizable PanedWindow containing:
             - Instructions (read-only)
             - Prompt input
             - Recommended Commands (editable)
             - Terminal Output.
          4) Action buttons at the bottom.
        """
        # Add chat history frame on the left
        self.history_frame = tk.Frame(self.root, width=200)
        self.history_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Create header frame for history label and buttons
        history_header = tk.Frame(self.history_frame)
        history_header.pack(fill=tk.X, pady=(0, 5))
        
        # Add label and buttons in same row
        tk.Label(history_header, text="Chat History").pack(side=tk.LEFT)
        
        # Button frame for New Chat and Delete buttons
        button_frame = tk.Frame(history_header)
        button_frame.pack(side=tk.RIGHT)
        
        tk.Button(button_frame, text="New Chat", command=self.start_new_chat).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Delete", command=self.delete_selected_chats).pack(side=tk.LEFT, padx=2)
        
        # Add history listbox with scrollbar
        history_scroll = tk.Scrollbar(self.history_frame)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure listbox for multi-select
        self.history_list = tk.Listbox(
            self.history_frame,
            width=25,
            yscrollcommand=history_scroll.set,
            selectmode=tk.EXTENDED  # Enable multi-select
        )
        self.history_list.pack(side=tk.LEFT, fill=tk.Y)
        history_scroll.config(command=self.history_list.yview)
        self.history_list.bind('<<ListboxSelect>>', self.on_history_select)
        # Add mouse click handler to prevent accidental multi-select
        self.history_list.bind('<Button-1>', self.on_history_click)

        # Create main content frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Top Frame: Provider Selection ---
        provider_frame = tk.Frame(main_frame)
        provider_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(provider_frame, text="AI Provider:").pack(side=tk.LEFT)
        provider_dropdown = ttk.Combobox(
            provider_frame,
            textvariable=self.ai_provider,
            values=["LM Studio", "OpenAI"],
            width=12
        )
        provider_dropdown.pack(side=tk.LEFT, padx=5)
        provider_dropdown.bind("<<ComboboxSelected>>", self.on_provider_change)

        # Add Clear All Chats button to the right of provider selection
        tk.Button(provider_frame, text="Clear All Chats", command=self.clear_all_chats).pack(side=tk.RIGHT)

        # --- Config Frame: LM Studio URL or OpenAI API Key ---
        config_frame = tk.Frame(main_frame)
        config_frame.pack(fill=tk.X, padx=5, pady=5)

        self.server_label = tk.Label(config_frame, text="LM Studio Server URL:")
        self.server_label.pack(side=tk.LEFT)
        self.server_entry = tk.Entry(config_frame, textvariable=self.server_url, width=40)
        self.server_entry.pack(side=tk.LEFT, padx=5)

        self.api_key_label = tk.Label(config_frame, text="OpenAI API Key:")
        self.api_key_entry = tk.Entry(config_frame, textvariable=self.openai_api_key, width=40, show="*")
        # By default, hide OpenAI fields
        self.api_key_label.pack_forget()
        self.api_key_entry.pack_forget()

        tk.Button(config_frame, text="Refresh Models", command=self.refresh_models).pack(side=tk.RIGHT)

        # --- Model Selection Frame ---
        model_frame = tk.Frame(main_frame)
        model_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(model_frame, text="Select Model:").pack(side=tk.LEFT)
        self.model_dropdown = ttk.Combobox(
            model_frame,
            textvariable=self.selected_model,
            values=self.models_list,
            width=40
        )
        self.model_dropdown.pack(side=tk.LEFT, padx=5)

        # --- PanedWindow for Instructions, Prompt, Commands, and Output ---
        self.main_paned = tk.PanedWindow(main_frame, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # 1) Instructions Frame (read-only)
        instructions_frame = tk.Frame(self.main_paned)
        self.main_paned.add(instructions_frame, minsize=80)
        tk.Label(instructions_frame, text=f"Instructions from {self.shell_label} Assistant:").pack(anchor="w")
        self.instructions_text = scrolledtext.ScrolledText(instructions_frame, wrap="word", height=6)
        self.instructions_text.pack(fill=tk.BOTH, expand=True)
        self.instructions_text.config(state=tk.DISABLED)

        # 2) Prompt Input Frame
        prompt_frame = tk.Frame(self.main_paned)
        self.main_paned.add(prompt_frame, minsize=80)
        tk.Label(prompt_frame, text="Enter your prompt:").pack(anchor="w")
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, wrap="word", height=6)
        self.prompt_text.pack(fill=tk.BOTH, expand=True)

        # 3) Recommended Commands Frame (editable)
        commands_frame = tk.Frame(self.main_paned)
        self.main_paned.add(commands_frame, minsize=60)
        self.commands_label = tk.Label(commands_frame, text=f"Recommended {self.shell_label} Commands:")
        self.commands_label.pack(anchor="w")
        self.commands_text = scrolledtext.ScrolledText(commands_frame, wrap="word", height=3)
        self.commands_text.pack(fill=tk.BOTH, expand=True)
        # Add text change event handler
        self.commands_text.bind('<<Modified>>', self.on_commands_text_change)

        # 4) Terminal Output Frame
        output_frame = tk.Frame(self.main_paned)
        self.main_paned.add(output_frame, minsize=100)
        
        # Create header frame for output
        output_header = tk.Frame(output_frame)
        output_header.pack(fill=tk.X)
        
        self.output_label = tk.Label(output_header, text=f"{self.shell_label} Output:")
        self.output_label.pack(side=tk.LEFT)
        
        # Add Kill Command button (initially disabled)
        self.kill_button = tk.Button(
            output_header,
            text="Kill Command",
            command=self.kill_current_process,
            state=tk.DISABLED,
            fg='red'
        )
        self.kill_button.pack(side=tk.RIGHT, padx=5)
        
        # Add output text widget
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap="word", height=8)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # --- Bottom Button Row ---
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.send_prompt_button = tk.Button(button_frame, text="Send Prompt", command=self.on_send_prompt)
        self.send_prompt_button.pack(side=tk.LEFT, padx=(0, 5))

        self.copy_output_button = tk.Button(button_frame, text="Copy Output to Prompt", command=self.copy_output_to_prompt)
        self.copy_output_button.pack(side=tk.LEFT, padx=(0, 5))

        self.run_command_button = tk.Button(button_frame, text=f"Run {self.shell_label} Command", command=self.on_run_command)
        self.run_command_button.pack(side=tk.LEFT, padx=(0, 5))
        self.run_command_button.config(state=tk.DISABLED)

        # Clear Output Button
        self.clear_output_button = tk.Button(button_frame, text="Clear Output", command=self.clear_output)
        self.clear_output_button.pack(side=tk.LEFT, padx=(0, 5))

    # ---------------------- Provider Handling ----------------------
    def on_provider_change(self, event):
        """
        Switch between 'LM Studio' and 'OpenAI' in the UI.
        Show/hide the server URL or API key fields accordingly.
        """
        provider = self.ai_provider.get()
        if provider == "LM Studio":
            self.server_label.config(text="LM Studio Server URL:")
            self.server_label.pack(side=tk.LEFT)
            self.server_entry.pack(side=tk.LEFT, padx=5)
            # Hide OpenAI fields
            self.api_key_label.pack_forget()
            self.api_key_entry.pack_forget()
            # Reset server URL to default if empty
            if not self.server_url.get():
                self.server_url.set(self.lmstudio_url_default)
        elif provider == "OpenAI":
            # Hide LM Studio server fields
            self.server_label.pack_forget()
            self.server_entry.pack_forget()
            # Show OpenAI fields
            self.api_key_label.pack(side=tk.LEFT)
            self.api_key_entry.pack(side=tk.LEFT, padx=5)
        # Clear model list and dropdown
        self.models_list.clear()
        self.model_dropdown['values'] = []
        self.selected_model.set("")

    def refresh_models(self):
        """
        Fetches the list of models depending on the selected AI provider.
        """
        provider = self.ai_provider.get()
        self.log_output(f"Refreshing models from {provider}...")

        def do_refresh():
            if provider == "LM Studio":
                models = self.get_lm_studio_models()
            else:
                models = self.get_openai_models(self.openai_api_key.get())

            if models:
                self.models_list = models
                self.root.after(0, self.update_model_dropdown)
                self.log_output("Models refreshed: " + ", ".join(models))
            else:
                self.log_output("Failed to refresh models.")

        threading.Thread(target=do_refresh, daemon=True).start()

    def get_lm_studio_models(self):
        """
        Retrieves model IDs from LM Studio's /v1/models endpoint.
        """
        url = self.server_url.get().rstrip('/') + "/v1/models"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                return [m["id"] for m in data["data"]]
            return []
        except Exception as e:
            print("Error fetching LM Studio models:", e)
            return []

    def get_openai_models(self, api_key):
        """
        Retrieves model IDs from OpenAI's /v1/models endpoint.
        """
        url = "https://api.openai.com/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                return [m["id"] for m in data["data"]]
            return []
        except Exception as e:
            print("Error fetching OpenAI models:", e)
            return []

    def update_model_dropdown(self):
        """
        Updates the model dropdown with the retrieved models.
        """
        self.model_dropdown['values'] = self.models_list
        if self.models_list and not self.selected_model.get():
            self.selected_model.set(self.models_list[0])

    # ---------------------- Prompt Handling ----------------------
    def on_send_prompt(self):
        """
        Gathers the user's prompt and sends it to the selected AI provider.
        Expects a JSON response with keys for either 'zsh' (or 'powershell') and 'instructions'.
        """
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showwarning("Warning", "Please enter a prompt.")
            return

        provider = self.ai_provider.get()
        model = self.selected_model.get()
        if not model:
            messagebox.showwarning("Warning", "Please select a model.")
            return

        self.log_output(f"Sending prompt to {provider} using model: {model}")

        def do_send():
            if provider == "LM Studio":
                response = self.send_lm_studio_prompt(model, prompt)
            else:
                response = self.send_openai_prompt(model, prompt, self.openai_api_key.get())

            if response:
                # Pick the shell command based on OS
                shell_cmd = response.get("powershell" if self.is_windows else "zsh", "").strip()
                instructions = response.get("instructions", "").strip()

                # Update instructions box (read-only)
                self.instructions_text.config(state=tk.NORMAL)
                self.instructions_text.delete("1.0", tk.END)
                self.instructions_text.insert(tk.END, instructions)
                self.instructions_text.config(state=tk.DISABLED)

                # Update recommended commands box (editable)
                self.commands_text.config(state=tk.NORMAL)
                self.commands_text.delete("1.0", tk.END)
                self.commands_text.insert(tk.END, shell_cmd)

                self.current_shell_command = shell_cmd
                if shell_cmd:
                    self.run_command_button.config(state=tk.NORMAL)
                else:
                    self.run_command_button.config(state=tk.DISABLED)
            else:
                self.log_output("Error: No response or invalid response from AI.")

        threading.Thread(target=do_send, daemon=True).start()

    def send_lm_studio_prompt(self, model, user_prompt):
        """
        Sends a chat-style request to LM Studio's /v1/chat/completions.
        Includes structured output format and OS-specific system prompts.
        """
        # Define the JSON schema for structured output
        json_schema = {
            "name": "shell_response",
            "strict": "true",
            "schema": {
                "type": "object",
                "properties": {
                    "powershell": {
                        "type": "string",
                        "description": "ONLY the exact PowerShell commands to execute. No comments, no explanations, no backticks. If no command is needed, use empty string."
                    },
                    "zsh": {
                        "type": "string",
                        "description": "ONLY the exact ZSH commands to execute. No comments, no explanations, no backticks. If no command is needed, use empty string."
                    },
                    "instructions": {
                        "type": "string",
                        "description": "All explanations, context, examples, and command descriptions go here. Use Markdown formatting."
                    },
                    "title": {
                        "type": "string",
                        "description": "A short, descriptive title for this chat exchange (max 50 characters)"
                    }
                },
                "required": ["powershell", "zsh", "instructions", "title"]
            }
        }

        # Include conversation history in the messages
        messages = []
        for exchange in self.conversation_history:
            messages.append({"role": "user", "content": exchange["prompt"]})
            if "response" in exchange:
                messages.append({"role": "assistant", "content": json.dumps(exchange["response"])})

        if self.is_windows:
            system_prompt = (
                "You are a highly skilled Windows PowerShell expert specializing in system administration, "
                "automation, and development tasks. Your responses should be tailored for Windows environments "
                "and utilize PowerShell's advanced features effectively.\n\n"
                "For every response, output a JSON object with these keys:\n\n"
                "• \"powershell\": ONLY include the exact PowerShell commands to execute. No comments, no explanations, "
                "no backticks, no markdown formatting. Multiple commands should be separated by semicolons or newlines. "
                "If no command is needed, output an empty string (\"\").\n\n"
                "• \"zsh\": Always output an empty string (\"\") since we're on Windows.\n\n"
                "• \"instructions\": All other information goes here, including:\n"
                "  - Command explanations and descriptions\n"
                "  - Prerequisites or dependencies\n"
                "  - Expected output or behavior\n"
                "  - Error handling and troubleshooting\n"
                "  - Alternative approaches\n"
                "  - Code examples and documentation\n"
                "You may use Markdown formatting in this field only.\n\n"
                "• \"title\": A concise, descriptive title for this chat exchange (max 50 characters).\n\n"
                "Ensure all PowerShell commands follow security best practices and are safe to execute.\n\n"
                "IMPORTANT: Never include command explanations or markdown formatting in the powershell field - "
                "all explanatory text must go in the instructions field."
            )
        else:
            system_prompt = (
                "You are a highly skilled Unix/macOS shell expert specializing in ZSH, system administration, "
                "and development tasks. Your responses should be tailored for Unix/macOS environments "
                "and leverage ZSH's advanced features effectively.\n\n"
                "For every response, output a JSON object with these keys:\n\n"
                "• \"zsh\": ONLY include the exact ZSH commands to execute. No comments, no explanations, "
                "no backticks, no markdown formatting. Multiple commands should be separated by semicolons or newlines. "
                "If no command is needed, output an empty string (\"\").\n\n"
                "• \"powershell\": Always output an empty string (\"\") since we're on Unix/macOS.\n\n"
                "• \"instructions\": All other information goes here, including:\n"
                "  - Command explanations and descriptions\n"
                "  - Prerequisites or dependencies\n"
                "  - Expected output or behavior\n"
                "  - Error handling and troubleshooting\n"
                "  - Alternative approaches\n"
                "  - Code examples and documentation\n"
                "You may use Markdown formatting in this field only.\n\n"
                "• \"title\": A concise, descriptive title for this chat exchange (max 50 characters).\n\n"
                "Ensure all commands follow security best practices and are safe to execute.\n\n"
                "IMPORTANT: Never include command explanations or markdown formatting in the zsh field - "
                "all explanatory text must go in the instructions field."
            )

        # Add system prompt and current user prompt
        messages = [{"role": "system", "content": system_prompt}] + messages
        messages.append({"role": "user", "content": user_prompt})

        # Base payload that works for all models
        payload = {
            "model": model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": json_schema
            },
            "max_tokens": 1000
        }

        url = self.server_url.get().rstrip('/') + "/v1/chat/completions"
        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "choices" not in data or len(data["choices"]) == 0:
                return None
            assistant_message = data["choices"][0]["message"]["content"]
            # Strip markdown code block markers if present
            if assistant_message.startswith("```json"):
                assistant_message = assistant_message.replace("```json", "").rstrip("```").strip()
            try:
                parsed = json.loads(assistant_message)
                # Update chat title if this is the first message
                if not self.conversation_history:
                    self.current_chat_title = parsed.get('title', 'New Chat')
                # Add to conversation history
                self.conversation_history.append({
                    "prompt": user_prompt,
                    "response": parsed
                })
                # Save chat
                self.save_current_chat()
                # Update chat list
                self.update_chat_list()
                return parsed
            except json.JSONDecodeError:
                return { self.shell_key: "", "instructions": assistant_message }
        except Exception as e:
            print("Error sending LM Studio prompt:", e)
            return None

    def send_openai_prompt(self, model, user_prompt, api_key):
        """
        Send a chat-style request to OpenAI's /v1/chat/completions endpoint.
        Uses OpenAI's structured output format for GPT-4 and newer models.
        """
        try:
            # Create OpenAI client
            client = openai.OpenAI(api_key=api_key)
            
            # System prompt based on OS
            if platform.system() == "Windows":
                system_prompt = """You are a Windows PowerShell automation expert. Follow these rules:
1. Provide PowerShell commands that are safe and effective
2. Include detailed explanations of what each command does
3. Format response as a JSON object with these fields:
   - powershell: ONLY the exact PowerShell commands (no backticks/comments)
   - zsh: Empty string for Windows
   - instructions: Markdown-formatted explanations
   - title: Short descriptive title (max 50 chars)
4. Ensure all commands are properly escaped and quoted
5. Use absolute paths when necessary"""
            else:
                system_prompt = """You are a Unix/macOS shell automation expert. Follow these rules:
1. Provide ZSH commands that are safe and effective
2. Include detailed explanations of what each command does
3. Format response as a JSON object with these fields:
   - powershell: Empty string for Unix/macOS
   - zsh: ONLY the exact ZSH commands (no backticks/comments)
   - instructions: Markdown-formatted explanations
   - title: Short descriptive title (max 50 chars)
4. Ensure all commands are properly escaped and quoted
5. Use absolute paths when necessary"""

            # Include conversation history in the messages
            messages = []
            for exchange in self.conversation_history:
                messages.append({"role": "user", "content": exchange["prompt"]})
                if "response" in exchange:
                    messages.append({"role": "assistant", "content": json.dumps(exchange["response"])})

            # Add system prompt and current user prompt
            messages = [{"role": "system", "content": system_prompt}] + messages
            messages.append({"role": "user", "content": user_prompt})

            # Create chat completion
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Extract and validate the response
            response_text = response.choices[0].message.content
            response_data = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["powershell", "zsh", "instructions", "title"]
            for field in required_fields:
                if field not in response_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Update chat title if this is the first message
            if not self.conversation_history:
                self.current_chat_title = response_data.get('title', 'New Chat')
            
            # Add to conversation history
            self.conversation_history.append({
                "prompt": user_prompt,
                "response": response_data
            })
            
            # Save chat
            self.save_current_chat()
            
            # Update chat list
            self.update_chat_list()
            
            return response_data
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse OpenAI response: {e}")
            return {
                "powershell": "",
                "zsh": "",
                "instructions": "Error: Invalid response format from OpenAI",
                "title": "Error Processing Response"
            }
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return {
                "powershell": "",
                "zsh": "",
                "instructions": f"Error: {str(e)}",
                "title": "API Error"
            }

    # ---------------------- Command Execution ----------------------
    def on_run_command(self):
        """
        Runs the command currently in the Recommended Commands box.
        """
        updated_cmd = self.commands_text.get("1.0", tk.END).strip()
        if not updated_cmd:
            self.log_output(f"No {self.shell_label} command to execute.")
            return
        self.current_shell_command = updated_cmd
        self.execute_shell_command(self.current_shell_command)

    def execute_shell_command(self, command):
        """
        Executes the given command in either ZSH (macOS) or PowerShell (Windows),
        capturing and displaying output in real time.
        """
        self.log_output(f"Executing command: {command}")
        
        # Enable kill button
        self.kill_button.config(state=tk.NORMAL)
        self.output_running = True

        def run_command():
            try:
                if self.is_windows:
                    # For Windows, use hidden PowerShell window
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    
                    process = subprocess.Popen(
                        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", command],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                        startupinfo=startupinfo
                    )
                else:
                    # For Unix/Mac, use process group
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        preexec_fn=os.setsid
                    )
                
                self.current_process = process
                
                # Set up a buffer for output
                output_buffer = []
                max_buffer_size = 1000  # Maximum lines to keep in history
                
                while self.output_running:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        # Add to buffer if not too large
                        if len(output_buffer) < max_buffer_size:
                            output_buffer.append(line.rstrip())
                        self.root.after(0, self.log_output, line.rstrip())
                
                # If process is still running when loop exits, terminate it
                if process.poll() is None:
                    self.kill_current_process()
                
                # Save reasonable amount of output to chat history
                self.terminal_output = output_buffer
                
                self.log_output("Command execution completed.")
                
            except Exception as e:
                self.log_output(f"Error executing command: {str(e)}")
            finally:
                self.current_process = None
                self.output_running = False
                self.root.after(0, lambda: self.kill_button.config(state=tk.DISABLED))

        threading.Thread(target=run_command, daemon=True).start()

    def kill_current_process(self):
        """Kill the currently running command process and all its children"""
        if self.current_process:
            try:
                self.output_running = False
                
                if self.is_windows:
                    try:
                        # On Windows, first try to gracefully terminate PowerShell
                        subprocess.run(
                            ["powershell", "-Command", "Get-Process -Id " + str(self.current_process.pid) + " | Stop-Process -Force"],
                            timeout=2
                        )
                    except:
                        # If that fails, use psutil as backup
                        try:
                            parent = psutil.Process(self.current_process.pid)
                            for child in parent.children(recursive=True):
                                try:
                                    child.terminate()
                                except:
                                    child.kill()
                            parent.terminate()
                        except:
                            # Last resort: force kill
                            self.current_process.kill()
                else:
                    # On Unix, kill the process group
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                    
                self.log_output("\nCommand terminated by user.")
                
            except Exception as e:
                self.log_output(f"\nError killing process: {str(e)}")
            finally:
                self.current_process = None
                self.kill_button.config(state=tk.DISABLED)

    # ---------------------- Utility Functions ----------------------
    def log_output(self, message):
        """
        Append a line of text to the Terminal Output box and save to history.
        """
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.terminal_output.append(message)  # Save to history

    def copy_output_to_prompt(self):
        """
        Copies the Terminal Output text into the Prompt box.
        """
        output = self.output_text.get("1.0", tk.END)
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert(tk.END, output)

    def clear_output(self):
        """
        Clears the Terminal Output box and history.
        """
        self.output_text.delete("1.0", tk.END)
        self.terminal_output = []  # Clear history

    def on_commands_text_change(self, event=None):
        """Handle changes to the commands text field"""
        if self.commands_text.edit_modified():  # Check if content changed
            content = self.commands_text.get("1.0", tk.END).strip()
            self.run_command_button.config(state=tk.NORMAL if content else tk.DISABLED)
            self.commands_text.edit_modified(False)  # Reset modified flag

    def start_new_chat(self, force_new=False):
        """Start a new chat session"""
        # Kill any running process before starting new chat
        if self.current_process:
            self.kill_current_process()
        
        # Save current chat if exists and we're not forcing a new one
        if not force_new and hasattr(self, 'current_chat_id') and self.current_chat_id:
            self.save_current_chat()
        
        self.initialize_new_chat()

    def initialize_new_chat(self):
        """Initialize a new chat without updating the chat list"""
        # Clear all input/output fields
        self.prompt_text.delete("1.0", tk.END)
        self.instructions_text.config(state=tk.NORMAL)
        self.instructions_text.delete("1.0", tk.END)
        self.instructions_text.config(state=tk.DISABLED)
        self.commands_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        
        # Reset conversation history and terminal output
        self.current_chat_id = self.generate_chat_id()
        self.conversation_history = []
        self.terminal_output = []
        self.current_chat_title = "New Chat"
        
        # Clear any existing selection
        self.history_list.selection_clear(0, tk.END)
        
        # Save the empty new chat
        self.save_current_chat()
        
        # Update the list but skip the empty check to avoid recursion
        self.update_chat_list(skip_empty_check=True)

    def generate_chat_id(self):
        """Generate a unique chat ID"""
        return f"chat_{int(time.time())}"

    def save_current_chat(self):
        """Save the current chat to a JSON file"""
        if hasattr(self, 'current_chat_id') and (self.conversation_history or self.terminal_output):
            chat_data = {
                'id': self.current_chat_id,
                'title': self.current_chat_title if hasattr(self, 'current_chat_title') else "New Chat",
                'timestamp': time.time(),
                'history': self.conversation_history,
                'terminal_output': self.terminal_output  # Save terminal output
            }
            
            # Create chats directory if it doesn't exist
            os.makedirs(CHAT_DIR, exist_ok=True)
            
            # Save to JSON file
            with open(os.path.join(CHAT_DIR, f"{self.current_chat_id}.json"), 'w') as f:
                json.dump(chat_data, f, indent=2)

    def load_chat(self, chat_id):
        """Load a chat from its JSON file"""
        # Kill any running process before loading new chat
        if self.current_process:
            self.kill_current_process()
            
        try:
            chat_file = os.path.join(CHAT_DIR, f"{chat_id}.json")
            if not os.path.exists(chat_file):
                print(f"Chat file not found: {chat_file}")
                return
            
            with open(chat_file, 'r') as f:
                chat_data = json.load(f)
            
            self.current_chat_id = chat_data['id']
            self.current_chat_title = chat_data.get('title', "Untitled Chat")
            self.conversation_history = chat_data['history']
            self.terminal_output = chat_data.get('terminal_output', [])  # Load terminal output with default empty list
            
            # Replay the conversation in the UI
            self.replay_conversation()
            
        except Exception as e:
            print(f"Error loading chat: {e}")
            logging.error(f"Error loading chat: {e}")

    def replay_conversation(self):
        """Replay the loaded conversation in the UI"""
        try:
            # Clear current content
            self.prompt_text.delete("1.0", tk.END)
            self.instructions_text.config(state=tk.NORMAL)
            self.instructions_text.delete("1.0", tk.END)
            self.commands_text.delete("1.0", tk.END)
            self.output_text.delete("1.0", tk.END)
            
            # Replay terminal output if exists
            if hasattr(self, 'terminal_output'):
                for line in self.terminal_output:
                    self.output_text.insert(tk.END, str(line) + "\n")
            
            # Replay the last exchange if exists
            if self.conversation_history:
                last_exchange = self.conversation_history[-1]
                # Set the prompt
                if 'prompt' in last_exchange:
                    self.prompt_text.insert(tk.END, last_exchange['prompt'])
                
                # Set the response if it exists
                if 'response' in last_exchange:
                    response = last_exchange['response']
                    # Set instructions
                    if 'instructions' in response:
                        self.instructions_text.insert(tk.END, response['instructions'])
                    self.instructions_text.config(state=tk.DISABLED)
                    
                    # Set shell command
                    shell_cmd = response.get('zsh' if not self.is_windows else 'powershell', '')
                    if shell_cmd:
                        self.commands_text.insert(tk.END, shell_cmd)
                        self.current_shell_command = shell_cmd
                        self.run_command_button.config(state=tk.NORMAL)
                    else:
                        self.run_command_button.config(state=tk.DISABLED)
        
        except Exception as e:
            print(f"Error replaying conversation: {e}")
            logging.error(f"Error replaying conversation: {e}")
            # Try to show error to user
            messagebox.showerror("Error", f"Failed to load chat content: {str(e)}")

    def update_chat_list(self, skip_empty_check=False):
        """Update the chat history list"""
        try:
            self.history_list.delete(0, tk.END)
            
            # Get all chat files
            chat_files = glob.glob(os.path.join(CHAT_DIR, "*.json"))
            self.chats = []
            
            for file in chat_files:
                try:
                    with open(file, 'r') as f:
                        chat_data = json.load(f)
                        self.chats.append((chat_data['timestamp'], chat_data['title'], chat_data['id']))
                except Exception as e:
                    logging.error(f"Failed to read chat file {file}: {str(e)}")
                    continue
            
            # Sort by timestamp (newest first)
            self.chats.sort(reverse=True)
            
            # Update listbox
            if self.chats:
                for _, title, _ in self.chats:
                    self.history_list.insert(tk.END, title)
                
                # Select current chat if it exists
                if hasattr(self, 'current_chat_id') and self.current_chat_id:
                    for i, (_, _, chat_id) in enumerate(self.chats):
                        if chat_id == self.current_chat_id:
                            self.history_list.selection_clear(0, tk.END)
                            self.history_list.selection_set(i)
                            self.history_list.see(i)
                            break
            elif not skip_empty_check:
                # No chats exist - start fresh
                self.initialize_new_chat()
            
        except Exception as e:
            logging.error(f"Error updating chat list: {str(e)}")
            messagebox.showerror("Error", f"Failed to update chat list: {str(e)}")

    def on_history_click(self, event):
        """Handle mouse clicks on history list to prevent accidental multi-select"""
        # Get the clicked item index
        clicked_index = self.history_list.nearest(event.y)
        
        # If not holding Ctrl/Command, clear other selections
        if not (event.state & 0x0004):  # Check for Control/Command key
            self.history_list.selection_clear(0, tk.END)
            self.history_list.selection_set(clicked_index)
            
            # Load the clicked chat
            if hasattr(self, 'chats') and clicked_index < len(self.chats):
                _, _, chat_id = self.chats[clicked_index]
                if chat_id != self.current_chat_id:  # Only load if different chat selected
                    self.save_current_chat()  # Save current chat before loading new one
                    self.load_chat(chat_id)
        
        return 'break'  # Prevent default handling

    def on_history_select(self, event):
        """Handle chat history selection"""
        selection = self.history_list.curselection()
        if selection and hasattr(self, 'chats') and self.chats:
            try:
                index = selection[0]
                if index < len(self.chats):
                    _, _, chat_id = self.chats[index]
                    if chat_id != self.current_chat_id:  # Only load if different chat selected
                        self.save_current_chat()  # Save current chat before loading new one
                        self.load_chat(chat_id)
            except Exception as e:
                logging.error(f"Error loading selected chat: {str(e)}")
                messagebox.showerror("Error", f"Failed to load selected chat: {str(e)}")

    def delete_selected_chats(self):
        """Delete the selected chats"""
        selections = self.history_list.curselection()
        if not selections:
            messagebox.showwarning("Warning", "Please select chats to delete")
            return
            
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected chats?"):
            return
            
        try:
            # Get selected chat IDs before deleting
            selected_chat_ids = []
            for index in selections:
                if index < len(self.chats):
                    _, _, chat_id = self.chats[index]
                    selected_chat_ids.append(chat_id)
            
            if not selected_chat_ids:
                return
                
            # Track if we're deleting the current chat
            is_deleting_current = self.current_chat_id in selected_chat_ids
            
            # Delete the files
            for chat_id in selected_chat_ids:
                chat_file = os.path.join(CHAT_DIR, f"{chat_id}.json")
                try:
                    if os.path.exists(chat_file):
                        os.remove(chat_file)
                        logging.info(f"Deleted chat file: {chat_file}")
                except Exception as e:
                    logging.error(f"Failed to delete chat file {chat_file}: {str(e)}")
                    messagebox.showerror("Error", f"Failed to delete chat: {str(e)}")
            
            # Update the list before potentially starting a new chat
            remaining_files = glob.glob(os.path.join(CHAT_DIR, "*.json"))
            
            if not remaining_files or is_deleting_current:
                # No chats left or current chat was deleted - start fresh
                self.initialize_new_chat()
            else:
                # Load the newest remaining chat
                self.update_chat_list(skip_empty_check=True)
                if self.chats:
                    _, _, newest_chat_id = self.chats[0]
                    self.load_chat(newest_chat_id)
            
        except Exception as e:
            logging.error(f"Error in delete_selected_chats: {str(e)}")
            messagebox.showerror("Error", f"Failed to delete chats: {str(e)}")
            
    def clear_all_chats(self):
        """Clear all chat history"""
        if not messagebox.askyesno("Confirm Clear", "Are you sure you want to delete all chats? This cannot be undone."):
            return
            
        try:
            # Delete all chat files
            deleted_files = False
            for file in glob.glob(os.path.join(CHAT_DIR, "*.json")):
                try:
                    os.remove(file)
                    deleted_files = True
                    logging.info(f"Deleted chat file: {file}")
                except Exception as e:
                    logging.error(f"Failed to delete file {file}: {str(e)}")
            
            # Always start fresh after clearing all chats
            self.initialize_new_chat()
            
        except Exception as e:
            logging.error(f"Error in clear_all_chats: {str(e)}")
            messagebox.showerror("Error", f"Failed to clear chats: {str(e)}")


if __name__ == "__main__":
    try:
        setup_logging(LOG_DIR)
        logging.info("Initializing main window")
        
        root = tk.Tk()
        app = LMStudioApp(root)
        logging.info("Starting mainloop")
        root.mainloop()
    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        logging.error(traceback.format_exc())
        
        # Try to show error in a message box
        try:
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            messagebox.showerror("Error", f"Failed to start AIPrompt: {str(e)}\n\nCheck Application Support/AIPrompt/Logs/aiprompt.log for details.")
        except:
            print(f"Failed to show error dialog: {e}")
        raise