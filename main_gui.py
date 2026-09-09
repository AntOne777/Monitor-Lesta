import sys
import json
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.controller import MonitorController

def load_servers():
    try:
        with open("config/servers.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        clusters = data.get("clusters", {}).get("list", [])
        # если список – это словарь с индексами (как в вашем втором файле)
        if isinstance(clusters, dict):
            clusters = list(clusters.values())
        hosts_info = []
        for cluster in clusters:
            name = cluster.get("name", "")
            address = cluster.get("address", "")
            place = cluster.get("place", "")
            color = cluster.get("color", [0,0,0])
            if address:
                hosts_info.append((name, address, place, color))
        return hosts_info
    except Exception as e:
        print(f"Ошибка загрузки серверов: {e}")
        return []

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # Загружаем серверы
    servers = load_servers()
    if not servers:
        print("Нет серверов для мониторинга.")
        sys.exit(1)

    # Передаём список серверов в дашборд для создания карточек
    window.dashboard_widget.set_servers(servers)

    # Создаём контроллер с адресами
    hosts_info = [(name, addr) for name, addr, _, _ in servers]
    controller = MonitorController(hosts_info)

    # Связываем сигналы с обновлением UI
    controller.data_updated.connect(window.dashboard_widget.update_server_data)
    controller.best_server_updated.connect(window.dashboard_widget.update_best_server)
    # controller.online_updated.connect(...)  # можно добавить

    # Кнопки управления
    window.dashboard_widget.btn_start.clicked.connect(lambda: controller.start_monitoring(interval_ms=500))
    window.dashboard_widget.btn_stop.clicked.connect(controller.stop_monitoring)

    # Статус кнопок
    controller.data_updated.connect(lambda d: window.dashboard_widget.status_label.setText("🟢 Мониторинг запущен"))

    sys.exit(app.exec())
