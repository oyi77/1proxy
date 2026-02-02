from prometheus_client import Counter, Histogram, Gauge, make_asgi_app


class ProxyMetrics:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProxyMetrics, cls).__new__(cls)
            cls._instance._init_metrics()
        return cls._instance

    def _init_metrics(self):
        self.requests_total = Counter(
            "proxy_requests_total",
            "Total proxy requests processed",
            ["status", "protocol"],
        )
        self.latency_histogram = Histogram(
            "proxy_latency_seconds",
            "Proxy response latency",
            buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
        )
        self.active_proxies = Gauge(
            "active_proxies", "Number of active validated proxies"
        )


metrics_app = make_asgi_app()
