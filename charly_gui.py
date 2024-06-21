import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from ttkthemes import ThemedTk
import subprocess
import os
import threading
from charly import main

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Video and Audio Synchronization")
        self.root.geometry("630x400")

        # Styling and Layout Adjustments
        self.style = ttk.Style()
        self.style.configure('TLabel', font=('Helvetica', 11))
        self.style.configure('TEntry', padding=5)
        self.style.configure('TButton', font=('Helvetica', 11), padding=5)
        self.style.configure('TRadiobutton', font=('Helvetica', 11))

        self.create_widgets()
        
    def create_widgets(self):
        self.main_file_label = ttk.Label(self.root, text="Main File")
        self.main_file_label.grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.main_file_entry = ttk.Entry(self.root, width=50)
        self.main_file_entry.grid(row=0, column=1, padx=10, pady=5)
        self.main_file_button = ttk.Button(self.root, text="Browse", command=self.browse_main_file)
        self.main_file_button.grid(row=0, column=2, padx=10, pady=5)

        self.audio_file_label = ttk.Label(self.root, text="Audio File")
        self.audio_file_label.grid(row=1, column=0, padx=10, pady=5, sticky='w')
        self.audio_file_entry = ttk.Entry(self.root, width=50)
        self.audio_file_entry.grid(row=1, column=1, padx=10, pady=5)
        self.audio_file_button = ttk.Button(self.root, text="Browse", command=self.browse_audio_file)
        self.audio_file_button.grid(row=1, column=2, padx=10, pady=5)

        self.output_file_label = ttk.Label(self.root, text="Output File (Optional)")
        self.output_file_label.grid(row=2, column=0, padx=10, pady=5, sticky='w')
        self.output_file_entry = ttk.Entry(self.root, width=50)
        self.output_file_entry.grid(row=2, column=1, padx=10, pady=5)
        self.output_file_button = ttk.Button(self.root, text="Save As", command=self.browse_output_file)
        self.output_file_button.grid(row=2, column=2, padx=10, pady=5)

        self.audio_delay_label = ttk.Label(self.root, text="Audio Delay")
        self.audio_delay_label.grid(row=3, column=0, padx=10, pady=5, sticky='w')
        self.audio_delay_var = tk.StringVar(value="delay")
        self.audio_delay_delay = ttk.Radiobutton(self.root, text="Delay", variable=self.audio_delay_var, value="delay")
        self.audio_delay_delay.grid(row=3, column=1, padx=10, pady=5, sticky='w')
        self.audio_delay_advance = ttk.Radiobutton(self.root, text="Advance", variable=self.audio_delay_var, value="advance")
        self.audio_delay_advance.grid(row=3, column=2, padx=10, pady=5, sticky='w')

        self.seconds_label = ttk.Label(self.root, text="Seconds (Optional)")
        self.seconds_label.grid(row=4, column=0, padx=10, pady=5, sticky='w')
        self.seconds_entry = ttk.Entry(self.root, width=20)
        self.seconds_entry.grid(row=4, column=1, padx=10, pady=5)

        self.use_auto_sync_var = tk.BooleanVar()
        self.use_auto_sync_check = ttk.Checkbutton(self.root, text="Use Auto Sync", variable=self.use_auto_sync_var, command=self.toggle_auto_sync)
        self.use_auto_sync_check.grid(row=5, column=1, padx=10, pady=5, sticky='w')

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="indeterminate")
        self.sync_button = ttk.Button(self.root, text="Synchronize", command=self.synchronize)
        self.sync_button.grid(row=7, column=0, columnspan=3, padx=10, pady=10, ipadx=10)

    def browse_main_file(self):
        self.main_file = filedialog.askopenfilename()
        self.main_file_entry.delete(0, tk.END)
        self.main_file_entry.insert(0, self.main_file)

    def browse_audio_file(self):
        self.audio_file = filedialog.askopenfilename()
        self.audio_file_entry.delete(0, tk.END)
        self.audio_file_entry.insert(0, self.audio_file)

    def browse_output_file(self):
        self.output_file = filedialog.asksaveasfilename(defaultextension=".mkv")
        self.output_file_entry.delete(0, tk.END)
        self.output_file_entry.insert(0, self.output_file)

    def toggle_auto_sync(self):
        if self.use_auto_sync_var.get():
            self.audio_delay_delay.config(state=tk.DISABLED)
            self.audio_delay_advance.config(state=tk.DISABLED)
            self.seconds_entry.config(state=tk.DISABLED)
        else:
            self.audio_delay_delay.config(state=tk.NORMAL)
            self.audio_delay_advance.config(state=tk.NORMAL)
            self.seconds_entry.config(state=tk.NORMAL)

    def synchronize(self):
        main_file = self.main_file_entry.get()
        audio_file = self.audio_file_entry.get()
        output_file = self.output_file_entry.get()
        audio_delay = self.audio_delay_var.get()
        use_auto_sync = self.use_auto_sync_var.get()
        
        try:
            seconds = float(self.seconds_entry.get()) if self.seconds_entry.get() else None
        except ValueError:
            messagebox.showerror("Error", "Seconds must be a number")
            return

        if not main_file or not audio_file:
            messagebox.showerror("Error", "Main File and Audio File are required")
            return

        # Autogenerate output file name if not provided
        if not output_file:
            base, ext = os.path.splitext(main_file)
            output_file = f"{base}_edited{ext}"

        self.progress.grid(row=6, column=0, columnspan=3, padx=10, pady=10)
        self.progress.start()

        # Run the synchronization in a separate thread
        thread = threading.Thread(target=self.run_sync, args=(main_file, audio_file, output_file, audio_delay, seconds, use_auto_sync))
        thread.start()

    def run_sync(self, main_file, audio_file, output_file, audio_delay, seconds, use_auto_sync):
        try:
            main(main_file, audio_file, audio_delay, output_file, seconds, use_auto_sync)
            self.root.after(100, self.on_sync_complete, output_file)
        except Exception as e:
            self.root.after(100, self.on_sync_error, str(e))

    def on_sync_complete(self, output_file):
        self.progress.stop()
        self.progress.grid_forget()
        messagebox.showinfo("Success", f"Synchronization completed! Output file saved as {output_file}")
        if messagebox.askyesno("Open Explorer", "Do you want to open the file location?"):
            self.open_file_location(output_file)

    def on_sync_error(self, error_message):
        self.progress.stop()
        self.progress.grid_forget()
        messagebox.showerror("Error", error_message)

    def open_file_location(self, path):
        if os.path.isfile(path):
            subprocess.run(['explorer', '/select,', os.path.normpath(path)])

if __name__ == "__main__":
    root = ThemedTk(theme="radiance")  # Choose a more colorful, material-inspired theme
    app = App(root)
    root.mainloop()
