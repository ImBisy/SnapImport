import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import subprocess
import sys
import os

class SnapImportGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SnapImport GUI")
        self.root.geometry("600x400")

        # Output text area
        self.output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=15)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Button frame
        button_frame = tk.Frame(root)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        # Buttons
        tk.Button(button_frame, text="Setup", command=self.run_setup).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Import", command=self.run_import).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Dry Run", command=self.run_dry_run).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Rename Folder", command=self.run_rename).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Detect SD", command=self.run_detect_sd).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear Output", command=self.clear_output).pack(side=tk.LEFT, padx=5)

    def run_command(self, cmd):
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), '..')
            result = subprocess.run(["python3"] + cmd, capture_output=True, text=True, cwd=os.path.dirname(__file__), env=env)
            output = result.stdout + result.stderr
            self.output_text.insert(tk.END, f"$ python3 {' '.join(cmd)}\n{output}\n")
            self.output_text.see(tk.END)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def run_setup(self):
        self.run_command([sys.executable, "-m", "snapimport"])

    def run_import(self):
        self.run_command([sys.executable, "-m", "snapimport", "import"])

    def run_dry_run(self):
        self.run_command([sys.executable, "-m", "snapimport", "import", "--dry-run"])

    def run_rename(self):
        folder = filedialog.askdirectory(title="Select Folder to Rename")
        if folder:
            self.run_command([sys.executable, "-m", "snapimport", "rename", folder])

    def run_detect_sd(self):
        self.run_command([sys.executable, "-m", "snapimport", "detect-sd"])

    def clear_output(self):
        self.output_text.delete(1.0, tk.END)

def start_gui():
    root = tk.Tk()
    gui = SnapImportGUI(root)
    root.mainloop()

if __name__ == "__main__":
    start_gui()
