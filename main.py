from __future__ import annotations
import sys
from typing import Dict

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import QApplication

from qfluentwidgets import (
    FluentIcon,
    setTheme,
    Theme,
    MSFluentWindow,
)

from core.analytics import ServerMetrics
from core.config import APP_VERSION, SERVERS, settings
from ui.dashboard import DashboardWidget
from worker import OnlineWorker, PingManagerWorker

APP_NAME = "МИР ТАНКОВ  —  МОНИТОРИНГ СЕРВЕРОВ"


class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()
        setTheme(Theme.DARK)
        self._setup_window()
        self._init_metrics()
        self._init_pages()
        self._init_navigation()
        self._init_workers()
        self._init_refresh_timer()

    def _resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(980, 640)
        self.resize(1280, 760)
        try:
            self.setWindowIcon(QIcon(self._resource_path("assets/icon.ico")))
        except Exception:
            pass

        # 1. Remove Acrylic / Mica effect to prevent Windows DWM gray tint
        try:
            self.windowEffect.removeBackgroundEffect(self.winId())
        except Exception:
            pass

        try:
            self.setMicaEffectEnabled(False)
        except Exception:
            pass

        # 2. Set solid black background for MSFluentWindow
        self.setBackgroundColor(QColor("#070b12"))

        # 3. StackedWidget & TitleBar styling in uniform dark
        if hasattr(self, "stackedWidget"):
            self.stackedWidget.setObjectName("MainStack")
            self.stackedWidget.setStyleSheet("#MainStack { background: transparent; border: none; }")
        if hasattr(self, "titleBar"):
            # Set to standard Windows title bar height (32px)
            self.titleBar.setFixedHeight(32)
            if self.layout():
                m = self.layout().contentsMargins()
                self.layout().setContentsMargins(m.left(), 32, m.right(), m.bottom())
            
            # Force solid black color and remove any borders
            ss = self.titleBar.styleSheet()
            self.titleBar.setStyleSheet(ss + "\nMSFluentTitleBar { background-color: #070b12; border: none; }")

        self.setStyleSheet("""
            MSFluentWindow, #MainStack, #dashboardWidget, StackedWidget {
                background: #070b12 !important;
                background-color: #070b12 !important;
                border: none !important;
            }
        """)

        # 4. Windows 11 DWM native caption & border coloring
        try:
            import ctypes
            hwnd = int(self.winId())
            # COLORREF 0x00BBGGRR: #070b12 -> B=0x12, G=0x0b, R=0x07
            color = ctypes.c_int(0x00120b07)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(color), ctypes.sizeof(color))
        except Exception:
            pass

    def _init_metrics(self):
        self._metrics: Dict[str, ServerMetrics] = {
            srv.name: ServerMetrics(name=srv.name) for srv in SERVERS
        }

    def _init_pages(self):
        self.dashboard_page = DashboardWidget(self)

    def _init_navigation(self):
        self.addSubInterface(self.dashboard_page, FluentIcon.HOME, "")
        self.navigationInterface.setCurrentItem(self.dashboard_page.objectName())
        self.navigationInterface.setVisible(False)
        self.navigationInterface.setFixedWidth(0)

    def _init_workers(self):
        self._ping_manager = PingManagerWorker(SERVERS, settings, self)
        self._ping_manager.ping_result.connect(self._on_ping_result)
        self._ping_manager.error_occurred.connect(self._on_ping_error)
        self._ping_manager.start()

        self._online_worker = OnlineWorker(settings, self)
        self._online_worker.online_updated.connect(self._on_online_updated)
        self._online_worker.total_updated.connect(
            self.dashboard_page.update_total_online)
        self._online_worker.fetch_error.connect(self._on_api_error)
        self._online_worker.start()

    def _init_refresh_timer(self):
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(250)
        self._refresh_timer.timeout.connect(self._push_metrics_to_ui)
        self._refresh_timer.start()

    @pyqtSlot(str, object)
    def _on_ping_result(self, server_name, ping_ms):
        m = self._metrics.get(server_name)
        if m:
            m.push(ping_ms, settings.smoothing_window)

    @pyqtSlot(str, str)
    def _on_ping_error(self, server_name, error):
        m = self._metrics.get(server_name)
        if m:
            m.last_ping = None
            m.is_online = False

    @pyqtSlot(dict)
    def _on_online_updated(self, online_map):
        for name, count in online_map.items():
            m = self._metrics.get(name)
            if m:
                m.online = count

    @pyqtSlot(str)
    def _on_api_error(self, msg):
        self.dashboard_page.set_error(msg)

    @pyqtSlot()
    def _push_metrics_to_ui(self):
        self.dashboard_page.refresh_metrics(self._metrics)

    def closeEvent(self, event):
        self._refresh_timer.stop()
        self._ping_manager.stop()
        self._online_worker.stop()
        
        super().closeEvent(event)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
