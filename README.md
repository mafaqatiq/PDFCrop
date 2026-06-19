# PDF Precise Cropper

A sleek, lightweight, interactive desktop application to crop single-page PDF files visually with high precision. Built in Python using standard `tkinter` for the GUI, `pymupdf` (fitz) for PDF rendering and cropping, and `Pillow` for image compositing.

Features a modern Light Slate & Teal interface designed to feel like a premium web application.

---

## Key Features

- **Translucent Dimming Overlay**: Excluded regions are automatically masked with a soft translucent slate-grey overlay, making the active crop region stand out in high contrast.
- **Precision Bounding Controls**: Features an interactive crop box with 8 clickable resize handles (corners and midpoints) and drag-to-move capabilities.
- **Compensation for Rotation**: Seamlessly adjusts coordinates using PDF derotation matrices, ensuring rotated PDF documents crop accurately.
- **Real-Time Coordinates Panel**: Displays current selection size and position dynamically in multiple units:
  - **Points (pt)**: Native PDF dimensions.
  - **Inches (")**: Standard document metrics.
  - **Millimeters (mm)**: Accurate international print sizing.
- **Clean Responsive Layout**: Preview automatically scales and re-renders cleanly as you resize the window.
- **Non-Destructive Export**: Prompts you to save a separate cropped copy, keeping your original PDF file intact.

---

## Installation & Setup

This project uses **[uv](https://github.com/astral-sh/uv)**, an extremely fast Python package resolver and installer.

### Prerequisites
- Python >= 3.14 (or any version compatible with PyMuPDF/Pillow)
- `uv` installed on your system.

### Steps
1. Navigate to the project directory:
   ```powershell
   cd PDFCrop
   ```
2. Synchronize the environment (this automatically creates a virtual environment `.venv` and installs PyMuPDF and Pillow):
   ```powershell
   uv sync
   ```

---

## Run Instructions

Once the dependencies are installed via `uv`, you can run the application directly:

### Option A: Using `uv run` (Recommended)
```powershell
uv run main.py
```

### Option B: Using the Virtual Environment Python Executable
```powershell
.venv\Scripts\python.exe main.py
```

---

## How to Use

1. Click **Upload PDF File** in the sidebar to load a single-page PDF document.
2. The page boundaries will load on the canvas workspace.
3. Position your crop box:
   - **Move**: Click and drag inside the selection box to reposition it.
   - **Resize**: Click and drag any of the 8 handles surrounding the selection box.
4. Review the coordinates and dimensions inside the **CROP REGION** card in the sidebar.
5. Click **Crop & Save PDF** to choose where to export your newly cropped document.
6. Click **Reset Crop Box** at any time to return the crop region to its default centered layout.
