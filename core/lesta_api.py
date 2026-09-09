import requests
from typing import Optional, Dict

class LestaAPI:
    BASE_URL = "https://api.tanki.su/wot/servers/info/"

    @staticmethod
    def get_online() -> Optional[Dict[str, int]]:
        try:
            response = requests.get(LestaAPI.BASE_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    return data['data']
                else:
                    return data
            else:
                return None
        except Exception as e:
            print(f"Ошибка получения онлайна: {e}")
            return None
