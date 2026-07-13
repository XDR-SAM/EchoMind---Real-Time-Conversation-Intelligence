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

        self.transcript_snapshots = deque(maxlen=12)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._drain_queue)
        self._poll_timer.start(75)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        self.title_label = QLabel("Meeting Copilot")
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        header.addWidget(self.title_label)
        header.addStretch(1)

        self.mic_checkbox = QCheckBox("Microphone")
        self.mic_checkbox.setToolTip("Use microphone input instead of system audio.")
        header.addWidget(self.mic_checkbox)
        root.addLayout(header)

        self.transcript_view = QTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setPlaceholderText("Live transcript will appear here.")
        root.addWidget(self.transcript_view)

        self.suggestion_label = QLabel("Waiting for speech...")
        self.suggestion_label.setFont(QFont("Segoe UI", 11))
        self.suggestion_label.setWordWrap(True)
        root.addWidget(self.suggestion_label)

        controls = QHBoxLayout()
        self.pin_button = QPushButton("Unpin")
        controls.addWidget(self.pin_button)
        self.close_button = QPushButton("Exit")
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
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_active and self._drag_position is not None:
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
                border:1px solid rgba(255,255,255,0.06); border-radius:14px;
            }}
            QPushButton {{
                background:#1f2937; color:{foreground};
                border:1px solid #374151; border-radius:8px; padding:6px 12px;
            }}
            QPushButton:hover {{ background:#334155; }}
            QPushButton:pressed {{ background:#0f172a; }}
            QCheckBox {{ color:#cbd5e1; spacing:8px; }}
            QCheckBox::indicator {{ width:18px; height:18px; border-radius:4px; }}
            QTextEdit {{
                background:#0b1220; color:{foreground};
                border:1px solid #1f2937; border-radius:10px;
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

        if transcript:
            self.transcript_snapshots.append(transcript)
            text = "\n".join(self.transcript_snapshots)
            self.transcript_view.setPlainText(text)
            self.transcript_view.moveCursor(QTextEdit.MoveOperation.End)

        if suggestion:
            self.suggestion_label.setText(suggestion)
        if lang:
            self.title_label.setText(f"Meeting Copilot  ·  {lang}")
