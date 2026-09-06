"""Read the existing H100 quota request; no request creation or compute launch."""
from datetime import datetime, timezone
import json
from pathlib import Path
import boto3
from botocore.config import Config

output = Path(__file__).with_name('receipt.json')
if output.exists():
    raise RuntimeError('NEW_STATUS_RECEIPT_REQUIRED')
session = boto3.Session(profile_name='default', region_name='us-west-2')
config = Config(connect_timeout=10, read_timeout=30, retries={'max_attempts': 0})
account = session.client('sts', config=config).get_caller_identity()['Account']
if account != '807562639912':
    raise RuntimeError('AWS_ACCOUNT_MISMATCH')
client = session.client('service-quotas', config=config)
request = client.get_requested_service_quota_change(
    RequestId='7b94b9c2dd564a999316b4217037c59fd72Ae8fc')
quota = client.get_service_quota(ServiceCode='ec2', QuotaCode='L-417A185B')
receipt = {'schema': 'cas-meta2-h100-readonly-status/0.1',
    'utc': datetime.now(timezone.utc).isoformat(), 'account': account,
    'region': 'us-west-2', 'request_response': request, 'quota_response': quota,
    'quota_sufficient_for_one_p5_4xlarge': quota['Quota']['Value'] >= 16,
    'capacity_proven': False, 'compute_launched': False, 'quota_request_submitted': False}
with output.open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, default=str, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps({'status': request['RequestedQuota']['Status'],
                  'quota_value': quota['Quota']['Value'], 'compute_launched': False}))
