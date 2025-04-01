import tkinter as tk
import os

root = tk.Tk()
root.title("AIPrompt")
root.geometry("400x300")

tk.Label(root, text="If you see this, GUI works!").pack(expand=True)

# Add a button to show you're alive
tk.Button(root, text="Close", command=root.destroy).pack()

root.mainloop()