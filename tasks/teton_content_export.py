import os
import subprocess
import shutil
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import threading
from ui.dialogs import ProgressDialog, ConfirmationDialog


class TetonContentExportTask:
    def __init__(self, root, on_export_complete=None, on_folder_cleared=None):
        self.root = root
        self.on_export_complete = on_export_complete
        self.on_folder_cleared = on_folder_cleared
        self.export_folder = None
        self.current_export_id = None
        self.export_process = None
        self.export_files = [
            "checksums.md5",
            "eep_anatomyimages.zip",
            "eep_cdr.zip",
            "eep_cochrane.zip",
            "eep_dermimages.zip",
            "eep_eetopics.zip",
            "eep_hp_diag.zip",
            "eep_metadata.xls.zip"
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
                export_timestamp TEXT,
                export_folder TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
            ''')

            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_export_timestamp 
            ON exports(export_timestamp)
            ''')

            # Check if status column exists, if not add it (for existing databases)
            cursor.execute('''
            PRAGMA table_info(exports)
            ''')
            columns = [column[1] for column in cursor.fetchall()]
            if 'status' not in columns:
                cursor.execute('''
                ALTER TABLE exports
                ADD COLUMN status TEXT DEFAULT 'completed'
                ''')
                # Assume all existing records were completed successfully
                cursor.execute('''
                UPDATE exports
                SET status = 'completed'
                WHERE status IS NULL
                ''')

            conn.commit()
            conn.close()
            print(f"Successfully initialized database: {self.db_file}")

        except Exception as e:
            print(f"Error initializing export database: {str(e)}")
            messagebox.showwarning("Database Warning",
                                   "Could not initialize export tracking database. History will not be saved.")

    def log_export_start(self, export_folder):
        """Log the start of an export with pending status"""
        conn = None
        try:
            folder_name = os.path.basename(export_folder)

            conn = sqlite3.connect(self.db_file, timeout=30)
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO exports (
                export_timestamp, 
                export_folder,
                status
            ) VALUES (NULL, ?, 'pending')
            ''', (folder_name,))

            conn.commit()
            export_id = cursor.lastrowid
            print(f"Successfully logged export start to database with ID: {export_id}")
            return export_id

        except Exception as e:
            print(f"Error logging export start to database: {str(e)}")
            messagebox.showerror("Database Error", f"Failed to log export to database: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()

    def update_export_status(self, export_id, status, add_timestamp=False):
        """Update the export status in the database"""
        if export_id is None:
            print(f"Cannot update status to '{status}': export_id is None")
            return False

        conn = None
        try:
            print(f"update_export_status called with export_id={export_id}, status={status}")

            if not os.path.exists(os.path.dirname(self.db_file)):
                os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

            if not os.path.exists(self.db_file):
                print(f"Database file does not exist: {self.db_file}")
                return False

            conn = sqlite3.connect(self.db_file, timeout=30)
            cursor = conn.cursor()

            # First verify the record exists
            cursor.execute("SELECT id FROM exports WHERE id = ?", (export_id,))
            if not cursor.fetchone():
                print(f"Record with ID {export_id} does not exist in database")
                return False

            if add_timestamp:
                # Format timestamp in Excel-friendly format (YYYY-MM-DD HH:MM:SS)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"Updating record {export_id} with timestamp {timestamp} and status {status}")

                # Update the record with timestamp and status
                cursor.execute('''
                UPDATE exports 
                SET export_timestamp = ?, 
                    status = ? 
                WHERE id = ?
                ''', (timestamp, status, export_id))
            else:
                # Just update the status
                cursor.execute('''
                UPDATE exports 
                SET status = ? 
                WHERE id = ?
                ''', (status, export_id))

            conn.commit()
            print(f"Successfully updated record {export_id} status to {status}")
            return True

        except sqlite3.Error as e:
            print(f"SQLite error in update_export_status: {str(e)}")
            if conn:
                conn.rollback()
            return False
        except Exception as e:
            print(f"General error in update_export_status: {str(e)}")
            if conn:
                conn.rollback()
            return False
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
        """Run the Teton content export process without progress bar"""
        try:
            # Create export folder in the same directory as the executable/script
            current_date = datetime.now().strftime("%Y-%m-%d")
            base_dir = os.path.dirname(os.path.abspath(__file__))  # Directory where the script/exe is located
            self.export_folder = os.path.join(base_dir, current_date)

            # Create the folder if it doesn't exist
            os.makedirs(self.export_folder, exist_ok=True)

            # Log the export to database - get ID for tracking
            self.current_export_id = self.log_export_start(self.export_folder)

            # Show info message that export is starting
            messagebox.showinfo(
                "Export Starting",
                "Teton content export is starting in a separate window.\n\n"
                "Please wait for it to complete - this may take several minutes."
            )

            batch_file = "C:\\opt\\software\\eeplus\\bin\\eeplus-filters-R01B085\\compileEEPContentsForThirdPartyExport.bat"

            if not os.path.exists(batch_file):
                raise FileNotFoundError(f"Batch file not found at {batch_file}")

            # Change to the batch file's directory before running it
            batch_dir = os.path.dirname(batch_file)
            os.chdir(batch_dir)

            # Run the batch file in a new console window
            self.export_process = subprocess.Popen(
                ['cmd', '/c', batch_file],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            # Start a thread to monitor the process
            monitor_thread = threading.Thread(
                target=self.monitor_export_process,
                daemon=True
            )
            monitor_thread.start()

        except Exception as e:
            # Mark as failed in the database
            if self.current_export_id:
                self.update_export_status(self.current_export_id, "failed")

            messagebox.showerror(
                "Export Failed",
                f"Teton content export failed to start:\n{str(e)}"
            )

    def monitor_export_process(self):
        """Monitor the export process and handle completion without progress dialog"""
        try:
            # Wait for the process to complete
            return_code = self.export_process.wait()
            was_manually_closed = return_code != 0

            if was_manually_closed:
                # Update database to show interrupted
                if self.current_export_id:
                    self.update_export_status(self.current_export_id, "interrupted")

                # Show warning message
                self.root.after(0, lambda: messagebox.showwarning(
                    "Export Interrupted",
                    "The Teton export process was interrupted before completion."
                ))
                return

            # Process completed normally, continue with verification and file copying
            export_dir = "C:\\opt\\software\\eeplus\\input\\eeplus\\ThirdPartyExport\\"

            # Verify the exported files
            missing_files = []
            for file in self.export_files:
                if not os.path.exists(os.path.join(export_dir, file)):
                    missing_files.append(file)

            if missing_files:
                # Update database to show failed
                if self.current_export_id:
                    self.update_export_status(self.current_export_id, "failed")

                error_msg = f"Missing exported files: {', '.join(missing_files)}"
                self.root.after(0, lambda: messagebox.showerror("Export Failed", error_msg))
                return

            # Copy files to the dated folder
            try:
                # Copy each file
                for file in self.export_files:
                    src = os.path.join(export_dir, file)
                    dst = os.path.join(self.export_folder, file)
                    shutil.copy2(src, dst)

                # Mark export as completed in database
                if self.current_export_id:
                    self.update_export_status(self.current_export_id, "completed", add_timestamp=True)

                if self.on_export_complete:
                    self.root.after(0, self.on_export_complete)

                self.root.after(0, lambda: messagebox.showinfo(
                    "Export Complete",
                    "Teton content export completed successfully!\n\n"
                    f"Files copied to: {self.export_folder}"
                ))
            except Exception as e:
                # Update database to show failed
                if self.current_export_id:
                    self.update_export_status(self.current_export_id, "failed")

                error_msg = f"Failed to copy exported files: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("Export Failed", error_msg))

        except Exception as e:
            # Update database to show failed
            if self.current_export_id:
                self.update_export_status(self.current_export_id, "failed")

            error_msg = f"Error monitoring export process: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Export Error", error_msg))
        finally:
            # Clean up
            self.current_export_id = None
            self.export_process = None

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

            # Check if status column exists
            cursor.execute("PRAGMA table_info(exports)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'status' in columns:
                cursor.execute('''
                SELECT id, export_timestamp, export_folder, status
                FROM exports
                ORDER BY 
                    CASE WHEN export_timestamp IS NULL THEN 1 ELSE 0 END,
                    export_timestamp DESC
                ''')
            else:
                # Fallback for databases without status column
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