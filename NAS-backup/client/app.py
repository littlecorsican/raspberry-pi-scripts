import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import threading
from datetime import datetime
from typing import List, Dict, Optional

class FileBackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Backup App")
        self.root.geometry("800x550")  # Increased width for better display
        
        # Load environment variables
        load_dotenv()
        self.backup_url = os.getenv('BACKUP_URL')
        
        if not self.backup_url:
            messagebox.showwarning("Warning", "BACKUP_URL not found in .env file")
        
        # File to persist list items
        self.data_file = Path("file_list.json")
        
        # Store file data: list of dicts with 'path' and 'last_backup'
        self.file_data: List[Dict] = []
        
        # Create GUI elements
        self.create_widgets()
        
        # Load saved file paths
        self.load_file_paths()
    
    def create_widgets(self):
        # Create frames
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Treeview for displaying files with backup times
        self.create_file_list_treeview(main_frame)
        
        # Frame for buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Add File button
        self.add_button = tk.Button(
            button_frame,
            text="Add File",
            command=self.add_file,
            width=15,
            bg="#4CAF50",
            fg="white"
        )
        self.add_button.pack(side=tk.LEFT, padx=5)
        
        # Remove Selected button
        self.remove_button = tk.Button(
            button_frame,
            text="Remove Selected",
            command=self.remove_selected,
            width=15,
            bg="#f44336",
            fg="white"
        )
        self.remove_button.pack(side=tk.LEFT, padx=5)
        
        # Backup button
        self.backup_button = tk.Button(
            button_frame,
            text="Backup Files",
            command=self.start_backup,
            width=15,
            bg="#2196F3",
            fg="white"
        )
        self.backup_button.pack(side=tk.LEFT, padx=5)
        
        # Clear All button
        self.clear_button = tk.Button(
            button_frame,
            text="Clear All",
            command=self.clear_all,
            width=15,
            bg="#FF9800",
            fg="white"
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(
            self.root,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg="#f0f0f0"
        )
        self.status_label.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Progress bar
        self.progress = tk.DoubleVar()
        self.progress_bar = tk.Scale(
            self.root,
            from_=0, to=100,
            orient=tk.HORIZONTAL,
            length=760,
            variable=self.progress,
            state='disabled',
            showvalue=False
        )
        self.progress_bar.pack(pady=(0, 10), padx=20)
    
    def create_file_list_treeview(self, parent):
        """Create Treeview widget to display files with backup times"""
        # Create frame for treeview and scrollbars
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create Treeview
        self.tree = tk.ttk.Treeview(
            tree_frame,
            columns=('file', 'last_backup', 'status'),
            show='headings',
            height=15
        )
        
        # Define columns
        self.tree.heading('file', text='File')
        self.tree.heading('last_backup', text='Last Backup')
        self.tree.heading('status', text='Status')
        
        # Configure column widths
        self.tree.column('file', width=300)
        self.tree.column('last_backup', width=150)
        self.tree.column('status', width=100)
        
        # Add scrollbars
        v_scrollbar = tk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
    
    def format_backup_time(self, backup_time: Optional[str]) -> str:
        """Format backup time for display"""
        if not backup_time:
            return "Never"
        
        try:
            dt = datetime.fromisoformat(backup_time)
            
            # If backup was today, show time only
            # Otherwise show date
            if dt.date() == datetime.now().date():
                return dt.strftime("Today %H:%M")
            elif dt.date() == datetime.now().date().replace(day=datetime.now().day - 1):
                return dt.strftime("Yesterday %H:%M")
            else:
                return dt.strftime("%Y-%m-%d")
        except:
            return "Invalid date"
    
    def update_treeview(self):
        """Update the treeview with current file data"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add file data to treeview
        for file_info in self.file_data:
            file_path = file_info['path']
            last_backup = self.format_backup_time(file_info.get('last_backup'))
            
            # Check if file exists
            if os.path.exists(file_path):
                status = "✓" if file_info.get('last_backup') else "Ready"
                tags = ('exists',)
            else:
                status = "Missing"
                tags = ('missing',)
            
            # Add to treeview
            self.tree.insert(
                '', 
                'end',
                values=(os.path.basename(file_path), last_backup, status),
                tags=tags
            )
        
        # Configure tag colors
        self.tree.tag_configure('exists', foreground='black')
        self.tree.tag_configure('missing', foreground='red')
    
    def add_file(self):
        """Open file dialog and add selected file to list"""
        file_path = filedialog.askopenfilename(
            title="Select a file",
            filetypes=[("All files", "*.*")]
        )
        
        if file_path:
            # Check if file already exists in list
            for file_info in self.file_data:
                if file_info['path'] == file_path:
                    messagebox.showinfo("Info", "File already in list")
                    return
            
            # Add new file with no backup history
            self.file_data.append({
                'path': file_path,
                'last_backup': None,
                'added_date': datetime.now().isoformat()
            })
            
            self.save_file_paths()
            self.update_treeview()
            self.update_status(f"Added: {os.path.basename(file_path)}")
    
    def remove_selected(self):
        """Remove selected item from list"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "No item selected")
            return
        
        # Get selected index
        selected_index = self.tree.index(selection[0])
        
        # Remove from file_data
        if 0 <= selected_index < len(self.file_data):
            removed_file = self.file_data[selected_index]['path']
            self.file_data.pop(selected_index)
            
            self.save_file_paths()
            self.update_treeview()
            self.update_status(f"Removed: {os.path.basename(removed_file)}")
    
    def clear_all(self):
        """Clear all items from list"""
        if not self.file_data:
            return
        
        if messagebox.askyesno("Confirm", "Clear all files from list?"):
            self.file_data.clear()
            self.save_file_paths()
            self.update_treeview()
            self.update_status("Cleared all files")
    
    def on_tree_select(self, event):
        """Handle treeview selection"""
        # You can add custom selection handling here if needed
        pass
    
    def load_file_paths(self):
        """Load saved file paths from JSON file"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    
                    # Handle both old format (list of strings) and new format (list of dicts)
                    if isinstance(data, list):
                        if data and isinstance(data[0], dict):
                            # New format with backup times
                            self.file_data = data
                        else:
                            # Old format - convert to new format
                            self.file_data = [
                                {
                                    'path': path,
                                    'last_backup': None,
                                    'added_date': datetime.now().isoformat()
                                }
                                for path in data
                            ]
                    
                    self.update_treeview()
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load saved files: {e}")
    
    def save_file_paths(self):
        """Save current file data to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.file_data, f, indent=2, default=str)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save files: {e}")
    
    def update_file_backup_time(self, file_path: str):
        """Update backup time for a specific file"""
        for file_info in self.file_data:
            if file_info['path'] == file_path:
                file_info['last_backup'] = datetime.now().isoformat()
                break
        self.save_file_paths()
        self.update_treeview()
    
    def start_backup(self):
        """Start the backup process in a separate thread"""
        if not self.backup_url:
            messagebox.showerror("Error", "Backup URL not configured. Check your .env file")
            return
        
        if not self.file_data:
            messagebox.showwarning("Warning", "No files to backup")
            return
        
        # Get list of files to backup (only those that exist)
        files_to_backup = [f for f in self.file_data if os.path.exists(f['path'])]
        
        if not files_to_backup:
            messagebox.showwarning("Warning", "No existing files to backup")
            return
        
        # Disable buttons during backup
        self.set_buttons_state(tk.DISABLED)
        self.progress_bar.config(state='normal')
        self.progress.set(0)
        self.update_status("Starting backup...")
        
        # Start backup in separate thread
        thread = threading.Thread(
            target=self.perform_backup, 
            args=(files_to_backup,)
        )
        thread.daemon = True
        thread.start()
    
    def perform_backup(self, files_to_backup: List[Dict]):
        """Perform the backup by sending POST requests"""
        total_files = len(files_to_backup)
        successful = 0
        failed = []
        
        for index, file_info in enumerate(files_to_backup):
            file_path = file_info['path']
            file_name = os.path.basename(file_path)
            
            try:
                # Update progress
                progress_value = (index / total_files) * 100
                self.root.after(0, lambda v=progress_value: self.progress.set(v))
                self.root.after(0, self.update_status, f"Backing up: {file_name}")
                
                # Prepare the file for upload
                with open(file_path, 'rb') as f:
                    files_data = {'file': (file_name, f)}
                    
                    # Send POST request
                    response = requests.post(
                        self.backup_url,
                        files=files_data,
                        timeout=30  # 30 second timeout
                    )
                    
                    if response.status_code == 200:
                        successful += 1
                        # Update backup time for this file
                        self.root.after(0, self.update_file_backup_time, file_path)
                        self.root.after(0, self.update_status, f"Success: {file_name}")
                    else:
                        failed.append(f"{file_name} (Server error: {response.status_code})")
                        self.root.after(0, self.update_status, f"Failed: {file_name}")
                        
            except requests.exceptions.RequestException as e:
                failed.append(f"{file_name} (Network error: {str(e)})")
            except Exception as e:
                failed.append(f"{file_name} (Error: {str(e)})")
        
        # Update final progress
        self.root.after(0, lambda: self.progress.set(100))
        
        # Show summary
        self.root.after(0, self.show_backup_summary, successful, total_files, failed)
        
        # Re-enable buttons
        self.root.after(0, lambda: self.set_buttons_state(tk.NORMAL))
        self.root.after(0, lambda: self.progress_bar.config(state='disabled'))
    
    def show_backup_summary(self, successful: int, total: int, failed: List[str]):
        """Show backup completion summary"""
        summary = f"Backup complete: {successful}/{total} files uploaded"
        if failed:
            summary += f"\n\nFailed files:\n" + "\n".join(failed)
            messagebox.showinfo("Backup Summary", summary)
        else:
            self.update_status(summary)
            messagebox.showinfo("Backup Complete", summary)
    
    def update_status(self, message: str):
        """Update the status label"""
        self.status_label.config(text=message)
    
    def set_buttons_state(self, state: str):
        """Enable or disable all buttons"""
        buttons = [self.add_button, self.remove_button, 
                  self.backup_button, self.clear_button]
        for button in buttons:
            button.config(state=state)
    
    def on_closing(self):
        """Handle application closing"""
        self.save_file_paths()
        self.root.destroy()

def main():
    root = tk.Tk()
    
    # Import ttk after creating root window
    global ttk
    import tkinter.ttk as ttk
    
    app = FileBackupApp(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()