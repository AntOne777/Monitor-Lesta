from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QGridLayout, QFrame, QPushButton)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # Индикаторы
        indicators = QHBoxLayout()
        indicators.setSpacing(15)
        self.indicator_availability = self._create_indicator("🟢 Доступность РФ", "—")
        self.indicator_uptime = self._create_indicator("⏱ Время работы", "—")
        self.indicator_packets = self._create_indicator("📦 Всего пакетов", "—")
        self.indicator_loss = self._create_indicator("❌ Потери", "—")
        indicators.addWidget(self.indicator_availability)
        indicators.addWidget(self.indicator_uptime)
        indicators.addWidget(self.indicator_packets)
        indicators.addWidget(self.indicator_loss)
        self.layout.addLayout(indicators)

        # Управление
        control_layout = QHBoxLayout()
        self.status_label = QLabel("⏹ Мониторинг остановлен")
        self.status_label.setObjectName("statusLabel")
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()
        self.btn_start = QPushButton("▶ Запустить")
        self.btn_start.setObjectName("controlButton")
        self.btn_start.setFixedHeight(35)
        self.btn_stop = QPushButton("⏹ Остановить")
        self.btn_stop.setObjectName("controlButton")
        self.btn_stop.setFixedHeight(35)
        self.btn_stop.setEnabled(False)
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        self.layout.addLayout(control_layout)

        # Рекомендация
        self.recommend_widget = QFrame()
        self.recommend_widget.setObjectName("recommendWidget")
        recommend_layout = QHBoxLayout(self.recommend_widget)
        recommend_layout.addWidget(QLabel("🏆 Рекомендуемый сервер:"))
        self.recommend_name = QLabel("—")
        self.recommend_name.setObjectName("recommendName")
        recommend_layout.addWidget(self.recommend_name)
        recommend_layout.addStretch()
        recommend_layout.addWidget(QLabel("Пинг:"))
        self.recommend_ping = QLabel("—")
        recommend_layout.addWidget(self.recommend_ping)
        self.layout.addWidget(self.recommend_widget)

        # Сетка карточек серверов
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)
        self.card_widgets = {}  # address -> QFrame
        self.layout.addLayout(self.grid_layout)

    def _create_indicator(self, title, value):
        frame = QFrame()
        frame.setObjectName("indicatorFrame")
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignCenter)
        label_title = QLabel(title)
        label_title.setObjectName("indicatorTitle")
        label_value = QLabel(value)
        label_value.setObjectName("indicatorValue")
        layout.addWidget(label_title)
        layout.addWidget(label_value)
        return frame

    def set_servers(self, servers_info):
        """servers_info: [(name, address, location, color_rgb), ...]"""
        # Очищаем старые карточки
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.card_widgets.clear()

        row, col = 0, 0
        max_cols = 4
        for name, addr, location, color in servers_info:
            card = self._create_server_card(name, location, color)
            self.grid_layout.addWidget(card, row, col)
            self.card_widgets[addr] = card
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _create_server_card(self, name, location, color):
        card = QFrame()
        card.setObjectName("serverCard")
        # можно установить цвет рамки через style
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        name_label = QLabel(name)
        name_label.setObjectName("serverName")
        loc_label = QLabel(location)
        loc_label.setObjectName("serverLocation")
        ping_label = QLabel("Пинг: —")
        ping_label.setObjectName("serverPing")
        online_label = QLabel("Онлайн: —")
        online_label.setObjectName("serverOnline")
        layout.addWidget(name_label)
        layout.addWidget(loc_label)
        layout.addWidget(ping_label)
        layout.addWidget(online_label)
        # Сохраним ссылки на лейблы для обновления
        card.ping_label = ping_label
        card.online_label = online_label
        return card

    def update_server_data(self, addr, avg_ping, loss, online=None):
        card = self.card_widgets.get(addr)
        if card:
            if avg_ping == float('inf'):
                card.ping_label.setText("Пинг: ∞")
            else:
                card.ping_label.setText(f"Пинг: {avg_ping:.1f} мс")
            if online is not None:
                card.online_label.setText(f"Онлайн: {online}")
            # можно также менять цвет в зависимости от потерь

    def update_best_server(self, name, stats, score):
        self.recommend_name.setText(name)
        if stats:
            self.recommend_ping.setText(f"{stats['avg']:.1f} мс")
        else:
            self.recommend_ping.setText("—")
