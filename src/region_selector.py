from __future__ import annotations

import json
import logging
import platform
import subprocess
import tempfile
from typing import Any

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
            logger.warning("tkinter region selector unavailable: %s", exc)
            return self._select_region_with_opencv(image)

        try:
            return self._select_region_with_tk(image, tk)
        except Exception as exc:  # pragma: no cover - GUI availability depends on host
            logger.warning("tkinter region selector failed; falling back to OpenCV: %s", exc)
            try:
                return self._select_region_with_opencv(image)
            except Exception as opencv_exc:
                logger.warning("OpenCV region selector failed: %s", opencv_exc)
                if platform.system().lower() == "windows":
                    return self._select_region_with_powershell(image)
                raise

    def _select_region_with_tk(self, image: Image.Image, tk: Any) -> tuple[int, int, int, int]:
        root = tk.Tk()
        try:
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
            region = result["region"]
            if region is None:
                raise RuntimeError("Region selection was cancelled.")
            return region
        finally:
            root.destroy()

    def _select_region_with_opencv(self, image: Image.Image) -> tuple[int, int, int, int]:
        try:
            import cv2
            import numpy as np
        except Exception as exc:  # pragma: no cover - depends on host packages
            raise RuntimeError(self._tk_error_message()) from exc

        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        overlay = frame.copy()
        cv2.putText(
            overlay,
            "Drag to select barrage area, then press Enter or Space. Esc cancels.",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

        window_name = "Select barrage region"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        try:
            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        except Exception:
            pass
        try:
            cv2.imshow(window_name, overlay)
            x, y, w, h = cv2.selectROI(window_name, overlay, showCrosshair=True, fromCenter=False)
        finally:
            cv2.destroyWindow(window_name)

        if w <= 5 or h <= 5:
            raise RuntimeError("Region selection was cancelled.")
        return (int(x), int(y), int(w), int(h))

    def _select_region_with_powershell(self, image: Image.Image) -> tuple[int, int, int, int]:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_image:
            temp_path = temp_image.name
        try:
            image.save(temp_path)
            script = rf"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$imagePath = '{temp_path.replace("'", "''")}'
$image = [System.Drawing.Image]::FromFile($imagePath)
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Select barrage region'
$form.WindowState = 'Maximized'
$form.FormBorderStyle = 'None'
$form.TopMost = $true
$form.KeyPreview = $true
$form.BackColor = [System.Drawing.Color]::Black
$form.Cursor = [System.Windows.Forms.Cursors]::Cross

$picture = New-Object System.Windows.Forms.PictureBox
$picture.Dock = 'Fill'
$picture.Image = $image
$picture.SizeMode = 'Normal'
$form.Controls.Add($picture)

$instruction = New-Object System.Windows.Forms.Label
$instruction.AutoSize = $true
$instruction.BackColor = [System.Drawing.Color]::FromArgb(180, 0, 0, 0)
$instruction.ForeColor = [System.Drawing.Color]::Gold
$instruction.Font = New-Object System.Drawing.Font('Segoe UI', 14, [System.Drawing.FontStyle]::Bold)
$instruction.Padding = New-Object System.Windows.Forms.Padding(12, 8, 12, 8)
$instruction.Text = 'Drag to select barrage area. Press Enter to confirm, Esc to cancel.'
$instruction.Location = New-Object System.Drawing.Point(20, 20)
$form.Controls.Add($instruction)
$instruction.BringToFront()

$script:startPoint = $null
$script:endPoint = $null
$script:isDragging = $false
$script:selection = $null

$picture.add_MouseDown({{
    if ($_.Button -eq [System.Windows.Forms.MouseButtons]::Left) {{
        $script:startPoint = $_.Location
        $script:endPoint = $_.Location
        $script:isDragging = $true
        $picture.Invalidate()
    }}
}})

$picture.add_MouseMove({{
    if ($script:isDragging) {{
        $script:endPoint = $_.Location
        $picture.Invalidate()
    }}
}})

$picture.add_MouseUp({{
    if ($script:isDragging) {{
        $script:endPoint = $_.Location
        $script:isDragging = $false
        $x = [Math]::Min($script:startPoint.X, $script:endPoint.X)
        $y = [Math]::Min($script:startPoint.Y, $script:endPoint.Y)
        $w = [Math]::Abs($script:startPoint.X - $script:endPoint.X)
        $h = [Math]::Abs($script:startPoint.Y - $script:endPoint.Y)
        if ($w -gt 5 -and $h -gt 5) {{
            $script:selection = @{{ x = $x; y = $y; w = $w; h = $h }}
        }}
        $picture.Invalidate()
    }}
}})

$picture.add_Paint({{
    if ($script:startPoint -and $script:endPoint) {{
        $x = [Math]::Min($script:startPoint.X, $script:endPoint.X)
        $y = [Math]::Min($script:startPoint.Y, $script:endPoint.Y)
        $w = [Math]::Abs($script:startPoint.X - $script:endPoint.X)
        $h = [Math]::Abs($script:startPoint.Y - $script:endPoint.Y)
        if ($w -gt 0 -and $h -gt 0) {{
            $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(70, 0, 229, 255))
            $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::DeepSkyBlue, 3)
            $_.Graphics.FillRectangle($brush, $x, $y, $w, $h)
            $_.Graphics.DrawRectangle($pen, $x, $y, $w, $h)
            $brush.Dispose()
            $pen.Dispose()
        }}
    }}
}})

$form.add_KeyDown({{
    if ($_.KeyCode -eq [System.Windows.Forms.Keys]::Escape) {{
        $script:selection = $null
        $form.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
        $form.Close()
    }} elseif ($_.KeyCode -eq [System.Windows.Forms.Keys]::Enter) {{
        $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
        $form.Close()
    }}
}})

[void]$form.ShowDialog()

$image.Dispose()
$form.Dispose()

if ($script:selection -eq $null) {{
    Write-Output 'CANCELLED'
}} else {{
    $script:selection | ConvertTo-Json -Compress
}}
"""
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            try:
                subprocess.run(["cmd", "/c", "del", "/f", "/q", temp_path], check=False)
            except Exception:
                pass

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(f"PowerShell region selector failed: {stderr or result.returncode}")

        output = (result.stdout or "").strip()
        if not output or output == "CANCELLED":
            raise RuntimeError("Region selection was cancelled.")
        region = json.loads(output)
        return (int(region["x"]), int(region["y"]), int(region["w"]), int(region["h"]))

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
