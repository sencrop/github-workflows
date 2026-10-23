#!/usr/bin/env python3
"""Compare the RDS and ElastiCache capacity in service with the reservations held (active or awaiting payment).

Capacity is counted in normalized size units per pool (engine + instance family),
the way AWS applies size-flexible reservations: a t4g.xlarge weighs 8 units,
a t4g.micro 0.5, a Multi-AZ deployment counts double.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from collections import defaultdict

SIZE_UNITS = {
    "nano": 0.25, "micro": 0.5, "small": 1, "medium": 2, "large": 4, "xlarge": 8,
    "2xlarge": 16, "4xlarge": 32, "8xlarge": 64, "12xlarge": 96, "16xlarge": 128, "24xlarge": 192,
    "32xlarge": 256, "48xlarge": 384,
}
RDS_PRODUCT_BY_ENGINE = {"postgres": "postgresql"}
AURORA_IO_OPTIMIZED_FACTOR = 1.3
RDS_NOT_BILLED_STATUSES = {"creating", "deleting", "deleted", "failed", "stopped", "stopping"}
ELASTICACHE_NOT_BILLED_STATUSES = {"creating", "deleting", "deleted", "create-failed", "incompatible-network"}
SKIPPED = []
RESERVATION_STATES = {"active", "payment-pending"}
EXEMPT_TAG = "reservation-exempt-until"
NOW = dt.datetime.now(dt.timezone.utc)


class Aws:
    def __init__(self, region, fixture_dir=None):
        self.region = region
        self.fixture_dir = fixture_dir

    def call(self, service, operation, *args):
        if self.fixture_dir:
            name = f"{service}_{operation}" + ("_" + "_".join(a.strip("-") for a in args) if args else "")
            path = os.path.join(self.fixture_dir, name + ".json")
            if not os.path.exists(path):
                return {}
            with open(path) as f:
                return json.load(f)
        cmd = ["aws", service, operation, "--region", self.region, "--output", "json", *args]
        out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
        return json.loads(out) if out.strip() else {}


def parse_time(value):
    if isinstance(value, dt.datetime):
        return value
    return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def size_units(instance_class):
    return SIZE_UNITS.get(instance_class.split(".")[-1])


def skip(service, identifier, reason):
    SKIPPED.append(f"{identifier} ({service}): {reason}")


def rds_pool(product, license_included, instance_class, multi_az):
    """SQL Server and Oracle License Included reservations are not size-flexible: they only cover the exact class and deployment."""
    if product.startswith("sqlserver") or (product.startswith("oracle") and license_included):
        return f"{product} (li) / {instance_class}" + (" Multi-AZ" if multi_az else "")
    return f"{product} / {'.'.join(instance_class.split('.')[:2])}"


def aurora_io_optimized_clusters(aws):
    clusters = aws.call("rds", "describe-db-clusters").get("DBClusters", [])
    return {c["DBClusterIdentifier"] for c in clusters if c.get("StorageType") == "aurora-iopt1"}


def exemption(tags):
    for tag in tags or []:
        if tag.get("Key") == EXEMPT_TAG:
            try:
                return dt.date.fromisoformat(tag["Value"])
            except ValueError:
                return dt.date.min
    return None


def rds_resources(aws):
    io_optimized = aurora_io_optimized_clusters(aws)
    for db in aws.call("rds", "describe-db-instances").get("DBInstances", []):
        if db.get("DBInstanceStatus") in RDS_NOT_BILLED_STATUSES:
            continue
        units = size_units(db["DBInstanceClass"])
        if units is None:
            skip("rds", db["DBInstanceIdentifier"], f"{db['DBInstanceClass']} is not a reservable size")
            continue
        engine = db["Engine"]
        product = RDS_PRODUCT_BY_ENGINE.get(engine, engine)
        label = db["DBInstanceClass"] + (" Multi-AZ" if db.get("MultiAZ") else "")
        if db.get("DBClusterIdentifier") in io_optimized:
            units *= AURORA_IO_OPTIMIZED_FACTOR
            label += " I/O-Optimized"
        yield {
            "service": "rds",
            "id": db["DBInstanceIdentifier"],
            "pool": rds_pool(product, db.get("LicenseModel") == "license-included", db["DBInstanceClass"], db.get("MultiAZ")),
            "label": label,
            "units": units * (2 if db.get("MultiAZ") else 1),
            "created": parse_time(db["InstanceCreateTime"]),
            "exempt_until": exemption(db.get("TagList")),
        }


def rds_reservations(aws):
    for ri in aws.call("rds", "describe-reserved-db-instances").get("ReservedDBInstances", []):
        if ri.get("State") not in RESERVATION_STATES:
            continue
        units = size_units(ri["DBInstanceClass"])
        if units is None:
            skip("rds reservation", ri["ReservedDBInstanceId"], f"unknown size {ri['DBInstanceClass']}")
            continue
        start = parse_time(ri["StartTime"])
        yield {
            "id": ri["ReservedDBInstanceId"],
            "pool": rds_pool(ri["ProductDescription"].lower().split("(")[0], "(li)" in ri["ProductDescription"].lower(), ri["DBInstanceClass"], ri.get("MultiAZ")),
            "label": f"{ri['DBInstanceCount']} x {ri['DBInstanceClass']}" + (" Multi-AZ" if ri.get("MultiAZ") else "") + (" (awaiting payment)" if ri.get("State") == "payment-pending" else ""),
            "units": ri["DBInstanceCount"] * units * (2 if ri.get("MultiAZ") else 1),
            "end": start + dt.timedelta(seconds=int(ri["Duration"])),
        }


def elasticache_resources(aws):
    clusters = aws.call("elasticache", "describe-cache-clusters", "--show-cache-node-info").get("CacheClusters", [])
    for cluster in clusters:
        if cluster.get("CacheClusterStatus") in ELASTICACHE_NOT_BILLED_STATUSES:
            continue
        units = size_units(cluster["CacheNodeType"])
        if units is None:
            skip("elasticache", cluster["CacheClusterId"], f"{cluster['CacheNodeType']} is not a reservable size")
            continue
        tags = aws.call("elasticache", "list-tags-for-resource", "--resource-name", cluster["ARN"]).get("TagList")
        family = ".".join(cluster["CacheNodeType"].split(".")[:2])
        yield {
            "service": "elasticache",
            "id": cluster["CacheClusterId"],
            "pool": f"elasticache / {family}",
            "label": f"{cluster['NumCacheNodes']} x {cluster['CacheNodeType']} {cluster.get('Engine', '')}".rstrip(),
            "units": cluster["NumCacheNodes"] * units,
            "created": parse_time(cluster["CacheClusterCreateTime"]),
            "exempt_until": exemption(tags),
        }


def elasticache_reservations(aws):
    for ri in aws.call("elasticache", "describe-reserved-cache-nodes").get("ReservedCacheNodes", []):
        if ri.get("State") not in RESERVATION_STATES:
            continue
        units = size_units(ri["CacheNodeType"])
        if units is None:
            skip("elasticache reservation", ri["ReservedCacheNodeId"], f"unknown size {ri['CacheNodeType']}")
            continue
        start = parse_time(ri["StartTime"])
        family = ".".join(ri["CacheNodeType"].split(".")[:2])
        yield {
            "id": ri["ReservedCacheNodeId"],
            "pool": f"elasticache / {family}",
            "label": f"{ri['CacheNodeCount']} x {ri['CacheNodeType']} {ri.get('ProductDescription', '')}".rstrip() + (" (awaiting payment)" if ri.get("State") == "payment-pending" else ""),
            "units": ri["CacheNodeCount"] * units,
            "end": start + dt.timedelta(seconds=int(ri["Duration"])),
        }


def analyse(resources, reservations, expiry_days, grace_days, min_uncovered_units):
    today = NOW.date()
    recent, exempt, expired_exemptions, demand = [], [], [], defaultdict(list)
    for r in resources:
        age = (NOW - r["created"]).days
        if r["exempt_until"] is not None and r["exempt_until"] >= today:
            exempt.append(r)
            continue
        if r["exempt_until"] is not None:
            expired_exemptions.append(r)
        if age < grace_days:
            recent.append(r)
            continue
        demand[r["pool"]].append(r)

    reserved = defaultdict(float)
    for ri in reservations:
        reserved[ri["pool"]] += ri["units"]

    uncovered = []
    for pool, items in sorted(demand.items()):
        in_service = sum(r["units"] for r in items)
        gap = in_service - reserved.get(pool, 0)
        if gap > 0 and gap >= min_uncovered_units:
            uncovered.append({"pool": pool, "in_service": in_service, "reserved": reserved.get(pool, 0), "gap": gap, "items": items})

    expiring = [ri for ri in reservations if ri["end"] <= NOW + dt.timedelta(days=expiry_days)]
    expiring.sort(key=lambda ri: ri["end"])
    return uncovered, expiring, recent, exempt, expired_exemptions


def fmt_units(value):
    return f"{value:g} unit" + ("" if value == 1 else "s")


def report(uncovered, expiring, recent, exempt, expired_exemptions, expiry_days):
    lines = [f"*Reserved instances check — {NOW:%Y-%m-%d}*"]
    if uncovered:
        lines.append(f"*Capacity without reservation ({len(uncovered)} pool{'s' if len(uncovered) > 1 else ''})*")
        for u in uncovered:
            lines.append(f"• `{u['pool']}`: {fmt_units(u['in_service'])} in service, {fmt_units(u['reserved'])} reserved, *{fmt_units(u['gap'])} uncovered*")
            for r in sorted(u["items"], key=lambda r: -r["units"]):
                lines.append(f"    ◦ {r['id']} ({r['label']}, {fmt_units(r['units'])})")
    else:
        lines.append("• All capacity in service is covered by reservations (active or awaiting payment).")
    if expiring:
        lines.append(f"*Reservations expiring within {expiry_days} days*")
        for ri in expiring:
            lines.append(f"• {ri['label']} (`{ri['pool']}`) ends {ri['end']:%Y-%m-%d}, in {(ri['end'] - NOW).days} days")
    if expired_exemptions:
        lines.append("*Exemptions past their date (counted as regular capacity)*")
        lines += [f"• {r['id']}: {EXEMPT_TAG}={r['exempt_until']}" for r in expired_exemptions]
    if exempt:
        lines.append("*Exempted (tag `" + EXEMPT_TAG + "`)*")
        lines += [f"• {r['id']} ({r['label']}) until {r['exempt_until']}" for r in exempt]
    if recent:
        lines.append("*Ignored, created recently*")
        lines += [f"• {r['id']} ({r['label']}), {(NOW - r['created']).days} days old" for r in recent]
    if SKIPPED:
        lines.append("*Skipped*")
        lines += [f"• {item}" for item in SKIPPED]
    return "\n".join(lines)


def write_github_outputs(alert, text):
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a") as f:
            f.write(f"alert={'true' if alert else 'false'}\n")
            f.write("report<<REPORT_EOF\n" + text + "\nREPORT_EOF\n")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(text.replace("•", "-").replace("◦", "  -") + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default=os.environ.get("AWS_DEFAULT_REGION", "eu-central-1"))
    parser.add_argument("--expiry-days", type=int, default=60, help="warn when a reservation ends within this many days")
    parser.add_argument("--grace-days", type=int, default=30, help="ignore resources younger than this many days")
    parser.add_argument("--min-uncovered-units", type=float, default=1, help="report a pool only when its uncovered capacity reaches this many size units (1 = one *.small)")
    parser.add_argument("--fixture-dir", help="read <service>_<operation>[_<args>].json files from this directory instead of calling the AWS CLI")
    args = parser.parse_args()

    if args.fixture_dir and not os.path.isdir(args.fixture_dir):
        parser.error(f"fixture directory not found: {args.fixture_dir}")
    aws = Aws(args.region, args.fixture_dir)
    resources = list(rds_resources(aws)) + list(elasticache_resources(aws))
    reservations = list(rds_reservations(aws)) + list(elasticache_reservations(aws))
    uncovered, expiring, recent, exempt, expired_exemptions = analyse(
        resources, reservations, args.expiry_days, args.grace_days, args.min_uncovered_units
    )
    text = report(uncovered, expiring, recent, exempt, expired_exemptions, args.expiry_days)
    alert = bool(uncovered or expiring)
    print(text)
    write_github_outputs(alert, text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
