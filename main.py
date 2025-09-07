import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import os
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Default number of pixels per micrometer.
PIX_PER_UM = 14.8
DEFAULT_CORROSION_THRESHOLD = 5.0
DEFAULT_TOP_PIXEL_IGNORE = 100


class ImageManipulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SEM Corrosion Analyzer")
        self.root.geometry("1920x1080")

        self.original_image = None
        self.display_image = None
        self.analysis_image = None

        # Entries and sliders.
        self.crop_top_entry = None
        self.crop_bottom_entry = None
        self.crop_left_entry = None
        self.crop_right_entry = None
        self.crop_pixels_per_um_entry = None
        self.ignore_top_pixel_rows_entry = None
        self.corrosion_depth_threshold_entry = None
        self.threshold_slider = None
        self.tilt_slider = None

        self.mask = np.empty((0, 0), dtype=np.uint8)
        self.void_ratio = np.empty(0, dtype=np.float64)
        self.filepath = ""
        self.deepest_corrosion = 0.0
        self.total_loss_ratio = 0.0
        self.top_bottom_distance = tk.StringVar(value="0.0")

        self.crop_var_top = tk.StringVar(value="0")
        self.crop_var_bottom = tk.StringVar(value="0")
        self.crop_var_left = tk.StringVar(value="0")
        self.crop_var_right = tk.StringVar(value="0")
        self.crop_var_right = tk.StringVar(value="0")
        self.filepath_var = tk.StringVar(value="")
        self.ignore_top_rows = tk.StringVar(
            value=str(DEFAULT_TOP_PIXEL_IGNORE))
        self.corrosion_depth_threshold = tk.StringVar(
            value=str(DEFAULT_CORROSION_THRESHOLD))
        self.pixels_per_micrometer = tk.StringVar(value=str(PIX_PER_UM))
        self.tilt_var = tk.DoubleVar(value=0.0)
        self.threshold_value = tk.IntVar(value=0)

        self.setup_gui()

        # Bind update events
        self.crop_var_top.trace_add('write', self.update_image)
        self.crop_var_bottom.trace_add('write', self.update_image)
        self.crop_var_left.trace_add('write', self.update_image)
        self.crop_var_right.trace_add('write', self.update_image)
        self.tilt_var.trace_add('write', self.update_image)
        self.threshold_value.trace_add('write', self.update_image)
        self.pixels_per_micrometer.trace_add('write', self.update_image)
        self.ignore_top_rows.trace_add('write', self.update_image)
        self.corrosion_depth_threshold.trace_add('write', self.update_image)

    def setup_gui(self):
        # Main container with padding
        main_container = tk.Frame(self.root, bg='lightgray')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top controls section
        controls_section = tk.Frame(main_container, bg='lightgray')
        controls_section.pack(fill=tk.X, pady=(0, 10))

        # Crop and measurement controls frame with decorative border
        crop_measurement_frame = tk.LabelFrame(
            controls_section,
            text="Image Processing Controls",
            font=('Arial', 10, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=10,
            pady=5
        )
        crop_measurement_frame.pack(fill=tk.X, pady=(0, 10))

        # Crop controls row
        crop_row = tk.Frame(crop_measurement_frame)
        crop_row.pack(fill=tk.X, pady=5)

        # Crop from top
        crop_frame_top = tk.Frame(crop_row)
        crop_frame_top.pack(side=tk.LEFT, padx=10)
        tk.Label(crop_frame_top, text="Crop Top:", font=('Arial', 9)).pack()
        self.crop_top_entry = tk.Entry(crop_frame_top, textvariable=self.crop_var_top, width=8,
                                       relief=tk.SUNKEN, bd=1).pack()

        # Crop from bottom
        crop_frame_bottom = tk.Frame(crop_row)
        crop_frame_bottom.pack(side=tk.LEFT, padx=10)
        tk.Label(crop_frame_bottom, text="Crop Bottom:",
                 font=('Arial', 9)).pack()
        self.crop_bottom_entry = tk.Entry(crop_frame_bottom, textvariable=self.crop_var_bottom, width=8,
                                          relief=tk.SUNKEN, bd=1).pack()

        # Crop from left
        crop_frame_left = tk.Frame(crop_row)
        crop_frame_left.pack(side=tk.LEFT, padx=10)
        tk.Label(crop_frame_left, text="Crop Left:", font=('Arial', 9)).pack()
        self.crop_left_entry = tk.Entry(crop_frame_left, textvariable=self.crop_var_left, width=8,
                                        relief=tk.SUNKEN, bd=1).pack()

        # Crop from right
        crop_frame_right = tk.Frame(crop_row)
        crop_frame_right.pack(side=tk.LEFT, padx=10)
        tk.Label(crop_frame_right, text="Crop Right:",
                 font=('Arial', 9)).pack()
        self.crop_right_entry = tk.Entry(crop_frame_right, textvariable=self.crop_var_right, width=8,
                                         relief=tk.SUNKEN, bd=1).pack()

        # Separator line
        separator = tk.Frame(crop_row, width=2, bg='gray',
                             relief=tk.SUNKEN, bd=1)
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=20)

        # Pixels per micrometer in the same row but separate section
        pixels_frame = tk.Frame(crop_row)
        pixels_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(pixels_frame, text="Pixels/μm:",
                 font=('Arial', 9, 'bold')).pack()
        self.crop_pixels_per_um_entry = tk.Entry(pixels_frame, textvariable=self.pixels_per_micrometer, width=10,
                                                 relief=tk.SUNKEN, bd=1, font=('Arial', 9)).pack()

        # Ignore top pixel rows, irradiation surface may cause false positives.
        pixels_ignore = tk.Frame(crop_row)
        pixels_ignore.pack(side=tk.LEFT, padx=20)
        tk.Label(pixels_ignore, text="Ignore top pixel rows",
                 font=('Arial', 9, 'bold')).pack()
        self.ignore_top_pixel_rows_entry = tk.Entry(pixels_ignore, textvariable=self.ignore_top_rows, width=10,
                                                    relief=tk.SUNKEN, bd=1, font=('Arial', 9)).pack()

        # Minimum threshold to consider the deepest corrosion depth
        min_threshold = tk.Frame(crop_row)
        min_threshold.pack(side=tk.LEFT, padx=20)
        tk.Label(min_threshold, text="Corrosion depth threshold (%)",
                 font=('Arial', 9, 'bold')).pack()
        self.corrosion_depth_threshold_entry = tk.Entry(min_threshold, textvariable=self.corrosion_depth_threshold, width=10,
                                                        relief=tk.SUNKEN, bd=1, font=('Arial', 9)).pack()

        # Top-bottom distance information
        pixels_ignore = tk.Frame(crop_row)
        pixels_ignore.pack(side=tk.LEFT, padx=20)
        tk.Label(pixels_ignore, text="Crop distance from top to bottom (μm)",
                 font=('Arial', 9, 'bold')).pack()
        tk.Label(pixels_ignore, textvariable=self.top_bottom_distance, width=10,
                 relief=tk.SUNKEN, bd=1, font=('Arial', 9)).pack()

        # Filepath
        pixels_ignore = tk.Frame(crop_row)
        pixels_ignore.pack(side=tk.LEFT, padx=20)
        tk.Label(pixels_ignore, text="File",
                 font=('Arial', 9, 'bold')).pack()
        tk.Label(pixels_ignore, textvariable=self.filepath_var, width=100,
                 relief=tk.SUNKEN, bd=1, font=('Arial', 9)).pack()

        # Threshold control frame
        threshold_frame = tk.LabelFrame(
            controls_section,
            text="Threshold Control",
            font=('Arial', 10, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=10,
            pady=5
        )
        threshold_frame.pack(fill=tk.X, pady=(0, 5))

        threshold_container = tk.Frame(threshold_frame)
        threshold_container.pack(fill=tk.X, pady=5)
        tk.Label(threshold_container, text="Threshold Pixel Value:",
                 font=('Arial', 9)).pack(side=tk.LEFT)
        self.threshold_slider = tk.Scale(threshold_container, from_=0, to=255, orient=tk.HORIZONTAL,
                                         variable=self.threshold_value, length=300, relief=tk.SUNKEN,
                                         bd=1).pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)

        # Tilt control frame
        tilt_frame = tk.LabelFrame(
            controls_section,
            text="Tilt Adjustment",
            font=('Arial', 10, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=10,
            pady=5
        )
        tilt_frame.pack(fill=tk.X, pady=(0, 10))

        tilt_container = tk.Frame(tilt_frame)
        tilt_container.pack(fill=tk.X, pady=5)
        tk.Label(tilt_container, text="Tilt (degrees):",
                 font=('Arial', 9)).pack(side=tk.LEFT)
        self.tilt_slider = tk.Scale(tilt_container, from_=-45, to=45, resolution=0.1,
                                    orient=tk.HORIZONTAL, variable=self.tilt_var, length=400,
                                    relief=tk.SUNKEN, bd=1).pack(side=tk.LEFT, padx=(10, 0),
                                                                 fill=tk.X, expand=True)

        # Paned window for side-by-side display
        paned_window = tk.PanedWindow(main_container, orient=tk.HORIZONTAL,
                                      relief=tk.RAISED, bd=2, sashwidth=5,
                                      bg='darkgray')
        paned_window.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Left pane - Image display
        canvas_frame = tk.LabelFrame(paned_window, text="Image Display",
                                     font=('Arial', 10, 'bold'),
                                     relief=tk.RAISED, bd=2, bg='gray95')
        self.canvas = tk.Canvas(
            canvas_frame, bg='black', relief=tk.SUNKEN, bd=1)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        paned_window.add(canvas_frame, minsize=300)

        # Right pane - Plot display
        plot_frame = tk.LabelFrame(paned_window, text="Analysis Plot",
                                   font=('Arial', 10, 'bold'),
                                   relief=tk.RAISED, bd=2, bg='gray95')

        # Create matplotlib figure and canvas
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.plot_canvas = FigureCanvasTkAgg(self.fig, plot_frame)
        self.plot_canvas.draw()

        # Add plot_canvas to tkinter window
        plot_widget = self.plot_canvas.get_tk_widget()
        plot_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add toolbar
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar_frame = tk.Frame(plot_frame, relief=tk.SUNKEN, bd=1)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.toolbar = NavigationToolbar2Tk(self.plot_canvas, toolbar_frame)
        self.toolbar.update()

        paned_window.add(plot_frame, minsize=300)

        # Set initial 50-50 split (adjust based on window width)
        self.root.update_idletasks()

        # Bottom buttons frame
        buttons_frame = tk.Frame(main_container, bg='lightgray')
        buttons_frame.pack(fill=tk.X, pady=(5, 0))

        # Create a centered frame for buttons
        button_container = tk.Frame(buttons_frame, bg='lightgray')
        button_container.pack()

        # Load and Save buttons with improved styling
        load_button = tk.Button(
            button_container,
            text="📁 Load TIFF Image",
            command=self.load_image,
            font=('Arial', 10, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=20,
            pady=5,
            bg='lightblue',
            activebackground='deepskyblue'
        )
        load_button.pack(side=tk.LEFT, padx=10)

        save_button = tk.Button(
            button_container,
            text="💾 Save All",
            command=self.save_all,
            font=('Arial', 10, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=20,
            pady=5,
            bg='lightgreen',
            activebackground='limegreen'
        )
        save_button.pack(side=tk.LEFT, padx=10)

        # Pick some nicer colors.
        load_button = tk.Button(
            button_container,
            text="Load another file",
            command=self.load,
            font=('Arial', 10, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=20,
            pady=5,
            bg='orange',
            activebackground='limegreen'
        )
        load_button.pack(side=tk.LEFT, padx=10)

        self.plot_sine()

        # TODO: Remove when plotting is implemented properly.
    def plot_sine(self):
        self.ax.clear()
        x = np.linspace(0, 2*np.pi, 100)
        y = np.sin(x)
        self.ax.plot(x, y, 'b-', linewidth=2, label='sin(x)')
        self.ax.set_xlabel('X axis')
        self.ax.set_ylabel('Y axis')
        self.ax.set_title('Placeholder plot')
        self.ax.grid(True, alpha=0.3)
        self.ax.legend()
        self.plot_canvas.draw()

    def save_all(self):
        if self.filepath == "":
            return

        # Create a directory called "output" in the local directory, if it doesn't already exist
        output_dir = Path("./output")
        output_dir.mkdir(exist_ok=True)

        # Extract filename without extension from self.filepath
        filepath_obj = Path(self.filepath)
        filename_without_ext = filepath_obj.stem

        # Create suggested directory path
        suggested_dir = output_dir / filename_without_ext

        try:
            # Create the suggested directory
            suggested_dir.mkdir(exist_ok=True)

            # Prompt the user to save the image using tkinter file dialog
            print(f"Suggested save directory: {suggested_dir}")
            selected_dir = filedialog.askdirectory(
                title="Select directory to save analysis results",
                initialdir=str(suggested_dir)
            )

            if not selected_dir:  # User cancelled
                # Delete the created directory since user didn't use it
                if suggested_dir.exists() and not any(suggested_dir.iterdir()):
                    suggested_dir.rmdir()
                print("Save cancelled.")
                return

            save_dir = Path(selected_dir)

            # Delete the suggested directory if it's empty and user picked different path
            if suggested_dir != save_dir and suggested_dir.exists() and not any(suggested_dir.iterdir()):
                suggested_dir.rmdir()

            # Ensure the save directory exists
            save_dir.mkdir(parents=True, exist_ok=True)

            # Save the processed image if it exists
            if self.analysis_image is not None:
                # Save as grayscale TIFF image with modified filename
                processed_filename = f"{filename_without_ext}_processed.tif"
                save_path = save_dir / processed_filename

                # Save using OpenCV as grayscale
                success = cv2.imwrite(str(save_path), self.analysis_image, [
                                      cv2.IMWRITE_TIFF_COMPRESSION, 1])

                if success:
                    print(
                        f"Processed image saved successfully to: {save_path}")
                else:
                    print(f"Failed to save processed image to: {save_path}")
            else:
                print("No analysis image to save.")

            # Save the display image (with mask overlay)
            if hasattr(self, 'display_image') and self.display_image is not None:
                display_filename = f"{filename_without_ext}_display.png"
                display_save_path = save_dir / display_filename

                # Get the PIL image from the PhotoImage
                # We need to recreate the display image since PhotoImage doesn't have a direct save method
                if self.analysis_image is not None:
                    img_with_mask = self.apply_mask(self.analysis_image)
                    if len(img_with_mask.shape) == 3:
                        img_with_mask_rgb = cv2.cvtColor(
                            img_with_mask, cv2.COLOR_BGR2RGB)
                    else:
                        img_with_mask_rgb = img_with_mask

                    display_img = Image.fromarray(img_with_mask_rgb)
                    display_img.save(str(display_save_path))
                    print(
                        f"Display image saved successfully to: {display_save_path}")

            # Save the void ratio data
            if hasattr(self, 'void_ratio') and len(self.void_ratio) > 0:
                void_ratio_filename = f"{filename_without_ext}_void_ratio.csv"
                void_ratio_path = save_dir / void_ratio_filename

                # Create depth array in micrometers
                try:
                    pix_per_um = max(
                        0, float(self.pixels_per_micrometer.get() or PIX_PER_UM))
                except ValueError:
                    pix_per_um = PIX_PER_UM

                height = len(self.void_ratio)
                depth_um = np.arange(height) / pix_per_um

                # Save as CSV with headers
                # Convert to percentage
                data = np.column_stack((depth_um, self.void_ratio * 100))
                np.savetxt(str(void_ratio_path), data, delimiter=',',
                           header='Depth_um,Void_Ratio_Percent', comments='', fmt='%.6f')
                print(
                    f"Void ratio data saved successfully to: {void_ratio_path}")

            # Save the plot
            if hasattr(self, 'fig') and self.fig is not None:
                plot_filename = f"{filename_without_ext}_plot.png"
                plot_path = save_dir / plot_filename
                self.fig.savefig(str(plot_path), dpi=300, bbox_inches='tight')
                print(f"Plot saved successfully to: {plot_path}")

            # Save analysis parameters and results
            params_filename = f"{filename_without_ext}_analysis_params.txt"
            params_path = save_dir / params_filename

            try:
                pix_per_um = float(
                    self.pixels_per_micrometer.get() or PIX_PER_UM)
                ignore_rows = int(self.ignore_top_rows.get()
                                  or DEFAULT_TOP_PIXEL_IGNORE)
                corr_threshold = float(
                    self.corrosion_depth_threshold.get() or DEFAULT_CORROSION_THRESHOLD)
            except ValueError:
                pix_per_um = PIX_PER_UM
                ignore_rows = DEFAULT_TOP_PIXEL_IGNORE
                corr_threshold = DEFAULT_CORROSION_THRESHOLD

            with open(str(params_path), 'w') as f:
                f.write("SEM Corrosion Analysis Parameters and Results\n")
                f.write("=" * 50 + "\n\n")

                # Source information
                f.write("SOURCE INFORMATION:\n")
                f.write(f"Original image file: {self.filepath}\n")
                f.write(f"Analysis date: {Path().cwd()}\n\n")

                # Processing parameters
                f.write("PROCESSING PARAMETERS:\n")
                f.write(f"Crop top (pixels): {self.crop_var_top.get()}\n")
                f.write(
                    f"Crop bottom (pixels): {self.crop_var_bottom.get()}\n")
                f.write(f"Crop left (pixels): {self.crop_var_left.get()}\n")
                f.write(f"Crop right (pixels): {self.crop_var_right.get()}\n")
                f.write(f"Tilt angle (degrees): {self.tilt_var.get()}\n")
                f.write(f"Threshold value: {self.threshold_value.get()}\n")
                f.write(f"Pixels per micrometer: {pix_per_um}\n")
                f.write(f"Ignore top pixel rows: {ignore_rows}\n")
                f.write(f"Corrosion depth threshold (%): {corr_threshold}\n\n")

                # Analysis results
                f.write("ANALYSIS RESULTS:\n")
                f.write(
                    f"Top to bottom distance (μm): {self.top_bottom_distance.get()}\n")
                f.write(
                    f"Deepest corrosion depth (μm): {self.deepest_corrosion:.3f}\n")
                f.write(
                    f"Total loss ratio (%): {self.total_loss_ratio * 100:.3f}\n")

                if self.analysis_image is not None:
                    f.write(
                        f"Final image dimensions: {self.analysis_image.shape[1]} x {self.analysis_image.shape[0]} pixels\n")

            print(f"Analysis parameters saved successfully to: {params_path}")

            messagebox.showinfo(
                "Save Complete", f"All analysis files saved to:\n{save_dir}")

        except Exception as e:
            print(f"Error during save operation: {e}")
            messagebox.showerror(
                "Save Error", f"Error during save operation: {e}")
            # Clean up suggested directory if it was created but save failed
            if suggested_dir.exists() and not any(suggested_dir.iterdir()):
                try:
                    suggested_dir.rmdir()
                except:
                    pass

    def load(self):
        """Load analysis parameters from a previously saved analysis"""
        params_file = filedialog.askopenfilename(
            title="Select Analysis Parameters File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not params_file or not os.path.exists(params_file):
            return

        try:
            # Parse the parameters file
            params = {}
            original_filepath = ""

            with open(params_file, 'r') as f:
                lines = f.readlines()

            # Extract parameters from the file
            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    # Map file keys to parameter names
                    if key == "Original image file":
                        original_filepath = value
                    elif key == "Crop top (pixels)":
                        params['crop_top'] = value
                    elif key == "Crop bottom (pixels)":
                        params['crop_bottom'] = value
                    elif key == "Crop left (pixels)":
                        params['crop_left'] = value
                    elif key == "Crop right (pixels)":
                        params['crop_right'] = value
                    elif key == "Tilt angle (degrees)":
                        params['tilt'] = value
                    elif key == "Threshold value":
                        params['threshold'] = value
                    elif key == "Pixels per micrometer":
                        params['pixels_per_um'] = value
                    elif key == "Ignore top pixel rows":
                        params['ignore_top'] = value
                    elif key == "Corrosion depth threshold (%)":
                        params['corr_threshold'] = value

            # Check if original image file exists
            if original_filepath and os.path.exists(original_filepath):
                # Load the original image
                self.filepath = original_filepath
                self.filepath_var.set(Path(self.filepath).stem)

                try:
                    self.original_image = cv2.imread(
                        self.filepath, cv2.IMREAD_UNCHANGED)
                    if self.original_image is None:
                        raise ValueError("Could not load image")

                    print(f"Loaded image: {self.filepath}")
                    print(f"Shape: {self.original_image.shape}")
                    print(f"Data type: {self.original_image.dtype}")

                except Exception as e:
                    messagebox.showerror(
                        "Error", f"Failed to load original image: {e}")
                    return
            else:
                # Ask user to locate the original image
                messagebox.showwarning("Original Image Not Found",
                                       f"Original image not found at: {original_filepath}\n"
                                       "Please select the original image file.")

                new_filepath = filedialog.askopenfilename(
                    title="Select Original TIFF Image",
                    filetypes=[("TIFF files", "*.tiff *.tif"),
                               ("All files", "*.*")]
                )

                if not new_filepath:
                    return

                self.filepath = new_filepath
                self.filepath_var.set(Path(self.filepath).stem)

                try:
                    self.original_image = cv2.imread(
                        self.filepath, cv2.IMREAD_UNCHANGED)
                    if self.original_image is None:
                        raise ValueError("Could not load image")
                    print(f"Loaded image: {self.filepath}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load image: {e}")
                    return

            # Set all the parameters in the GUI
            self.crop_var_top.set(params.get('crop_top', '0'))
            self.crop_var_bottom.set(params.get('crop_bottom', '0'))
            self.crop_var_left.set(params.get('crop_left', '0'))
            self.crop_var_right.set(params.get('crop_right', '0'))

            try:
                self.tilt_var.set(float(params.get('tilt', '0.0')))
            except ValueError:
                self.tilt_var.set(0.0)

            try:
                self.threshold_value.set(int(params.get('threshold', '0')))
            except ValueError:
                self.threshold_value.set(0)

            self.pixels_per_micrometer.set(
                params.get('pixels_per_um', str(PIX_PER_UM)))
            self.ignore_top_rows.set(params.get(
                'ignore_top', str(DEFAULT_TOP_PIXEL_IGNORE)))
            self.corrosion_depth_threshold.set(params.get(
                'corr_threshold', str(DEFAULT_CORROSION_THRESHOLD)))

            # Update the image display with the loaded parameters
            self.update_image()

            messagebox.showinfo(
                "Load Complete", f"Analysis parameters loaded successfully from:\n{params_file}")
            print(f"Parameters loaded from: {params_file}")

        except Exception as e:
            messagebox.showerror(
                "Load Error", f"Error loading parameters: {e}")
            print(f"Error loading parameters: {e}")

    def load_image(self):
        self.filepath = filedialog.askopenfilename(
            title="Select TIFF Image",
            filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*.*")]
        )
        self.filepath_var.set(Path(self.filepath).stem)

        if self.filepath and os.path.exists(self.filepath):
            try:
                self.original_image = cv2.imread(
                    self.filepath, cv2.IMREAD_UNCHANGED)
                print(f"Shape: {self.original_image.shape}")
                print(f"Data type: {self.original_image.dtype}")
                print(f"Channels: {len(self.original_image.shape)}")
                if self.original_image is None:
                    raise ValueError("Could not load image")

                # Reset controls
                self.crop_var_top.set("0")
                self.crop_var_bottom.set("0")
                self.crop_var_left.set("0")
                self.crop_var_right.set("0")
                self.tilt_var.set(0.0)
                self.update_image()
            except Exception:
                messagebox.showerror("error", "failed to load image")

    def update_image(self, *args):
        if self.original_image is None:
            return

        try:
            crop_pixels_top = max(0, int(self.crop_var_top.get() or 0))
            crop_pixels_bottom = max(0, int(self.crop_var_bottom.get() or 0))
            crop_pixels_left = max(0, int(self.crop_var_left.get() or 0))
            crop_pixels_right = max(0, int(self.crop_var_right.get() or 0))
        except ValueError as e:
            crop_pixels_top = 0
            crop_pixels_bottom = 0
            crop_pixels_left = 0
            crop_pixels_right = 0
            messagebox.showerror("error", f"Conversion failed. {e}")

        img = cv2.normalize(self.original_image.copy(), None,
                            0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

        #  img_cpy = cv2.normalize(
        #      img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

        # Apply rotation
        if self.tilt_var.get() != 0:
            height, width = img.shape[:2]
            center = (width // 2, height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(
                center, self.tilt_var.get(), 1.0)

            cos = abs(rotation_matrix[0, 0])
            sin = abs(rotation_matrix[0, 1])
            new_width = int((height * sin) + (width * cos))
            new_height = int((height * cos) + (width * sin))

            rotation_matrix[0, 2] += (new_width / 2) - center[0]
            rotation_matrix[1, 2] += (new_height / 2) - center[1]

            # Set border value based on image type
            if len(img.shape) == 3:
                # Color image - use white for all channels
                border_value = (255, 255, 255)
            else:
                # Grayscale image
                border_value = 255

            img = cv2.warpAffine(img, rotation_matrix, (new_width, new_height),
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=border_value)

        # Apply crop
        if crop_pixels_top > 0:
            height = img.shape[0]
            if crop_pixels_top < height:
                img = img[crop_pixels_top:, :]
        if crop_pixels_bottom > 0:
            height = img.shape[0]
            if crop_pixels_bottom < height:
                img = img[:height - crop_pixels_bottom, :]
        if crop_pixels_left > 0:
            width = img.shape[1]
            if crop_pixels_left < width:
                img = img[:, crop_pixels_left:]
        if crop_pixels_right > 0:
            width = img.shape[1]
            if crop_pixels_right < width:
                img = img[:, :width - crop_pixels_right]

        final_height = img.shape[0]

        try:
            pix_per_um = max(0, float(self.pixels_per_micrometer.get() or 0))
        except ValueError as e:
            pix_per_um = PIX_PER_UM
            messagebox.showerror("error", f"Conversion failed. {e}")

        top_bottom_string = f"{final_height / pix_per_um:.3g}"
        self.top_bottom_distance.set(top_bottom_string)
        self.analysis_image = img
        img_with_mask = self.apply_mask(img)
        self.display_on_canvas(img_with_mask)
        self.process_data()

    def apply_mask(self, img):
        if img is None:
            raise ValueError(f"Could not load analysis image.")

        img_cpy = cv2.normalize(
            img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        _, mask = cv2.threshold(
            img_cpy, self.threshold_value.get(), 255, cv2.THRESH_BINARY_INV)

        # Convert to RGB if the image is grayscale
        if len(img_cpy.shape) == 2:
            img_cpy = cv2.cvtColor(img_cpy, cv2.COLOR_GRAY2RGB)
        elif len(img_cpy.shape) == 3 and img_cpy.shape[2] == 3:
            # Convert from BGR to RGB if it's a color image
            img_cpy = cv2.cvtColor(img_cpy, cv2.COLOR_BGR2RGB)

        # Apply red overlay where mask is 255 (mask regions)

        try:
            ignore_rows = max(0, int(self.ignore_top_rows.get() or 0))
        except ValueError as e:
            ignore_rows = 0
            messagebox.showerror("error", f"Conversion failed. {e}")

        mask[:ignore_rows, :] = 0
        img_cpy[mask == 255] = [0, 0, 255]  # Red in RGB format

        self.mask = mask
        return img_cpy

    def display_on_canvas(self, cv2_image):

        height, width = cv2_image.shape[:2]

        scale = min(1920/width, 1080/height, 1.0)

        if scale < 1.0:
            new_width = int(width * scale)
            new_height = int(height * scale)
            cv2_image = cv2.resize(cv2_image, (new_width, new_height))
            height, width = new_height, new_width

        # Convert OpenCV image to PIL format properly
        if len(cv2_image.shape) == 3:
            # Color image - convert BGR to RGB
            cv2_image_rgb = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        else:
            # Grayscale image
            cv2_image_rgb = cv2_image

        # Ensure proper data type (8-bit unsigned integer)
        if cv2_image_rgb.dtype != np.uint8:
            # Normalize to 0-255 range if needed
            cv2_image_rgb = cv2_image_rgb.astype(np.float32)
            cv2_image_rgb = ((cv2_image_rgb - cv2_image_rgb.min()) /
                             (cv2_image_rgb.max() - cv2_image_rgb.min()) * 255).astype(np.uint8)

        img = Image.fromarray(cv2_image_rgb)
        self.display_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        x = canvas_width // 2
        y = canvas_height // 2

        self.canvas.create_image(
            x, y, anchor=tk.CENTER, image=self.display_image)

    def process_data(self):
        # Get mask dimensions
        if self.mask is None:
            return

        height, width = self.mask.shape

        # Initialize array to store void ratios for each row
        self.void_ratio = np.zeros(height)

        if self.analysis_image is None:
            return

        # Process rows from bottom up (highest index to lowest)
        for i in range(height):
            row_index = height - 1 - i  # Bottom-up indexing
            mask_row = self.mask[row_index, :]
            analysis_row = self.analysis_image[row_index, :]

            # Calculate ratio of 255 pixels to valid pixels in the row
            white_pixels = np.sum(mask_row == 255)

            # Exclude pixels where analysis_image has value 255
            excluded_pixels = np.sum(analysis_row == 255)
            total_pixels = width - excluded_pixels

            # Handle case where all pixels are excluded
            if total_pixels > 0:
                ratio = white_pixels / total_pixels
            else:
                ratio = 0

            # Store in void_ratio array
            self.void_ratio[i] = ratio
        try:
            pix_per_um = max(0, float(self.pixels_per_micrometer.get() or 0))
            corrosion_threshold = max(
                0, float(self.corrosion_depth_threshold.get() or 0)) / 100
        except ValueError as e:
            pix_per_um = PIX_PER_UM
            corrosion_threshold = DEFAULT_CORROSION_THRESHOLD / 100
            messagebox.showerror("error", f"Conversion failed. {e}")

        # Find deepest row (from bottom up) with ratio > 1%
        self.deepest_corrosion = None
        for i, ratio in enumerate(reversed(self.void_ratio)):
            if ratio > corrosion_threshold:
                # Convert to actual depth and scale by pixels per micrometer
                idx = self.void_ratio.size - i
                self.deepest_corrosion = idx / pix_per_um
                break

        # If no row found with ratio > 1%, set to 0
        if self.deepest_corrosion is None:
            self.deepest_corrosion = 0

        # Calculate overall ratio of 255 pixels to total pixels
        total_white_pixels = np.sum(self.mask == 255)
        total_pixels = self.mask.size
        self.total_loss_ratio = total_white_pixels / total_pixels
        self.update_plot()

    def update_plot(self, *args):
        self.ax.clear()

        # Create x-axis in micrometers (depth from surface)
        height = len(self.void_ratio)
        try:
            pix_per_um = max(0, float(self.pixels_per_micrometer.get() or 0))
            corrosion_threshold = max(
                0, float(self.corrosion_depth_threshold.get() or 0))
        except ValueError as e:
            pix_per_um = PIX_PER_UM
            corrosion_threshold = DEFAULT_CORROSION_THRESHOLD
            messagebox.showerror("error", f"Conversion failed. {e}")

        x = np.arange(height) / pix_per_um

        # Convert void ratio to percentage
        y = self.void_ratio * 100

        # Plot the data
        self.ax.plot(x, y, 'r-', linewidth=2, label='Void Ratio')

        # Add horizontal line at threshold
        self.ax.axhline(y=corrosion_threshold, color='k', linestyle='--',
                        alpha=0.7, label=f'{corrosion_threshold}% Threshold')

        # Mark deepest corrosion point if it exists
        if self.deepest_corrosion > 0:
            self.ax.axvline(x=self.deepest_corrosion, color='g', linestyle='--',
                            alpha=0.7, label=f'Deepest Corrosion: {self.deepest_corrosion:.2f} μm')

        # Set labels and title
        self.ax.set_xlabel('Depth (micrometers)')
        self.ax.set_ylabel('Void Ratio (%)')
        self.ax.set_title(
            f'Void Ratio vs Depth (Total Loss: {self.total_loss_ratio*100:.2f}%)')

        # Add grid and legend
        self.ax.grid(True, alpha=0.3)
        self.ax.legend()

        # Refresh the plot
        self.plot_canvas.draw()


def main():
    root = tk.Tk()
    app = ImageManipulatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
