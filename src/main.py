from edifice import App, Label, HBoxView, VBoxView, Window, component, use_state, Image as ImageUI, Button, Slider, use_async, run_subprocess_with_callback
from PySide6 import QtWidgets, QtGui
from PIL import Image, ImageEnhance
from functools import partial

import io
import os
import asyncio

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}

def pick_directory(parent=None, title="Select Directory"):
    dialog = QtWidgets.QFileDialog(parent)
    dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
    dialog.setWindowTitle(title)
    if dialog.exec() == QtWidgets.QDialog.Accepted:
        selected = dialog.selectedFiles()
        if selected:
            return selected[0]
    return None

def bytes_to_qpixmap(b):
    # Convert PNG bytes to QPixmap without touching disk
    qt_img = QtGui.QImage.fromData(b, "PNG")
    return QtGui.QPixmap.fromImage(qt_img)

def apply_effects(pil_img: Image.Image, hue_shift_deg: float, sat_mult: float, val_mult: float, sharp_mult: float) -> Image.Image:
    """
    Apply hue/saturation/value and sharpness effects.
    This is CPU-bound and should be offloaded from the UI thread.
    """
    hsv = pil_img.convert("HSV")
    h, s, v = hsv.split()

    hue_shift = int((hue_shift_deg % 360) * 255 / 360)

    h_data = bytes(((px + hue_shift) % 256 for px in h.getdata()))
    h = Image.frombytes("L", h.size, h_data)

    s_data = bytes((max(0, min(255, int(px * sat_mult))) for px in s.getdata()))
    s = Image.frombytes("L", s.size, s_data)

    v_data = bytes((max(0, min(255, int(px * val_mult))) for px in v.getdata()))
    v = Image.frombytes("L", v.size, v_data)

    adjusted = Image.merge("HSV", (h, s, v)).convert("RGB")

    sharp_enh = ImageEnhance.Sharpness(adjusted)
    adjusted = sharp_enh.enhance(sharp_mult)

    return adjusted

def list_image_files_in_dir(dir_path: str):
    """Return sorted list of image file absolute paths in a directory (non-recursive)."""
    try:
        entries = os.listdir(dir_path)
    except Exception:
        return []
    files = []
    for name in entries:
        full = os.path.join(dir_path, name)
        if os.path.isfile(full):
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTS:
                files.append(full)
    files.sort()
    return files

@component
def Header(self, title):
    with HBoxView(style={"height": 50, "padding": 10, "align": "center"}):
        Label(text=title, style={"text-align": "center"})

@component
def Effects(self, title, effects, on_change, is_disabled=False):
    on_change_ = on_change if not is_disabled else lambda x: x
    with VBoxView():
        Label(text=f"<h2>{title}</h2><hr>")
        with HBoxView():
            Label(f"Hue: {int(effects['hue'])}°", style={"width": 110})
            Slider(
                min_value=-180, max_value=180, value=effects["hue"],
                on_change=lambda v: (on_change_({**effects, "hue": v})),
            )
        with HBoxView():
            Label(f"Saturation: {effects['sat']:.2f}x", style={"width": 110})
            Slider(
                min_value=0.0, max_value=3.0, value=effects["sat"],
                on_change=lambda v: (on_change_({**effects, "sat": v}) ),
            )
        with HBoxView():
            Label(f"Value: {effects['val']:.2f}x", style={"width": 110})
            Slider(
                min_value=0.0, max_value=3.0, value=effects["val"],
                on_change=lambda v: (on_change_({**effects, "val": v}) ),
            )
        with HBoxView():
            Label(f"Sharpness: {effects['sharp']:.2f}x", style={"width": 110})
            Slider(
                min_value=0.0, max_value=3.0, value=effects["sharp"],
                on_change=lambda v: (on_change_({**effects, "sharp": v}) ),
            )

def image_load(path, callback):
    try:
        name = os.path.basename(path) 
        callback({"name": name})
        img_pil = Image.open(path).convert("RGB")
        buf = io.BytesIO()
        img_pil.save(buf, format="PNG")
        data = buf.getvalue()
        callback({"data": data, "error": None})
        return data
    except Exception as e:
        callback({"error": str(e), "data": None})
        return None
 
@component
def ImagePreview(self, images, effects):
    """
    images: list[str] (file paths)
    effects: dict with keys hue, sat, val, sharp
    """
    state, set_state = use_state({
        "error": None,
        "data": None,
        "name": None,
        "index": 0,      # change by prev and next
    })

    image_index = state["index"]
    image_path = images[image_index] if images and images[image_index] is not None else None 
    image_name = state["name"]

    def updater_state(payload):
        set_state(lambda prev: {**prev, **payload})

    def step(kind):
        if kind == "prev" and (image_index > 0 and image_index < len(images)):
            set_state(lambda prev: {**prev, "index": prev["index"]-1})
        elif kind == "next" and (image_index >= 0 and image_index < len(images)):
            set_state(lambda prev: {**prev, "index": prev["index"]+1})

    async def run_load_image():
        try:
            if image_path is not None:
                # use_async won't work with plain partial function (high-order-function)
                worker = partial(image_load, image_path)
                data = await run_subprocess_with_callback(worker, updater_state)
                set_state(lambda prev: {**prev, "data": data, "error": None })
        except asyncio.CancelledError:
            set_state(lambda prev: {**prev, "error": "Cancelled"})
            raise 
        except Exception as e:
            set_state(lambda prev: {**prev, "error": "Unknown: failed to load the image"})

    use_async(run_load_image, image_path)

    with VBoxView(style={"margin-top": 10}):
        with HBoxView(style={
            "min-width": 240,
            "min-height": 180,
            "border": "1px solid #ccc",
            "background-color": "#f6f6f6",
            "align": "center",
            "padding": 8,
        }):
            if state["data"]:
                ImageUI(bytes_to_qpixmap(state["data"]), style={"border": "1px solid #ddd"})
            else:
                Label("No image yet", style={"color": "#888", "font-size": 12})
        if state["data"]:
            with HBoxView(style={ "padding": 5, "margin-top": 8, "padding-left": 5, "padding-right": 5 }) :
                Button("Prev", on_click=lambda _: step("prev"))
                Label(image_name or "-", style={"align": "center"})
                Button("Next", on_click=lambda _: step("next"))

@component
def MyApp(self):
    # Directories
    state, set_state = use_state({
        "source_dir": None,     # dir for all images inputs
        "output_dir": None,     # dir for export
        "images": [],           # list[str] of file paths
        # effect configuration, user can adjust in ImagePreview
        "image_effect": {"hue": 0.0, "sat": 1.0, "val": 1.0, "sharp": 1.0}
    })

    def updater(payload):
        set_state(lambda prev: {**prev, **payload})

    source_dir = state["source_dir"]
    output_dir = state["output_dir"]
    source_images = state["images"]            
    effects = state["image_effect"]

    is_empty_source_images = len(source_images) == 0 
    is_disabled_effect = output_dir is None and is_empty_source_images

    def select_source_directory(_ev):
        path = pick_directory(title="Select Source Directory")
        if path:
            updater({ "source_dir": path })
            imgs = list_image_files_in_dir(path)
            if imgs:
                updater({ "images" : imgs})
            else:
                QtWidgets.QMessageBox.information(None, "No Images", "No image files found in the selected directory.")

    def select_output_directory(_ev):
        path = pick_directory(title="Select Output Directory")
        if path:
            updater({ "output_dir": path })

    with Window(title="Desi — Image Effects"):
        Header(title="<h1>Desi - Image Viewer and Effects</h1>")

        ImagePreview(images=source_images, effects=effects)

        with VBoxView(style={"padding": 10} ):
            with HBoxView():
                Label(f"Source Dir: {source_dir or ''}")
                Button("Pick Source Dir", on_click=select_source_directory)

            with HBoxView():
                Label(f"Output Dir: {output_dir or ''}")
                Button("Pick Output Dir", on_click=select_output_directory)

            Effects(title="Effects", 
                    effects=effects, 
                    is_disabled=is_disabled_effect,
                    on_change=lambda effects: updater({"image_effect": effects}))

            with HBoxView(style={"margin-top": 10}):
                Button("Save Processed")

if __name__ == "__main__":
    App(MyApp()).start()
