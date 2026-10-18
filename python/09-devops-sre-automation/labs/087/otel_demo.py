"""Local OpenTelemetry metrics SDK demonstration; no OTLP network export."""
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

def main():
    reader=InMemoryMetricReader()
    provider=MeterProvider(metric_readers=[reader])
    try:
        meter=provider.get_meter("chapter-087-sre-monitor")
        counter=meter.create_counter("sre.monitor.samples",unit="1",description="Successful samples")
        counter.add(1,{"service.name":"lab-monitor","environment":"lab"})
        data=reader.get_metrics_data()
        count=sum(len(metric.scope_metrics) for metric in data.resource_metrics)
        print("Local OTEL resource metric groups:",count)
    finally:
        provider.shutdown()

if __name__=="__main__":main()
