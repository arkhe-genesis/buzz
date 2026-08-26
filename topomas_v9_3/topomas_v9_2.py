class BaseAgent:
    def __init__(self, name, config, metrics, cache, model_registry, **kwargs):
        self.name = name
        self.config = config
        self.metrics = metrics
        self.cache = cache
        self.model_registry = model_registry
        self.logger = type("Logger", (), {"info": print, "error": print})()

class TopoMASConfig:
    pass

class MetricsCollector:
    def time(self, metric_name, labels):
        class Context:
            def __enter__(self): pass
            def __exit__(self, *args): pass
        return Context()
    def inc(self, *args): pass
    def gauge(self, *args): pass

class ResultCache:
    pass

class ModelRegistry:
    def register(self, *args): pass

CENTROSYMMETRIC_SG = []
