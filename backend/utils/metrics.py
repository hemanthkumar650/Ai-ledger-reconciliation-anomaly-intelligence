from __future__ import annotations

from collections import defaultdict
from threading import Lock


class MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._request_counts: dict[str, int] = defaultdict(int)
        self._request_errors: dict[str, int] = defaultdict(int)
        self._request_latency_ms_sum: dict[str, float] = defaultdict(float)
        self._llm_calls_total: dict[str, int] = defaultdict(int)
        self._llm_retries_total: dict[str, int] = defaultdict(int)
        self._llm_failures_total: dict[str, int] = defaultdict(int)

    def record_request(self, method: str, path: str, latency_ms: float, status_code: int) -> None:
        key = f"{method} {path}"
        with self._lock:
            self._request_counts[key] += 1
            self._request_latency_ms_sum[key] += latency_ms
            if status_code >= 400:
                self._request_errors[key] += 1

    def increment_llm_call(self, provider: str) -> None:
        with self._lock:
            self._llm_calls_total[provider] += 1

    def increment_llm_retry(self, provider: str) -> None:
        with self._lock:
            self._llm_retries_total[provider] += 1

    def increment_llm_failure(self, provider: str) -> None:
        with self._lock:
            self._llm_failures_total[provider] += 1

    def snapshot(self) -> dict:
        with self._lock:
            request_metrics: dict[str, dict[str, float | int]] = {}
            for key, count in self._request_counts.items():
                total_latency = self._request_latency_ms_sum.get(key, 0.0)
                request_metrics[key] = {
                    "count": count,
                    "errors": self._request_errors.get(key, 0),
                    "avg_latency_ms": round(total_latency / count, 2) if count else 0.0,
                }

            return {
                "requests": request_metrics,
                "llm_calls_total": dict(self._llm_calls_total),
                "llm_retries_total": dict(self._llm_retries_total),
                "llm_failures_total": dict(self._llm_failures_total),
            }

    @staticmethod
    def _escape_label(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def prometheus_snapshot(self) -> str:
        with self._lock:
            lines: list[str] = [
                "# HELP auditai_http_requests_total Total HTTP requests by method and path",
                "# TYPE auditai_http_requests_total counter",
            ]
            for key, count in self._request_counts.items():
                method, path = key.split(" ", 1)
                lines.append(
                    "auditai_http_requests_total{method=\"%s\",path=\"%s\"} %d"
                    % (self._escape_label(method), self._escape_label(path), count)
                )

            lines.extend(
                [
                    "# HELP auditai_http_errors_total Total HTTP error responses by method and path",
                    "# TYPE auditai_http_errors_total counter",
                ]
            )
            for key, count in self._request_errors.items():
                method, path = key.split(" ", 1)
                lines.append(
                    "auditai_http_errors_total{method=\"%s\",path=\"%s\"} %d"
                    % (self._escape_label(method), self._escape_label(path), count)
                )

            lines.extend(
                [
                    "# HELP auditai_http_latency_ms_avg Average request latency in milliseconds",
                    "# TYPE auditai_http_latency_ms_avg gauge",
                ]
            )
            for key, count in self._request_counts.items():
                method, path = key.split(" ", 1)
                total_latency = self._request_latency_ms_sum.get(key, 0.0)
                avg_latency = total_latency / count if count else 0.0
                lines.append(
                    "auditai_http_latency_ms_avg{method=\"%s\",path=\"%s\"} %.2f"
                    % (self._escape_label(method), self._escape_label(path), avg_latency)
                )

            lines.extend(
                [
                    "# HELP auditai_llm_calls_total Total LLM calls by provider",
                    "# TYPE auditai_llm_calls_total counter",
                ]
            )
            for provider, count in self._llm_calls_total.items():
                lines.append(
                    "auditai_llm_calls_total{provider=\"%s\"} %d"
                    % (self._escape_label(provider), count)
                )

            lines.extend(
                [
                    "# HELP auditai_llm_retries_total Total LLM retries by provider",
                    "# TYPE auditai_llm_retries_total counter",
                ]
            )
            for provider, count in self._llm_retries_total.items():
                lines.append(
                    "auditai_llm_retries_total{provider=\"%s\"} %d"
                    % (self._escape_label(provider), count)
                )

            lines.extend(
                [
                    "# HELP auditai_llm_failures_total Total LLM failures by provider",
                    "# TYPE auditai_llm_failures_total counter",
                ]
            )
            for provider, count in self._llm_failures_total.items():
                lines.append(
                    "auditai_llm_failures_total{provider=\"%s\"} %d"
                    % (self._escape_label(provider), count)
                )

            return "\n".join(lines) + "\n"

    def reset(self) -> None:
        with self._lock:
            self._request_counts.clear()
            self._request_errors.clear()
            self._request_latency_ms_sum.clear()
            self._llm_calls_total.clear()
            self._llm_retries_total.clear()
            self._llm_failures_total.clear()


metrics_store = MetricsStore()
