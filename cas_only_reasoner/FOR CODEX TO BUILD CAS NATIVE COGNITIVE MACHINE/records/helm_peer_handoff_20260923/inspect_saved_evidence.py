"""Read saved receipts, compare Git bytes and inspect AWS state. No project imports or execution."""
import argparse, datetime, hashlib, json, pathlib, subprocess
from botocore.config import Config
from botocore.exceptions import ClientError
import boto3

p=argparse.ArgumentParser()
p.add_argument("--peer", required=True)
p.add_argument("--repo", required=True)
p.add_argument("--out", required=True)
a=p.parse_args()
peer=pathlib.Path(a.peer)
repo=pathlib.Path(a.repo)
rel="cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
commit="dfe15fa6462866a449ddff4d6b04006ae6f3c665"
old="20208c923d41c24614504d4ecc2b289ecb66eda8"
base="records/helm_eval_design_20260923"
job=base+"/aws_probe_job"
res=job+"/results"
def git(*args):
    return subprocess.check_output(["git","-C",str(repo),*args])
def sha(b):
    return hashlib.sha256(b).hexdigest()
def lf(b):
    return b.replace(b"\r\n",b"\n")
seen={}
def read(path):
    raw=(peer/path).read_bytes()
    blob=git("show",commit+":"+rel+"/"+path)
    seen[path]={"path":str(peer/path),"bytes":len(raw),"sha256_raw":sha(raw),
        "sha256_lf":sha(lf(raw)),"git_blob":git("rev-parse",commit+":"+rel+"/"+path).decode().strip(),
        "committed_sha256_raw":sha(blob),"raw_equals_commit":raw==blob,
        "lf_equals_commit":lf(raw)==lf(blob)}
    return raw
def js(path):
    return json.loads(read(path))
out={"schema":"codex.peer-handoff-verification/1","verified_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
     "scope":"Saved-record and source-byte inspection plus read-only AWS state. No tests, neural execution or training.",
     "peer_commit":commit,"builder_start":git("rev-parse","HEAD").decode().strip(),
     "remote_heads":git("ls-remote","--heads","origin","research/helm-integration-20260923","codex/helm-stage2-checker-20260923").decode().strip().splitlines()}
out["commit_times"]={r:git("show","-s","--format=%H %cI",r).decode().strip() for r in [commit,"60e382b0","7f85af1e"]}
summary=js(job+"/RESULTS_READING.json")
launch=js(job+"/launch_record.json")
watch=js(job+"/watch_record.json")
read(job+"/JOB_LIMITS.md")
read(job+"/results/STATUS")
pre=js(res+"/preflight.json")
out["preflight"]={k:v for k,v in pre.items() if k!="opened_files"}
out["launch"]={k:v for k,v in launch.items() if k not in ["wheels","checkpoint_sha256","links_stored"]}
out["watch_record"]=watch
out["probe_models"]=[]
out["preservation_models"]=[]
out["historical_source_hash_checks"]=[]
for seed in ["20260917","20260918","20260919"]:
    for kind,filename in [("probe","before_reading_v0_2_T4_seed"+seed+".json"),
                          ("preservation","preservation_reference_20208c92_T4_seed"+seed+".json")]:
        d=js(res+"/"+filename)
        for path,expected in d["source_sha256_lf"].items():
            actual=sha(lf(git("show",old+":"+rel+"/"+path)))
            out["historical_source_hash_checks"].append({"record":filename,"source":path,"expected":expected,"actual":actual,"matches":actual==expected})
        for r in d["results"]:
            if kind=="probe":
                row={k:r[k] for k in ["label","verdict","M0_delta0","M1z","M2z","summary","model"]}
                row["complete"]=d["complete"]
                row["per_focus_count"]=len(r["per_focus"])
                row["summary_matches_saved_reading"]=all(r[k]==sr[q] for k,q in [("label","label"),("verdict","verdict"),("M0_delta0","delta0"),("M1z","M1z"),("M2z","M2z")] for sr in summary["probe_T4"][seed]["results"] if sr["label"]==r["label"])
                cp=r["model"]["checkpoint"]
                if cp:
                    cp_key=next((key for key in launch["checkpoint_sha256"] if cp.endswith(key)),None)
                    row["checkpoint_hash_matches_launch"]=bool(cp_key and r["model"]["checkpoint_sha256"]==launch["checkpoint_sha256"][cp_key])
                out["probe_models"].append(row)
            else:
                row={k:r[k] for k in r if k!="per_record"}
                row["complete"]=d["complete"]
                row["per_record_count"]=len(r["per_record"])
                row["digest_matches_saved_reading"]=r["overall_digest"]==summary["preservation_T4"][seed]["digests"][r["label"]]
                out["preservation_models"].append(row)
st=js(res+"/probe_self_test_result_T4.json")
out["probe_self_test"]={k:{"verdict":v["verdict"],"summary":v["summary"],
    "matches_saved_reading":v["verdict"]==summary["self_test"]["verdicts"][k] and v["summary"]==summary["self_test"]["summaries"][k]} for k,v in st["results"].items()}
out["source_unchanged_during_probe_selftest"]=len(set(st["pointer_learner_sha256_lf_before_after"]))==1
out["cross_device"]={k:v for k,v in summary.items() if k.startswith("cross_gpu")}
out["cross_device_custody"]="3 comparisons refer to retained laptop seed-20260919 JSON; 4 laptop digests are literal printed values in peer read_results.py, not a complete retained reference receipt."
read(base+"/analogy_wiring_probe/preservation_reference_20208c92_seed20260919.json")
for name in ["PREREG_ANALOGY_WIRING_PROBE_v0_2.md","BEFORE_READING_RESULT.md","RUN_LOG.md"]:
    read(base+"/analogy_wiring_probe/"+name)
read(job+"/read_results.py")
read(res+"/results.tar.gz")
out["oracle_selftest"]=js(base+"/d1_acceptance/oracle_selftest_result.json")
read(base+"/d1_acceptance/README.md")
read(base+"/d1_acceptance/a2_compare_harness.py")
out["cloud"]={}
ec2=boto3.client("ec2",region_name="us-west-2",config=Config(connect_timeout=10,read_timeout=20,retries={"max_attempts":1}))
try:
    data=ec2.describe_instances(InstanceIds=["i-07e0016d92bd6197b","i-00787ea718c2631ea"])
    for reservation in data["Reservations"]:
        for instance in reservation["Instances"]:
            iid=instance["InstanceId"]
            volumes=ec2.describe_volumes(Filters=[{"Name":"attachment.instance-id","Values":[iid]}])["Volumes"]
            out["cloud"][iid]={"state":instance["State"]["Name"],"instance_type":instance["InstanceType"],
               "block_devices":instance.get("BlockDeviceMappings",[]),"currently_attached_volume_ids":[v["VolumeId"] for v in volumes]}
    try:
        ec2.describe_volumes(VolumeIds=["vol-0d3077a69b01406c3"])
        out["cloud"]["builder_volume"]="EXISTS"
    except ClientError as exc:
        out["cloud"]["builder_volume"]=exc.response["Error"]["Code"]
except ClientError as exc:
    out["cloud"]["error"]=exc.response["Error"]["Code"]
out["cloud"]["verified_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
out["record_fingerprints"]=list(seen.values())
out["accounting"]={"files_fingerprinted":len(seen),"git_lf_mismatches":sum(not v["lf_equals_commit"] for v in seen.values()),
    "git_raw_differences":sum(not v["raw_equals_commit"] for v in seen.values()),
    "historical_source_checks":len(out["historical_source_hash_checks"]),
    "historical_source_mismatches":sum(not r["matches"] for r in out["historical_source_hash_checks"]),
    "probe_models":len(out["probe_models"]),"preservation_models":len(out["preservation_models"])}
out["limits"]=[
    "Saved metrics are inspected, not recomputed by neural inference.",
    "A3 same-job T4 switch-off acceptance remains unrun by Codex.",
    "Oracle self-test is not checker_v2 acceptance.",
    "Probe source receipt hashes cover five listed historical source files, not the whole runtime dependency graph.",
    "Four cross-device reference values have printed-value custody in read_results.py.",
    "watch_record cost_upper_bound_usd is an estimate, not a provider bill. Its disk note says 20 GB while launch_record says 100 GB; total-cost upper-bound wording needs reconciliation.",
    "No peer S3 objects were deleted. No peer worktree edits made.",
    "Empty current EC2 attachments alone do not establish deletion of an unidentified historical peer volume."
]
pathlib.Path(a.out).write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8", newline="\n")
print(json.dumps({"accounting":out["accounting"],"cloud":out["cloud"],"out":a.out},indent=2))
