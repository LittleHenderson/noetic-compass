"""Action-time pre-flight for the LIVE activation. Refuses on ANY failure.

A check that cannot RUN is treated as a failure, never as a pass, and is
reported distinctly from a check that ran and said no.
"""
import boto3, sys, hashlib, pathlib, subprocess, shutil

R=pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
sys.path.insert(0,str(R/"tools"/"runpod_open_weight_canary_v2"))
import verify_activation_parameters as vap
STACK="cas-harness-preprod-guardian"; NAME="live-activation-v3-verified"

def session():
    c=boto3.client("sts").assume_role(
        RoleArn="arn:aws:iam::063693212118:role/OrganizationAccountAccessRole",
        RoleSessionName="preflight")["Credentials"]
    return boto3.Session(aws_access_key_id=c["AccessKeyId"],
        aws_secret_access_key=c["SecretAccessKey"], aws_session_token=c["SessionToken"])

s=session()
cf=s.client("cloudformation",region_name="us-west-2")
lam=s.client("lambda",region_name="us-west-2"); s3=s.client("s3",region_name="us-west-2")
fail=[]

a=lam.get_account_settings()["AccountLimit"]; head=a["ConcurrentExecutions"]-100
print(f"1. quota / capacity : limit={a['ConcurrentExecutions']} headroom={head} (LIVE reserves 8)")
if head<8: fail.append("insufficient reservable headroom")

d=cf.describe_change_set(ChangeSetName=NAME,StackName=STACK)
print(f"2. change set       : {d['Status']}/{d['ExecutionStatus']} changes={len(d['Changes'])}")
if d["Status"]!="CREATE_COMPLETE" or d["ExecutionStatus"]!="AVAILABLE":
    fail.append("change set not CREATE_COMPLETE/AVAILABLE")

repl=[x for x in d["Changes"] if x["ResourceChange"].get("Replacement")=="True"]
rem=[x for x in d["Changes"] if x["ResourceChange"]["Action"]=="Remove"]
print(f"3. destructive ops  : replacements={len(repl)} removals={len(rem)}")
if repl or rem: fail.append("change set would replace or remove a resource")

st=cf.describe_stacks(StackName=STACK)["Stacks"][0]
print(f"4. stack state      : {st['StackStatus']}")
if not st["StackStatus"].endswith("_COMPLETE"): fail.append("stack not in a stable *_COMPLETE state")

p={x["ParameterKey"]:x.get("ParameterValue") for x in d["Parameters"]}
known=dict(p)
known["DeploymentBindingSha256"]="a54c1810957e8903527f28e16a3856ee91b2eae90757705557949015c1e8fa3e"
doc=(R/"docs/working/aws_gate1_evidence_20260821/timing_evidence/deployment-binding.PREPROD.json").read_bytes()
f=vap.verify_activation_parameters(known, doc)
print(f"5. param verifier   : {'PASS' if not f else 'FAIL'}")
if f: fail.extend(f)

for label,key,ver,want in (
    ("artifact",p["LambdaArtifactKey"],p["LambdaArtifactVersion"],p["RuntimeZipSha256"]),
    ("binding ",p["DeploymentBindingObjectKey"],p["DeploymentBindingObjectVersion"],p["DeploymentBindingObjectSha256"]),
    ("timing  ",p["TimingEvidenceObjectKey"],p["TimingEvidenceObjectVersion"],p["TimingValidationEvidenceSha256"])):
    b=s3.get_object(Bucket=p["LambdaArtifactBucket"],Key=key,VersionId=ver)["Body"].read()
    ok=hashlib.sha256(b).hexdigest()==want
    print(f"6. link {label}    : {len(b)} B  sha256 match={ok}")
    if not ok: fail.append(f"{label.strip()} hash link mismatch")

# The canary freeze check needs the REPO interpreter (numpy). An interpreter that
# cannot import the module cannot answer the question, and must not be read as a pass
# OR as a specific "stale" verdict.
repo_py = shutil.which("python") or sys.executable
probe = (
 "import io,json,sys,importlib.util,pathlib;"
 f"p=pathlib.Path(r'{R}');"
 "spec=importlib.util.spec_from_file_location('c',p/'noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/run_open_weight_trajectory_canary_v2.py');"
 "m=importlib.util.module_from_spec(spec);sys.modules['c']=m;spec.loader.exec_module(m);"
 "pre=json.loads(io.open(p/'docs/working/OPEN_WEIGHT_TRAJECTORY_CANARY_V2_PREREG.json',encoding='utf-8',newline='').read());"
 "print('VERDICT',m._current_source_file_manifest_document()['manifest_sha256']==pre['launch_bindings']['required_source_file_manifest_sha256'])")
r=subprocess.run([repo_py,"-c",probe],capture_output=True,text=True,cwd=str(R))
if "VERDICT" not in r.stdout:
    print(f"7. canary freeze    : CHECK COULD NOT RUN ({repo_py})")
    print("      stderr tail:", (r.stderr or "").strip().splitlines()[-1:] )
    fail.append("canary freeze check could not run -- unknown, not assumed good")
else:
    frozen = "VERDICT True" in r.stdout
    print(f"7. canary freeze    : current={frozen}")
    if not frozen: fail.append("canary source freeze is not current at HEAD")

print()
if fail:
    print("PRE-FLIGHT FAILED -- NOT EXECUTING:")
    for x in fail: print("   -", x)
    sys.exit(1)
print("ALL 7 PRE-FLIGHT CHECKS PASSED.")
sys.exit(0)
