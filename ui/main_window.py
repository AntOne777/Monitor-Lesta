import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QStackedWidget, QLabel, QFrame, QApplication)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QPalette, QColor
from ui.dashboard_widget import DashboardWidget
from ui.servers_widget import ServersWidget
from ui.settings_dialog import SettingsDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WoT Ping Monitor NG – Lesta")
        self.setMinimumSize(1200, 700)
        # self.setWindowIcon(QIcon("resources/icon.ico"))  # раскомментировать при наличии

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Боковое меню
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setFixedWidth(200)
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setAlignment(Qt.AlignTop)
        left_panel_layout.setSpacing(0)

        logo_label = QLabel("WoT Ping")
        logo_label.setObjectName("logoLabel")
        logo_label.setAlignment(Qt.AlignCenter)
        left_panel_layout.addWidget(logo_label)

        self.btn_dashboard = self._create_menu_button("📊 Дашборд")
        self.btn_servers = self._create_menu_button("🖥 Серверы")
        self.btn_graphs = self._create_menu_button("📈 Графики")
        self.btn_settings = self._create_menu_button("⚙ Настройки")

        left_panel_layout.addWidget(self.btn_dashboard)
        left_panel_layout.addWidget(self.btn_servers)
        left_panel_layout.addWidget(self.btn_graphs)
        left_panel_layout.addWidget(self.btn_settings)
        left_panel_layout.addStretch()
        main_layout.addWidget(left_panel)

        # Стек страниц
        self.stack = QStackedWidget()
        self.dashboard_widget = DashboardWidget()
        self.servers_widget = ServersWidget()
        self.graphs_widget = QLabel("Графики (в разработке)")
        self.graphs_widget.setAlignment(Qt.AlignCenter)
        self.settings_widget = SettingsDialog()  # пока диалог, но можно и виджет
        self.settings_widget.setParent(self)  # чтобы не открывалось отдельно

        self.stack.addWidget(self.dashboard_widget)   # index 0
        self.stack.addWidget(self.servers_widget)     # index 1
        self.stack.addWidget(self.graphs_widget)      # index 2
        self.stack.addWidget(self.settings_widget)    # index 3

        main_layout.addWidget(self.stack)

        self.btn_dashboard.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_servers.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.btn_graphs.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(3))

        self.apply_dark_theme()

    def _create_menu_button(self, text):
        btn = QPushButton(text)
        btn.setObjectName("menuButton")
        btn.setFixedHeight(45)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def apply_dark_theme(self):
        try:
            with open("resources/style.qss", "r", encoding="utf-8") as f:
                style = f.read()
                self.setStyleSheet(style)
        except:
            # Встроенная тёмная тема
            dark_palette = QPalette()
            dark_palette.setColor(QPalette.Window, QColor(40, 40, 40))
            dark_palette.setColor(QPalette.WindowText, Qt.white)
            dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
            dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
            dark_palette.setColor(QPalette.ToolTipText, Qt.white)
            dark_palette.setColor(QPalette.Text, Qt.white)
            dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ButtonText, Qt.white)
            dark_palette.setColor(QPalette.BrightText, Qt.red)
            dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.HighlightedText, Qt.black)
            self.setPalette(dark_palette)
