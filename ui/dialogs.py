import csv
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from datetime import datetime

from utils.file_utils import ensure_directory_exists


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class ServerEnvironmentDialog:
    def __init__(self, parent):
        self.result = None

        # Create a dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Environment")
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Set background color to white for the dialog
        self.dialog.configure(bg='white')

        # Set EEP icon for dialog
        try:
            icon_path = resource_path(os.path.join("assets", "EEP_512_512.ico"))
            self.dialog.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error loading icon for dialog: {e}")

        # Center the dialog on parent
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (400 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (200 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Configure styles
        style = ttk.Style()
        style.configure("TRadiobutton", font=("Arial", 11), background='white')
        style.configure("Accent.TButton", font=("Arial", 11, "bold"))
        style.configure("ServerEnv.TFrame", background='white')

        # Create content
        frame = ttk.Frame(self.dialog, padding=20, style="ServerEnv.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)

        # Make the label have a white background
        label = ttk.Label(
            frame,
            text="Select Server Environment:",
            font=("Arial", 12, "bold"),
            background='white'
        )
        label.pack(pady=(0, 20))

        self.environment_var = tk.StringVar(value="UAT")

        ttk.Radiobutton(
            frame,
            text="UAT Server",
            variable=self.environment_var,
            value="UAT",
            style="TRadiobutton"
        ).pack(anchor=tk.W, pady=5)

        ttk.Radiobutton(
            frame,
            text="Production Server",
            variable=self.environment_var,
            value="Production",
            style="TRadiobutton"
        ).pack(anchor=tk.W, pady=5)

        # Create buttons
        button_frame = ttk.Frame(frame, style="ServerEnv.TFrame")
        button_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Continue",
            command=self.on_continue,
            style="Accent.TButton"
        ).pack(side=tk.RIGHT, padx=5)

        # Wait for dialog to close
        parent.wait_window(self.dialog)

    def on_continue(self):
        self.result = self.environment_var.get()
        self.dialog.destroy()


class ProgressDialog:
    def __init__(self, parent, title="Progress"):
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Set background color to white for the dialog
        self.dialog.configure(bg='white')

        # Set EEP icon for dialog
        try:
            icon_path = resource_path(os.path.join("assets", "EEP_512_512.ico"))
            self.dialog.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error loading icon for dialog: {e}")

        # Center the dialog on parent
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (500 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (200 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Prevent closing the dialog
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        # Configure styles
        style = ttk.Style()
        style.configure("Progress.TFrame", background='white')
        style.configure("Progress.TLabel", background='white')

        # Create content
        frame = ttk.Frame(self.dialog, padding=20, style="Progress.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(
            frame,
            text="Processing...",
            font=("Arial", 12),
            wraplength=460,  # Allow wrapping for long status messages
            background='white'
        )
        self.status_label.pack(pady=(0, 20))

        self.progress = ttk.Progressbar(
            frame,
            orient="horizontal",
            length=460,
            mode="determinate"
        )
        self.progress.pack(fill=tk.X, pady=10)

        # Add a please wait message
        self.wait_label = ttk.Label(
            frame,
            text="Please wait while the process completes...",
            font=("Arial", 10),
            foreground="#666666",
            background='white'
        )
        self.wait_label.pack(pady=10)

    def set_status(self, message):
        """Update the status message"""
        self.status_label.config(text=message)
        self.dialog.update()

    def set_progress(self, value):
        """Update the progress bar (0.0 to 1.0)"""
        self.progress["value"] = value * 100
        self.dialog.update()

    def destroy(self):
        """Close the dialog"""
        self.dialog.destroy()


class ConfirmationDialog:
    def __init__(self, parent, title="Confirmation", message="Are you sure?",
                 yes_button_text="Yes", no_button_text="No", show_icon=True):
        self.result = False

        # Create a dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Set background color to white for the dialog
        self.dialog.configure(bg='white')

        # Set EEP icon for dialog
        try:
            icon_path = resource_path(os.path.join("assets", "EEP_512_512.ico"))
            self.dialog.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error loading icon for dialog: {e}")

        # Center the dialog on parent
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (450 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (200 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Configure styles first to ensure they're available
        style = ttk.Style()

        # Create unique style names for the confirmation dialog
        style.configure("Confirmation.TButton", font=("Arial", 11))
        style.configure("Confirmation.Accent.TButton", font=("Arial", 11, "bold"))
        style.configure("Confirmation.TFrame", background='white')  # Only affects confirmation dialog

        # Create content frame with white background using our unique style
        frame = ttk.Frame(self.dialog, padding=20, style='Confirmation.TFrame')
        frame.pack(fill=tk.BOTH, expand=True)

        # Question icon (using Unicode character) - only if show_icon is True
        if show_icon:
            icon_label = ttk.Label(
                frame,
                text="❓",
                font=("Arial", 24),
                background='white'  # Set label background to white
            )
            icon_label.pack(pady=(0, 10))

        # Message label with white background
        message_label = ttk.Label(
            frame,
            text=message,
            font=("Arial", 11),
            wraplength=400,
            justify="center",
            background='white'  # Set label background to white
        )
        message_label.pack(pady=(0, 20))

        # Create buttons with explicit width and visibility check
        button_frame = ttk.Frame(frame, style='Confirmation.TFrame')
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # "No" button
        no_button = ttk.Button(
            button_frame,
            text=no_button_text,
            command=self.on_no,
            width=15,
            style='Confirmation.TButton'
        )
        no_button.pack(side=tk.RIGHT, padx=5)

        # "Yes" button
        yes_button = ttk.Button(
            button_frame,
            text=yes_button_text,
            command=self.on_yes,
            width=15,
            style="Confirmation.Accent.TButton"
        )
        yes_button.pack(side=tk.RIGHT, padx=5)

        # Force update to ensure buttons are drawn
        self.dialog.update_idletasks()

        # Wait for dialog to close
        parent.wait_window(self.dialog)

    def on_yes(self):
        self.result = True
        self.dialog.destroy()

    def on_no(self):
        self.result = False
        self.dialog.destroy()


class UploadHistoryDialog:
    def __init__(self, parent, history_data, db_file):
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Topic Upload History")
        self.dialog.geometry("1000x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Set background color to white for the dialog
        self.dialog.configure(bg='white')

        # Store db_file as instance variable
        self.db_file = db_file
        # Set EEP icon for dialog
        try:
            icon_path = resource_path(os.path.join("assets", "EEP_512_512.ico"))
            self.dialog.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error loading icon for dialog: {e}")

        # Center the dialog on parent
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (1000 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (600 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Configure styles
        style = ttk.Style()
        style.configure("UploadHistory.TFrame", background='white')
        style.configure("Treeview",
                        rowheight=25,
                        font=("Arial", 10),
                        anchor="center")  # Center align all data
        style.configure("Treeview.Heading",
                        font=("Arial", 10, "bold"),
                        anchor="center")  # Center align headers
        style.configure("Accent.TButton", font=("Arial", 11, "bold"))

        # Create content
        frame = ttk.Frame(self.dialog, padding=10, style="UploadHistory.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)

        # Create treeview with scrollbars
        tree_frame = ttk.Frame(frame, style="UploadHistory.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        y_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Horizontal scrollbar
        x_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Create the treeview
        columns = (
            "upload_time", "topic_month", "xml_files", "images",
            "database_zip", "images_zip", "status"
        )

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set,
            selectmode="browse",
            show="headings"
        )

        # Configure scrollbars
        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)

        # Configure columns with center alignment
        column_defs = [
            ("upload_time", "Uploaded Date & Time", 180, True),
            ("topic_month", "Topic Month", 120, True),
            ("xml_files", "No of XML Files", 120, True),
            ("images", "No of Images", 120, True),
            ("database_zip", "Database ZIP", 200, True),
            ("images_zip", "Images ZIP", 200, True)
        ]

        for col_id, heading, width, stretch in column_defs:
            self.tree.heading(col_id, text=heading, anchor="center")
            self.tree.column(col_id, width=width, minwidth=width,
                             stretch=stretch, anchor="center")

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Modify the values insertion to remove status
        for record in history_data:
            # Handle formatting of timestamp
            timestamp = record[1]
            if timestamp is None or timestamp == "None" or timestamp == "":
                timestamp_display = "Pending"
            else:
                # Try to format the timestamp nicely
                try:
                    dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    timestamp_display = dt.strftime("%Y-%m-%d %I:%M %p")
                except (ValueError, TypeError):
                    timestamp_display = timestamp

            values = (
                timestamp_display,  # upload_time
                record[2],  # topic_month
                record[3],  # xml_files
                record[4],  # images
                record[5],  # database_zip
                record[6]  # images_zip
            )
            self.tree.insert("", tk.END, values=values)

        # Add button frame
        button_frame = ttk.Frame(frame, style="UploadHistory.TFrame")
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Export to CSV button
        ttk.Button(
            button_frame,
            text="Export to CSV",
            command=self.export_to_csv,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)

        # Close button
        ttk.Button(
            button_frame,
            text="Close",
            command=self.dialog.destroy,
            style="Accent.TButton"
        ).pack(side=tk.RIGHT, padx=5)

        # Store parent for refresh functionality
        self.parent = parent

        # Wait for dialog to close
        parent.wait_window(self.dialog)

    def export_to_csv(self):
        """Export the history data to a CSV file with Excel-friendly formatting"""
        try:
            # Get all data from the treeview
            data = []
            headers = [
                "Uploaded Date & Time",
                "Topic Month",
                "No of XML Files",
                "No of Images",
                "Database ZIP",
                "Images ZIP",
                "Status"
            ]
            data.append(headers)  # Add headers first

            for item in self.tree.get_children():
                values = list(self.tree.item(item, 'values'))
                data.append(values)

            if len(data) <= 1:  # Only headers exist
                messagebox.showwarning("Warning", "No data to export")
                return

            # Create CSV file path - use the same folder as the database
            history_folder = os.path.dirname(self.parent.db_file)  # Get from parent
            ensure_directory_exists(history_folder)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = os.path.join(history_folder, f"topic_upload_history_{timestamp}.csv")

            # Write to CSV with Excel-compatible formatting
            with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:  # utf-8-sig for Excel
                writer = csv.writer(f)
                writer.writerows(data)

            messagebox.showinfo("Success", f"Data exported to:\n{csv_file}")

            # Open the file location in Explorer
            try:
                os.startfile(os.path.dirname(csv_file))
            except Exception as e:
                print(f"Error opening file location: {e}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data:\n{str(e)}")


class TetonHistoryDialog:
    def __init__(self, parent, history_data, db_file):
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Teton Export History")
        self.dialog.geometry("800x400")  # Wider to accommodate two columns
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Set background color to white for the dialog
        self.dialog.configure(bg='white')
        # Store db_file as instance variable
        self.db_file = db_file
        # Set EEP icon for dialog
        try:
            icon_path = resource_path(os.path.join("assets", "EEP_512_512.ico"))
            self.dialog.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error loading icon for dialog: {e}")

        # Center the dialog on parent
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (800 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (400 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Configure styles
        style = ttk.Style()
        style.configure("TetonHistory.TFrame", background='white')
        style.configure("Treeview",
                        rowheight=25,
                        font=("Arial", 10),
                        anchor="center")  # Center align all data
        style.configure("Treeview.Heading",
                        font=("Arial", 10, "bold"),
                        anchor="center")  # Center align headers
        style.configure("Accent.TButton", font=("Arial", 11, "bold"))

        # Create content
        frame = ttk.Frame(self.dialog, padding=10, style="TetonHistory.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)

        # Create treeview with scrollbars
        tree_frame = ttk.Frame(frame, style="TetonHistory.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        y_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Create the treeview with two columns
        columns = ("export_date", "export_folder")

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            yscrollcommand=y_scroll.set,
            selectmode="browse",
            show="headings"
        )

        # Configure scrollbar
        y_scroll.config(command=self.tree.yview)

        # Configure columns
        self.tree.heading("export_date", text="Export Date & Time", anchor="center")
        self.tree.column("export_date", width=300, minwidth=200, stretch=tk.YES, anchor="center")

        self.tree.heading("export_folder", text="Export Folder Name", anchor="center")
        self.tree.column("export_folder", width=300, minwidth=200, stretch=tk.YES, anchor="center")

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Add data to the treeview
        for record in history_data:
            # Handle formatting of timestamp
            timestamp = record[1]  # Second item is the export timestamp
            if timestamp is None or timestamp == "None" or timestamp == "":
                timestamp_display = "Unknown"
            else:
                # Try to format the timestamp nicely
                try:
                    dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    timestamp_display = dt.strftime("%Y-%m-%d %I:%M %p")
                except (ValueError, TypeError):
                    timestamp_display = timestamp

            folder_name = record[2]  # Third item is the folder name
            self.tree.insert("", tk.END, values=(timestamp_display, folder_name))

        # Add button frame
        button_frame = ttk.Frame(frame, style="TetonHistory.TFrame")
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Export to CSV button
        ttk.Button(
            button_frame,
            text="Export to CSV",
            command=self.export_to_csv,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)

        # Close button
        ttk.Button(
            button_frame,
            text="Close",
            command=self.dialog.destroy,
            style="Accent.TButton"
        ).pack(side=tk.RIGHT, padx=5)

        # Store parent for refresh functionality
        self.parent = parent

        # Wait for dialog to close
        parent.wait_window(self.dialog)

    def export_to_csv(self):
        """Export the Teton export history data to a CSV file"""
        try:
            # Get all data from the treeview
            data = []
            headers = [
                "Export Date & Time",
                "Export Folder Name",
                "Status"
            ]
            data.append(headers)  # Add headers first

            for item in self.tree.get_children():
                values = list(self.tree.item(item, 'values'))
                data.append(values)

            if len(data) <= 1:  # Only headers exist
                messagebox.showwarning("Warning", "No data to export")
                return

            # Create CSV file path - use the same folder as the database
            history_folder = os.path.dirname(self.parent.db_file)  # Get from parent
            ensure_directory_exists(history_folder)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = os.path.join(history_folder, f"teton_export_history_{timestamp}.csv")

            # Write to CSV with Excel-compatible formatting
            with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:  # utf-8-sig for Excel
                writer = csv.writer(f)
                writer.writerows(data)

            messagebox.showinfo("Success", f"Data exported to:\n{csv_file}")

            # Open the file location in Explorer
            try:
                os.startfile(os.path.dirname(csv_file))
            except Exception as e:
                print(f"Error opening file location: {e}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data:\n{str(e)}")