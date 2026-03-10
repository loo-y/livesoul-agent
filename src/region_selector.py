from __future__ import annotations

import logging
import platform

from PIL import Image, ImageTk

from .config import AppConfig
from .screenshot import ScreenshotCapture

logger = logging.getLogger(__name__)


class RegionSelector:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def select_region(self) -> tuple[int, int, int, int]:
        if self.config.screenshot_image_path:
            raise RuntimeError(
                "Interactive region selection is unavailable when SCREENSHOT_IMAGE_PATH is set."
            )

        image = ScreenshotCapture(self.config)._capture_image()
        region = self._select_region(image)
        self.config.barrage_region_x = region[0]
        self.config.barrage_region_y = region[1]
        self.config.barrage_region_w = region[2]
        self.config.barrage_region_h = region[3]
        logger.info("Selected barrage region for current session: %s", region)
        return region

    def _select_region(self, image: Image.Image) -> tuple[int, int, int, int]:
        try:
            import tkinter as tk
        except Exception as exc:  # pragma: no cover - GUI availability depends on host
            raise RuntimeError(self._tk_error_message()) from exc

        root = tk.Tk()
        root.title("Select barrage region")
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        with_context = self._set_window_attributes(root)
        root.configure(cursor="crosshair")

        photo = ImageTk.PhotoImage(image)
        canvas = tk.Canvas(root, width=image.width, height=image.height, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_image(0, 0, anchor="nw", image=photo)
        if with_context:
            canvas.create_rectangle(0, 0, image.width, image.height, fill="black", stipple="gray50")
        canvas.create_text(
            20,
            20,
            anchor="nw",
            text="Drag to select barrage area. Press Enter to confirm, Esc to cancel.",
            fill="#ffeb3b",
            font=("Helvetica", 20, "bold"),
        )

        start_x = 0
        start_y = 0
        rect_id: int | None = None
        result: dict[str, tuple[int, int, int, int] | None] = {"region": None}

        def on_press(event: tk.Event) -> None:
            nonlocal start_x, start_y, rect_id
            start_x, start_y = event.x, event.y
            if rect_id is not None:
                canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(
                start_x,
                start_y,
                start_x,
                start_y,
                outline="#00e5ff",
                width=3,
            )

        def on_drag(event: tk.Event) -> None:
            if rect_id is not None:
                canvas.coords(rect_id, start_x, start_y, event.x, event.y)

        def on_release(event: tk.Event) -> None:
            x1, y1 = min(start_x, event.x), min(start_y, event.y)
            x2, y2 = max(start_x, event.x), max(start_y, event.y)
            width, height = x2 - x1, y2 - y1
            if width > 5 and height > 5:
                result["region"] = (x1, y1, width, height)

        def confirm(_event: tk.Event | None = None) -> None:
            root.quit()

        def cancel(_event: tk.Event | None = None) -> None:
            result["region"] = None
            root.quit()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        root.bind("<Return>", confirm)
        root.bind("<Escape>", cancel)

        root.mainloop()
        root.destroy()

        region = result["region"]
        if region is None:
            raise RuntimeError("Region selection was cancelled.")
        return region

    def _set_window_attributes(self, root: object) -> bool:
        system = platform.system().lower()
        try:
            if system == "darwin":
                root.attributes("-alpha", 0.92)
            else:
                root.attributes("-alpha", 0.94)
            return True
        except Exception:
            return False

    def _tk_error_message(self) -> str:
        system = platform.system().lower()
        base = "tkinter is required for interactive region selection."
        if system == "darwin":
            return f"{base} On macOS, install a Python build with Tk support, for example via python.org or Homebrew."
        return base
