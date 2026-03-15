from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

from .config import ensure_runtime_config, list_profiles, load_settings as load_json_settings, save_settings as save_json_settings

try:
    from PySide6.QtCore import QPoint, QProcess, QTimer, Qt
    from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPen, QPixmap, QTextCursor, QTextOption
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QPlainTextEdit,
        QScrollArea,
        QSplitter,
        QTabWidget,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - optional GUI dependency
    raise SystemExit(
        "PySide6 is required for the desktop GUI. Install it with `pip install PySide6`."
    ) from exc


def _resolve_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


ROOT = _resolve_app_root()
RUNTIME_CONFIG_JSON = ROOT / "runtime" / "config.json"
PROFILES_DIR = ROOT / "profiles"
PROMPT_FILE_SPECS = (
    ("SOUL.md", "角色灵魂"),
    ("IDENTITY.md", "基础身份"),
    ("USER.md", "用户约束"),
    ("LLM_SYSTEM.md", "文本模型提示词"),
    ("VISION_PROMPT.md", "视觉模型提示词"),
)
RUNTIME_STDOUT = ROOT / "runtime" / "app.stdout.log"
RUNTIME_STDERR = ROOT / "runtime" / "app.stderr.log"
RUNTIME_FRAMES = ROOT / "runtime" / "frames"
RUNTIME_MEMORY_JSON = ROOT / "runtime" / "memory" / "session_memory.json"
RUNTIME_REGION_JSON = ROOT / "runtime" / "current_region.json"
REGION_LOG_PATTERN = re.compile(r"Selected barrage region for current session: \((\d+), (\d+), (\d+), (\d+)\)")
LOG_LEVEL_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} [\d:,]+)\s+\|\s+(?P<level>[A-Z]+)\s+\|\s+(?P<logger>[^|]+)\s+\|\s+(?P<message>.*)$"
)


@dataclass(slots=True)
class FieldSpec:
    key: str
    label: str
    kind: str = "text"
    placeholder: str = ""
    options: tuple[str, ...] = ()


SETTINGS_FIELDS = (
    FieldSpec("AUTO_SELECT_REGION", "启动时重新选区", kind="bool"),
    FieldSpec("SCREENSHOT_INTERVAL", "截图间隔", placeholder="0.5"),
    FieldSpec("VISION_TIMEOUT_SECONDS", "视觉超时秒数", placeholder="300"),
    FieldSpec("VISION_MODEL_NAME", "视觉模型"),
    FieldSpec("VISION_API_BASE", "视觉接口地址"),
    FieldSpec("LLM_MODEL_NAME", "回复模型"),
    FieldSpec("LLM_API_BASE", "回复接口地址"),
    FieldSpec(
        "TTS_PROVIDER",
        "语音提供商",
        kind="combo",
        options=("siliconflow", "minimaxi"),
    ),
    FieldSpec("TTS_MODEL_NAME", "语音模型"),
    FieldSpec("TTS_API_ENDPOINT", "语音接口地址"),
    FieldSpec("TTS_VOICE", "音色"),
    FieldSpec("TTS_RESPONSE_FORMAT", "音频格式", kind="combo", options=("mp3", "wav", "opus", "ogg")),
    FieldSpec("TTS_SAMPLE_RATE", "采样率", placeholder="44100"),
    FieldSpec("TTS_STREAM", "流式返回", kind="bool"),
    FieldSpec("LOG_LEVEL", "日志级别", kind="combo", options=("DEBUG", "INFO", "WARNING", "ERROR")),
)

SUPPORTED_TTS_PROVIDERS = ("siliconflow", "minimaxi")


class JsonConfigStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        ensure_runtime_config(base_dir)

    def load(self) -> dict[str, object]:
        return load_json_settings(self.base_dir)

    def save(self, payload: dict[str, object]) -> None:
        save_json_settings(payload, self.base_dir)

    def list_profiles(self) -> list[dict[str, str]]:
        return list_profiles(self.base_dir)


class PreviewLabel(QLabel):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(120)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("previewPanel")
        self.setText(f"{title}\n暂无画面")

    def set_image(self, path: Path | None) -> None:
        if path is None or not path.exists():
            self.setText(f"{self.title}\n暂无画面")
            self.setPixmap(QPixmap())
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.setText(f"{self.title}\n预览不可用")
            self.setPixmap(QPixmap())
            return
        scaled = pixmap.scaled(
            max(self.width() - 24, 120),
            max(self.height() - 24, 120),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        current = self.pixmap()
        if current and not current.isNull():
            self.setPixmap(
                current.scaled(
                    max(self.width() - 24, 120),
                    max(self.height() - 24, 120),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )


class RegionOverlay(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self.label = "当前监控区域"
        self.drag_enabled = False
        self.drag_offset = QPoint()
        self.region_changed_callback = None
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

    def show_region(self, x: int, y: int, w: int, h: int) -> None:
        self.setGeometry(x, y, w, h)
        self.show()
        self.raise_()
        self.update()

    def set_drag_enabled(self, enabled: bool) -> None:
        self.drag_enabled = enabled
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not enabled)
        self.label = "拖动中：调整监控区域" if enabled else "当前监控区域"
        self.update()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if not self.drag_enabled or event.button() != Qt.MouseButton.LeftButton:
            return
        self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if not self.drag_enabled or not event.buttons() & Qt.MouseButton.LeftButton:
            return
        new_top_left = event.globalPosition().toPoint() - self.drag_offset
        self.move(new_top_left)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if not self.drag_enabled or event.button() != Qt.MouseButton.LeftButton:
            return
        if callable(self.region_changed_callback):
            geometry = self.geometry()
            self.region_changed_callback(geometry.x(), geometry.y(), geometry.width(), geometry.height())
        event.accept()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        border = QColor("#ff8a3d")
        fill = QColor(255, 138, 61, 32)
        pen = QPen(border, 3)
        painter.setPen(pen)
        painter.setBrush(fill)
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(rect, 14, 14)
        painter.fillRect(12, 12, 152, 34, QColor(20, 24, 30, 190))
        painter.setPen(QColor("#fff8ef"))
        painter.drawText(24, 35, self.label)


class LiveSoulMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LiveSoul 控制台")
        self.resize(1280, 640)
        self.setMinimumSize(940, 520)
        self.python_executable = sys.executable
        self.current_region: tuple[int, int, int, int] | None = None

        self.config_store = JsonConfigStore(ROOT)
        self.process = QProcess(self)
        self.process.setProgram(self.python_executable)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.append_process_output)
        self.process.stateChanged.connect(self.handle_process_state_change)
        self.process.finished.connect(self.handle_process_finished)

        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(1800)
        self.preview_timer.timeout.connect(self.refresh_runtime_views)
        self.preview_timer.start()

        self.status_badge = QLabel("待机")
        self.status_badge.setObjectName("statusBadge")
        self.status_summary = QLabel("准备就绪。你可以先检查配置，或直接点击“启动 LiveSoul”。")
        self.status_summary.setObjectName("statusSummary")
        self.status_summary.setWordWrap(True)
        self.overlay = RegionOverlay()
        self.overlay.region_changed_callback = self.handle_overlay_region_changed

        self.info_labels: dict[str, QLabel] = {}
        self.prompt_editors: dict[str, QTextEdit] = {}
        self.setting_widgets: dict[str, QWidget] = {}
        self.current_settings_payload: dict[str, object] = {}
        self.active_profile_id = "default"
        self.log_entries: list[str] = []
        self.last_frame_preview = PreviewLabel("最近一次裁剪画面")
        self.memory_preview = QPlainTextEdit()
        self.memory_preview.setReadOnly(True)
        self.memory_preview.setPlaceholderText("这里会显示最近识别到的弹幕和回复内容。")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("启动后，这里会实时滚动运行日志。")
        self.log_output.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)

        self.init_ui()
        self._apply_interaction_cues()
        self.load_prompt_files()
        self.load_settings()
        self.refresh_runtime_views()

    def init_ui(self) -> None:
        self._apply_window_style()
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        outer.addWidget(self._build_header())
        outer.addWidget(self._build_tab_widget(), stretch=1)
        self.setCentralWidget(central)

        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh_runtime_views)
        self.addAction(refresh_action)
        refresh_action.setShortcut("Ctrl+R")

    def _apply_window_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f4efe7;
                color: #1f2328;
                font-family: "Segoe UI Variable", "Aptos", "Segoe UI";
                font-size: 14px;
            }
            QTabWidget::pane {
                border: 1px solid #d8cfc1;
                background: #fcfaf6;
                border-radius: 18px;
                top: -1px;
            }
            QTabBar::tab {
                background: #ece2d4;
                color: #5b4d3a;
                padding: 11px 18px;
                margin-right: 8px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #fffdf9;
                color: #132029;
            }
            QGroupBox {
                border: 1px solid #ded5c8;
                border-radius: 18px;
                margin-top: 14px;
                background: #fffdf9;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                color: #634b2c;
            }
            QPushButton {
                background: #1f5f5b;
                color: white;
                border: none;
                border-radius: 14px;
                padding: 12px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #174f4b;
            }
            QPushButton:pressed {
                background: #103c39;
                padding-top: 13px;
                padding-bottom: 11px;
            }
            QPushButton:disabled {
                background: #c5bfb2;
                color: #726a5f;
            }
            QPushButton[variant="ghost"] {
                background: #e8f1ef;
                color: #1f5f5b;
                border: 1px solid #bcd4cf;
            }
            QPushButton[variant="ghost"]:hover {
                background: #dbeae7;
            }
            QPushButton[variant="ghost"]:pressed {
                background: #cfe1dd;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
                background: #fffdf9;
                border: 1px solid #d7cdbc;
                border-radius: 12px;
                padding: 10px 12px;
                selection-background-color: #c9853e;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
                border: 1px solid #1f5f5b;
            }
            QCheckBox {
                spacing: 8px;
            }
            QLabel#heroTitle {
                font-size: 32px;
                font-weight: 700;
                color: #1d2430;
            }
            QLabel#heroSubtitle {
                color: #665d52;
                font-size: 14px;
            }
            QLabel#statusBadge {
                background: #f3e9d8;
                border: 1px solid #dcc8a6;
                border-radius: 18px;
                padding: 7px 14px;
                font-weight: 700;
                color: #6a4e23;
            }
            QLabel#statusSummary {
                background: #fff7ec;
                border: 1px solid #ead9bf;
                border-radius: 16px;
                padding: 12px 14px;
                color: #5d5348;
                min-height: 52px;
            }
            QFrame[card="true"] {
                background: #fffdf9;
                border: 1px solid #ddd3c6;
                border-radius: 18px;
            }
            QLabel[cardTitle="true"] {
                color: #70563c;
                font-size: 12px;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }
            QLabel[cardValue="true"] {
                color: #1f2328;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#previewPanel {
                background: #efe8de;
            }
            """
        )

    def _build_header(self) -> QWidget:
        container = QFrame()
        container.setProperty("card", True)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(18)

        left = QVBoxLayout()
        title = QLabel("LiveSoul 控制台")
        title.setObjectName("heroTitle")
        subtitle = QLabel(
            "在一个窗口里完成弹幕监控、区域选择、提示词编辑、运行状态查看和语音播放。"
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)
        left.addWidget(title)
        left.addWidget(subtitle)

        right = QVBoxLayout()
        right.setSpacing(10)
        pin_button = QPushButton("窗口置顶")
        pin_button.setProperty("variant", "ghost")
        pin_button.setCheckable(True)
        pin_button.toggled.connect(self.toggle_pin)
        self.pin_button = pin_button
        overlay_button = QPushButton("显示监控框")
        overlay_button.setProperty("variant", "ghost")
        overlay_button.setCheckable(True)
        overlay_button.setChecked(True)
        overlay_button.toggled.connect(self.toggle_overlay)
        self.overlay_button = overlay_button
        adjust_overlay_button = QPushButton("拖动监控框")
        adjust_overlay_button.setProperty("variant", "ghost")
        adjust_overlay_button.setCheckable(True)
        adjust_overlay_button.toggled.connect(self.toggle_overlay_adjust_mode)
        self.adjust_overlay_button = adjust_overlay_button
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(pin_button)
        button_row.addWidget(overlay_button)
        button_row.addWidget(adjust_overlay_button)
        right.addLayout(button_row)
        status_row = QHBoxLayout()
        status_row.addStretch(1)
        status_row.addWidget(self.status_badge, alignment=Qt.AlignmentFlag.AlignRight)
        right.addLayout(status_row)
        self.status_summary.setMinimumWidth(340)
        self.status_summary.setMaximumWidth(420)
        right.addWidget(self.status_summary, alignment=Qt.AlignmentFlag.AlignRight)
        right.addStretch(1)

        layout.addLayout(left, stretch=3)
        layout.addLayout(right, stretch=1)
        return container

    def _build_tab_widget(self) -> QWidget:
        tabs = QTabWidget()
        tabs.addTab(self._make_scrollable(self._build_dashboard_tab()), "总览")
        tabs.addTab(self._make_scrollable(self._build_prompts_tab()), "人设与提示词")
        tabs.addTab(self._make_scrollable(self._build_settings_tab()), "运行配置")
        tabs.addTab(self._make_scrollable(self._build_monitor_tab()), "监控与预览")
        return tabs

    def _make_scrollable(self, content: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        return scroll

    def _build_dashboard_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        for index, (title, key) in enumerate(
            (
                ("当前状态", "runtime_state"),
                ("监控区域", "region"),
                ("语音配置", "tts"),
                ("最近更新", "updated_at"),
            )
        ):
            cards.addWidget(self._create_info_card(title, key), 0, index)
        layout.addLayout(cards)

        actions_row = QHBoxLayout()
        self.start_button = QPushButton("启动 LiveSoul")
        self.start_button.clicked.connect(self.start_runtime)
        self.stop_button = QPushButton("停止运行")
        self.stop_button.setProperty("variant", "ghost")
        self.stop_button.clicked.connect(self.stop_runtime)
        self.stop_button.setEnabled(False)
        self.refresh_button = QPushButton("刷新界面")
        self.refresh_button.setProperty("variant", "ghost")
        self.refresh_button.clicked.connect(self.refresh_runtime_views)
        actions_row.addWidget(self.start_button)
        actions_row.addWidget(self.stop_button)
        actions_row.addWidget(self.refresh_button)
        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._wrap_group("实时日志", self.log_output))
        splitter.addWidget(self._wrap_group("最近记忆", self.memory_preview))
        splitter.setSizes([760, 320])
        layout.addWidget(splitter, stretch=1)
        return tab

    def _build_prompts_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        profile_bar = QHBoxLayout()
        profile_label = QLabel("当前人设")
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self.handle_profile_changed)
        profile_hint = QLabel("同一套人设下可同时维护角色提示词、文本模型提示词和视觉识别提示词。")
        profile_hint.setStyleSheet("color:#7b6d5d;")
        profile_bar.addWidget(profile_label)
        profile_bar.addWidget(self.profile_combo)
        profile_bar.addWidget(profile_hint)
        profile_bar.addStretch(1)
        layout.addLayout(profile_bar)
        editor_grid = QGridLayout()
        editor_grid.setHorizontalSpacing(12)
        editor_grid.setVerticalSpacing(12)

        for index, (filename, title) in enumerate(PROMPT_FILE_SPECS):
            editor = QTextEdit()
            editor.setPlaceholderText(f"在这里编辑 {title}")
            editor.setMinimumHeight(120)
            self.prompt_editors[filename] = editor

            group = QGroupBox(title)
            group_layout = QVBoxLayout(group)
            path_label = QLabel(filename)
            path_label.setStyleSheet("color:#7b6d5d;font-size:12px;")
            path_label.setObjectName(f"pathLabel:{filename}")
            group_layout.addWidget(path_label)
            group_layout.addWidget(editor)
            editor_grid.addWidget(group, index // 2, index % 2)

        layout.addLayout(editor_grid)
        buttons = QHBoxLayout()
        reload_button = QPushButton("重新读取文件")
        reload_button.setProperty("variant", "ghost")
        reload_button.clicked.connect(self.load_prompt_files)
        save_button = QPushButton("保存提示词")
        save_button.clicked.connect(self.save_prompt_files)
        buttons.addWidget(save_button)
        buttons.addWidget(reload_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return tab

    def _build_settings_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        form_box = QGroupBox("运行参数")
        form = QFormLayout(form_box)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(14)

        for spec in SETTINGS_FIELDS:
            widget: QWidget
            if spec.kind == "combo":
                combo = QComboBox()
                combo.addItems(spec.options)
                widget = combo
            elif spec.kind == "bool":
                checkbox = QCheckBox()
                widget = checkbox
            else:
                line = QLineEdit()
                line.setPlaceholderText(spec.placeholder)
                if "KEY" in spec.key:
                    line.setEchoMode(QLineEdit.EchoMode.Password)
                widget = line
            self.setting_widgets[spec.key] = widget
            form.addRow(spec.label, widget)

        api_group = QGroupBox("接口密钥")
        api_form = QFormLayout(api_group)
        self.vision_api_key = self._create_secret_input()
        self.llm_api_key = self._create_secret_input()
        self.tts_api_key = self._create_secret_input()
        api_form.addRow("视觉 API Key", self._wrap_secret_input(self.vision_api_key))
        api_form.addRow("回复 API Key", self._wrap_secret_input(self.llm_api_key))
        api_form.addRow("语音 API Key", self._wrap_secret_input(self.tts_api_key))

        footer = QHBoxLayout()
        save_button = QPushButton("保存运行配置")
        save_button.clicked.connect(self.save_settings)
        dotenv_button = QPushButton("打开项目目录")
        dotenv_button.setProperty("variant", "ghost")
        dotenv_button.clicked.connect(self.open_project_folder)
        footer.addWidget(save_button)
        footer.addWidget(dotenv_button)
        footer.addStretch(1)

        layout.addWidget(form_box)
        layout.addWidget(api_group)
        layout.addLayout(footer)
        return tab

    def _build_monitor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        controls = QHBoxLayout()
        choose_image = QPushButton("选择静态截图")
        choose_image.setProperty("variant", "ghost")
        choose_image.clicked.connect(self.choose_static_image)
        clear_image = QPushButton("清除静态截图")
        clear_image.setProperty("variant", "ghost")
        clear_image.clicked.connect(self.clear_static_image)
        controls.addWidget(choose_image)
        controls.addWidget(clear_image)
        controls.addStretch(1)
        layout.addLayout(controls)

        previews = QHBoxLayout()
        previews.addWidget(self._wrap_group("最新裁剪预览", self.last_frame_preview), stretch=3)
        runtime_panel = QWidget()
        runtime_layout = QVBoxLayout(runtime_panel)
        runtime_layout.setContentsMargins(0, 0, 0, 0)
        runtime_layout.setSpacing(10)
        self.runtime_notes = QPlainTextEdit()
        self.runtime_notes.setReadOnly(True)
        self.runtime_notes.setPlaceholderText("这里会显示当前区域、最近弹幕、最近回复等关键运行信息。")
        runtime_layout.addWidget(self._wrap_group("运行摘要", self.runtime_notes))
        previews.addWidget(runtime_panel, stretch=2)
        layout.addLayout(previews, stretch=1)
        return tab

    def _create_info_card(self, title: str, key: str) -> QWidget:
        card = QFrame()
        card.setProperty("card", True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setProperty("cardTitle", True)
        value = QLabel("—")
        value.setProperty("cardValue", True)
        value.setWordWrap(True)
        detail = QLabel("")
        detail.setStyleSheet("color:#7b6d5d;")
        detail.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(value)
        layout.addWidget(detail)
        self.info_labels[key] = value
        self.info_labels[f"{key}_detail"] = detail
        return card

    def _create_secret_input(self) -> QLineEdit:
        line = QLineEdit()
        line.setEchoMode(QLineEdit.EchoMode.Password)
        line.setPlaceholderText("未填写时请保持为空")
        return line

    def _wrap_secret_input(self, line_edit: QLineEdit) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        toggle = QToolButton()
        toggle.setText("显示")
        toggle.setCheckable(True)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)

        def handle_toggle(checked: bool) -> None:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)
            toggle.setText("隐藏" if checked else "显示")

        toggle.toggled.connect(handle_toggle)
        layout.addWidget(line_edit, stretch=1)
        layout.addWidget(toggle)
        return wrapper

    def _wrap_group(self, title: str, widget: QWidget) -> QWidget:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.addWidget(widget)
        return group

    def _current_profile_dir(self) -> Path:
        return PROFILES_DIR / self.active_profile_id

    def _prompt_path(self, filename: str) -> Path:
        return self._current_profile_dir() / filename

    def _populate_profile_combo(self) -> None:
        profiles = self.config_store.list_profiles()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in profiles:
            label = profile["name"]
            description = profile.get("description") or ""
            if description:
                label = f"{label}  {description}"
            self.profile_combo.addItem(label, profile["id"])
        index = self.profile_combo.findData(self.active_profile_id)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
        self.profile_combo.blockSignals(False)

    def append_process_output(self) -> None:
        payload = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if not payload:
            return
        self._append_log_payload(payload)
        self.update_runtime_summary_from_log(payload)

    def _apply_interaction_cues(self) -> None:
        for widget_type in (QPushButton, QCheckBox, QComboBox):
            for widget in self.findChildren(widget_type):
                widget.setCursor(Qt.CursorShape.PointingHandCursor)

    def update_runtime_summary_from_log(self, payload: str) -> None:
        lines = [line.strip() for line in payload.splitlines() if line.strip()]
        if not lines:
            return
        latest = lines[-1]
        if "Selected barrage region" in latest:
            self.status_summary.setText("已完成监控区域选择，后续会持续按该区域裁剪。")
            self.info_labels["region_detail"].setText("已完成区域选择，后续会持续按该区域裁剪。")
            match = REGION_LOG_PATTERN.search(latest)
            if match:
                self.current_region = tuple(int(value) for value in match.groups())  # type: ignore[assignment]
                self.info_labels["region"].setText(
                    ", ".join(str(value) for value in self.current_region)
                )
                self._sync_overlay_visibility()
        if "LiveSoul agent started" in latest:
            self.status_summary.setText("主循环已启动，正在等待新画面。")
            self.info_labels["runtime_state"].setText("运行中")
            self.info_labels["runtime_state_detail"].setText("主循环已经启动，正在等待新画面。")
        if "Generated reply:" in latest:
            self.status_summary.setText("已生成回复，正在播放语音或等待播放完成。")
            self.info_labels["runtime_state_detail"].setText("已生成回复，正在播放或等待播放完成。")
        if "Recognized barrage via" in latest:
            self.status_summary.setText("已识别到新弹幕，识别链路工作正常。")
            self.info_labels["runtime_state_detail"].setText("已识别到新弹幕，识别链路工作正常。")
        if "Pipeline loop failed" in latest or "Traceback" in latest:
            self.status_badge.setText("异常")
            self.status_summary.setText("运行中出现错误，请查看实时日志。")
            self.info_labels["runtime_state"].setText("异常")
            self.info_labels["runtime_state_detail"].setText("运行中出现错误，请查看左侧日志。")

    def _append_log_payload(self, payload: str) -> None:
        lines = [line for line in payload.splitlines() if line.strip()]
        if not lines:
            return
        self.log_entries.extend(lines)
        self.log_entries = self.log_entries[-120:]
        self.log_output.setHtml("".join(self._render_log_line(line) for line in self.log_entries))
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)

    def _render_log_line(self, line: str) -> str:
        match = LOG_LEVEL_PATTERN.match(line.strip())
        if not match:
            return (
                "<div style='margin:0 0 10px 0;padding:10px 12px;border-radius:12px;"
                "background:#f4efe7;border:1px solid #dfd4c4;color:#544b40;'>"
                f"<div style='white-space:pre-wrap'>{escape(line)}</div>"
                "</div>"
            )

        level = match.group("level").upper()
        timestamp = self._display_timestamp(match.group("timestamp"))
        palette = {
            "DEBUG": ("#eef2f8", "#55749b", "#27496b"),
            "INFO": ("#edf6f3", "#5c8f82", "#1f5f5b"),
            "WARNING": ("#fff7e7", "#d49a2c", "#7b5200"),
            "ERROR": ("#fff0ee", "#db6d5f", "#8d2f25"),
            "CRITICAL": ("#fdecea", "#b73a31", "#7c1d16"),
        }
        background, badge, text_color = palette.get(level, ("#f4efe7", "#8d8274", "#544b40"))
        return (
            f"<div style='margin:0 0 10px 0;padding:12px 14px;border-radius:14px;background:{background};"
            "border:1px solid #ded5c8;'>"
            "<div style='display:flex;justify-content:space-between;gap:12px;margin-bottom:8px;'>"
            f"<span style='background:{badge};color:#fff;padding:3px 8px;border-radius:999px;font-size:12px;font-weight:700;'>{escape(level)}</span>"
            f"<span style='color:#756858;font-size:12px'>{escape(timestamp)}</span>"
            "</div>"
            f"<div style='color:#7d6d5b;font-size:12px;margin-bottom:6px'>{escape(match.group('logger').strip())}</div>"
            f"<div style='white-space:pre-wrap;color:{text_color};line-height:1.55'>{escape(match.group('message').strip())}</div>"
            "</div>"
        )

    def _display_timestamp(self, value: str) -> str:
        if not value:
            return "未知"
        normalized = value.strip().replace("T", " ")
        try:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
        normalized = re.sub(r"([.,]\d+)(?=(?:Z|[+-]\d{2}:\d{2})?$)", "", normalized)
        normalized = re.sub(r"(?:Z|[+-]\d{2}:\d{2})$", "", normalized)
        return normalized.strip()

    def handle_process_state_change(self, state: QProcess.ProcessState) -> None:
        running = state == QProcess.ProcessState.Running
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        if state == QProcess.ProcessState.NotRunning:
            self.status_badge.setText("待机")
            self.info_labels["runtime_state"].setText("未启动")
            self.info_labels["runtime_state_detail"].setText("点击“启动 LiveSoul”后会进入区域选择和主循环。")
            self.overlay.hide()
        elif state == QProcess.ProcessState.Starting:
            self.status_badge.setText("启动中")
            self.info_labels["runtime_state"].setText("启动中")
            self.info_labels["runtime_state_detail"].setText("正在拉起运行进程，请稍候。")
        else:
            self.status_badge.setText("运行中")
            self.info_labels["runtime_state"].setText("运行中")
            self.info_labels["runtime_state_detail"].setText("程序已启动，可以关注日志和预览。")
            self._sync_overlay_visibility()

    def handle_process_finished(self, *_args) -> None:
        self.status_summary.setText("运行已停止。你可以调整配置后重新启动。")
        self.refresh_runtime_views()

    def start_runtime(self) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        self.save_settings(silent=True)
        self.log_entries = []
        self.log_output.clear()
        if getattr(sys, "frozen", False):
            runtime_exe = ROOT / "LiveSoulRuntime.exe"
            self.process.setProgram(str(runtime_exe))
            self.process.setArguments([])
        else:
            self.process.setProgram(self.python_executable)
            self.process.setArguments(["-u", "-m", "src.main"])
        self.process.start()
        if not self.process.waitForStarted(5000):
            QMessageBox.critical(self, "启动失败", "LiveSoul 运行进程未能成功启动。")
            return
        self.status_summary.setText("已启动运行进程。接下来如果需要，会弹出区域选择窗口。")

    def stop_runtime(self) -> None:
        if self.process.state() == QProcess.ProcessState.NotRunning:
            return
        self.process.terminate()
        if not self.process.waitForFinished(5000):
            self.process.kill()
        self.status_summary.setText("已从界面停止运行。")

    def load_prompt_files(self) -> None:
        profile_dir = self._current_profile_dir()
        profile_dir.mkdir(parents=True, exist_ok=True)
        for filename, _title in PROMPT_FILE_SPECS:
            path = self._prompt_path(filename)
            self.prompt_editors[filename].setPlainText(path.read_text(encoding="utf-8") if path.exists() else "")
        self.status_summary.setText("人设提示词已载入，你可以直接在界面中修改。")

    def save_prompt_files(self) -> None:
        profile_dir = self._current_profile_dir()
        profile_dir.mkdir(parents=True, exist_ok=True)
        for filename, _title in PROMPT_FILE_SPECS:
            self._prompt_path(filename).write_text(self.prompt_editors[filename].toPlainText(), encoding="utf-8")
        self.status_summary.setText("当前人设文件已保存。下次生成回复时会读取最新内容。")
        QMessageBox.information(self, "保存成功", "当前人设文件已保存。")

    def handle_profile_changed(self) -> None:
        profile_id = self.profile_combo.currentData()
        if not profile_id or profile_id == self.active_profile_id:
            return
        self.active_profile_id = str(profile_id)
        self.current_settings_payload["active_profile_id"] = self.active_profile_id
        self.load_prompt_files()
        self.status_summary.setText("已切换人设。重新生成回复时会使用当前人设。")

    def load_settings(self) -> None:
        values = self.config_store.load()
        self.current_settings_payload = values
        self.active_profile_id = str(values.get("active_profile_id") or "default")
        self._populate_profile_combo()

        capture = values.get("capture", {})
        vision = values.get("vision", {})
        llm = values.get("llm", {})
        tts = values.get("tts", {})
        runtime = values.get("runtime", {})

        provider_value = str(tts.get("provider") or "").strip().lower()
        if provider_value and provider_value not in SUPPORTED_TTS_PROVIDERS:
            tts["provider"] = "siliconflow"
            self.status_summary.setText(
                f"检测到旧的语音提供商配置“{provider_value}”，界面已临时回退为 siliconflow。保存配置后会写回 runtime/config.json。"
            )
        for spec in SETTINGS_FIELDS:
            value = self._extract_field_value(spec.key, capture, vision, llm, tts, runtime)
            widget = self.setting_widgets[spec.key]
            if spec.kind == "combo":
                combo = widget  # type: ignore[assignment]
                index = combo.findText(str(value))
                if index >= 0:
                    combo.setCurrentIndex(index)
            elif spec.kind == "bool":
                widget.setChecked(bool(value))  # type: ignore[attr-defined]
            else:
                widget.setText("" if value in (None, "") else str(value))  # type: ignore[attr-defined]
        self.vision_api_key.setText(str(vision.get("api_key") or ""))
        self.llm_api_key.setText(str(llm.get("api_key") or ""))
        self.tts_api_key.setText(str(tts.get("api_key") or ""))
        self.info_labels["tts"].setText(str(tts.get("provider") or "—"))
        self.info_labels["tts_detail"].setText(str(tts.get("model") or ""))
        self._update_region_label(values)
        self._load_region_from_settings(values)
        self.load_prompt_files()

    def save_settings(self, silent: bool = False) -> None:
        payload = dict(self.current_settings_payload or self.config_store.load())
        capture = dict(payload.get("capture", {}))
        vision = dict(payload.get("vision", {}))
        llm = dict(payload.get("llm", {}))
        tts = dict(payload.get("tts", {}))
        runtime = dict(payload.get("runtime", {}))

        for spec in SETTINGS_FIELDS:
            widget = self.setting_widgets[spec.key]
            if spec.kind == "combo":
                value: object = widget.currentText()  # type: ignore[attr-defined]
            elif spec.kind == "bool":
                value = widget.isChecked()  # type: ignore[attr-defined]
            else:
                value = widget.text().strip()  # type: ignore[attr-defined]
            self._assign_field_value(spec.key, value, capture, vision, llm, tts, runtime)

        vision["api_key"] = self.vision_api_key.text().strip()
        llm["api_key"] = self.llm_api_key.text().strip()
        tts["api_key"] = self.tts_api_key.text().strip()
        payload["capture"] = capture
        payload["vision"] = vision
        payload["llm"] = llm
        payload["tts"] = tts
        payload["runtime"] = runtime
        payload["active_profile_id"] = self.active_profile_id
        self.current_settings_payload = payload
        self.config_store.save(payload)
        self.info_labels["tts"].setText(str(tts.get("provider") or "—"))
        self.info_labels["tts_detail"].setText(str(tts.get("model") or ""))
        self._update_region_label(payload)
        self._write_runtime_region_file_if_present(payload)
        self.status_summary.setText("运行配置已保存到 runtime/config.json。重新启动后会按新配置生效。")
        if not silent:
            QMessageBox.information(self, "保存成功", "运行配置已保存到 runtime/config.json。")

    def _update_region_label(self, values: dict[str, str]) -> None:
        capture = values.get("capture", {})
        region_payload = capture.get("barrage_region", {})
        if bool(capture.get("auto_select_region", True)):
            region = "每次启动时手动选择"
        else:
            coords = [region_payload.get(name) for name in ("x", "y", "w", "h")]
            region = ", ".join(str(value) for value in coords if value is not None) if any(value is not None for value in coords) else "未设置"
        self.info_labels["region"].setText(region)
        profile_name = self.profile_combo.currentText().split("  ", 1)[0] if hasattr(self, "profile_combo") else self.active_profile_id
        self.info_labels["region_detail"].setText(f"当前人设：{profile_name}。程序启动时会按这里的设置决定是否重新框选。")

    def _load_region_from_settings(self, values: dict[str, object]) -> None:
        capture = values.get("capture", {})
        region_payload = capture.get("barrage_region", {})
        try:
            coords = tuple(
                int(region_payload.get(name))
                for name in ("x", "y", "w", "h")
            )
        except (ValueError, TypeError):
            self.current_region = None
            return
        if all(value >= 0 for value in coords[:2]) and all(value > 0 for value in coords[2:]):
            self.current_region = coords  # type: ignore[assignment]
        else:
            self.current_region = None

    def _extract_field_value(
        self,
        key: str,
        capture: dict[str, object],
        vision: dict[str, object],
        llm: dict[str, object],
        tts: dict[str, object],
        runtime: dict[str, object],
    ) -> object:
        mapping = {
            "AUTO_SELECT_REGION": capture.get("auto_select_region", True),
            "SCREENSHOT_INTERVAL": capture.get("screenshot_interval", ""),
            "VISION_TIMEOUT_SECONDS": capture.get("vision_timeout_seconds", ""),
            "VISION_MODEL_NAME": vision.get("model", ""),
            "VISION_API_BASE": vision.get("api_base", ""),
            "LLM_MODEL_NAME": llm.get("model", ""),
            "LLM_API_BASE": llm.get("api_base", ""),
            "TTS_PROVIDER": tts.get("provider", ""),
            "TTS_MODEL_NAME": tts.get("model", ""),
            "TTS_API_ENDPOINT": tts.get("api_endpoint", ""),
            "TTS_VOICE": tts.get("voice", ""),
            "TTS_RESPONSE_FORMAT": tts.get("response_format", ""),
            "TTS_SAMPLE_RATE": tts.get("sample_rate", ""),
            "TTS_STREAM": tts.get("stream", False),
            "LOG_LEVEL": runtime.get("log_level", "INFO"),
        }
        return mapping.get(key, "")

    def _assign_field_value(
        self,
        key: str,
        value: object,
        capture: dict[str, object],
        vision: dict[str, object],
        llm: dict[str, object],
        tts: dict[str, object],
        runtime: dict[str, object],
    ) -> None:
        if key == "AUTO_SELECT_REGION":
            capture["auto_select_region"] = bool(value)
        elif key == "SCREENSHOT_INTERVAL":
            capture["screenshot_interval"] = float(value or 0.5)
        elif key == "VISION_TIMEOUT_SECONDS":
            capture["vision_timeout_seconds"] = float(value or 300)
        elif key == "VISION_MODEL_NAME":
            vision["model"] = str(value)
        elif key == "VISION_API_BASE":
            vision["api_base"] = str(value)
        elif key == "LLM_MODEL_NAME":
            llm["model"] = str(value)
        elif key == "LLM_API_BASE":
            llm["api_base"] = str(value)
        elif key == "TTS_PROVIDER":
            tts["provider"] = str(value)
        elif key == "TTS_MODEL_NAME":
            tts["model"] = str(value)
        elif key == "TTS_API_ENDPOINT":
            tts["api_endpoint"] = str(value)
        elif key == "TTS_VOICE":
            tts["voice"] = str(value)
        elif key == "TTS_RESPONSE_FORMAT":
            tts["response_format"] = str(value)
        elif key == "TTS_SAMPLE_RATE":
            tts["sample_rate"] = int(value or 32000)
        elif key == "TTS_STREAM":
            tts["stream"] = bool(value)
        elif key == "LOG_LEVEL":
            runtime["log_level"] = str(value).upper()

    def _write_runtime_region_file_if_present(self, values: dict[str, object]) -> None:
        capture = values.get("capture", {})
        region_payload = capture.get("barrage_region", {})
        try:
            region = (
                int(region_payload.get("x")),
                int(region_payload.get("y")),
                int(region_payload.get("w")),
                int(region_payload.get("h")),
            )
        except (TypeError, ValueError):
            return
        self._write_runtime_region_file(region)

    def choose_static_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择静态截图",
            str(ROOT),
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if not file_path:
            return
        payload = dict(self.current_settings_payload or self.config_store.load())
        capture = dict(payload.get("capture", {}))
        capture["screenshot_image_path"] = file_path
        payload["capture"] = capture
        self.current_settings_payload = payload
        self.config_store.save(payload)
        self.status_summary.setText("已启用静态截图模式。下次启动会重复读取这张图片。")

    def clear_static_image(self) -> None:
        payload = dict(self.current_settings_payload or self.config_store.load())
        capture = dict(payload.get("capture", {}))
        capture["screenshot_image_path"] = ""
        payload["capture"] = capture
        self.current_settings_payload = payload
        self.config_store.save(payload)
        self.status_summary.setText("已清除静态截图模式，后续会恢复真实抓屏。")

    def open_project_folder(self) -> None:
        if hasattr(os, "startfile"):
            os.startfile(str(ROOT))  # type: ignore[attr-defined]

    def toggle_pin(self, pinned: bool) -> None:
        flags = self.windowFlags()
        if pinned:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
            self.status_summary.setText("设置窗口已置顶。再次点击可取消置顶。")
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
            self.status_summary.setText("已取消窗口置顶。")
        self.show()

    def toggle_overlay(self, enabled: bool) -> None:
        if enabled:
            self.status_summary.setText("监控区域描边已开启。运行中选区后会显示透明边框。")
        else:
            self.status_summary.setText("监控区域描边已关闭。")
            self.overlay.hide()
            self.adjust_overlay_button.setChecked(False)
        self._sync_overlay_visibility()

    def toggle_overlay_adjust_mode(self, enabled: bool) -> None:
        self.overlay.set_drag_enabled(enabled)
        if enabled:
            self.overlay_button.setChecked(True)
            self.status_summary.setText("现在可以直接拖动屏幕上的监控框。松手后会立即更新监控区域。")
            self._sync_overlay_visibility()
        else:
            self.status_summary.setText("已退出监控框拖动模式。")

    def handle_overlay_region_changed(self, x: int, y: int, w: int, h: int) -> None:
        app = QApplication.instance()
        if app is None:
            return
        physical_region = self._map_overlay_geometry_to_region((x, y, w, h))
        self.current_region = physical_region
        self._write_runtime_region_file(physical_region)
        self.info_labels["region"].setText(
            f"{physical_region[0]}, {physical_region[1]}, {physical_region[2]}, {physical_region[3]}"
        )
        self.info_labels["region_detail"].setText("监控区域已拖动更新，当前运行会立即使用新位置。")
        self.status_summary.setText("监控区域已更新。后续截图会按新位置裁剪。")

    def _sync_overlay_visibility(self) -> None:
        if (
            self.overlay_button.isChecked()
            and self.process.state() == QProcess.ProcessState.Running
            and self.current_region is not None
        ):
            self.overlay.show_region(*self._map_region_to_overlay_geometry(self.current_region))
        else:
            self.overlay.hide()

    def _map_region_to_overlay_geometry(self, region: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        x, y, w, h = region
        app = QApplication.instance()
        if app is None:
            return region

        for screen in app.screens():
            geometry = screen.geometry()
            ratio = screen.devicePixelRatio() or 1.0
            physical_left = int(round(geometry.x() * ratio))
            physical_top = int(round(geometry.y() * ratio))
            physical_width = int(round(geometry.width() * ratio))
            physical_height = int(round(geometry.height() * ratio))
            within_x = physical_left <= x < physical_left + physical_width
            within_y = physical_top <= y < physical_top + physical_height
            if within_x and within_y:
                mapped_x = geometry.x() + int(round((x - physical_left) / ratio))
                mapped_y = geometry.y() + int(round((y - physical_top) / ratio))
                mapped_w = max(int(round(w / ratio)), 1)
                mapped_h = max(int(round(h / ratio)), 1)
                return (mapped_x, mapped_y, mapped_w, mapped_h)

        primary = app.primaryScreen()
        if primary is None:
            return region
        ratio = primary.devicePixelRatio() or 1.0
        return (
            int(round(x / ratio)),
            int(round(y / ratio)),
            max(int(round(w / ratio)), 1),
            max(int(round(h / ratio)), 1),
        )

    def _map_overlay_geometry_to_region(self, geometry_tuple: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        x, y, w, h = geometry_tuple
        app = QApplication.instance()
        if app is None:
            return geometry_tuple

        for screen in app.screens():
            geometry = screen.geometry()
            if geometry.contains(x, y):
                ratio = screen.devicePixelRatio() or 1.0
                physical_left = int(round(geometry.x() * ratio))
                physical_top = int(round(geometry.y() * ratio))
                mapped_x = physical_left + int(round((x - geometry.x()) * ratio))
                mapped_y = physical_top + int(round((y - geometry.y()) * ratio))
                mapped_w = max(int(round(w * ratio)), 1)
                mapped_h = max(int(round(h * ratio)), 1)
                return (mapped_x, mapped_y, mapped_w, mapped_h)
        primary = app.primaryScreen()
        if primary is None:
            return geometry_tuple
        ratio = primary.devicePixelRatio() or 1.0
        return (
            int(round(x * ratio)),
            int(round(y * ratio)),
            max(int(round(w * ratio)), 1),
            max(int(round(h * ratio)), 1),
        )

    def _write_runtime_region_file(self, region: tuple[int, int, int, int]) -> None:
        payload = {"x": region[0], "y": region[1], "w": region[2], "h": region[3]}
        RUNTIME_REGION_JSON.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_REGION_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def refresh_runtime_views(self) -> None:
        latest_frame = self._latest_png(RUNTIME_FRAMES)
        self.last_frame_preview.set_image(latest_frame)
        self._load_runtime_region()
        self._load_memory_snapshot()
        self._load_log_tail()
        self._sync_overlay_visibility()

    def _latest_png(self, folder: Path) -> Path | None:
        if not folder.exists():
            return None
        files = sorted(folder.glob("*.png"), key=lambda path: path.stat().st_mtime, reverse=True)
        return files[0] if files else None

    def _load_runtime_region(self) -> None:
        if not RUNTIME_REGION_JSON.exists():
            return
        try:
            payload = json.loads(RUNTIME_REGION_JSON.read_text(encoding="utf-8"))
            region = (
                int(payload["x"]),
                int(payload["y"]),
                int(payload["w"]),
                int(payload["h"]),
            )
        except Exception:
            return
        self.current_region = region
        self.info_labels["region"].setText(f"{region[0]}, {region[1]}, {region[2]}, {region[3]}")
        self.info_labels["region_detail"].setText("当前监控框会持续标出这个区域。")

    def _load_memory_snapshot(self) -> None:
        if not RUNTIME_MEMORY_JSON.exists():
            self.memory_preview.setPlainText("")
            self.runtime_notes.setPlainText("还没有运行快照。启动后，这里会显示最近识别到的弹幕和回复。")
            self.info_labels["updated_at"].setText("暂无快照")
            self.info_labels["updated_at_detail"].setText("启动运行后，这里会显示最近一次的更新时间。")
            return
        try:
            payload = json.loads(RUNTIME_MEMORY_JSON.read_text(encoding="utf-8"))
        except Exception as exc:
            self.memory_preview.setPlainText(f"读取运行记忆失败：{exc}")
            return
        updated_at = self._display_timestamp(str(payload.get("updated_at", "") or ""))
        last_text = str(payload.get("last_recognized_text", "") or "")
        history = payload.get("dialogue_history", [])

        self.info_labels["updated_at"].setText(updated_at or "未知")
        self.info_labels["updated_at_detail"].setText("这是最近一次持久化到本地的运行快照。")

        blocks = [f"更新时间：\n{updated_at or '未知'}", f"最近识别文本：\n{last_text or '—'}"]
        note_blocks = [f"最近识别文本：\n{last_text or '—'}"]
        if isinstance(history, list) and history:
            recent = history[-3:]
            for item in recent:
                recognized = str(item.get("recognized_text", "") or "")
                reply = str(item.get("reply_text", "") or "")
                blocks.append(f"弹幕：\n{recognized}\n\n回复：\n{reply}")
                note_blocks.append(f"回复：\n{reply}")
        self.memory_preview.setPlainText("\n\n".join(blocks))
        self.runtime_notes.setPlainText("\n\n".join(note_blocks))

    def _load_log_tail(self) -> None:
        log_path = RUNTIME_STDERR if RUNTIME_STDERR.exists() else RUNTIME_STDOUT
        if not log_path.exists():
            return
        text = log_path.read_text(encoding="utf-8", errors="replace")
        tail_lines = [line for line in text.splitlines()[-80:] if line.strip()]
        if self.process.state() == QProcess.ProcessState.NotRunning and tail_lines != self.log_entries:
            self.log_entries = tail_lines
            self.log_output.setHtml("".join(self._render_log_line(line) for line in self.log_entries))
            self.log_output.moveCursor(QTextCursor.MoveOperation.End)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("LiveSoul 控制台")
    app.setStyle("Fusion")
    font = QFont("Segoe UI Variable", 10)
    app.setFont(font)
    palette = app.palette()
    palette.setColor(palette.ColorRole.Highlight, QColor("#c9853e"))
    app.setPalette(palette)
    window = LiveSoulMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
