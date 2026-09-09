from .statistics import get_all_stats

class ServerRanker:
    @staticmethod
    def calculate_score(stats: dict) -> float:
        loss = stats.get('loss', 100)
        if loss > 5.0 or stats.get('count', 0) < 10:
            return -1.0
        avg = stats['avg']
        if avg == float('inf'):
            return -1.0
        jitter = stats['jitter']
        uniformity = stats['uniformity'] / 100.0
        density = stats['density'] / 100.0
        jitter_norm = min(jitter / 100.0, 1.0)
        avg_norm = min(avg / 50.0, 2.0)
        stability = (1 - jitter_norm) * 0.4 + uniformity * 0.3 + density * 0.3
        score = stability / avg_norm
        return round(score, 4)

    @staticmethod
    def get_best_server(hosts_data: dict) -> tuple:
        best_host = None
        best_score = -1.0
        best_stats = None
        window = 20
        for host, data in hosts_data.items():
            pings = data.get('pings', [])
            if len(pings) < 10:
                continue
            stats = get_all_stats(pings, window)
            score = ServerRanker.calculate_score(stats)
            if score > best_score:
                best_score = score
                best_host = host
                best_stats = stats
        return best_host, best_stats, best_score
