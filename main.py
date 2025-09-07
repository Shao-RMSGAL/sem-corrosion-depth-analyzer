import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import os
from pathlib import Path


class ImageManipulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SEM Corrosion Analyzer")
        self.root.geometry("1920x1080")

        self.original_image = None
        self.display_image = None
        self.analysis_image = None
        self.filepath = ""

        self.crop_var_top = tk.StringVar(value="0")
        self.crop_var_bottom = tk.StringVar(value="0")
        self.crop_var_left = tk.StringVar(value="0")
        self.crop_var_right = tk.StringVar(value="0")
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

    def setup_gui(self):
        # File selection
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10, padx=10, fill=tk.X)
        tk.Button(file_frame, text="Load TIFF Image",
                  command=self.load_image).pack(side=tk.LEFT)

        # Controls
        controls_frame = tk.Frame(self.root)
        controls_frame.pack(pady=10, padx=10, fill=tk.X)

        # Crop control
        crop_frame_top = tk.Frame(controls_frame)
        crop_frame_top.pack(side=tk.LEFT, padx=20)
        tk.Label(crop_frame_top, text="Crop from top (pixels):").pack()
        tk.Entry(crop_frame_top, textvariable=self.crop_var_top, width=10).pack()

        crop_frame_bottom = tk.Frame(controls_frame)
        crop_frame_bottom.pack(side=tk.LEFT, padx=20)
        tk.Label(crop_frame_bottom, text="Crop from bottom (pixels):").pack()
        tk.Entry(crop_frame_bottom,
                 textvariable=self.crop_var_bottom, width=10).pack()

        crop_frame_left = tk.Frame(controls_frame)
        crop_frame_left.pack(side=tk.LEFT, padx=20)
        tk.Label(crop_frame_left, text="Crop from left (pixels):").pack()
        tk.Entry(crop_frame_left,
                 textvariable=self.crop_var_left, width=10).pack()

        crop_frame_right = tk.Frame(controls_frame)
        crop_frame_right.pack(side=tk.LEFT, padx=20)
        tk.Label(crop_frame_right, text="Crop from right (pixels):").pack()
        tk.Entry(crop_frame_right,
                 textvariable=self.crop_var_right, width=10).pack()

        # Threshold control
        threshold_control = tk.Frame(controls_frame)
        threshold_control.pack(side=tk.LEFT)
        tk.Label(threshold_control, text="Threshold pixel value:").pack()
        tk.Scale(threshold_control, from_=0, to=255,
                 orient=tk.HORIZONTAL, variable=self.threshold_value, length=255).pack(fill=tk.X, expand=True)

        # Tilt control
        tilt_frame = tk.Frame(controls_frame)
        tilt_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(tilt_frame, text="Tilt (degrees):").pack()
        tk.Scale(tilt_frame, from_=-45, to=45, resolution=0.1,
                 orient=tk.HORIZONTAL, variable=self.tilt_var, length=900).pack(fill=tk.X, expand=True)

        # Image display
        canvas_frame = tk.Frame(self.root, bg='gray90')
        canvas_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Plot display
        #  canvas_frame = tk.Frame(self.root, bg='gray90')
        #  canvas_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        #  self.canvas = tk.Canvas(canvas_frame, bg='black')
        #  self.canvas.pack(fill=tk.BOTH, expand=True)

        # Save button
        save_button_frame = tk.Frame(self.root, bg='gray90')
        save_button_frame.pack(pady=10, padx=10)
        save_button = tk.Button(
            tilt_frame, text="Save All", command=self.save_all)
        save_button.pack()

    def save_all(self):
        if self.filepath == "":
            return

        print(self.filepath)

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
                title="Select directory to save image",
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

            # Save the image if it exists
            if self.analysis_image is not None:
                # Save as grayscale TIFF image
                save_path = save_dir / "image.tif"

                # Ensure the save directory exists
                save_dir.mkdir(parents=True, exist_ok=True)

                # Save using OpenCV as grayscale
                success = cv2.imwrite(str(save_path), self.analysis_image, [
                                      cv2.IMWRITE_TIFF_COMPRESSION, 1])

                if success:
                    print(f"Image saved successfully to: {save_path}")
                else:
                    print(f"Failed to save image to: {save_path}")
            else:
                print("No analysis image to save.")

        except Exception as e:
            print(f"Error during save operation: {e}")
            # Clean up suggested directory if it was created but save failed
            if suggested_dir.exists() and not any(suggested_dir.iterdir()):
                try:
                    suggested_dir.rmdir()
                except:
                    pass

    def load_image(self):
        self.filepath = filedialog.askopenfilename(
            title="Select TIFF Image",
            filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*.*")]
        )

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
        except ValueError:
            crop_pixels_top = 0
            crop_pixels_bottom = 0
            crop_pixels_left = 0
            crop_pixels_right = 0

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

        self.analysis_image = img
        img_with_mask = self.apply_mask(img)
        self.display_on_canvas(img_with_mask)

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
        img_cpy[mask == 255] = [0, 0, 255]  # Red in RGB format

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


def main():
    root = tk.Tk()
    app = ImageManipulatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
