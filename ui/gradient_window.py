#gradient_window
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageFilter
import os
import sys
from tkinter.font import Font
from tasks.topic_upload import TopicUploadTask
from ui.dialogs import UploadHistoryDialog, TetonHistoryDialog
from tasks.teton_content_export import TetonContentExportTask


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class GradientWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("EEP Topic Upload Tool")

        # This is crucial for PyInstaller compatibility
        self.root.wm_attributes("-toolwindow", False)
        self.root.wm_attributes("-topmost", True)
        self.root.update()
        self.root.wm_attributes("-topmost", False)

        # Set window size (accounting for title bar height)
        window_width = 800
        window_height = 400
        self.root.geometry(f"{window_width}x{window_height}")

        # Set application icon
        try:
            icon_path = resource_path(os.path.join("assets", "EEP_512_512.ico"))
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error loading icon: {e}")

        # Task handlers
        self.topic_upload_task = TopicUploadTask(
            self.root,
            on_upload_complete=self.enable_buttons_after_upload,
            on_folder_cleared=self.disable_clear_button
        )

        self.teton_export_task = TetonContentExportTask(
            self.root,
            on_export_complete=self.enable_teton_buttons_after_export,
            on_folder_cleared=self.disable_teton_clear_button
        )

        # Background image (with proper path handling)
        try:
            bg_path = resource_path(os.path.join("assets", "Background.png"))
            self.bg_image = Image.open(bg_path)
            # Resize image to window size
            self.bg_image = self.bg_image.resize((window_width, window_height), Image.LANCZOS)
            print(f"Loaded background image from: {bg_path}")
        except Exception as e:
            # Fallback if image not found
            print(f"Error loading background image: {e}")
            self.bg_image = Image.new('RGB', (window_width, window_height), (50, 50, 50))

        # Create gradient overlay
        self.gradient = Image.new('RGBA', (window_width, window_height), (0, 0, 0, 0))
        for y in range(window_height):
            alpha = int(200 * (1 - y / window_height))
            overlay = Image.new('RGBA', (window_width, 1), (0, 0, 0, alpha))
            self.gradient.paste(overlay, (0, y))

        # Apply gradient to the image
        try:
            self.image_with_gradient = Image.alpha_composite(
                self.bg_image.convert('RGBA'),
                self.gradient
            )
        except Exception as e:
            print(f"Error applying gradient: {e}")
            # Fallback in case of error
            self.image_with_gradient = self.bg_image.convert('RGBA')

        # Create background
        self.bg_photo = ImageTk.PhotoImage(self.image_with_gradient.convert('RGB'))
        self.background = tk.Label(root, image=self.bg_photo)
        self.background.place(x=0, y=0, relwidth=1, relheight=1)

        # Create tab control with black background
        style = ttk.Style()
        style.theme_use('default')
        # Configure the notebook style
        style.configure('TNotebook', background='black', borderwidth=0)
        style.configure('TNotebook.Tab',
                        background='#333333',  # Dark grey for unselected tabs
                        foreground='white',
                        padding=[34, 15],
                        borderwidth=0,
                        lightcolor='black',
                        darkcolor='black',
                        bordercolor='black')
        style.map('TNotebook.Tab',
                  background=[('selected', 'black')],  # Black for selected tab
                  foreground=[('selected', 'white')],
                  expand=[('selected', [0, 0, 0, 0])])

        # Configure the frame backgrounds
        style.configure('TFrame', background='black')

        self.tab_control = ttk.Notebook(root, style='TNotebook')

        # Create tabs with black background
        self.topic_upload_tab = ttk.Frame(self.tab_control, style='TFrame')
        self.teton_export_tab = ttk.Frame(self.tab_control, style='TFrame')

        # Add tabs to the notebook with width matching button frame
        self.tab_control.add(self.topic_upload_tab, text='EEP Topic Upload', padding=5)
        self.tab_control.add(self.teton_export_tab, text='Teton Content Export', padding=5)
        self.tab_control.place(x=0, y=0, width=340, height=450)

        # Configure tab appearance
        style.layout('TNotebook.Tab', [
            ('Notebook.tab', {
                'sticky': 'nswe',
                'children': [
                    ('Notebook.padding', {
                        'side': 'top',
                        'sticky': 'nswe',
                        'children': [
                            ('Notebook.label', {'side': 'top', 'sticky': ''}),
                        ]
                    })
                ]
            })
        ])

        # Create buttons for each tab
        self.create_topic_upload_buttons()
        self.create_teton_export_buttons()

        # Bind tab change event
        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # Window settings
        self.root.resizable(False, False)

        # Force window to update and show properly
        self.root.update_idletasks()
        self.root.deiconify()

    def on_tab_changed(self, event):
        """Handle tab change event"""
        selected_tab = self.tab_control.tab(self.tab_control.select(), "text")
        if selected_tab == "EEP Topic Upload":
            self.update_topic_upload_button_states()
        elif selected_tab == "Teton Content Export":
            self.update_teton_export_button_states()

    def enable_teton_buttons_after_export(self):
        """Enable buttons after successful export"""
        self.clear_exported_btn.config(state=tk.NORMAL)
        self.view_exported_btn.config(state=tk.NORMAL)

    def disable_teton_clear_button(self):
        """Disable the clear folder button after deletion"""
        self.clear_exported_btn.config(state=tk.DISABLED)
        self.view_exported_btn.config(state=tk.DISABLED)


    def enable_buttons_after_upload(self):
        """Enable buttons after successful upload"""
        self.clear_folder_btn.config(state=tk.NORMAL)
        self.open_folder_btn.config(state=tk.NORMAL)

    def disable_clear_button(self):
        """Disable the clear folder button after deletion"""
        self.clear_folder_btn.config(state=tk.DISABLED)
        self.open_folder_btn.config(state=tk.DISABLED)

    def create_rounded_button(self, parent, text, command, bg_color, active_bg_color, width=None):
        """Create a button with simulated rounded corners using styling"""
        button = tk.Button(
            parent,
            text=text,
            font=("Arial", 12, "bold"),
            command=command,
            bd=0,
            fg="white",
            bg=bg_color,
            activebackground=active_bg_color,
            activeforeground="white",
            highlightthickness=0,
            padx=8,
            pady=4,
            width=width,
            relief="flat"
        )
        button.config(relief="groove", borderwidth=0)
        return button

    def create_topic_upload_buttons(self):

        """Create buttons for the EEP Topic Upload tab"""
        # Define button dimensions
        button_width = 22  # characters
        button_height = 1  # lines

        # Common pack options for all buttons
        button_pack_options = {
            'fill': 'x',
            'padx': 10,  # Horizontal padding
            'pady': 6  # Default vertical padding
        }

        # Topic Upload Button - with special top padding of 30
        self.topic_upload_btn = tk.Button(
            self.topic_upload_tab,
            text="EEP Topic Upload",
            font=("Arial", 14, "bold"),
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            activeforeground="white",
            bd=0,
            highlightthickness=0,
            command=self.topic_upload_task.start_topic_upload,
            width=button_width,
            height=button_height
        )
        self.topic_upload_btn.pack(**{**button_pack_options, 'pady': (55, 6)})  # Special top padding of 30

        # All other buttons use the standard padding
        # Run Filter Job Button
        self.run_filter_btn = tk.Button(
            self.topic_upload_tab,
            text="Run Filter Job",
            font=("Arial", 14, "bold"),
            bg="#2196F3",
            fg="white",
            activebackground="#FB8C00",
            activeforeground="white",
            bd=0,
            highlightthickness=0,
            command=self.topic_upload_task.run_filter_job,
            width=button_width,
            height=button_height
        )
        self.run_filter_btn.pack(**button_pack_options)

        # Elastic Index Job Button
        self.elastic_index_btn = tk.Button(
            self.topic_upload_tab,
            text="Run Elastic Index Job",
            font=("Arial", 14, "bold"),
            bg="#2196F3",
            fg="white",
            activebackground="#0b7dda",
            activeforeground="white",
            bd=0,
            highlightthickness=0,
            command=self.topic_upload_task.run_elastic_index_job,
            width=button_width,
            height=button_height
        )
        self.elastic_index_btn.pack(**button_pack_options)

        # View Upload History Button
        self.history_btn = tk.Button(
            self.topic_upload_tab,
            text="View Upload History",
            font=("Arial", 14, "bold"),
            bg="#2196F3",  # Purple color
            fg="white",
            activebackground="#5E35B1",
            activeforeground="white",
            bd=0,
            highlightthickness=0,
            command=self.show_upload_history,
            width=button_width,
            height=button_height
        )
        self.history_btn.pack(**button_pack_options)

        # Open Temporary Files Folder Button
        self.open_folder_btn = tk.Button(
            self.topic_upload_tab,
            text="Open Temporary Files Folder",
            font=("Arial", 14, "bold"),
            bg="#2196F3",
            fg="white",
            activebackground="#00796b",
            activeforeground="white",
            bd=0,
            highlightthickness=0,
            command=self.open_working_folder,
            state=tk.DISABLED,
            width=button_width,
            height=button_height
        )
        self.open_folder_btn.pack(**button_pack_options)

        # Clear Temporary Files Button
        self.clear_folder_btn = tk.Button(
            self.topic_upload_tab,
            text="Clear Temporary Files",
            font=("Arial", 14, "bold"),
            bg="#ff8989",
            fg="white",
            activebackground="#da190b",
            activeforeground="white",
            bd=0,
            highlightthickness=0,
            command=self.topic_upload_task.clear_working_folder,
            state=tk.DISABLED,
            width=button_width,
            height=button_height
        )
        self.clear_folder_btn.pack(**button_pack_options)

        # Update button states
        self.update_topic_upload_button_states()

    def create_teton_export_buttons(self):
        """Create buttons for the Teton Content Export tab"""
        # Define button dimensions
        button_width = 22  # characters
        button_height = 1  # lines

        # Common pack options for all buttons
        button_pack_options = {
            'fill': 'x',
            'padx': 10,  # Horizontal padding
            'pady': 6  # Default vertical padding
        }

        # Start Teton Content Export Button - with special top padding of 30
        self.teton_export_btn = tk.Button(
            self.teton_export_tab,
            text="Start Teton Content Export",
            font=("Arial", 14, "bold"),
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            activeforeground="white",
            bd=0,
            highlightthickness=0,
            command=self.start_teton_export,
            width=button_width,
            height=button_height
        )
        self.teton_export_btn.pack(**{**button_pack_options, 'pady': (55, 6)})

        # Teton Content Export History Button
        self.teton_history_btn = tk.Button(
            self.teton_export_tab,
            text="Teton Content Export History",
            font=("Arial", 14, "bold"),
            bg="#2196F3",
            fg="white",
            activebackground="#5E35B1",
            activeforeground="white",
            bd=0,
            highlightthickness=0,
            command=self.show_teton_history,
            width=button_width,
            height=button_height
        )
        self.teton_history_btn.pack(**button_pack_options)

        # View Exported Files Folder Button
        self.view_exported_btn = tk.Button(
            self.teton_export_tab,
            text="View Exported Files Folder",
            font=("Arial", 14, "bold"),
            bg="#2196F3",
            fg="white",
            activebackground="#00796b",
            activeforeground="white",
            bd=0,
            highlightthickness=0,
            command=self.open_exported_folder,
            state=tk.DISABLED,
            width=button_width,
            height=button_height
        )
        self.view_exported_btn.pack(**button_pack_options)

        # Clear Exported Files Folder Button
        self.clear_exported_btn = tk.Button(
            self.teton_export_tab,
            text="Clear Exported Files Folder",
            font=("Arial", 14, "bold"),
            bg="#ff8989",
            fg="white",
            activebackground="#da190b",
            activeforeground="white",
            bd=0,
            highlightthickness=0,
            command=self.clear_exported_folder,
            state=tk.DISABLED,
            width=button_width,
            height=button_height
        )
        self.clear_exported_btn.pack(**button_pack_options)

        # Update button states
        self.update_teton_export_button_states()

    def update_topic_upload_button_states(self):
        """Update the state of buttons in the topic upload tab"""
        if hasattr(self.topic_upload_task, 'working_folder') and self.topic_upload_task.working_folder:
            self.clear_folder_btn.config(state=tk.NORMAL)
            self.open_folder_btn.config(state=tk.NORMAL)
        else:
            self.clear_folder_btn.config(state=tk.DISABLED)
            self.open_folder_btn.config(state=tk.DISABLED)

    def update_teton_export_button_states(self):
        """Update the state of buttons in the teton export tab"""
        if hasattr(self.teton_export_task, 'export_folder') and self.teton_export_task.export_folder:
            self.clear_exported_btn.config(state=tk.NORMAL)
            self.view_exported_btn.config(state=tk.NORMAL)
        else:
            self.clear_exported_btn.config(state=tk.DISABLED)
            self.view_exported_btn.config(state=tk.DISABLED)

    def open_working_folder(self):
        """Open the working folder in File Explorer"""
        if hasattr(self.topic_upload_task, 'working_folder') and self.topic_upload_task.working_folder:
            try:
                os.startfile(self.topic_upload_task.working_folder)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open folder: {str(e)}")

    def show_upload_history(self):
        """Show the upload history dialog"""
        history = self.topic_upload_task.get_upload_history()
        if history:
            UploadHistoryDialog(self.root, history, self.topic_upload_task.db_file)
        else:
            messagebox.showinfo(
                "No History",
                "No upload history found in the database."
            )

    def start_teton_export(self):
        """Start the Teton content export process"""
        self.teton_export_task.start_teton_export()

    def show_teton_history(self):
        """Show Teton export history"""
        history = self.teton_export_task.get_export_history()
        if history:
            TetonHistoryDialog(self.root, history, self.teton_export_task.db_file)
        else:
            messagebox.showinfo(
                "No History",
                "No Teton export history found."
            )

    def open_exported_folder(self):
        """Open the exported files folder"""
        self.teton_export_task.open_exported_folder()

    def clear_exported_folder(self):
        """Clear the exported files folder"""
        self.teton_export_task.clear_exported_folder()