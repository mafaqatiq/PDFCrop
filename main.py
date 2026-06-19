import os
import tkinter as tk
from tkinter import filedialog as fd
from tkinter import messagebox as mb
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageTk

# Modern Slate & Teal light theme colors for clean visual design
THEME = {
    "bg": "#f8fafc",            # Slate-50 main window background
    "canvas_bg": "#cbd5e1",     # Slate-300 canvas background (contrasts with white page)
    "sidebar_bg": "#ffffff",    # Pure white sidebar
    "card_bg": "#f1f5f9",       # Slate-100 details container card
    "fg": "#0f172a",            # Slate-900 primary text
    "fg_muted": "#475569",      # Slate-600 secondary/muted text
    "accent_blue": "#0d9488",   # Teal-600 main action accent (renamed in-place)
    "accent_green": "#059669",  # Emerald-600 success accent
    "accent_red": "#e11d48",    # Rose-600 danger highlight / reset
    "border": "#cbd5e1"         # Slate-300 border lines and dividers
}


class PDFCropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Precise Cropper")
        self.root.geometry("1150x760")
        self.root.minsize(950, 650)
        self.root.configure(bg=THEME["bg"])
        
        # Program state variables
        self.input_pdf_path = None
        self.pdf_doc = None
        self.page = None
        self.orig_page_rect = None
        self.base_image = None   # PIL image representation of rendered page
        self.tk_image = None     # Current active photoimage on canvas
        
        # Display margins/offsets on canvas
        self.img_x0 = 0
        self.img_y0 = 0
        self.img_x1 = 0
        self.img_y1 = 0
        
        # Normalized bounding coordinates of crop box relative to image (0.0 to 1.0)
        self.norm_x0 = 0.1
        self.norm_y0 = 0.1
        self.norm_x1 = 0.9
        self.norm_y1 = 0.9
        
        # Absolute pixel positions of crop box on the canvas
        self.crop_x0 = 0
        self.crop_y0 = 0
        self.crop_x1 = 0
        self.crop_y1 = 0
        
        # Drag-and-resize states
        self.drag_mode = None  # None, "move", or "resize"
        self.active_handle = None
        self.drag_start = (0, 0)
        self.init_crop_coords = (0, 0, 0, 0)
        
        # Set up graphical elements
        self.setup_ui()
        self.bind_button_hovers()
        
        # Clean shutdown handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        # Configure root layout
        self.root.grid_columnconfigure(0, weight=0, minsize=320)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Sidebar container
        sidebar = tk.Frame(self.root, bg=THEME["sidebar_bg"], bd=0, highlightthickness=0)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Scrollable/padded content area
        sidebar_inner = tk.Frame(sidebar, bg=THEME["sidebar_bg"])
        sidebar_inner.pack(fill="both", expand=True, padx=20, pady=25)
        
        # Application Branding Header
        title_lbl = tk.Label(
            sidebar_inner,
            text="PDF CROPPER",
            font=("Segoe UI", 16, "bold"),
            bg=THEME["sidebar_bg"],
            fg=THEME["accent_blue"]
        )
        title_lbl.pack(anchor="w", pady=(0, 2))
        
        desc_lbl = tk.Label(
            sidebar_inner,
            text="Precise single-page PDF crop utility",
            font=("Segoe UI", 9, "italic"),
            bg=THEME["sidebar_bg"],
            fg=THEME["fg_muted"]
        )
        desc_lbl.pack(anchor="w", pady=(0, 15))
        
        divider = tk.Frame(sidebar_inner, height=1, bg=THEME["border"])
        divider.pack(fill="x", pady=(0, 20))
        
        # File selector trigger button
        self.upload_btn = tk.Button(
            sidebar_inner,
            text="Upload PDF File",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["accent_blue"],
            fg=THEME["sidebar_bg"],
            activebackground="#0f766e",
            activeforeground=THEME["sidebar_bg"],
            bd=0,
            cursor="hand2",
            padx=10,
            pady=8,
            relief="flat"
        )
        self.upload_btn.config(command=self.upload_pdf)
        self.upload_btn.pack(fill="x", pady=(0, 20))
        
        # Metadata / Info card container
        self.card = tk.Frame(
            sidebar_inner,
            bg=THEME["card_bg"],
            bd=1,
            highlightbackground=THEME["border"],
            highlightthickness=1
        )
        self.card.pack(fill="x", pady=(0, 20))
        
        card_inner = tk.Frame(self.card, bg=THEME["card_bg"])
        card_inner.pack(fill="both", expand=True, padx=15, pady=15)
        
        # File details group
        tk.Label(
            card_inner,
            text="DOCUMENT INFO",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["card_bg"],
            fg=THEME["accent_blue"]
        ).pack(anchor="w", pady=(0, 5))
        
        self.file_name_lbl = tk.Label(
            card_inner,
            text="File: No PDF Loaded",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["card_bg"],
            fg=THEME["fg"],
            anchor="w",
            justify="left",
            wraplength=250
        )
        self.file_name_lbl.pack(anchor="w", pady=(0, 3))
        
        self.orig_size_lbl = tk.Label(
            card_inner,
            text="Original Size: -",
            font=("Segoe UI", 9),
            bg=THEME["card_bg"],
            fg=THEME["fg_muted"],
            anchor="w",
            justify="left"
        )
        self.orig_size_lbl.pack(anchor="w", pady=(0, 15))
        
        # Crop dimension details group
        tk.Label(
            card_inner,
            text="CROP REGION",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["card_bg"],
            fg=THEME["accent_blue"]
        ).pack(anchor="w", pady=(0, 5))
        
        self.crop_size_lbl = tk.Label(
            card_inner,
            text="Crop Size: -",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["card_bg"],
            fg=THEME["fg"],
            anchor="w",
            justify="left"
        )
        self.crop_size_lbl.pack(anchor="w", pady=(0, 3))
        
        self.crop_pos_lbl = tk.Label(
            card_inner,
            text="Position: -",
            font=("Segoe UI", 9),
            bg=THEME["card_bg"],
            fg=THEME["fg_muted"],
            anchor="w",
            justify="left"
        )
        self.crop_pos_lbl.pack(anchor="w")
        
        # Action Triggers
        self.save_btn = tk.Button(
            sidebar_inner,
            text="Crop & Save PDF",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["border"],
            fg=THEME["fg_muted"],
            activebackground=THEME["accent_green"],
            activeforeground=THEME["sidebar_bg"],
            bd=0,
            state="disabled",
            cursor="arrow",
            padx=10,
            pady=8,
            relief="flat"
        )
        self.save_btn.config(command=self.save_cropped_pdf)
        self.save_btn.pack(fill="x", pady=(0, 10))
        
        self.reset_btn = tk.Button(
            sidebar_inner,
            text="Reset Crop Box",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["border"],
            fg=THEME["fg_muted"],
            activebackground=THEME["accent_red"],
            activeforeground=THEME["sidebar_bg"],
            bd=0,
            state="disabled",
            cursor="arrow",
            padx=10,
            pady=6,
            relief="flat"
        )
        self.reset_btn.config(command=self.reset_crop_box)
        self.reset_btn.pack(fill="x")
        
        # Main Preview Canvas area on right
        main_area = tk.Frame(self.root, bg=THEME["bg"])
        main_area.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        main_area.grid_rowconfigure(0, weight=1)
        main_area.grid_columnconfigure(0, weight=1)
        
        # Visual bounding border container for Canvas
        canvas_frame = tk.Frame(
            main_area,
            bg=THEME["bg"],
            bd=1,
            highlightbackground=THEME["border"],
            highlightthickness=1
        )
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Preview Canvas
        self.canvas = tk.Canvas(
            canvas_frame,
            bg=THEME["canvas_bg"],
            bd=0,
            highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Interactive bindings
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        self.canvas_image_id = self.canvas.create_image(0, 0, anchor="nw")
        
        # Guide Label footer
        inst_lbl = tk.Label(
            main_area,
            text="Drag the box center to move. Drag corners & edges to adjust crop bounds precisely.",
            font=("Segoe UI", 9),
            bg=THEME["bg"],
            fg=THEME["fg_muted"]
        )
        inst_lbl.grid(row=1, column=0, pady=(10, 0))

    def bind_button_hovers(self):
        # Apply clean hover styling shifts
        def on_enter(btn, hover_bg, hover_fg):
            return lambda e: btn.config(bg=hover_bg, fg=hover_fg) if btn["state"] == "normal" else None
        def on_leave(btn, orig_bg, orig_fg):
            return lambda e: btn.config(bg=orig_bg, fg=orig_fg) if btn["state"] == "normal" else None
            
        # Upload Button hovers
        self.upload_btn.bind("<Enter>", on_enter(self.upload_btn, "#0f766e", "#ffffff"))
        self.upload_btn.bind("<Leave>", on_leave(self.upload_btn, THEME["accent_blue"], "#ffffff"))
        
        # Save Button hovers
        self.save_btn.bind("<Enter>", on_enter(self.save_btn, "#047857", "#ffffff"))
        self.save_btn.bind("<Leave>", on_leave(self.save_btn, THEME["accent_green"], "#ffffff"))
        
        # Reset Button hovers
        self.reset_btn.bind("<Enter>", on_enter(self.reset_btn, "#be123c", "#ffffff"))
        self.reset_btn.bind("<Leave>", on_leave(self.reset_btn, THEME["accent_red"], "#ffffff"))


    def upload_pdf(self):
        filepath = fd.askopenfilename(
            title="Open Single-Page PDF File",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not filepath:
            return
        
        try:
            doc = fitz.open(filepath)
            if len(doc) == 0:
                mb.showerror("Empty PDF", "The selected PDF file contains no pages.")
                doc.close()
                return
            
            # Close existing active document if any
            if self.pdf_doc:
                self.pdf_doc.close()
                
            self.input_pdf_path = filepath
            self.pdf_doc = doc
            self.page = doc[0]
            
            # Use visual bounds (automatically compensates for page rotation)
            self.orig_page_rect = self.page.rect
            
            # Enable actions and update visuals
            self.save_btn.config(state="normal", bg=THEME["accent_green"], fg="#ffffff", cursor="hand2")
            self.reset_btn.config(state="normal", bg=THEME["accent_red"], fg="#ffffff", cursor="hand2")
            
            base_name = os.path.basename(filepath)
            self.file_name_lbl.config(text=f"File: {base_name}")
            
            # Calculate standard sizes
            pw = self.orig_page_rect.width
            ph = self.orig_page_rect.height
            pw_in, ph_in = pw / 72.0, ph / 72.0
            pw_mm, ph_mm = pw_in * 25.4, ph_in * 25.4
            
            self.orig_size_lbl.config(
                text=f"Original Size:\n{pw:.1f} x {ph:.1f} pt\n({pw_in:.2f}\" x {ph_in:.2f}\")\n{pw_mm:.0f} x {ph_mm:.0f} mm"
            )
            
            # Initialize crop area to center 80%
            self.norm_x0 = 0.1
            self.norm_y0 = 0.1
            self.norm_x1 = 0.9
            self.norm_y1 = 0.9
            
            self.render_pdf_page()
            
        except Exception as e:
            mb.showerror("Load Failed", f"Could not load PDF document:\n{str(e)}")

    def render_pdf_page(self):
        if not self.pdf_doc:
            return
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # Fallback dimensions during initial rendering
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w = 780
            canvas_h = 620
            
        max_w = canvas_w - 40
        max_h = canvas_h - 40
        
        orig_w = self.orig_page_rect.width
        orig_h = self.orig_page_rect.height
        
        # Scale page keeping aspect ratio
        scale_w = max_w / orig_w
        scale_h = max_h / orig_h
        scale = min(scale_w, scale_h)
        
        if scale <= 0:
            scale = 1.0
            
        disp_w = int(orig_w * scale)
        disp_h = int(orig_h * scale)
        
        # Render high-quality crisp page from PDF
        pixmap = self.page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        self.base_image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        
        # Center target image inside canvas viewport
        self.img_x0 = (canvas_w - disp_w) // 2
        self.img_y0 = (canvas_h - disp_h) // 2
        self.img_x1 = self.img_x0 + disp_w
        self.img_y1 = self.img_y0 + disp_h
        
        # Transform normalized coordinates to canvas pixel space
        self.crop_x0 = self.img_x0 + self.norm_x0 * disp_w
        self.crop_y0 = self.img_y0 + self.norm_y0 * disp_h
        self.crop_x1 = self.img_x0 + self.norm_x1 * disp_w
        self.crop_y1 = self.img_y0 + self.norm_y1 * disp_h
        
        self.draw_crop_box()
        self.update_crop_labels()

    def update_canvas_image(self):
        if not self.base_image:
            return
        
        # Construct visual dimmed exclusion region overlay (slate grey translucent mask)
        overlay = Image.new("RGBA", self.base_image.size, (30, 41, 59, 110)) 
        draw = ImageDraw.Draw(overlay)
        
        # Map visual crop coordinates relative to base image space
        rx0 = max(0, min(self.base_image.width, self.crop_x0 - self.img_x0))
        ry0 = max(0, min(self.base_image.height, self.crop_y0 - self.img_y0))
        rx1 = max(0, min(self.base_image.width, self.crop_x1 - self.img_x0))
        ry1 = max(0, min(self.base_image.height, self.crop_y1 - self.img_y0))
        
        # Cut out crop box transparency
        draw.rectangle([rx0, ry0, rx1, ry1], fill=(0, 0, 0, 0))
        
        rgba_base = self.base_image.convert("RGBA")
        composited = Image.alpha_composite(rgba_base, overlay)
        
        self.tk_image = ImageTk.PhotoImage(composited)
        self.canvas.itemconfig(self.canvas_image_id, image=self.tk_image)
        self.canvas.coords(self.canvas_image_id, self.img_x0, self.img_y0)

    def draw_crop_box(self):
        self.canvas.delete("crop_element")
        
        if not self.base_image:
            return
        
        # Redraw PIL dimmed base image
        self.update_canvas_image()
        
        # Border outline
        self.canvas.create_rectangle(
            self.crop_x0, self.crop_y0, self.crop_x1, self.crop_y1,
            outline=THEME["accent_blue"],
            width=2,
            tags="crop_element"
        )
        
        # Draw 8 handle controls
        handles = self.get_handle_positions()
        for hx, hy in handles:
            self.canvas.create_rectangle(
                hx - 5, hy - 5, hx + 5, hy + 5,
                fill="#ffffff",
                outline=THEME["accent_blue"],
                width=1.5,
                tags="crop_element"
            )

    def get_handle_positions(self):
        x0, y0, x1, y1 = self.crop_x0, self.crop_y0, self.crop_x1, self.crop_y1
        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2
        return [
            (x0, y0),  # 0: TL
            (mx, y0),  # 1: TM
            (x1, y0),  # 2: TR
            (x1, my),  # 3: MR
            (x1, y1),  # 4: BR
            (mx, y1),  # 5: BM
            (x0, y1),  # 6: BL
            (x0, my),  # 7: ML
        ]

    def get_handle_under_mouse(self, x, y):
        tolerance = 7
        positions = self.get_handle_positions()
        for i, (hx, hy) in enumerate(positions):
            if abs(x - hx) <= tolerance and abs(y - hy) <= tolerance:
                return i
        return None

    def on_button_press(self, event):
        if not self.pdf_doc:
            return
        
        # Check active handles
        h_idx = self.get_handle_under_mouse(event.x, event.y)
        if h_idx is not None:
            self.drag_mode = "resize"
            self.active_handle = h_idx
            self.drag_start = (event.x, event.y)
            self.init_crop_coords = (self.crop_x0, self.crop_y0, self.crop_x1, self.crop_y1)
            return
            
        # Check moving bounding box
        if self.crop_x0 <= event.x <= self.crop_x1 and self.crop_y0 <= event.y <= self.crop_y1:
            self.drag_mode = "move"
            self.drag_start = (event.x, event.y)
            self.init_crop_coords = (self.crop_x0, self.crop_y0, self.crop_x1, self.crop_y1)

    def on_mouse_drag(self, event):
        if self.drag_mode is None:
            return
            
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        ix0, iy0, ix1, iy1 = self.init_crop_coords
        
        disp_w = self.img_x1 - self.img_x0
        disp_h = self.img_y1 - self.img_y0
        
        min_pixels = 25  # prevent crop region from collapsing
        
        if self.drag_mode == "move":
            x0 = ix0 + dx
            y0 = iy0 + dy
            w = ix1 - ix0
            h = iy1 - iy0
            
            # Constrain cropbox to image border bounds
            if x0 < self.img_x0:
                x0 = self.img_x0
            if x0 + w > self.img_x1:
                x0 = self.img_x1 - w
            if y0 < self.img_y0:
                y0 = self.img_y0
            if y0 + h > self.img_y1:
                y0 = self.img_y1 - h
                
            self.crop_x0, self.crop_y0 = x0, y0
            self.crop_x1, self.crop_y1 = x0 + w, y0 + h
            
        elif self.drag_mode == "resize":
            x0, y0, x1, y1 = ix0, iy0, ix1, iy1
            
            # Handle modification coordinates
            # Left adjustment
            if self.active_handle in (0, 6, 7):
                x0 = max(self.img_x0, min(ix0 + dx, x1 - min_pixels))
            # Right adjustment
            if self.active_handle in (2, 3, 4):
                x1 = min(self.img_x1, max(ix1 + dx, x0 + min_pixels))
            # Top adjustment
            if self.active_handle in (0, 1, 2):
                y0 = max(self.img_y0, min(iy0 + dy, y1 - min_pixels))
            # Bottom adjustment
            if self.active_handle in (4, 5, 6):
                y1 = min(self.img_y1, max(iy1 + dy, y0 + min_pixels))
                
            self.crop_x0, self.crop_y0 = x0, y0
            self.crop_x1, self.crop_y1 = x1, y1
            
        # Recalculate scaled bounds
        self.norm_x0 = (self.crop_x0 - self.img_x0) / disp_w
        self.norm_y0 = (self.crop_y0 - self.img_y0) / disp_h
        self.norm_x1 = (self.crop_x1 - self.img_x0) / disp_w
        self.norm_y1 = (self.crop_y1 - self.img_y0) / disp_h
        
        self.draw_crop_box()
        self.update_crop_labels()

    def on_button_release(self, event):
        self.drag_mode = None
        self.active_handle = None

    def on_mouse_move(self, event):
        if not self.pdf_doc:
            return
            
        h_idx = self.get_handle_under_mouse(event.x, event.y)
        if h_idx is not None:
            # Update appropriate resizing cursor shapes
            if h_idx in (0, 4):
                self.canvas.config(cursor="size_nw_se")
            elif h_idx in (2, 6):
                self.canvas.config(cursor="size_ne_sw")
            elif h_idx in (1, 5):
                self.canvas.config(cursor="size_ns")
            else:
                self.canvas.config(cursor="size_we")
        elif self.crop_x0 <= event.x <= self.crop_x1 and self.crop_y0 <= event.y <= self.crop_y1:
            self.canvas.config(cursor="fleur")
        else:
            self.canvas.config(cursor="arrow")

    def on_canvas_resize(self, event):
        if not self.pdf_doc:
            return
        # Refresh and rescale page on canvas window size adjustments
        self.render_pdf_page()

    def update_crop_labels(self):
        if not self.pdf_doc:
            return
            
        rel_x0 = self.crop_x0 - self.img_x0
        rel_y0 = self.crop_y0 - self.img_y0
        rel_x1 = self.crop_x1 - self.img_x0
        rel_y1 = self.crop_y1 - self.img_y0
        
        disp_w = self.img_x1 - self.img_x0
        disp_h = self.img_y1 - self.img_y0
        
        orig_w = self.orig_page_rect.width
        orig_h = self.orig_page_rect.height
        
        # Calculate visual points in original dimensions
        pdf_w = (rel_x1 - rel_x0) / disp_w * orig_w
        pdf_h = (rel_y1 - rel_y0) / disp_h * orig_h
        pdf_x = rel_x0 / disp_w * orig_w
        pdf_y = rel_y0 / disp_h * orig_h
        
        w_in, h_in = pdf_w / 72.0, pdf_h / 72.0
        w_mm, h_mm = w_in * 25.4, h_in * 25.4
        
        self.crop_size_lbl.config(
            text=f"Crop Size:\n{pdf_w:.1f} x {pdf_h:.1f} pt\n({w_in:.2f}\" x {h_in:.2f}\")\n{w_mm:.0f} x {h_mm:.0f} mm"
        )
        self.crop_pos_lbl.config(
            text=f"Position:\nX: {pdf_x:.1f} pt, Y: {pdf_y:.1f} pt"
        )

    def reset_crop_box(self):
        if not self.pdf_doc:
            return
            
        self.norm_x0 = 0.1
        self.norm_y0 = 0.1
        self.norm_x1 = 0.9
        self.norm_y1 = 0.9
        
        disp_w = self.img_x1 - self.img_x0
        disp_h = self.img_y1 - self.img_y0
        
        self.crop_x0 = self.img_x0 + self.norm_x0 * disp_w
        self.crop_y0 = self.img_y0 + self.norm_y0 * disp_h
        self.crop_x1 = self.img_x0 + self.norm_x1 * disp_w
        self.crop_y1 = self.img_y0 + self.norm_y1 * disp_h
        
        self.draw_crop_box()
        self.update_crop_labels()

    def save_cropped_pdf(self):
        if not self.pdf_doc:
            return
            
        rel_x0 = self.crop_x0 - self.img_x0
        rel_y0 = self.crop_y0 - self.img_y0
        rel_x1 = self.crop_x1 - self.img_x0
        rel_y1 = self.crop_y1 - self.img_y0
        
        disp_w = self.img_x1 - self.img_x0
        disp_h = self.img_y1 - self.img_y0
        
        orig_w = self.orig_page_rect.width
        orig_h = self.orig_page_rect.height
        
        # Calculate visual points mapped to page rect space
        pdf_x0 = max(0.0, min(orig_w, (rel_x0 / disp_w) * orig_w))
        pdf_y0 = max(0.0, min(orig_h, (rel_y0 / disp_h) * orig_h))
        pdf_x1 = max(0.0, min(orig_w, (rel_x1 / disp_w) * orig_w))
        pdf_y1 = max(0.0, min(orig_h, (rel_y1 / disp_h) * orig_h))
        
        visual_rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
        
        # Compensate for page rotation by applying the derotation matrix
        # set_cropbox operates on the original unrotated coordinates
        unrotated_rect = visual_rect * self.page.derotation_matrix
        
        init_dir = os.path.dirname(self.input_pdf_path)
        base_name = os.path.basename(self.input_pdf_path)
        cropped_name = "cropped_" + base_name
        
        save_path = fd.asksaveasfilename(
            initialdir=init_dir,
            initialfile=cropped_name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not save_path:
            return
            
        try:
            # Load fresh document to prevent modifying working memory instance
            out_doc = fitz.open(self.input_pdf_path)
            out_page = out_doc[0]
            out_page.set_cropbox(unrotated_rect)
            
            # Save the cropped page contents
            out_doc.save(save_path)
            out_doc.close()
            
            mb.showinfo("Success", f"Cropped PDF saved successfully to:\n{save_path}")
            
        except Exception as e:
            mb.showerror("Export Failed", f"Could not save cropped PDF document:\n{str(e)}")

    def on_close(self):
        if self.pdf_doc:
            self.pdf_doc.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = PDFCropApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

