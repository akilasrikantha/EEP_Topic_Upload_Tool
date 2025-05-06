# Updated topic_upload.py
import os
import re
import shutil
import zipfile
import subprocess
import threading
import time
import sqlite3
from datetime import datetime
from tkinter import filedialog, messagebox
from ui.dialogs import ServerEnvironmentDialog, ProgressDialog, ConfirmationDialog
from utils.file_utils import ensure_directory_exists


class TopicUploadTask:
    def __init__(self, parent, on_upload_complete=None, on_folder_cleared=None):
        self.parent = parent
        self.source_folder = None
        self.working_folder = None
        self.environment = None
        self.on_upload_complete = on_upload_complete  # Callback function
        self.on_folder_cleared = on_folder_cleared  # Callback function
        self.current_upload_id = None  # Initialize as None

        # Regex patterns
        self.database_pattern = r'database-\d+-\w+-\d+\.zip'
        self.images_pattern = r'\d+-\w+-\d+-images\.zip'

        # Initialize upload tracking database
        self.init_upload_db()

        # Database path
        self.db_file = os.path.abspath(os.path.join("Topic Upload History", "topic_uploads.db"))

    def start_topic_upload(self):
        """Start the EEP Topic Upload process"""
        # First select the folder containing the ZIP files
        self.source_folder = filedialog.askdirectory(
            title="Select folder containing database and images ZIP files"
        )

        if not self.source_folder:
            return  # User cancelled

        # Create working directory in the same folder user selected
        self.working_folder = os.path.join(self.source_folder, "EEP Topic Upload Temporary Files")
        try:
            if not os.path.exists(self.working_folder):
                os.makedirs(self.working_folder)
        except OSError as e:
            messagebox.showerror(
                "Error",
                f"Failed to create working directory:\n{str(e)}"
            )
            return

        # Validate zip files exist
        database_zip, images_zip = self.find_zip_files(self.source_folder)

        if not database_zip or not images_zip:
            messagebox.showerror(
                "Error",
                "Required ZIP files not found.\n\nExpected files with format:\n- database-DD-Month-YYYY.zip\n- DD-Month-YYYY-images.zip"
            )
            return

        # Start process with progress dialog
        progress_dialog = ProgressDialog(self.parent, "EEP Topic Upload")
        progress_dialog.set_status("Starting topic upload process...")

        # Run the process in a separate thread
        thread = threading.Thread(
            target=self.process_zip_files,
            args=(database_zip, images_zip, progress_dialog)
        )
        thread.daemon = True
        thread.start()

    def init_upload_db(self):
        """Initialize SQLite database for upload tracking if it doesn't exist"""
        history_folder = "Topic Upload History"

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

        db_file = os.path.join(history_folder, "topic_uploads.db")

        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_timestamp TEXT,
                topic_month TEXT NOT NULL,
                xml_files INTEGER NOT NULL,
                images INTEGER NOT NULL,
                database_zip TEXT NOT NULL,
                images_zip TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
            ''')

            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_topic_month 
            ON uploads(topic_month)
            ''')

            # Add the status column if it doesn't exist (for existing databases)
            cursor.execute('''
            PRAGMA table_info(uploads)
            ''')
            columns = [column[1] for column in cursor.fetchall()]

            # Handle migration from old schema to new schema
            if 'filter_completed' in columns and 'status' not in columns:
                # Add the new status column
                cursor.execute('''
                ALTER TABLE uploads
                ADD COLUMN status TEXT DEFAULT 'pending'
                ''')

                # Convert existing data: update status based on filter_completed value
                cursor.execute('''
                UPDATE uploads
                SET status = CASE 
                    WHEN filter_completed = 1 THEN 'completed'
                    ELSE 'pending'
                END
                ''')

                conn.commit()
                print("Successfully migrated database from filter_completed to status")

            # Ensure status column exists
            elif 'status' not in columns:
                cursor.execute('''
                ALTER TABLE uploads
                ADD COLUMN status TEXT DEFAULT 'pending'
                ''')

            conn.commit()
            conn.close()
            print(f"Successfully initialized database: {db_file}")

        except Exception as e:
            print(f"Error initializing upload database: {str(e)}")
            messagebox.showwarning("Database Warning",
                                   "Could not initialize upload tracking database. History will not be saved.")

    def log_upload_to_db(self, database_zip, images_zip):
        """Log upload metadata to SQLite database, but don't set timestamp yet"""
        conn = None
        try:
            # Extract information from filenames
            db_match = re.search(r'database-(\d+)-(\w+)-(\d+)\.zip', database_zip, re.IGNORECASE)
            img_match = re.search(r'(\d+)-(\w+)-(\d+)-images\.zip', images_zip, re.IGNORECASE)

            if not db_match or not img_match:
                print("Error: Could not extract date information from filenames")
                return None

            # Verify month names match
            db_month = db_match.group(2).lower()
            img_month = img_match.group(2).lower()
            if db_month != img_month:
                messagebox.showerror(
                    "Error",
                    "Month names in ZIP files don't match:\n"
                    f"Database month: {db_month}\n"
                    f"Images month: {img_month}"
                )
                return None

            day = db_match.group(1)
            month = db_match.group(2)
            year = db_match.group(3)
            topic_month = f"{day}-{month}-{year}"

            # Count files in the original zips
            xml_count = 0
            with zipfile.ZipFile(database_zip, 'r') as zip_ref:
                xml_count = len([f for f in zip_ref.namelist() if f.lower().endswith('.xml')])

            image_count = 0
            with zipfile.ZipFile(images_zip, 'r') as zip_ref:
                image_count = len([f for f in zip_ref.namelist()
                                   if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))])

            # Ensure directory exists
            ensure_directory_exists(os.path.dirname(self.db_file))

            conn = sqlite3.connect(self.db_file, timeout=30)
            cursor = conn.cursor()

            # Insert with NULL timestamp and 'pending' status
            cursor.execute('''
            INSERT INTO uploads (
                upload_timestamp, topic_month, xml_files, images, 
                database_zip, images_zip, status
            ) VALUES (NULL, ?, ?, ?, ?, ?, 'pending')
            ''', (
                topic_month,
                xml_count,
                image_count,
                os.path.basename(database_zip),
                os.path.basename(images_zip)
            ))

            conn.commit()
            upload_id = cursor.lastrowid
            print(f"Successfully logged upload to database with ID: {upload_id}")
            return upload_id

        except Exception as e:
            print(f"Error logging upload to database: {str(e)}")
            messagebox.showerror("Database Error", f"Failed to log upload to database: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()


    def process_zip_files(self, database_zip, images_zip, progress_dialog):
        """Process the ZIP files and perform the necessary tasks"""
        try:
            # Extract files directly to working folder
            progress_dialog.set_status("Extracting database ZIP file...")
            with zipfile.ZipFile(database_zip, 'r') as zip_ref:
                zip_ref.extractall(self.working_folder)

            progress_dialog.set_status("Extracting images ZIP file...")
            with zipfile.ZipFile(images_zip, 'r') as zip_ref:
                zip_ref.extractall(self.working_folder)

            # Process database XML files
            progress_dialog.set_status("Processing database XML files...")
            database_output = os.path.join(self.working_folder, "database.zip")
            self.process_database_files(self.working_folder, database_output)

            # Process image files
            progress_dialog.set_status("Processing image files...")
            images_output = os.path.join(self.working_folder, "images.zip")
            self.process_image_files(self.working_folder, images_output)

            # Copy files to server location
            progress_dialog.set_status("Copying files to server...")
            if not self.copy_files_to_server(database_output, images_output):
                progress_dialog.destroy()
                messagebox.showerror("Error", "Failed to copy files to server location. Please check the path exists.")
                return

            # Log the upload to database before showing success message
            upload_id = self.log_upload_to_db(database_zip, images_zip)
            if upload_id is None:
                progress_dialog.destroy()
                messagebox.showerror("Error", "Failed to log upload to database.")
                return

            self.current_upload_id = upload_id  # Store the upload ID for later use

            progress_dialog.destroy()

            if self.on_upload_complete:
                self.on_upload_complete()

            # Ask user if they want to run the filter task
            run_filter = messagebox.askyesno(
                "Success",
                "Files have been copied to server. Do you want to run the filter job now?"
            )

            if run_filter:
                self.run_filter_job()
            else:
                messagebox.showinfo("Success", "Files have been copied to server. You can run the filter job later.")
                # Since we're not running filter now, we should still save the upload record
                self.mark_filter_complete(self.current_upload_id, completed=False)

        except Exception as e:
            progress_dialog.destroy()
            messagebox.showerror("Error", f"An error occurred during the process:\n{str(e)}")

    def update_upload_status(self, upload_id, status, add_timestamp=False):
        """Update the upload status in the database"""
        if upload_id is None:
            print(f"Cannot update status to '{status}': upload_id is None")
            return False

        conn = None
        try:
            print(f"update_upload_status called with upload_id={upload_id}, status={status}")

            # Ensure directory exists
            ensure_directory_exists(os.path.dirname(self.db_file))

            if not os.path.exists(self.db_file):
                print(f"Database file does not exist: {self.db_file}")
                return False

            conn = sqlite3.connect(self.db_file, timeout=30)
            cursor = conn.cursor()

            # First verify the record exists
            cursor.execute("SELECT id FROM uploads WHERE id = ?", (upload_id,))
            if not cursor.fetchone():
                print(f"Record with ID {upload_id} does not exist in database")
                return False

            if add_timestamp:
                # Format timestamp in Excel-friendly format (YYYY-MM-DD HH:MM:SS)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"Updating record {upload_id} with timestamp {timestamp} and status {status}")

                # Update the record with timestamp and status
                cursor.execute('''
                UPDATE uploads 
                SET upload_timestamp = ?, 
                    status = ? 
                WHERE id = ?
                ''', (timestamp, status, upload_id))
            else:
                # Just update the status
                cursor.execute('''
                UPDATE uploads 
                SET status = ? 
                WHERE id = ?
                ''', (status, upload_id))

            conn.commit()
            print(f"Successfully updated record {upload_id} status to {status}")
            return True

        except sqlite3.Error as e:
            print(f"SQLite error in update_upload_status: {str(e)}")
            if conn:
                conn.rollback()
            return False
        except Exception as e:
            print(f"General error in update_upload_status: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def mark_filter_complete(self, upload_id, completed=True):
        """Mark the upload as having completed filter processing in the database"""
        status = "completed" if completed else "pending"
        return self.update_upload_status(upload_id, status, add_timestamp=completed)

    def monitor_filter_process(self):
        """Monitor the filter process and show appropriate completion message"""
        try:
            return_code = self.filter_process.wait()  # Wait for process to complete
            was_manually_closed = return_code != 0

            # Show appropriate message (using after to ensure it runs in main thread)
            if hasattr(self.parent, 'after'):
                if was_manually_closed:
                    # Mark as interrupted in the database
                    if self.current_upload_id is not None:
                        self.update_upload_status(self.current_upload_id, "interrupted")

                    self.parent.after(0, lambda: messagebox.showwarning(
                        "Filter Job Interrupted",
                        "The filter task was stopped before completion.\n\n"
                        "If you closed the window manually, please run the filter job again "
                        "and let it complete normally."
                    ))
                else:
                    # Only mark as complete if the filter job succeeded
                    if self.current_upload_id is not None:
                        # Add small delay to ensure everything is ready
                        time.sleep(1)

                        # Debug print to trace the issue
                        print(f"Attempting to mark upload {self.current_upload_id} as complete")
                        success = self.update_upload_status(self.current_upload_id, "completed", add_timestamp=True)

                        if success:
                            print(f"Successfully marked upload {self.current_upload_id} as complete")
                            self.parent.after(0, lambda: messagebox.showinfo(
                                "Filter Job Complete",
                                "The filter task has completed successfully."
                            ))
                        else:
                            print(f"Failed to mark upload {self.current_upload_id} as complete")
                            self.parent.after(0, lambda: messagebox.showwarning(
                                "Warning",
                                "Filter completed but failed to update database record."
                            ))
                    else:
                        print("No current_upload_id available to update")
                        self.parent.after(0, lambda: messagebox.showwarning(
                            "Warning",
                            "Filter completed but no upload ID was found to update the database."
                        ))
        except Exception as e:
            # Mark as failed in the database
            if hasattr(self, 'current_upload_id') and self.current_upload_id is not None:
                self.update_upload_status(self.current_upload_id, "failed")

            print(f"Error monitoring filter process: {str(e)}")
            if hasattr(self.parent, 'after'):
                self.parent.after(0, lambda: messagebox.showerror(
                    "Error",
                    f"An error occurred while monitoring the filter process:\n{str(e)}"
                ))
        finally:
            # Clear the upload ID only after we're done with it
            if hasattr(self, 'current_upload_id') and self.current_upload_id is not None:
                print(f"Clearing current_upload_id: {self.current_upload_id}")
                self.current_upload_id = None
            # Hide loader when done
            if hasattr(self.parent, 'loader'):
                self.parent.loader.stop_loading()

    def get_upload_history(self):
        """Fetch all upload history from the database"""
        try:
            # Ensure directory exists
            ensure_directory_exists(os.path.dirname(self.db_file))

            # Ensure the database file exists
            if not os.path.exists(self.db_file):
                print(f"Database file does not exist: {self.db_file}")
                return []

            # Connect with timeout to avoid locking issues
            conn = sqlite3.connect(self.db_file, timeout=30)
            cursor = conn.cursor()

            # Print the schema to debug
            cursor.execute("PRAGMA table_info(uploads)")
            columns = cursor.fetchall()
            print("Table schema:", columns)

            # Count records to debug
            cursor.execute("SELECT COUNT(*) FROM uploads")
            count = cursor.fetchone()[0]
            print(f"Found {count} records in uploads table")

            # Check if we're using the old or new schema
            has_status_column = any(column[1] == 'status' for column in columns)

            if has_status_column:
                cursor.execute('''
                SELECT id, upload_timestamp, topic_month, xml_files, images, 
                       database_zip, images_zip, status
                FROM uploads
                ORDER BY 
                    CASE WHEN upload_timestamp IS NULL THEN 1 ELSE 0 END,
                    upload_timestamp DESC
                ''')
            else:
                # Fall back to old schema for backward compatibility
                cursor.execute('''
                SELECT id, upload_timestamp, topic_month, xml_files, images, 
                       database_zip, images_zip, filter_completed
                FROM uploads
                ORDER BY 
                    CASE WHEN upload_timestamp IS NULL THEN 1 ELSE 0 END,
                    upload_timestamp DESC
                ''')

            history = cursor.fetchall()
            print(f"Retrieved {len(history)} history records")
            conn.close()
            return history
        except Exception as e:
            print(f"Error fetching upload history: {str(e)}")
            return []

    def find_zip_files(self, folder_path):
        """Find the database and images zip files in the specified folder"""
        database_zip = None
        images_zip = None

        for file in os.listdir(folder_path):
            if file.lower().endswith('.zip'):
                if re.match(self.database_pattern, file, re.IGNORECASE):
                    database_zip = os.path.join(folder_path, file)
                elif re.match(self.images_pattern, file, re.IGNORECASE):
                    images_zip = os.path.join(folder_path, file)

        return database_zip, images_zip

    def extract_zip(self, zip_path, destination):
        """Extract a ZIP file and return the extracted folder path"""
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(destination)

        # Get the main folder name from the ZIP file
        zip_filename = os.path.basename(zip_path)
        folder_name = os.path.splitext(zip_filename)[0]

        return os.path.join(destination, folder_name)

    def process_database_files(self, search_root, output_zip):
        """Search for validate folder recursively and process XML files"""
        validate_folder = None

        # Recursively search for validate folder
        for root, dirs, files in os.walk(search_root):
            if "validate" in dirs:
                validate_folder = os.path.join(root, "validate")
                break

        if not validate_folder:
            raise FileNotFoundError(f"Could not find validate folder in {search_root}")

        with zipfile.ZipFile(output_zip, 'w') as zipf:
            for root, dirs, files in os.walk(validate_folder):
                for file in files:
                    if file.lower().endswith('.xml'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, validate_folder)
                        zipf.write(file_path, arcname=arcname)

    def process_image_files(self, search_root, output_zip):
        """Search for Images folder recursively and process image files"""
        images_folder = None

        # Recursively search for Images folder (case insensitive)
        for root, dirs, files in os.walk(search_root):
            for dir_name in dirs:
                if dir_name.lower() == "images":
                    images_folder = os.path.join(root, dir_name)
                    break
            if images_folder:
                break

        if not images_folder:
            raise FileNotFoundError(f"Could not find Images folder in {search_root}")

        with zipfile.ZipFile(output_zip, 'w') as zipf:
            for root, dirs, files in os.walk(images_folder):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, images_folder)
                        zipf.write(file_path, arcname=arcname)

    def copy_files_to_server(self, database_zip, images_zip):
        """Copy the repackaged files to the server location"""
        server_location = "C:\\opt\\software\\eeplus\\received-data\\"

        # Check if server location exists
        if not os.path.exists(server_location):
            messagebox.showerror("Error", f"Server location does not exist: {server_location}")
            return False

        try:
            # Copy files
            shutil.copy2(database_zip, os.path.join(server_location, "database.zip"))
            shutil.copy2(images_zip, os.path.join(server_location, "images.zip"))
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy files to server: {str(e)}")
            return False

    def run_filter_job(self):
        """Run the filter job and track its completion"""
        filter_job_path = "C:\\opt\\software\\eeplus\\bin\\eeplus-filters-R01B085\\runEETopicsFilterTask.bat"
        filter_job_dir = os.path.dirname(filter_job_path)

        if not os.path.exists(filter_job_path):
            messagebox.showerror("Error", f"Filter batch file not found: {filter_job_path}")
            return False

        try:
            # Notify user about the separate console window
            messagebox.showinfo(
                "Filter Job Starting",
                "The filter job will now start in a separate console window.\n\n"
                "Please wait for it to complete before proceeding.\n\n"
                "Note: Please don't close the window manually - let it complete naturally."
            )

            # Change to the batch file's directory before running it
            os.chdir(filter_job_dir)

            # Start the process and track it
            self.filter_process = subprocess.Popen(
                ['cmd', '/c', filter_job_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            # Create and store the thread as an instance variable
            self.monitor_thread = threading.Thread(
                target=self.monitor_filter_process,
                daemon=True
            )
            self.monitor_thread.start()

            return True

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start filter job: {str(e)}")
            return False

    def run_elastic_index_job(self):
        """Run the Elasticsearch index job and track its completion"""

        if not self.environment:
            # Ask for environment if not already set
            env_dialog = ServerEnvironmentDialog(self.parent)
            if not env_dialog.result:
                return  # User cancelled
            self.environment = env_dialog.result

        if self.environment == "UAT":
            index_job_path = "C:\\inetpub\\UAT Jobs\\UpdateElasticIndexJob_UAT\\UpdateElasticIndexJob.exe"
        else:  # Production
            index_job_path = "C:\\Jobs\\UpdateElasticIndexjob_UAT\\UpdateElasticIndexJob.exe"

        if not os.path.exists(index_job_path):
            messagebox.showerror("Error", f"Elasticsearch index job not found: {index_job_path}")
            return False

        try:
            # Show loader before starting
            if hasattr(self.parent, 'loader'):
                self.parent.loader.start_loading("Updating Elasticsearch index...")
            # Notify user about the separate console window
            messagebox.showinfo(
                "Elasticsearch Update Starting",
                "The Elasticsearch update job will now start in a separate console window.\n\n"
                "Please wait for it to complete before proceeding."
            )

            # Start the process and track it
            self.elastic_process = subprocess.Popen(
                [index_job_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            # Start a thread to monitor the process
            monitor_thread = threading.Thread(
                target=self.monitor_elastic_process,
                daemon=True
            )
            monitor_thread.start()

            return True

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Elasticsearch update: {str(e)}")
            return False

    def monitor_elastic_process(self):

        """Monitor the elastic process and show appropriate completion message"""
        return_code = self.elastic_process.wait()

        was_manually_closed = return_code != 0

        if hasattr(self.parent, 'after'):
            if was_manually_closed:
                self.parent.after(0, lambda: messagebox.showwarning(
                    "Index Job Interrupted",
                    "The Elasticsearch update was stopped before completion."
                ))
            else:
                self.parent.after(0, lambda: messagebox.showinfo(
                    "Index Update Complete",
                    "The Elasticsearch index update has completed successfully."
                ))

    def clear_working_folder(self):
        """Clear the working folder after user confirmation"""
        if not self.working_folder:
            messagebox.showwarning("Warning", "No temporary files to clear")
            return

        confirmation = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete the temporary files?\n\n{self.working_folder}"
        )

        if confirmation:
            try:
                if os.path.exists(self.working_folder):
                    shutil.rmtree(self.working_folder)
                    messagebox.showinfo("Success", "Temporary files have been deleted")
                    self.working_folder = None
                    # Call the callback instead of trying to access UI directly
                    if self.on_folder_cleared:
                        self.on_folder_cleared()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete temporary files: {str(e)}")