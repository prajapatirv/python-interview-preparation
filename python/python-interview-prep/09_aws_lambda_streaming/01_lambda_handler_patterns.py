"""
AWS Lambda handler shape: module-level initialization (reused across warm invocations),
structured logging, and re-raising on failure so Lambda's retry/DLQ mechanism works.
This simulates invoking the handler locally -- no AWS credentials or boto3 needed.

Run me: python 01_lambda_handler_patterns.py
"""
import json
import logging
import time

logging.basicConfig(level=logging.INFO, format="  [%(levelname)s] %(message)s")
logger = logging.getLogger()


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- module-level init
# THIS is what makes Lambda "warm starts" fast: a client created here survives between
# invocations of the same execution environment. Creating it INSIDE the handler instead would
# pay connection setup cost on every single invocation.
class FakeS3Client:
    def __init__(self):
        self.connect_calls = 0
        self.connect_calls += 1  # simulate a real connection being established once
        print(f"  FakeS3Client connected (connection #{self.connect_calls} for this process)")

    def get_object(self, bucket, key):
        return {"Body": f"contents of {bucket}/{key}"}


s3_client = FakeS3Client()  # created ONCE per execution environment, not per invocation


# ---------------------------------------------------------------- the handler
class FakeContext:
    """Stands in for AWS Lambda's real `context` object."""
    aws_request_id = "req-abc-123"


def handler(event: dict, context) -> dict:
    logger.info(f"RequestId: {context.aws_request_id}")
    try:
        records = event.get("Records", [])
        results = [process_record(r) for r in records]
        return {"statusCode": 200, "body": json.dumps({"processed": len(results)})}
    except Exception:
        logger.exception("unhandled error processing event")
        raise  # IMPORTANT: re-raise so Lambda retries / routes to a DLQ, don't swallow it


def process_record(record: dict) -> str:
    if record.get("_simulate_failure"):
        raise ValueError(f"malformed record: {record}")
    obj = s3_client.get_object(record["bucket"], record["key"])
    return obj["Body"]


# ---------------------------------------------------------------- simulate two invocations
section("invocation 1: normal event, succeeds")
event = {"Records": [{"bucket": "my-bucket", "key": "orders/2026-09-01.json"}]}
print("result:", handler(event, FakeContext()))

section("invocation 2: SAME warm process, no reconnect happens (connect_calls stays 1)")
event2 = {"Records": [{"bucket": "my-bucket", "key": "orders/2026-09-02.json"}]}
print("result:", handler(event2, FakeContext()))
print(f"s3_client.connect_calls is still {s3_client.connect_calls} -- proving reuse across invocations")

section("invocation 3: a bad record raises, and the handler re-raises (as Lambda expects)")
bad_event = {"Records": [{"_simulate_failure": True}]}
try:
    handler(bad_event, FakeContext())
except ValueError as e:
    print(f"handler correctly propagated the error for Lambda's retry policy to handle: {e}")

# EXPERIMENT: change `raise` in the except block to `return {"statusCode": 500}` instead and
# think through the consequence -- Lambda would consider the invocation "successful" (it got a
# normal return value, not an exception) and would NEVER retry or route to a DLQ, silently
# dropping the failed record.
