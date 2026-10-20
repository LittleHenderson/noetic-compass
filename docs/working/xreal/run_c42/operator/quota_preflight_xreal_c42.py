"""Read-only preflight for X-REAL c42: on-demand standard vCPU quota (L-1216C47A) headroom >= 4, m6i.xlarge offered in
us-west-2b, its shape and list price. No resource is created or changed. Usage: python -B quota_preflight_xreal_c42.py <out.json>"""
import datetime, json, sys
import boto3
out = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'remote_actions': 'READ_ONLY'}
sq = boto3.client('service-quotas', region_name='us-west-2')
out['quota_L-1216C47A_vcpus'] = sq.get_service_quota(ServiceCode='ec2', QuotaCode='L-1216C47A')['Quota']['Value']
ec = boto3.client('ec2', region_name='us-west-2')
rows, used = [], 0
for page in ec.get_paginator('describe_instances').paginate(Filters=[{'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'shutting-down']}]):
    for r in page['Reservations']:
        for i in r['Instances']:
            v = i['CpuOptions']['CoreCount'] * i['CpuOptions']['ThreadsPerCore']
            standard = i['InstanceType'][0] in 'acdhimrtz' and not i.get('InstanceLifecycle')
            rows.append({'id': i['InstanceId'], 'type': i['InstanceType'], 'vcpus': v, 'state': i['State']['Name'], 'standard_on_demand': standard})
            used += v if standard else 0
out['running_instances'] = rows
out['standard_on_demand_vcpus_in_use'] = used
out['headroom_vcpus'] = out['quota_L-1216C47A_vcpus'] - used
out['offered_us_west_2b'] = bool(ec.describe_instance_type_offerings(LocationType='availability-zone', Filters=[{'Name': 'instance-type', 'Values': ['m6i.xlarge']}, {'Name': 'location', 'Values': ['us-west-2b']}])['InstanceTypeOfferings'])
shape = ec.describe_instance_types(InstanceTypes=['m6i.xlarge'])['InstanceTypes'][0]
out['shape'] = {'vcpus': shape['VCpuInfo']['DefaultVCpus'], 'memory_mib': shape['MemoryInfo']['SizeInMiB']}
pr = boto3.client('pricing', 'us-east-1').get_products(ServiceCode='AmazonEC2', Filters=[{'Type': 'TERM_MATCH', 'Field': k, 'Value': v} for k, v in {'instanceType': 'm6i.xlarge', 'location': 'US West (Oregon)', 'operatingSystem': 'Linux', 'tenancy': 'Shared', 'preInstalledSw': 'NA', 'capacitystatus': 'Used'}.items()])
out['hourly_usd'] = [float(d['pricePerUnit']['USD']) for p in pr['PriceList'] for t in json.loads(p).get('terms', {}).get('OnDemand', {}).values() for d in t['priceDimensions'].values() if d['unit'] == 'Hrs']
out['verdict'] = 'QUOTA_OK' if out['headroom_vcpus'] >= 4 and out['offered_us_west_2b'] and out['shape'] == {'vcpus': 4, 'memory_mib': 16384} else 'BLOCKER'
with open(sys.argv[1], 'x', encoding='utf-8', newline='\n') as f:
    json.dump(out, f, indent=1)
print(json.dumps(out, indent=1))
