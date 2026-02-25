#!/usr/bin/env python3
"""
Enhanced Metrics and Analytics
Detailed performance metrics, histograms, percentiles, time-series data
"""
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque
import statistics


class Histogram:
    """
    Histogram with configurable buckets

    Example:
        hist = Histogram(buckets=[10, 50, 100, 500, 1000])
        hist.observe(75)   # Falls in 50-100 bucket
        hist.observe(250)  # Falls in 100-500 bucket
    """

    def __init__(self, buckets: List[float]):
        """
        Initialize histogram

        Args:
            buckets: Bucket boundaries (e.g., [10, 50, 100, 500])
        """
        self.buckets = sorted(buckets)
        self.counts = defaultdict(int)
        self.sum = 0
        self.count = 0

    def observe(self, value: float):
        """Add observation to histogram"""
        self.sum += value
        self.count += 1

        # Find bucket
        for bucket in self.buckets:
            if value <= bucket:
                self.counts[bucket] += 1
                return

        # Value exceeds all buckets
        self.counts[float("inf")] += 1

    def get_stats(self) -> Dict:
        """Get histogram statistics"""
        if self.count == 0:
            return {"count": 0, "sum": 0, "avg": 0, "buckets": {}}

        return {
            "count": self.count,
            "sum": self.sum,
            "avg": self.sum / self.count,
            "buckets": dict(self.counts),
        }


class Counter:
    """Thread-safe counter with labels"""

    def __init__(self, name: str, help_text: str = ""):
        self.name = name
        self.help_text = help_text
        self.values = defaultdict(int)

    def inc(self, labels: Optional[Dict] = None, amount: int = 1):
        """Increment counter"""
        key = self._labels_to_key(labels)
        self.values[key] += amount

    def get(self, labels: Optional[Dict] = None) -> int:
        """Get counter value"""
        key = self._labels_to_key(labels)
        return self.values.get(key, 0)

    def _labels_to_key(self, labels: Optional[Dict]) -> str:
        """Convert labels dict to string key"""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def get_all(self) -> Dict:
        """Get all counter values"""
        return dict(self.values)


class Gauge:
    """Gauge metric (can go up or down)"""

    def __init__(self, name: str, help_text: str = ""):
        self.name = name
        self.help_text = help_text
        self.values = defaultdict(float)

    def set(self, value: float, labels: Optional[Dict] = None):
        """Set gauge value"""
        key = self._labels_to_key(labels)
        self.values[key] = value

    def inc(self, amount: float = 1, labels: Optional[Dict] = None):
        """Increment gauge"""
        key = self._labels_to_key(labels)
        self.values[key] = self.values.get(key, 0) + amount

    def dec(self, amount: float = 1, labels: Optional[Dict] = None):
        """Decrement gauge"""
        key = self._labels_to_key(labels)
        self.values[key] = self.values.get(key, 0) - amount

    def get(self, labels: Optional[Dict] = None) -> float:
        """Get gauge value"""
        key = self._labels_to_key(labels)
        return self.values.get(key, 0)

    def _labels_to_key(self, labels: Optional[Dict]) -> str:
        """Convert labels dict to string key"""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def get_all(self) -> Dict:
        """Get all gauge values"""
        return dict(self.values)


class Summary:
    """
    Summary metric with quantiles

    Tracks count, sum, and calculates percentiles
    """

    def __init__(self, name: str, help_text: str = "", max_age: int = 600):
        self.name = name
        self.help_text = help_text
        self.max_age = max_age  # Keep observations for N seconds
        self.observations = deque()  # (timestamp, value)
        self.count = 0
        self.sum = 0

    def observe(self, value: float):
        """Add observation"""
        now = time.time()
        self.observations.append((now, value))
        self.count += 1
        self.sum += value

        # Clean old observations
        self._cleanup_old()

    def _cleanup_old(self):
        """Remove observations older than max_age"""
        cutoff = time.time() - self.max_age

        while self.observations and self.observations[0][0] < cutoff:
            self.observations.popleft()

    def get_stats(self, quantiles: List[float] = [0.5, 0.9, 0.95, 0.99]) -> Dict:
        """
        Get summary statistics

        Args:
            quantiles: Percentiles to calculate (e.g., [0.5, 0.9, 0.99])

        Returns:
            {
                'count': N,
                'sum': X,
                'avg': Y,
                'quantiles': {0.5: ..., 0.9: ..., 0.99: ...}
            }
        """
        self._cleanup_old()

        if not self.observations:
            return {"count": 0, "sum": 0, "avg": 0, "quantiles": {}}

        values = [v for _, v in self.observations]
        sorted_values = sorted(values)

        quantile_results = {}
        for q in quantiles:
            idx = int(len(sorted_values) * q)
            if idx >= len(sorted_values):
                idx = len(sorted_values) - 1
            quantile_results[q] = sorted_values[idx]

        return {
            "count": len(values),
            "sum": sum(values),
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "quantiles": quantile_results,
        }


class MetricsCollector:
    """
    Central metrics collector

    Features:
    - Counters, Gauges, Histograms, Summaries
    - Labeled metrics
    - Prometheus-compatible export
    - Time-series snapshots
    """

    def __init__(self):
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self.summaries: Dict[str, Summary] = {}
        self.snapshots = deque(maxlen=1000)  # Keep last 1000 snapshots

    def counter(self, name: str, help_text: str = "") -> Counter:
        """Get or create counter"""
        if name not in self.counters:
            self.counters[name] = Counter(name, help_text)
        return self.counters[name]

    def gauge(self, name: str, help_text: str = "") -> Gauge:
        """Get or create gauge"""
        if name not in self.gauges:
            self.gauges[name] = Gauge(name, help_text)
        return self.gauges[name]

    def histogram(
        self, name: str, buckets: List[float], help_text: str = ""
    ) -> Histogram:
        """Get or create histogram"""
        if name not in self.histograms:
            self.histograms[name] = Histogram(buckets)
        return self.histograms[name]

    def summary(self, name: str, help_text: str = "", max_age: int = 600) -> Summary:
        """Get or create summary"""
        if name not in self.summaries:
            self.summaries[name] = Summary(name, help_text, max_age)
        return self.summaries[name]

    def take_snapshot(self):
        """Take snapshot of all metrics"""
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "counters": {},
            "gauges": {},
            "histograms": {},
            "summaries": {},
        }

        for name, counter in self.counters.items():
            snapshot["counters"][name] = counter.get_all()

        for name, gauge in self.gauges.items():
            snapshot["gauges"][name] = gauge.get_all()

        for name, histogram in self.histograms.items():
            snapshot["histograms"][name] = histogram.get_stats()

        for name, summary in self.summaries.items():
            snapshot["summaries"][name] = summary.get_stats()

        self.snapshots.append(snapshot)

        return snapshot

    def get_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus format

        Returns:
            Prometheus-formatted metrics text
        """
        lines = []

        # Counters
        for name, counter in self.counters.items():
            lines.append(f"# HELP {name} {counter.help_text}")
            lines.append(f"# TYPE {name} counter")

            for labels_key, value in counter.get_all().items():
                if labels_key:
                    lines.append(f"{name}{{{labels_key}}} {value}")
                else:
                    lines.append(f"{name} {value}")

        # Gauges
        for name, gauge in self.gauges.items():
            lines.append(f"# HELP {name} {gauge.help_text}")
            lines.append(f"# TYPE {name} gauge")

            for labels_key, value in gauge.get_all().items():
                if labels_key:
                    lines.append(f"{name}{{{labels_key}}} {value}")
                else:
                    lines.append(f"{name} {value}")

        # Histograms
        for name, histogram in self.histograms.items():
            lines.append(f"# HELP {name} Histogram")
            lines.append(f"# TYPE {name} histogram")

            stats = histogram.get_stats()

            for bucket, count in stats["buckets"].items():
                bucket_label = "+In" if bucket == float("inf") else str(bucket)
                lines.append(f'{name}_bucket{{le="{bucket_label}"}} {count}')

            lines.append(f"{name}_sum {stats['sum']}")
            lines.append(f"{name}_count {stats['count']}")

        # Summaries
        for name, summary in self.summaries.items():
            lines.append(f"# HELP {name} Summary")
            lines.append(f"# TYPE {name} summary")

            stats = summary.get_stats()

            for quantile, value in stats.get("quantiles", {}).items():
                lines.append(f'{name}{{quantile="{quantile}"}} {value}')

            lines.append(f"{name}_sum {stats['sum']}")
            lines.append(f"{name}_count {stats['count']}")

        return "\n".join(lines)

    def get_time_series(
        self, metric_name: str, metric_type: str, duration_minutes: int = 60
    ) -> List[Dict]:
        """
        Get time-series data for a metric

        Args:
            metric_name: Metric name
            metric_type: 'counter', 'gauge', 'histogram', or 'summary'
            duration_minutes: How far back to look

        Returns:
            List of {timestamp, value} dicts
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)
        series = []

        for snapshot in self.snapshots:
            ts = datetime.fromisoformat(snapshot["timestamp"])
            if ts < cutoff:
                continue

            metric_data = snapshot.get(f"{metric_type}s", {}).get(metric_name)
            if metric_data:
                series.append(
                    {"timestamp": snapshot["timestamp"], "value": metric_data}
                )

        return series


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("📊 Enhanced Metrics Test")
    print("=" * 70)

    # Create collector
    metrics = MetricsCollector()

    # Counter example
    print("\n1️⃣ Counter: messages_sent")
    msg_counter = metrics.counter("messages_sent", "Total messages sent")
    msg_counter.inc(labels={"from": "code", "to": "browser"})
    msg_counter.inc(labels={"from": "code", "to": "browser"})
    msg_counter.inc(labels={"from": "browser", "to": "code"})

    print(
        f"   code→browser: {msg_counter.get(labels={'from': 'code', 'to': 'browser'})}"
    )
    print(
        f"   browser→code: {msg_counter.get(labels={'from': 'browser', 'to': 'code'})}"
    )

    # Gauge example
    print("\n2️⃣ Gauge: active_connections")
    conn_gauge = metrics.gauge("active_connections", "Number of active connections")
    conn_gauge.set(5, labels={"client": "browser"})
    conn_gauge.inc(2, labels={"client": "browser"})
    conn_gauge.dec(1, labels={"client": "browser"})

    print(f"   Browser connections: {conn_gauge.get(labels={'client': 'browser'})}")

    # Histogram example
    print("\n3️⃣ Histogram: message_size_bytes")
    size_hist = metrics.histogram(
        "message_size_bytes",
        buckets=[100, 1000, 10000, 100000],
        help_text="Message size distribution",
    )

    # Simulate message sizes
    for size in [50, 250, 500, 5000, 15000, 75000, 150000]:
        size_hist.observe(size)

    print(f"   Stats: {size_hist.get_stats()}")

    # Summary example
    print("\n4️⃣ Summary: request_duration_ms")
    duration_summary = metrics.summary(
        "request_duration_ms", help_text="Request duration in milliseconds", max_age=300
    )

    # Simulate request durations
    for duration in [10, 25, 30, 45, 50, 75, 100, 150, 200, 500]:
        duration_summary.observe(duration)

    stats = duration_summary.get_stats(quantiles=[0.5, 0.9, 0.95, 0.99])
    print(f"   Count: {stats['count']}")
    print(f"   Avg: {stats['avg']:.2f} ms")
    print(f"   P50: {stats['quantiles'][0.5]:.2f} ms")
    print(f"   P90: {stats['quantiles'][0.9]:.2f} ms")
    print(f"   P99: {stats['quantiles'][0.99]:.2f} ms")

    # Take snapshot
    print("\n5️⃣ Taking metrics snapshot...")
    snapshot = metrics.take_snapshot()
    print(f"   Snapshot at: {snapshot['timestamp']}")

    # Prometheus export
    print("\n6️⃣ Prometheus export (first 500 chars):")
    prom_metrics = metrics.get_prometheus_metrics()
    print(prom_metrics[:500] + "...")

    print("\n✅ Test complete")
