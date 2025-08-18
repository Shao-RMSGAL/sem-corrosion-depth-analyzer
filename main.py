import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import os


class ImageManipulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Manipulator")
        self.root.geometry("800x600")

        self.original_image = None
        self.display_image = None

        self.crop_var = tk.StringVar(value="0")
        self.tilt_var = tk.DoubleVar(value=0.0)

        self.setup_gui()

        # Bind update events
        self.crop_var.trace_add('write', self.update_image)
        self.tilt_var.trace_add('write', self.update_image)

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
        crop_frame = tk.Frame(controls_frame)
        crop_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(crop_frame, text="Crop from top (pixels):").pack()
        tk.Entry(crop_frame, textvariable=self.crop_var, width=10).pack()

        # Tilt control
        tilt_frame = tk.Frame(controls_frame)
        tilt_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(tilt_frame, text="Tilt (degrees):").pack()
        tk.Scale(tilt_frame, from_=-45, to=45, resolution=0.1,
                 orient=tk.HORIZONTAL, variable=self.tilt_var, length=180).pack()

        # Image display
        canvas_frame = tk.Frame(self.root, bg='gray90')
        canvas_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def load_image(self):
        filepath = filedialog.askopenfilename(
            title="Select TIFF Image",
            filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*.*")]
        )

        if filepath and os.path.exists(filepath):
            try:
                self.original_image = cv2.imread(
                    filepath, cv2.IMREAD_UNCHANGED)
                if self.original_image is None:
                    raise ValueError("Could not load image")

                # Reset controls
                self.crop_var.set("0")
                self.tilt_var.set(0.0)
                self.update_image()
            except Exception:
                messagebox.showerror("Error", "Failed to load image")

    def update_image(self, *args):
        if self.original_image is None:
            return

        try:
            crop_pixels = max(0, int(self.crop_var.get() or 0))
        except ValueError:
            crop_pixels = 0

        img = self.original_image.copy()

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
        if crop_pixels > 0:
            height = img.shape[0]
            if crop_pixels < height:
                img = img[crop_pixels:, :]

        self.display_on_canvas(img)

    def display_on_canvas(self, cv2_image):
        height, width = cv2_image.shape[:2]

        # Scale to fit canvas (max 600x400)
        scale = min(600/width, 400/height, 1.0)

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

