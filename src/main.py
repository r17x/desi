from edifice import  App, Label, HBoxView, VBoxView, Window, CheckBox, component, use_state, Image as ImageUI, Button, Slider, use_async, run_subprocess_with_callback
from PySide6 import QtWidgets, QtGui, QtCore
from PIL import Image, ImageEnhance
from functools import partial

import io
import os
import asyncio

AspectRatioMode = QtCore.Qt.AspectRatioMode

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
    # Pillow-like ranges:
    # - Hue: degrees [-180, 180]
    # - Factors: >= 0.0, practical UI cap 4.0 for Saturation/Value/Sharpness
    HUE_MIN, HUE_MAX = -180, 180
    FACTOR_MIN, FACTOR_MAX = 0.0, 4.0

    # Debounce with asyncio.sleep; no local state dict
    debounce_task = {"t": None}

    async def _emit_debounced(payload):
        t = debounce_task["t"]
        if t is not None and not t.done():
            t.cancel()
        async def _fire():
            try:
                await asyncio.sleep(0.15)  # 150ms debounce
                if not is_disabled:
                    on_change({**effects, **payload})
            except asyncio.CancelledError:
                pass
        debounce_task["t"] = asyncio.create_task(_fire())

    def _on_change(payload):
        if not is_disabled:
            asyncio.create_task(_emit_debounced(payload))

    with VBoxView():
        Label(text=f"<h2>{title}</h2><hr>")
        with HBoxView():
            Label(f"Hue: {int(effects['hue'])}°", style={"width": 110})
            Slider(
                min_value=HUE_MIN if not is_disabled else effects["hue"],
                max_value=HUE_MAX if not is_disabled else effects["hue"],
                value=effects["hue"],
                on_change=lambda v: (_on_change({"hue": v})),
            )
        with HBoxView():
            Label(f"Saturation: {effects['sat']:.2f}x", style={"width": 110})
            Slider(
                min_value=FACTOR_MIN if not is_disabled else effects["sat"],
                max_value=FACTOR_MAX if not is_disabled else effects["sat"],
                value=effects["sat"],
                on_change=lambda v: (_on_change({"sat": v})),
            )
        with HBoxView():
            Label(f"Value: {effects['val']:.2f}x", style={"width": 110})
            Slider(
                min_value=FACTOR_MIN if not is_disabled else effects["val"],
                max_value=FACTOR_MAX if not is_disabled else effects["val"],
                value=effects["val"],
                on_change=lambda v: (_on_change({"val": v})),
            )
        with HBoxView():
            Label(f"Sharpness: {effects['sharp']:.2f}x", style={"width": 110})
            Slider(
                min_value=FACTOR_MIN if not is_disabled else effects["sharp"],
                max_value=FACTOR_MAX if not is_disabled else effects["sharp"],
                value=effects["sharp"],
                on_change=lambda v: (_on_change({"sharp": v})),
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
    except Exception:
        callback({"error": "Failed to load Image", "data": None})
        return None

def make_image(png_bytes, hue, sat, val, sharp, quality, callback):
    """
    Preview worker: downscale first, then apply effects, return PNG bytes.
    quality:
      - "fast":  max_dim=768,  resample=BILINEAR
      - "low":   max_dim=1024, resample=BILINEAR
      - "hq":    max_dim=1280, resample=LANCZOS
    """
    try:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")

        if quality == "hq":
            max_dim = 1280
            resample = Image.Resampling.LANCZOS
        elif quality == "fast":
            max_dim = 768
            resample = Image.Resampling.BILINEAR
        else:  # "low" default
            max_dim = 1024
            resample = Image.Resampling.BILINEAR

        img.thumbnail((max_dim, max_dim), resample)
        out = apply_effects(img, hue_shift_deg=hue, sat_mult=sat, val_mult=val, sharp_mult=sharp)
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        return {"effected": buf.getvalue(), "error": None}
    except Exception:
        return {"effected": None, "error": "Failed to apply effects (preview)"}

@component
def ImagePreview(self, images, effects, on_change):
    """
    images: list[str] (file paths)
    effects: dict with keys hue, sat, val, sharp
    """
    state, set_state = use_state({
        "error": None,
        "data": None,               # original PNG bytes
        "effected_data": None,      # PNG bytes after apply_effects (preview size)
        "name": None,
        "index": 0,                 # change by prev and next
        "status": "idle",           # "loading" | "idle"
        "effect_status": "original" # "original"  | "effectable"
    })

    image_index = state["index"]
    image_path = images[image_index] if images and images[image_index] is not None else None 
    image_name = state["name"]
    data = state["data"]
    effected_data = state["effected_data"]
    is_loading = state["status"] == "loading"
    is_original = state["effect_status"] == "original"

    def updater_state(payload):
        set_state(lambda prev: {**prev, **payload})
        if "effect_status" in payload: 
            on_change(payload["effect_status"])

    def step(kind):
        if kind == "prev" and (image_index > 0 and image_index < len(images)):
            set_state(lambda prev: {**prev, "index": prev["index"]-1, "data": None, "effected_data": None})
        elif kind == "next" and (image_index >= 0 and image_index < len(images)-1):
            set_state(lambda prev: {**prev, "index": prev["index"]+1, "data": None, "effected_data": None})

    async def run_load_image():
        try:
            if image_path is not None and state["data"] is None:
                set_state(lambda prev: {**prev, "status": "loading" })
                worker = partial(image_load, image_path)
                data_bytes = await run_subprocess_with_callback(worker, updater_state)
                set_state(lambda prev: {**prev, "data": data_bytes, "error": None, "status": "idle", "effected_data": None})
        except asyncio.CancelledError:
            set_state(lambda prev: {**prev, "error": "Cancelled", "status": "idle" })
            raise 
        except Exception:
            set_state(lambda prev: {**prev, "error": "Unknown: failed to load the image", "status": "idle" })

    async def run_make_image():
        try:
            # Only compute if we have original data AND user wants effects
            if state["data"] is not None and state["effect_status"] == "effectable":
                set_state(lambda prev: {**prev, "status": "loading"})
                worker = partial(
                    make_image,  
                    state["data"],
                    float(effects["hue"]),
                    float(effects["sat"]),
                    float(effects["val"]),
                    float(effects["sharp"]),
                    "fast",  
                )
                result = await run_subprocess_with_callback(worker, updater_state)
                if result.get("error"):
                    set_state(lambda prev: {**prev, "error": result["error"], "status": "idle"})
                else:
                    set_state(lambda prev: {**prev, "effected_data": result["effected"], "error": None, "status": "idle"})
        except asyncio.CancelledError:
            set_state(lambda prev: {**prev, "error": "Cancelled", "status": "idle"})
            raise
        except Exception:
            set_state(lambda prev: {**prev, "error": "Unknown: failed to apply effects", "status": "idle"})

    use_async(run_load_image, (
        image_path, 
        len(images)
    ))

    use_async(run_make_image, (
        state["effect_status"],
        state["data"],
        effects["hue"], effects["sat"], effects["val"], effects["sharp"]
    ))

    with VBoxView(style={"margin-top": 10}):
        with HBoxView(style={
            "min-width": 240,
            "min-height": 180,
            "border": "1px solid #ccc",
            "background-color": "#f6f6f6",
            "align": "center",
            "padding": 8,
        }):
            # show original or effected (fallback to original while effect computes)
            shown_bytes = data if is_original else (effected_data or data)
            if shown_bytes:
                # Force repaint when bytes or mode change to avoid stale rendering
                img_el = ImageUI(bytes_to_qpixmap(shown_bytes), 
                                 aspect_ratio_mode=AspectRatioMode.KeepAspectRatio,
                                 style={"border": "1px solid #ddd"})
                img_el.set_key(f"{image_name or ''}:{'orig' if is_original else 'fx'}:"
                               f"{effects['hue']:.2f}-{effects['sat']:.3f}-{effects['val']:.3f}-{effects['sharp']:.3f}")
            else:
                Label("Please wait...." if is_loading else "No image yet", style={"color": "#888", "font-size": 12})
        if state["data"]:
            with VBoxView(style={"align": "center"}):
                CheckBox(text="Show Original", checked=is_original, on_change=lambda _: updater_state({"effect_status": "effectable" if state["effect_status"] == "original" else "original"}))
            with HBoxView(style={ "padding": 5, "margin-top": 8, "padding-left": 5, "padding-right": 5 }) :
                Button("Prev", on_click=lambda _: step("prev"))
                Label(image_name or "-", style={"align": "center"})
                Button("Next", on_click=lambda _: step("next"))

@component
def MyApp(self):
    state, set_state = use_state({
        "source_dir": None,     # dir for all images inputs
        "output_dir": None,     # dir for export
        "images": [],           # list[str] of file paths
        # effect configuration, user can adjust in ImagePreview
        "image_effect": {"hue": 0.0, "sat": 1.0, "val": 1.0, "sharp": 1.0},
        "preview_status": "original",
    })

    def updater(payload):
        set_state(lambda prev: {**prev, **payload})

    source_dir = state["source_dir"]
    output_dir = state["output_dir"]
    source_images = state["images"]            
    effects = state["image_effect"]

    is_empty_source_images = len(source_images) == 0 
    is_disabled_effect = output_dir is None and is_empty_source_images
    is_original = state["preview_status"] == "original"

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

        ImagePreview(images=source_images, effects=effects, on_change=lambda status: updater({"preview_status": status}))

        with VBoxView(style={"padding": 10} ):
            with HBoxView():
                Label(f"Source Dir: {source_dir or ''}")
                Button("Pick Source Dir", on_click=select_source_directory)

            with HBoxView():
                Label(f"Output Dir: {output_dir or ''}")
                Button("Pick Output Dir", on_click=select_output_directory)

            Effects(title="Effects", 
                    effects=effects, 
                    is_disabled=is_original,
                    on_change=lambda effects: updater({"image_effect": effects}))

            with HBoxView(style={"margin-top": 10}):
                Button("Save Processed", on_click=save)

if __name__ == "__main__":
    App(MyApp()).start()
