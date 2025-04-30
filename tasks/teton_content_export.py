import os
import subprocess
import shutil
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from ui.dialogs import ProgressDialog, ConfirmationDialog


class TetonContentExportTask:
    def __init__(self, root, on_export_complete=None, on_folder_cleared=None):
        self.root = root
        self.on_export_complete = on_export_complete
        self.on_folder_cleared = on_folder_cleared
        self.export_folder = None
        self.export_files = [
            "checksums.md5",
            "eep_anatomyimages.zip",
            "eep_cdr.zip",
            "eep_cochrane.zip",
            "eep_dermimages.zip",
            "eep_hp_diag.zip",
            "eep_metadata.xls"
        ]

        # Database file path
        self.db_file = os.path.abspath(os.path.join("Teton Export History", "teton_exports.db"))

        # Initialize database
        self.init_export_db()

    def init_export_db(self):
        """Initialize SQLite database for export tracking if it doesn't exist"""
        history_folder = "Teton Export History"

        # Create directory if it doesn't exist
        if not os.path.exists(history_folder):
            try:
                os.makedirs(history_folder)
                print(f"Created directory: {history_folder}")
            except Exception as e:
                print(f"Error creating directory {history_folder}: {str(e)}")
                messagebox.showwarning("Directory Warning",
                                       f"Could not create {history_folder} directory. History will not be saved.")
                return

        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                export_timestamp TEXT NOT NULL,
                export_folder TEXT NOT NULL
            )
            ''')

            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_export_timestamp 
            ON exports(export_timestamp)
            ''')

            conn.commit()
            conn.close()
            print(f"Successfully initialized database: {self.db_file}")

        except Exception as e:
            print(f"Error initializing export database: {str(e)}")
            messagebox.showwarning("Database Warning",
                                   "Could not initialize export tracking database. History will not be saved.")

    def log_export_to_db(self, export_folder):
        """Log export metadata to SQLite database"""
        conn = None
        try:
            # Format timestamp in Excel-friendly format (YYYY-MM-DD HH:MM:SS)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            folder_name = os.path.basename(export_folder)

            conn = sqlite3.connect(self.db_file, timeout=30)
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO exports (
                export_timestamp, 
                export_folder
            ) VALUES (?, ?)
            ''', (
                timestamp,
                folder_name
            ))

            conn.commit()
            export_id = cursor.lastrowid
            print(f"Successfully logged export to database with ID: {export_id}")
            return export_id

        except Exception as e:
            print(f"Error logging export to database: {str(e)}")
            messagebox.showerror("Database Error", f"Failed to log export to database: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()

    def start_teton_export(self):
        """Start the Teton content export process with confirmation"""
        confirm = ConfirmationDialog(
            self.root,
            title="Confirm Teton Export",
            message="Do you want to do Teton content export?\n\nNote: Teton content export should normally be done after all content (Topics, Cochrane, Calculators) is uploaded and verified.",
            yes_button_text="Start Export",
            no_button_text="Cancel",
            show_icon=False  # No question mark icon
        )

        if confirm.result:
            self.run_teton_export()

    def run_teton_export(self):
        """Run the Teton content export process"""
        progress = ProgressDialog(self.root, title="Teton Content Export")

        try:
            # Step 1: Run the export batch file
            progress.set_status("Starting Teton content export...")
            batch_file = "/opt/software/eeplus/bin/eeplus-filters-R01B085/compileEEPContentsForThirdPartyExport.bat"

            if not os.path.exists(batch_file):
                raise FileNotFoundError(f"Batch file not found at {batch_file}")

            # Run the batch file
            process = subprocess.Popen(
                batch_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )

            # Monitor progress (simplified for this example)
            while process.poll() is None:
                self.root.update()

            # Check for errors
            if process.returncode != 0:
                stderr = process.stderr.read().decode('utf-8', errors='replace')
                raise Exception(f"Export failed with error:\n{stderr}")

            # Step 2: Verify the exported files
            progress.set_status("Verifying exported files...")
            export_dir = "/opt/software/eeplus/input/eeplus/ThirdPartyExport/"

            missing_files = []
            for file in self.export_files:
                if not os.path.exists(os.path.join(export_dir, file)):
                    missing_files.append(file)

            if missing_files:
                raise Exception(f"Missing exported files: {', '.join(missing_files)}")

            # Step 3: Copy files to a dated folder
            progress.set_status("Copying exported files...")
            current_date = datetime.now().strftime("%Y-%m-%d")
            self.export_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), current_date)

            # Create the folder if it doesn't exist
            os.makedirs(self.export_folder, exist_ok=True)

            # Copy each file
            for file in self.export_files:
                src = os.path.join(export_dir, file)
                dst = os.path.join(self.export_folder, file)
                shutil.copy2(src, dst)

            # Log the export to database
            self.log_export_to_db(self.export_folder)

            # Complete
            progress.set_status("Teton content export completed successfully!")
            self.root.after(1000, progress.destroy)

            if self.on_export_complete:
                self.on_export_complete()

            messagebox.showinfo(
                "Export Complete",
                "Teton content export completed successfully!\n\n"
                f"Files copied to: {self.export_folder}"
            )

        except Exception as e:
            progress.destroy()
            messagebox.showerror(
                "Export Failed",
                f"Teton content export failed:\n{str(e)}"
            )

    def get_export_history(self):
        """Get the export history data from database"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

            # Ensure the database file exists
            if not os.path.exists(self.db_file):
                print(f"Database file does not exist: {self.db_file}")
                return []

            # Connect with timeout to avoid locking issues
            conn = sqlite3.connect(self.db_file, timeout=30)
            cursor = conn.cursor()

            cursor.execute('''
            SELECT id, export_timestamp, export_folder
            FROM exports
            ORDER BY export_timestamp DESC
            ''')

            history = cursor.fetchall()
            print(f"Retrieved {len(history)} export history records")
            conn.close()
            return history
        except Exception as e:
            print(f"Error fetching export history: {str(e)}")
            return []

    def open_exported_folder(self):
        """Open the exported files folder in File Explorer"""
        if self.export_folder and os.path.exists(self.export_folder):
            try:
                os.startfile(self.export_folder)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open folder: {str(e)}")
        else:
            messagebox.showwarning(
                "Folder Not Found",
                "No exported files folder exists or it has been deleted."
            )

    def clear_exported_folder(self):
        """Clear the exported files folder"""
        if not self.export_folder or not os.path.exists(self.export_folder):
            messagebox.showwarning(
                "Folder Not Found",
                "No exported files folder exists or it has been deleted."
            )
            return

        confirm = ConfirmationDialog(
            self.root,
            title="Confirm Deletion",
            message=f"Are you sure you want to delete all files in:\n{self.export_folder}?",
            yes_button_text="Delete",
            no_button_text="Cancel",
            show_icon=True  # Keep question mark icon for deletion confirmation
        )

        if confirm.result:
            try:
                shutil.rmtree(self.export_folder)
                self.export_folder = None

                if self.on_folder_cleared:
                    self.on_folder_cleared()

                messagebox.showinfo(
                    "Success",
                    "Exported files folder has been deleted."
                )
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Failed to delete folder: {str(e)}"
                )