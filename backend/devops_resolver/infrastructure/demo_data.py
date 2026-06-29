from devops_resolver.domain.models import DemoIncident, IncidentSeverity, KnowledgeDocument
from devops_resolver.shared.ids import new_id


def demo_incidents() -> list[DemoIncident]:
    return [
        DemoIncident(
            key="high-cpu",
            title="High CPU",
            description="CPU utilization exceeded 92% on api-prod-03 for 15 minutes.",
            severity=IncidentSeverity.high,
            runbook_title="High CPU Saturation",
            expected_root_cause="A burst of expensive /reports/export requests saturated worker threads.",
            expected_fix="Rate-limit report exports, scale api workers, and optimize the report query.",
            log_lines=[
                "2026-06-29T07:14:02Z api-prod-03 kernel: load average: 18.92 17.44 12.01",
                "2026-06-29T07:14:07Z api-prod-03 app[api]: slow request path=/reports/export duration_ms=28431 status=200",
                "2026-06-29T07:14:14Z api-prod-03 app[api]: worker pool exhausted active=64 queued=348",
                "2026-06-29T07:14:20Z api-prod-03 node_exporter: cpu_usage_percent=94.8",
            ],
        ),
        DemoIncident(
            key="disk-full",
            title="Disk Full",
            description="Disk usage exceeded 95% on payments-db-01.",
            severity=IncidentSeverity.critical,
            runbook_title="Disk Usage Exceeded 95%",
            expected_root_cause="PostgreSQL WAL archives accumulated after backup shipping stalled.",
            expected_fix="Restore archive shipping, move old WAL archives to cold storage, then expand volume.",
            log_lines=[
                "2026-06-29T08:03:11Z payments-db-01 postgres: archive command failed with exit code 1",
                "2026-06-29T08:05:43Z payments-db-01 node_exporter: filesystem_usage_percent=97.4 mount=/var/lib/postgresql",
                "2026-06-29T08:06:09Z payments-db-01 postgres: could not write to file pg_wal/xlogtemp.882: No space left on device",
                "2026-06-29T08:06:15Z payments-api app: checkout latency p95=6400ms db_wait=5900ms",
            ],
        ),
        DemoIncident(
            key="postgresql-down",
            title="PostgreSQL Down",
            description="Primary PostgreSQL endpoint is refusing connections.",
            severity=IncidentSeverity.critical,
            runbook_title="PostgreSQL Primary Unavailable",
            expected_root_cause="PostgreSQL crashed during checkpoint after disk pressure and restarted into recovery.",
            expected_fix="Confirm recovery completion, promote healthy replica if RTO is exceeded, then remediate storage.",
            log_lines=[
                "2026-06-29T09:22:18Z orders-db-01 postgres: PANIC: could not write to file pg_wal/00000001000000A1: No space left on device",
                "2026-06-29T09:22:20Z orders-db-01 systemd: postgresql.service: Main process exited, status=2/INVALIDARGUMENT",
                "2026-06-29T09:22:34Z orders-api app: psycopg.OperationalError connection refused host=orders-db.service",
                "2026-06-29T09:24:01Z orders-db-01 postgres: database system is in recovery mode",
            ],
        ),
        DemoIncident(
            key="redis-memory-full",
            title="Redis Memory Full",
            description="Redis maxmemory reached and cache writes are failing.",
            severity=IncidentSeverity.high,
            runbook_title="Redis Memory Exhaustion",
            expected_root_cause="Session cache keys lost TTLs after a deployment regression.",
            expected_fix="Restore TTL on session writes, evict oversized keys, and temporarily raise maxmemory.",
            log_lines=[
                "2026-06-29T10:11:00Z redis-cache-02 redis: used_memory_human=14.8G maxmemory_human=15.0G",
                "2026-06-29T10:11:06Z web app: RedisError OOM command not allowed when used memory > maxmemory",
                "2026-06-29T10:11:12Z redis-cache-02 redis: keyspace_hits=928322 keyspace_misses=81822 evicted_keys=0",
                "2026-06-29T10:12:10Z redis-cache-02 redis: scan prefix=session ttl=-1 count=1382042",
            ],
        ),
        DemoIncident(
            key="out-of-memory",
            title="Out Of Memory",
            description="Worker host terminated application processes due to memory pressure.",
            severity=IncidentSeverity.critical,
            runbook_title="Linux Out Of Memory Killer",
            expected_root_cause="Image processing workers loaded unbounded batches into memory.",
            expected_fix="Cap batch size, add memory requests/limits, and replay failed jobs after stabilization.",
            log_lines=[
                "2026-06-29T11:35:31Z worker-07 kernel: Out of memory: Killed process 4932 (image-worker) total-vm:18432000kB",
                "2026-06-29T11:35:38Z worker-07 app[worker]: job batch size=500 queue=image-resize",
                "2026-06-29T11:35:42Z worker-07 systemd: image-worker.service: Failed with result 'oom-kill'",
                "2026-06-29T11:36:01Z queue metrics: pending_jobs=18493 retry_rate=0.42",
            ],
        ),
        DemoIncident(
            key="service-crash",
            title="Service Crash",
            description="Billing service pods are crash-looping after deployment.",
            severity=IncidentSeverity.high,
            runbook_title="Service CrashLoopBackOff",
            expected_root_cause="New billing release requires a missing STRIPE_WEBHOOK_SECRET environment variable.",
            expected_fix="Rollback or add the missing secret, then restart the deployment.",
            log_lines=[
                "2026-06-29T12:02:03Z kubelet: billing-7dd8c9b89b-zvk9s Back-off restarting failed container",
                "2026-06-29T12:02:04Z billing app: ConfigError required env STRIPE_WEBHOOK_SECRET is missing",
                "2026-06-29T12:02:07Z deploy: rollout billing version=2026.06.29.4",
                "2026-06-29T12:03:21Z ingress: /billing/webhook status=503 upstream_reset=true",
            ],
        ),
        DemoIncident(
            key="ssl-expired",
            title="SSL Expired",
            description="Customers report browser certificate warnings on checkout.",
            severity=IncidentSeverity.critical,
            runbook_title="TLS Certificate Expired",
            expected_root_cause="Checkout certificate expired because DNS validation for renewal failed.",
            expected_fix="Fix DNS validation, renew the certificate, reload the ingress, and monitor expiry alerts.",
            log_lines=[
                "2026-06-29T13:00:01Z synthetic-check: https://checkout.example.com tls_error=certificate has expired",
                "2026-06-29T13:01:19Z cert-manager: Order checkout-prod failed reason=DNS01 self check failed",
                "2026-06-29T13:02:20Z ingress-nginx: SSL_do_handshake failed certificate verify failed",
                "2026-06-29T13:05:45Z support: spike in checkout abandonment browser=Chrome",
            ],
        ),
        DemoIncident(
            key="high-disk-io",
            title="High Disk IO",
            description="Search cluster latency increased with high disk IO wait.",
            severity=IncidentSeverity.high,
            runbook_title="High Disk IO Wait",
            expected_root_cause="Large shard merge saturated EBS throughput on search-data-04.",
            expected_fix="Throttle merges, rebalance shards, and raise provisioned IOPS for the data volume.",
            log_lines=[
                "2026-06-29T14:18:22Z search-data-04 node_exporter: io_wait_percent=47.9 device=nvme1n1",
                "2026-06-29T14:18:45Z elasticsearch: merge scheduler throttling now throttling indexing",
                "2026-06-29T14:19:03Z search-api: query_latency_p95_ms=3900 timeout_rate=0.18",
                "2026-06-29T14:20:15Z cloudwatch: volume_read_ops=15200 burst_balance=4",
            ],
        ),
        DemoIncident(
            key="nginx-502",
            title="Nginx 502",
            description="Nginx is returning 502 errors for the public API.",
            severity=IncidentSeverity.high,
            runbook_title="Nginx 502 Bad Gateway",
            expected_root_cause="Upstream API workers exhausted connections after database pool saturation.",
            expected_fix="Restart unhealthy workers, increase upstream keepalive limits, and resolve database pool pressure.",
            log_lines=[
                "2026-06-29T15:07:11Z nginx: upstream prematurely closed connection while reading response header from upstream",
                "2026-06-29T15:07:12Z nginx: status=502 request=/v1/orders upstream=10.20.1.44:8080",
                "2026-06-29T15:07:16Z api app: sqlalchemy.exc.TimeoutError QueuePool limit reached",
                "2026-06-29T15:08:03Z api metrics: active_db_connections=100 max_db_connections=100",
            ],
        ),
        DemoIncident(
            key="memory-leak",
            title="Memory Leak",
            description="API memory usage grows continuously until restarts.",
            severity=IncidentSeverity.high,
            runbook_title="Application Memory Leak",
            expected_root_cause="A request-scoped metrics buffer was retained in a global registry.",
            expected_fix="Disable the leaking metrics collector, deploy the patch, and rotate affected pods.",
            log_lines=[
                "2026-06-29T16:31:05Z api-prod-08 node_exporter: process_resident_memory_bytes=6800000000",
                "2026-06-29T16:36:05Z api-prod-08 node_exporter: process_resident_memory_bytes=7600000000",
                "2026-06-29T16:41:08Z api-prod-08 app: metrics registry size=241003 collector=request_debug",
                "2026-06-29T16:44:30Z kubelet: readiness probe failed endpoint=/healthz timeout",
            ],
        ),
    ]


def knowledge_documents() -> list[KnowledgeDocument]:
    documents: list[KnowledgeDocument] = []
    for demo in demo_incidents():
        documents.append(
            KnowledgeDocument(
                id=new_id("kb"),
                title=demo.runbook_title,
                category="runbook",
                tags=[demo.key, demo.severity.value, "linux", "production"],
                content=(
                    f"Symptoms: {demo.description}\n"
                    f"Likely root cause: {demo.expected_root_cause}\n"
                    "Investigation: inspect recent logs, resource metrics, dependency health, "
                    "and deployment changes. Prefer read-only commands and verify evidence from "
                    "at least two sources before declaring root cause.\n"
                    f"Remediation: {demo.expected_fix}\n"
                    "Escalation: page service owner if customer impact remains after mitigation."
                ),
            )
        )
        documents.append(
            KnowledgeDocument(
                id=new_id("prev"),
                title=f"Previous incident: {demo.title}",
                category="previous_incident",
                tags=[demo.key, "postmortem"],
                content=(
                    f"A previous {demo.title.lower()} incident showed these signals: "
                    f"{' | '.join(demo.log_lines[:3])}. The confirmed root cause was "
                    f"{demo.expected_root_cause}. The durable fix was: {demo.expected_fix}"
                ),
            )
        )
    documents.append(
        KnowledgeDocument(
            id=new_id("doc"),
            title="Production Investigation Standards",
            category="infrastructure_documentation",
            tags=["standard", "sre", "incident-response"],
            content=(
                "Investigations must collect direct evidence, identify blast radius, "
                "avoid destructive commands, and separate mitigation from permanent repair. "
                "Confidence below 80 requires another focused evidence-gathering loop."
            ),
        )
    )
    return documents
