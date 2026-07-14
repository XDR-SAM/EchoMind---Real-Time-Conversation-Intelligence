import logging
from collections import deque

from PyQt6.QtCore import QTimer
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
)

_TRAY_AVAILABLE = False
try:
    if QSystemTrayIcon.isSystemTrayAvailable():
        _TRAY_AVAILABLE = True
except Exception:
    _TRAY_AVAILABLE = False


class _TrayStub:
    def __init__(self, *args, **kwargs):
        pass

    def setIcon(self, *args, **kwargs):
        pass

    def setToolTip(self, *args, **kwargs):
        pass

    def show(self):
        pass

    def hide(self):
        pass

    def isVisible(self):
        return False

    def setContextMenu(self, *args, **kwargs):
        pass


class OverlayWindow(QFrame):
    def __init__(self, ui_queue, parent=None):
        super().__init__(parent)
        self.ui_queue = ui_queue
        self.setObjectName("OverlayWindow")
        self._apply_style()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(480)
        self.setMaximumWidth(620)
        self.setup_ui()
        self._init_tray()
        self._drag_active = False
        self._drag_position = None
        self._drag_threshold = 3

        self.transcript_snapshots: deque[str] = deque(maxlen=12)
        self._last_displayed_transcript = ""
        self._last_displayed_suggestion = ""

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._drain_queue)
        self._poll_timer.start(100)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        self.title_label = QLabel("Meeting Copilot")
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.title_label.setAccessibleName("Overlay title")
        header.addWidget(self.title_label)
        header.addStretch(1)

        self.mic_checkbox = QCheckBox("Microphone")
        self.mic_checkbox.setToolTip("Use microphone input instead of system audio.")
        self.mic_checkbox.setAccessibleName("Microphone toggle")
        header.addWidget(self.mic_checkbox)
        root.addLayout(header)

        self.transcript_view = QTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setPlaceholderText("Live transcript will appear here.")
        self.transcript_view.setAccessibleName("Live transcript")
        root.addWidget(self.transcript_view)

        self.suggestion_label = QLabel("Waiting for speech...")
        self.suggestion_label.setFont(QFont("Segoe UI", 11))
        self.suggestion_label.setWordWrap(True)
        self.suggestion_label.setAccessibleName("Suggestion")
        root.addWidget(self.suggestion_label)

        controls = QHBoxLayout()
        self.pin_button = QPushButton("Unpin")
        self.pin_button.setAccessibleName("Pin toggle")
        controls.addWidget(self.pin_button)
        self.close_button = QPushButton("Exit")
        self.close_button.setAccessibleName("Close overlay")
        self.close_button.setProperty("variant", "destructive")
        controls.addWidget(self.close_button)
        root.addLayout(controls)

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(28)
        self.shadow.setColor(QColor(0, 0, 0, 180))
        self.shadow.setOffset(0, 10)
        self.setGraphicsEffect(self.shadow)

    def _init_tray(self):
        self._tray = QSystemTrayIcon(self) if _TRAY_AVAILABLE else _TrayStub()
        if _TRAY_AVAILABLE:
            try:
                from PyQt6.QtWidgets import QStyle

                icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
                self._tray.setIcon(icon)
            except Exception:
                pass
            self._tray.setToolTip("Meeting Copilot")
            self._tray.show()
        self.close_button.clicked.connect(self._on_close_requested)

    def _on_close_requested(self):
        if _TRAY_AVAILABLE and self._tray is not None:
            self.hide()
        else:
            QApplication.instance().quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_start_position = self._drag_position
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_active and self._drag_position is not None:
            current = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            delta = current - self._drag_start_position
            if abs(delta.x()) > self._drag_threshold or abs(delta.y()) > self._drag_threshold:
                self.move(event.globalPosition().toPoint() - self._drag_position)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_active = False
        self._drag_position = None
        super().mouseReleaseEvent(event)

    def _apply_style(self):
        background = "#111827"
        foreground = "#f8fafc"
        if self.palette().color(self.backgroundRole()).value() < 90:
            background = "#0b1220"
            foreground = "#e2e8f0"
        self.setStyleSheet(
            f"""
            #OverlayWindow {{
                background:{background};
                color:{foreground};
                border:1px solid rgba(241,245,250,0.08); border-radius:16px;
            }}
            QFrame#OverlayWindow {{
                background:{background};
                color:{foreground};
            }}
            QPushButton {{
                background:#1f2937; color:{foreground};
                border:1px solid rgba(241,245,250,0.08); border-radius:10px;
                padding:7px 14px; min-width:88px;
                font-family:"Segoe UI","Roboto","Helvetica Neue",Arial,sans-serif;
                font-size:10.5pt;
            }}
            QPushButton:hover {-background:#334155; }
            QPushButton:pressed {{ background:#0B132B; }}
            QPushButton:hover {{
                background:#2563EB; border-color:#2563EB; color:#FFFFFF;
            }}
            QPushButton:pressed {{
                background:#1D4ED8; border-color:#1D4ED8; color:#FFFFFF;
            }}
            QPushButton:disabled {{
                background:#1f2937; color:#94a3b8;
                border:1px solid rgba(241,245,250,0.08);
            }}
            QPushButton[variant="destructive"] {{
                background:#7f1d1d; border:1px solid #991b1b;
            }}
            QPushButton[variant="destructive"]:hover {{ background:#991b1b; border-color:#B91C1C; color:#FEE2E2; }}
            QPushButton[variant="destructive"]:pressed {{
                background:#B91C1C; border-color:#DC2626; color:#FFFFFF;
            }}
            QCheckBox {{ color:#cbd5e1; spacing:8px; }}
            QCheckBox::indicator {{ width:18px; height:18px; border-radius:4px; }}
            QCheckBox::indicator:hover {{ border:1px solid #94a3b8; }}
            QTextEdit {{
                background:#0b1220; color:{foreground};
                border:1px solid rgba(241,245,250,0.08); border-radius:12px; padding:10px;
                selection-background-color:#2563EB; selection-color:#FFFFFF;
                font-family:"Segoe UI","Roboto","Helvetica Neue",Arial,sans-serif;
                font-size:11.5pt;
            }}
            QLabel {{
                background:transparent;
            }}
            QLabel:disabled {{
                color:#94a3b8;
            }}
            #MinimizeWindowToTrayButton {{
                background:transparent; color:#cbd5e1; border:none;
                min-width:28px; max-width:28px; padding:4px;
            }}
            #MinimizeWindowToTrayButton:hover {{
                color:#FFC72C; background:transparent;
            }}
            """
        )

    def _drain_queue(self):
        try:
            start = __import__("time").perf_counter()
            count = 0
            while True:
                item = self.ui_queue.get_nowait()
                self.apply_update(item)
                count += 1
                if count >= 8:
                    break
            elapsed_ms = (__import__("time").perf_counter() - start) * 1000
            if elapsed_ms > 10:
                logging.debug("overlay drain: count=%d elapsed=%.2f ms", count, elapsed_ms)
        except __import__("queue").Empty:
            pass

    def apply_update(self, item):
        transcript = item.get("transcript", "")
        suggestion = item.get("suggestion", "")
        lang = item.get("lang", "en")

        if transcript and transcript != self._last_displayed_transcript:
            self.transcript_snapshots.append(transcript)
            text = "\n".join(self.transcript_snapshots)
            self.transcript_view.setPlainText(text)
            self.transcript_view.moveCursor(QTextEdit.MoveOperation.End)
            self._last_displayed_transcript = transcript

        if suggestion and suggestion != self._last_displayed_suggestion:
            self.suggestion_label.setText(suggestion)
            self._last_displayed_suggestion = suggestion

        if lang:
            self.title_label.setText(f"Meeting Copilot · {lang}")
