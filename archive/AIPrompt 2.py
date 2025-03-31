import platform
import requests
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import json

class LMStudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI GUI Client")

        # Detect if we're on Windows or not
        self.is_windows = platform.system().lower().startswith('win')
        if self.is_windows:
            self.shell_label = "PowerShell"
            self.shell_key = "powershell"
        else:
            self.shell_label = "ZSH"
            self.shell_key = "zsh"

        # Default LM Studio info
        self.lmstudio_url_default = "http://192.168.1.51:1234"
        # We'll store the current server URL or API key in StringVars
        self.server_url = tk.StringVar(value=self.lmstudio_url_default)
        self.openai_api_key = tk.StringVar(value="")

        # Track which provider is selected
        self.ai_provider = tk.StringVar(value="LM Studio")
        # Holds the currently selected model
        self.selected_model = tk.StringVar(value="")

        # Model list for either LM Studio or OpenAI
        self.models_list = []

        # We'll store the current recommended command for the “Run Command” button
        self.current_shell_command = ""

        # Create the UI
        self.create_widgets()

        # By default, use LM Studio as our client
        self.refresh_models()

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
        # --- Top Frame: Provider Selection ---
        provider_frame = tk.Frame(self.root)
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

        # --- Config Frame: LM Studio URL or OpenAI API Key ---
        config_frame = tk.Frame(self.root)
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

        tk.Button(config_frame, text="Refresh Models", command=self.refresh_models).pack(side=tk.LEFT, padx=5)

        # --- Model Selection Frame ---
        model_frame = tk.Frame(self.root)
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
        self.main_paned = tk.PanedWindow(self.root, orient=tk.VERTICAL)
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
        # (Editable: do not disable editing)

        # 4) Terminal Output Frame
        output_frame = tk.Frame(self.main_paned)
        self.main_paned.add(output_frame, minsize=100)
        self.output_label = tk.Label(output_frame, text=f"{self.shell_label} Output:")
        self.output_label.pack(anchor="w")
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap="word", height=8)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # --- Bottom Button Row ---
        button_frame = tk.Frame(self.root)
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
        For models with "o1" or "o3" in their name (case-insensitive), use the alternate payload format:
          - Use role "assistant" for the first message with content as a list containing a text dict.
          - Use "max_completion_tokens": 1000.
        Otherwise, use the default format with "system" and "max_tokens": 1000.
        """
        if self.is_windows:
            system_prompt = (
                "You are a highly skilled coding, debugging, and troubleshooting assistant "
                "specialized in Windows development using the PowerShell terminal. For every response, "
                "output a JSON object with exactly two keys:\n\n"
                "• \"powershell\": Include any terminal command(s) to run in Windows PowerShell. "
                "If no command is needed, output an empty string (\"\").\n\n"
                "• \"instructions\": Include all additional context, explanation, debugging steps, and code examples. "
                "You may use Markdown formatting.\n\n"
                "Do not include any extra text outside this JSON structure."
            )
        else:
            system_prompt = (
                "You are a highly skilled coding, debugging, and troubleshooting assistant "
                "specialized in macOS development using the ZSH terminal. For every response, "
                "output a JSON object with exactly two keys:\n\n"
                "• \"zsh\": Include any terminal command(s) to run in a macOS ZSH terminal. "
                "If no command is needed, output an empty string (\"\").\n\n"
                "• \"instructions\": Include all additional context, explanation, debugging steps, and code examples. "
                "You may use Markdown formatting.\n\n"
                "Do not include any extra text outside this JSON structure."
            )

        # Check if the model name contains "o1" or "o3"
        if "o1" in model.lower() or "o3" in model.lower():
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": system_prompt}
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt}
                        ]
                    }
                ],
                "max_completion_tokens": 1000
            }
        else:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
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
                return parsed
            except json.JSONDecodeError:
                return { self.shell_key: "", "instructions": assistant_message }
        except Exception as e:
            print("Error sending LM Studio prompt:", e)
            return None

    def send_openai_prompt(self, model, user_prompt, api_key):
        """
        Sends a chat-style request to OpenAI's /v1/chat/completions.
        For models with "o1" or "o3" in their name (case-insensitive), use the alternate payload format.
        Otherwise, use the default payload format.
        """
        if self.is_windows:
            system_prompt = (
                "You are a highly skilled coding, debugging, and troubleshooting assistant "
                "specialized in Windows development using the PowerShell terminal. For every response, "
                "output a JSON object with exactly two keys:\n\n"
                "• \"powershell\": Include any terminal command(s) to run in Windows PowerShell. "
                "If no command is needed, output an empty string (\"\").\n\n"
                "• \"instructions\": Include all additional context, explanation, debugging steps, and code examples. "
                "You may use Markdown formatting.\n\n"
                "Do not include any extra text outside this JSON structure."
            )
        else:
            system_prompt = (
                "You are a highly skilled coding, debugging, and troubleshooting assistant "
                "specialized in macOS development using the ZSH terminal. For every response, "
                "output a JSON object with exactly two keys:\n\n"
                "• \"zsh\": Include any terminal command(s) to run in a macOS ZSH terminal. "
                "If no command is needed, output an empty string (\"\").\n\n"
                "• \"instructions\": Include all additional context, explanation, debugging steps, and code examples. "
                "You may use Markdown formatting.\n\n"
                "Do not include any extra text outside this JSON structure."
            )

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        # Check if the model name contains "o1" or "o3"
        if "o1" in model.lower() or "o3" in model.lower():
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": system_prompt}
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt}
                        ]
                    }
                ],
                "max_completion_tokens": 1000
            }
        else:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 1000
            }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "choices" not in data or len(data["choices"]) == 0:
                return None
            assistant_message = data["choices"][0]["message"]["content"]
            # Strip markdown markers if present
            if assistant_message.startswith("```json"):
                assistant_message = assistant_message.replace("```json", "").rstrip("```").strip()
            try:
                parsed = json.loads(assistant_message)
                return parsed
            except json.JSONDecodeError:
                return { self.shell_key: "", "instructions": assistant_message }
        except Exception as e:
            print("Error sending OpenAI prompt:", e)
            return None

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

        def run_command():
            try:
                if self.is_windows:
                    process = subprocess.Popen(
                        ["powershell", "-Command", command],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                else:
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        self.root.after(0, self.log_output, line.rstrip())
                process.wait()
                self.log_output("Command execution completed.")
            except Exception as e:
                self.log_output(f"Error executing command: {str(e)}")

        threading.Thread(target=run_command, daemon=True).start()

    # ---------------------- Utility Functions ----------------------
    def log_output(self, message):
        """
        Append a line of text to the Terminal Output box.
        """
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)

    def copy_output_to_prompt(self):
        """
        Copies the Terminal Output text into the Prompt box.
        """
        output = self.output_text.get("1.0", tk.END)
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert(tk.END, output)

    def clear_output(self):
        """
        Clears the Terminal Output box.
        """
        self.output_text.delete("1.0", tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = LMStudioApp(root)
    root.mainloop()