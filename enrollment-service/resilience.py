"""Circuit Breaker mínimo (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)."""
import threading
import time


class CircuitOpenError(Exception):
    """Lançada quando o circuito está aberto e a chamada é rejeitada sem tentar o serviço remoto."""


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 10.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = "CLOSED"
        self.failures = 0
        self.opened_at = 0.0
        self._lock = threading.Lock()

    def call(self, fn, *args, ignore=(), **kwargs):
        """Executa fn. Exceções em `ignore` (erros de negócio, ex.: 404) não contam como falha."""
        with self._lock:
            if self.state == "OPEN":
                if time.monotonic() - self.opened_at >= self.reset_timeout:
                    self.state = "HALF_OPEN"  # permite uma chamada de teste
                else:
                    raise CircuitOpenError()
        try:
            result = fn(*args, **kwargs)
        except ignore:
            self._on_success()
            raise
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self):
        with self._lock:
            self.failures = 0
            self.state = "CLOSED"

    def _on_failure(self):
        with self._lock:
            self.failures += 1
            if self.state == "HALF_OPEN" or self.failures >= self.failure_threshold:
                self.state = "OPEN"
                self.opened_at = time.monotonic()
