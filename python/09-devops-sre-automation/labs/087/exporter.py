"""Optional Prometheus exporter. Binds localhost only, no external push."""
import argparse,time
from prometheus_client import Gauge,Counter,CollectorRegistry,start_http_server
from monitor import Sampler
import psutil

def main(argv=None):
    p=argparse.ArgumentParser(description="Local-only Prometheus metrics endpoint")
    p.add_argument("--port",type=int,default=9109)
    p.add_argument("--interval",type=float,default=15)
    p.add_argument("--disk-path",default="/")
    p.add_argument("--dry-run",action="store_true")
    a=p.parse_args(argv)
    if not 1024<=a.port<=65535 or not 1<=a.interval<=300:
        p.error("invalid port or interval")
    if a.dry_run:
        print("dry-run: no listener and no sampling")
        return 0
    registry=CollectorRegistry()
    gauges={n:Gauge("sre_host_"+n+"_usage_percent","Host "+n+" percent",registry=registry)
            for n in ("cpu","memory","disk")}
    failures=Counter("sre_monitor_sample_errors_total","Host sample failures",registry=registry)
    last=Gauge("sre_monitor_last_success_timestamp_seconds","Last successful sample",registry=registry)
    start_http_server(a.port,addr="127.0.0.1",registry=registry)
    sampler=Sampler(psutil)
    print("Metrics available on loopback at http://127.0.0.1:"+str(a.port)+"/metrics")
    while True:
        try:
            s=sampler.sample(a.disk_path)
            for name,gauge in gauges.items():gauge.set(getattr(s,name))
            last.set(s.timestamp)
        except (OSError,ValueError):
            failures.inc()
        time.sleep(a.interval)

if __name__=="__main__":raise SystemExit(main())
