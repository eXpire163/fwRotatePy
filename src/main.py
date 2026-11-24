import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageTk


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".bmp"}


def met_path_for(image_path: Path) -> Path:
    met_directory = image_path.parent / "met"
    return met_directory / image_path.with_suffix(".met").name


def format_angle(angle: float) -> str:
    normalized = angle % 360
    if abs(normalized - round(normalized)) < 0.0001:
        return str(round(normalized))
    return f"{normalized:.1f}".rstrip("0").rstrip(".")


def write_met_file(image_path: Path, angle: float) -> None:
    met_path = met_path_for(image_path)
    met_path.parent.mkdir(parents=True, exist_ok=True)
    angle_text = format_angle(angle)
    met_path.write_text(
        "[Nachbearbeitung]\n"
        f"Drehwinkel={angle_text}\n"
        "Processed=1\n",
        encoding="utf-8",
    )


def preview_dimensions(width: int, height: int, percent: float) -> tuple[int, int]:
    percent = min(100.0, max(5.0, percent))
    scale = percent / 100.0
    return max(1, round(width * scale)), max(1, round(height * scale))


def grid_spacing_pixels(dpi: float, millimeters: float = 20.0) -> float:
    if dpi <= 0:
        dpi = 300.0
    return dpi * millimeters / 25.4


def draw_grid(image: Image.Image, dpi_x: float, dpi_y: float) -> Image.Image:
    result = image.convert("RGBA")
    spacing_x = grid_spacing_pixels(dpi_x)
    spacing_y = grid_spacing_pixels(dpi_y)

    overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    x = 0
    while x < result.width:
        draw.line((x, 0, x, result.height), fill=(255, 255, 0, 180), width=2)
        x += spacing_x

    y = 0
    while y < result.height:
        draw.line((0, y, result.width, y), fill=(255, 255, 0, 180), width=2)
        y += spacing_y

    return Image.alpha_composite(result, overlay).convert("RGB")


class RotationApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Image Rotation")
        self.root.geometry("1100x760")
        self.root.minsize(640, 480)

        self.folder: Path | None = None
        self.images: list[Path] = []
        self.index = 0
        self.angle = 0.0
        self.original: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.image_dpi: tuple[float, float] = (300.0, 300.0)
        self.preview_source: Image.Image | None = None
        self.preview_source_percent = 30.0

        top = tk.Frame(root)
        top.pack(fill="x", padx=10, pady=8)

        tk.Button(top, text="Bilder Ordner", command=self.select_folder).pack(side="left")
        tk.Button(top, text="Speichern (Leertaste)", command=self.save_and_next).pack(side="left", padx=(8, 0))

        tk.Label(top, text="Preview:").pack(side="left", padx=(12, 4))
        self.preview_percent = tk.StringVar(value="30")
        preview_entry = tk.Entry(top, textvariable=self.preview_percent, width=5)
        preview_entry.pack(side="left")
        tk.Label(top, text="%").pack(side="left", padx=(2, 8))

        tk.Label(top, text="Raster:").pack(side="left", padx=(4, 4))
        self.grid_spacing_mm = tk.StringVar(value="20")
        grid_entry = tk.Entry(top, textvariable=self.grid_spacing_mm, width=5)
        grid_entry.pack(side="left")
        tk.Label(top, text="mm").pack(side="left", padx=(2, 8))

        preview_entry.bind("<Return>", lambda _event: self.redraw())
        preview_entry.bind("<FocusOut>", lambda _event: self.redraw())
        grid_entry.bind("<Return>", lambda _event: self.redraw())
        grid_entry.bind("<FocusOut>", lambda _event: self.redraw())

        self.status = tk.StringVar(value="Wählen Sie einen Ordner, um zu beginnen")
        tk.Label(top, textvariable=self.status).pack(side="right")

        self.canvas = tk.Canvas(root, bg="#202020", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.root.bind("<Left>", lambda _event: self.adjust_angle(-0.2))
        self.root.bind("<Right>", lambda _event: self.adjust_angle(0.2))
        self.root.bind("<space>", lambda _event: self.save_and_next())
        self.root.bind("<Escape>", lambda _event: self.root.quit())

    def select_folder(self) -> None:
        folder_name = filedialog.askdirectory(title="Select image folder")
        if not folder_name:
            return

        self.folder = Path(folder_name)
        all_images = sorted(
            (
                path
                for path in self.folder.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ),
            key=lambda path: path.name.lower(),
        )
        self.images = [path for path in all_images if not met_path_for(path).exists()]
        self.index = 0

        if not all_images:
            messagebox.showinfo("Keine Bilder", "In diesem Ordner wurden keine unterstützten Bilder gefunden.")
            self.status.set("Keine Bilder gefunden")
            return

        if not self.images:
            messagebox.showinfo("Fertig", "Jedes Bild hat bereits eine .met-Datei.")
            self.status.set(f"Fertig - {len(all_images)} Bilder verarbeitet")
            self.original = None
            self.photo = None
            self.canvas.delete("all")
            return

        self.show_current()

    def show_current(self) -> None:
        if not self.images or self.index >= len(self.images):
            self.original = None
            self.photo = None
            self.canvas.delete("all")
            self.status.set("Fertig - alle Bilder verarbeitet")
            messagebox.showinfo("Fertig", "Jedes Bild hat jetzt eine .met-Datei.")
            return

        path = self.images[self.index]
        try:
            image = Image.open(path)
            image.load()
            dpi = image.info.get("dpi")
            if isinstance(dpi, tuple) and len(dpi) == 2:
                self.image_dpi = (float(dpi[0]) or 300.0, float(dpi[1]) or 300.0)
            else:
                self.image_dpi = (300.0, 300.0)
            self.original = image.convert("RGB")
            self.preview_source = None
            self.preview_source_percent = -1.0
        except Exception as exc:
            messagebox.showerror("Cannot open image", f"Could not open {path.name}:\n{exc}")
            self.index += 1
            self.show_current()
            return

        self.angle = 0.0
        self.status.set(f"{self.index + 1}/{len(self.images)} - {path.name} - angle: 0")
        self.redraw()

    def adjust_angle(self, change: float) -> None:
        if self.original is None:
            return
        self.angle = (self.angle + change) % 360
        self.update_status()
        self.redraw()

    def update_status(self) -> None:
        if not self.images or self.index >= len(self.images):
            return
        path = self.images[self.index]
        self.status.set(
            f"{self.index + 1}/{len(self.images)} - {path.name} - angle: {format_angle(self.angle)}°"
        )

    def on_mouse_down(self, event: tk.Event) -> None:
        self.drag_start_x = event.x
        self.drag_start_angle = self.angle

    def on_mouse_drag(self, event: tk.Event) -> None:
        if self.drag_start_x is None or self.original is None:
            return

        dx = event.x - self.drag_start_x
        whole_degree_steps = dx
        self.angle = (self.drag_start_angle + whole_degree_steps) % 360
        self.update_status()
        self.redraw()

    def on_mouse_up(self, _event: tk.Event) -> None:
        self.drag_start_x = None

    def redraw(self) -> None:
        if self.original is None:
            return

        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        if canvas_width <= 1 or canvas_height <= 1:
            return

        try:
            preview_percent = min(100.0, max(5.0, float(self.preview_percent.get())))
        except ValueError:
            preview_percent = 30.0

        if self.preview_source is None or abs(self.preview_source_percent - preview_percent) > 0.01:
            preview_size = preview_dimensions(
                self.original.width,
                self.original.height,
                preview_percent,
            )
            self.preview_source = self.original.resize(preview_size, Image.Resampling.BICUBIC)
            self.preview_source_percent = preview_percent

        rotated = self.preview_source.rotate(-self.angle, resample=Image.Resampling.BICUBIC, expand=True)
        available_width = max(1, canvas_width - 20)
        available_height = max(1, canvas_height - 20)
        scale = min(available_width / rotated.width, available_height / rotated.height, 1.0)

        if scale < 1.0:
            size = (max(1, round(rotated.width * scale)), max(1, round(rotated.height * scale)))
            rotated = rotated.resize(size, Image.Resampling.LANCZOS)

        self.photo = ImageTk.PhotoImage(rotated)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=self.photo)
        self.draw_fixed_grid(canvas_width, canvas_height)

    def draw_fixed_grid(self, canvas_width: int, canvas_height: int) -> None:
        try:
            spacing_mm = min(500.0, max(1.0, float(self.grid_spacing_mm.get())))
        except ValueError:
            spacing_mm = 20.0

        try:
            pixels_per_mm = float(self.canvas.winfo_fpixels("1m"))
            spacing = max(2.0, pixels_per_mm * spacing_mm)
        except tk.TclError:
            spacing = max(2.0, (96.0 / 25.4) * spacing_mm)

        center_x = canvas_width // 2
        center_y = canvas_height // 2

        x = center_x % spacing
        while x < canvas_width:
            self.canvas.create_line(x, 0, x, canvas_height, fill="#ffff00", width=1)
            x += spacing

        y = center_y % spacing
        while y < canvas_height:
            self.canvas.create_line(0, y, canvas_width, y, fill="#ffff00", width=1)
            y += spacing

    def save_and_next(self) -> None:
        if self.original is None or not self.images or self.index >= len(self.images):
            return

        path = self.images[self.index]
        try:
            write_met_file(path, self.angle)
        except Exception as exc:
            messagebox.showerror("Speichern fehlgeschlagen", f"Konnte {met_path_for(path).name} nicht speichern:\n{exc}")
            return

        self.index += 1
        self.show_current()


def main() -> None:
    root = tk.Tk()
    app = RotationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
