from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict


@dataclass(frozen=True)
class ServiceCallRecord:
    ts: str
    method: str
    latency_ms: int
    ok: bool
    error: str | None


class ServiceMetrics:
    def __init__(self, max_history: int = 100) -> None:
        self.started_at = datetime.now(timezone.utc)
        self.call_count = 0
        self.success_count = 0
        self.error_count = 0
        self._recent: Deque[ServiceCallRecord] = deque(maxlen=max_history)
        self._methods: Counter[str] = Counter()

    def record(self, *, method: str, latency_ms: int, ok: bool, error: str | None) -> None:
        self.call_count += 1
        self._methods[method] += 1
        if ok:
            self.success_count += 1
        else:
            self.error_count += 1
        self._recent.append(
            ServiceCallRecord(
                ts=datetime.now(timezone.utc).isoformat(),
                method=method,
                latency_ms=int(latency_ms),
                ok=ok,
                error=error,
            )
        )

    def snapshot(self, *, tool_count: int | None, transport: str, port: int) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        recent = list(self._recent)
        latency_values = [r.latency_ms for r in recent if r.ok]
        recent_errors = [
            {
                "ts": r.ts,
                "method": r.method,
                "error": r.error,
            }
            for r in recent
            if not r.ok
        ][-10:]
        return {
            "status": "ok",
            "started_at": self.started_at.isoformat(),
            "uptime_seconds": int((now - self.started_at).total_seconds()),
            "transport": transport,
            "port": port,
            "tool_count": tool_count,
            "call_count": self.call_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "recent_avg_latency_ms": (
                round(sum(latency_values) / len(latency_values), 1)
                if latency_values
                else None
            ),
            "recent_p95_latency_ms": (
                sorted(latency_values)[max(0, int(len(latency_values) * 0.95) - 1)]
                if latency_values
                else None
            ),
            "top_methods": dict(self._methods.most_common(10)),
            "recent_errors": recent_errors,
        }


class InstrumentedMassiveClient:
    def __init__(self, inner: Any, metrics: ServiceMetrics):
        self._inner = inner
        self._metrics = metrics

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._inner, name)
        if not callable(attr):
            return attr

        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            started = datetime.now(timezone.utc)
            ok = False
            err: str | None = None
            try:
                result = attr(*args, **kwargs)
                ok = True
                return result
            except Exception as exc:
                err = str(exc)
                raise
            finally:
                elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
                self._metrics.record(
                    method=name,
                    latency_ms=elapsed_ms,
                    ok=ok,
                    error=err,
                )

        return _wrapped


def safe_tool_count(server_obj: Any) -> int | None:
    try:
        tool_manager = getattr(server_obj, "_tool_manager", None)
        if tool_manager is not None:
            tools = getattr(tool_manager, "_tools", None)
            if isinstance(tools, dict):
                return len(tools)
        tools = getattr(server_obj, "_tools", None)
        if isinstance(tools, dict):
            return len(tools)
    except Exception:
        return None
    return None
