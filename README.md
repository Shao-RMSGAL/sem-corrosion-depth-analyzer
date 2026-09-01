# SEM Corrosion Analyzer

A desktop tool for measuring corrosion (void/porosity) depth in cross-sectional SEM (Scanning Electron Microscope) images of irradiated or corroded materials.

## What Goes In

- A grayscale (or color) **TIFF image** of a material cross-section, where the top of the image is the original material surface and depth increases downward through the sample.
- A set of user-supplied parameters:
  - **Crop (top/bottom/left/right)** — pixel margins to trim from each edge (e.g. to remove mounting material, edge artifacts, or scale bars).
  - **Tilt (degrees)** — rotates the image to correct for a sample that wasn't imaged perfectly level.
  - **Pixels/μm** — the image's spatial calibration (how many pixels correspond to one micrometer), typically taken from the SEM's scale bar.
  - **Threshold pixel value (0–255)** — the brightness cutoff used to distinguish solid material from voids/pores.
  - **Ignore top pixel rows** — a number of rows at the very top of the (cropped/rotated) image to exclude from analysis, since the original surface can produce false-positive "void" readings.
  - **Corrosion depth threshold (%)** — the void-fraction percentage above which a row is considered "corroded."
  - **Surface depletion threshold (%)** — a second, typically higher, void-fraction percentage used to define a shallower "surface depletion" boundary.

## What Comes Out

- A **processed image** with all detected void pixels highlighted in red.
- A **void-ratio-vs-depth plot**, showing the percentage of void area at each depth into the sample, in micrometers.
- Numeric results:
  - **Total loss ratio** — the overall fraction of the analyzed area classified as void.
  - **Deepest corrosion depth** — the depth of the deepest row whose void fraction exceeds the corrosion depth threshold.
  - **Half-depletion depth** — the depth of the shallowest row whose void fraction drops below the surface depletion threshold.
- A CSV of void ratio by depth, a saved copy of the processed image, the plot as a PNG, and a text file recording the parameters and results used to produce them.

## The Math: How Pixels Are Turned Into Numbers

### 1. Normalization
The raw image intensities are linearly rescaled so the darkest pixel becomes 0 and the brightest becomes 255 (standard 8-bit grayscale):

```
pixel_out = (pixel_in − min) / (max − min) × 255
```

### 2. Rotation (tilt correction)
If a tilt angle θ is specified, every pixel is rotated about the image center using a standard 2D rotation transform, and the canvas is enlarged so no part of the image is clipped. Areas exposed by the rotation (outside the original image bounds) are filled with white (value 255), which is later treated as "not real image data."

### 3. Cropping
The rotated image is trimmed by the specified number of pixel rows/columns from the top, bottom, left, and right, discarding those pixels entirely from further analysis.

### 4. Thresholding (identifying voids)
Each pixel in the cropped, normalized image is compared to the threshold value *T*:

```
if pixel_value < T:  classified as void (mask = 255)
else:                classified as solid material (mask = 0)
```

This is an *inverse* threshold — because voids/pores in SEM cross-sections typically appear darker than solid material, pixels *darker* than the threshold are flagged as void.

Rows within the "ignore top pixel rows" count are then forced to mask = 0 (never counted as void), since the true material surface can otherwise register as a false void.

### 5. Void ratio per row (depth profile)
For each horizontal row of pixels (each row corresponds to one depth into the material), the void ratio is:

```
void_ratio(row) = (# of void pixels in row) / (# of valid pixels in row)
```

where "valid pixels" excludes any pixels with value exactly 255 in the cropped analysis image (these are treated as background/rotation-fill pixels rather than real material, and are excluded from both numerator and denominator).

### 6. Converting rows to physical depth
Row index is converted to a depth in micrometers using the calibration factor:

```
depth (μm) = row_index / (pixels per μm)
```

Row 0 is the top of the (cropped) image; the deepest row corresponds to the greatest depth analyzed.

### 7. Deepest corrosion depth
Starting from the bottom of the image (deepest point) and scanning upward toward the surface, the tool finds the *first* row whose void ratio exceeds the corrosion depth threshold. That row's depth (in μm) is reported as the deepest corrosion depth — i.e., the greatest depth at which the material is still measurably void-affected above the noise floor.

### 8. Half-depletion depth
Scanning from the surface (row 0) downward, the tool finds the first row whose void ratio drops *below* the surface depletion threshold. That row's depth is reported as the half-depletion depth — the depth at which the material transitions from heavily voided (near-surface) to comparatively intact.

### 9. Total loss ratio
The overall fraction of void pixels across the entire cropped, thresholded image:

```
total_loss_ratio = (total void pixels) / (total pixels in mask)
```

reported as a percentage.

## Doing It by Hand

Given a cross-sectional grayscale image, a pixel/μm calibration, and a brightness threshold, you could reproduce these results manually by:
1. Cropping and (if needed) rotating the image so the surface is horizontal and at the top.
2. For each row, counting how many pixels fall below the threshold brightness (voids) versus the total non-background pixels in that row, and dividing to get a percentage.
3. Plotting that percentage against depth (row index divided by pixels/μm).
4. Reading off the depth where the curve last exceeds your corrosion threshold (scanning from the bottom) and where it first drops below your depletion threshold (scanning from the top).
5. Summing all void pixels in the image and dividing by the total pixel count for the overall loss ratio.
