import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageFilter
import os
import sys
from tkinter.font import Font
from tasks.topic_upload import TopicUploadTask
from ui.dialogs import UploadHistoryDialog


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
        self.root.geometry("800x400")  # Changed to match background image

        # Set application icon
        try:
            icon_path = resource_path(os.path.join("assets", "EEP_512_512.ico"))
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error loading icon: {e}")

        # Task handler
        self.topic_upload_task = TopicUploadTask(
            self.root,
            on_upload_complete=self.enable_buttons_after_upload,
            on_folder_cleared=self.disable_clear_button
        )

        # Remove default title bar
        self.root.overrideredirect(True)

        # Background image (with proper path handling)
        try:
            bg_path = resource_path(os.path.join("assets", "Background.png"))
            self.bg_image = Image.open(bg_path)
            # Resize image to 800x400
            self.bg_image = self.bg_image.resize((800, 400), Image.LANCZOS)
            print(f"Loaded background image from: {bg_path}")
        except Exception as e:
            # Fallback if image not found
            print(f"Error loading background image: {e}")
            self.bg_image = Image.new('RGB', (800, 400), (50, 50, 50))

        # Create gradient overlay
        self.gradient = Image.new('RGBA', (800, 400), (0, 0, 0, 0))
        for y in range(400):
            alpha = int(200 * (1 - y / 400))
            overlay = Image.new('RGBA', (800, 1), (0, 0, 0, alpha))
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

        # Create a dedicated title bar frame
        self.create_title_bar()

        # Create buttons - all in left corner, one under another
        self.create_buttons()

        # Make window draggable
        self.bind_drag_events()

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

    def create_title_bar(self):
        # Create a title bar frame at the top of the window
        self.title_bar = tk.Frame(self.root, bg='#222222', height=36)
        self.title_bar.pack(side="top", fill="x")

        # Try to load and display EEP icon in title bar
        try:
            icon_path = resource_path(os.path.join("assets", "EEP_512_512.ico"))
            icon_image = Image.open(icon_path)
            icon_image = icon_image.resize((24, 24), Image.LANCZOS)
            self.title_icon = ImageTk.PhotoImage(icon_image)
            icon_label = tk.Label(self.title_bar, image=self.title_icon, bg='#222222')
            icon_label.pack(side="left", padx=(5, 0), pady=6)
        except Exception as e:
            print(f"Error loading icon for title bar: {e}")

        # Add application name at the left side
        app_label = tk.Label(
            self.title_bar,
            text="EEP Topic Upload Tool",
            fg="white",
            bg='#222222',
            font=("Arial", 10),
            padx=0,
            pady=5
        )
        app_label.pack(side="left", padx=5)

        # Close button
        self.close_btn = self.create_rounded_button(
            self.title_bar,
            text="×",
            command=self.root.destroy,
            bg_color="#ff5c5c",
            active_bg_color="#ff3c3c",
            width=2
        )
        self.close_btn.pack(side="right", padx=5, pady=6)

        # Minimize button
        self.min_btn = self.create_rounded_button(
            self.title_bar,
            text="_",
            command=self.minimize_window,
            bg_color="#2196F3",
            active_bg_color="#ffa53c",
            width=2
        )
        self.min_btn.pack(side="right", padx=5, pady=6)

    def minimize_window(self):
        self.root.update_idletasks()
        self.root.state('withdrawn')
        self.root.overrideredirect(False)
        self.root.state('iconic')
        self.root.bind("<Map>", self.restore_custom_titlebar)

    def restore_custom_titlebar(self, event=None):
        self.root.unbind("<Map>")
        if self.root.state() == 'normal':
            self.root.overrideredirect(True)
            geometry = self.root.geometry()
            self.root.geometry(geometry)

    def create_buttons(self):
        # Define button dimensions
        button_width = 22  # characters
        button_height = 1  # lines

        # Buttons frame in left corner
        button_frame = tk.Frame(self.root, bg='black')
        button_frame.place(x=0, y=45, width=340, height=450)

        # Common pack options for all buttons
        button_pack_options = {
            'fill': 'x',
            'padx': 18,  # Horizontal padding
            'pady': 9  # Default vertical padding
        }

        # Topic Upload Button - with special top padding of 30
        self.topic_upload_btn = tk.Button(
            button_frame,
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
        self.topic_upload_btn.pack(**{**button_pack_options, 'pady': (30, 9)})  # Special top padding of 30

        # All other buttons use the standard padding
        # Run Filter Job Button
        self.run_filter_btn = tk.Button(
            button_frame,
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
            button_frame,
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
            button_frame,
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
            button_frame,
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
            button_frame,
            text="Clear Temporary Files",
            font=("Arial", 14, "bold"),
            bg="#f44336",
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
        self.update_button_states()

    def open_working_folder(self):
        """Open the working folder in File Explorer"""
        if hasattr(self.topic_upload_task, 'working_folder') and self.topic_upload_task.working_folder:
            try:
                os.startfile(self.topic_upload_task.working_folder)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open folder: {str(e)}")

    def update_button_states(self):
        """Update the state of buttons based on working folder status"""
        if hasattr(self.topic_upload_task, 'working_folder') and self.topic_upload_task.working_folder:
            self.clear_folder_btn.config(state=tk.NORMAL)
            self.open_folder_btn.config(state=tk.NORMAL)
        else:
            self.clear_folder_btn.config(state=tk.DISABLED)
            self.open_folder_btn.config(state=tk.DISABLED)

    def bind_drag_events(self):
        # Make window draggable from the title bar
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<ButtonRelease-1>", self.stop_move)
        self.title_bar.bind("<B1-Motion>", self.on_move)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def on_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def show_upload_history(self):
        """Show the upload history dialog"""
        history = self.topic_upload_task.get_upload_history()
        if history:
            UploadHistoryDialog(self.root, history)
        else:
            messagebox.showinfo(
                "No History",
                "No upload history found in the database."
            )