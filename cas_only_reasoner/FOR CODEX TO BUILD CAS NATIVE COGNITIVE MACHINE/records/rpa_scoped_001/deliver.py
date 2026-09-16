"""Copy the exact checked offline package to a new user-facing directory."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
HOME=ROOT.parents[3]
SOURCE=ROOT/'records/rpa_scoped_001/acceptance_001'
OUTPUT=HOME/'output/rpa_scoped_001'

def read(path):return json.loads(path.read_bytes())
def checksum(path):return sha256(path.read_bytes()).hexdigest()
def snapshot(folder):
    return {str(p.relative_to(folder)):checksum(p) for p in sorted(folder.rglob('*')) if p.is_file()}
def require(condition,message):
    if not condition:raise ValueError(message)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--acceptance-sha',required=True)
    parser.add_argument('--browser',type=Path,required=True)
    parser.add_argument('--browser-sha',required=True)
    parser.add_argument('--index-sha',required=True)
    args=parser.parse_args()
    require((HOME/'cas_reasoner.txt').is_file(),'Expected outer homebase is absent')
    require(checksum(SOURCE/'receipt.json')==args.acceptance_sha,'Acceptance receipt changed')
    receipt=read(SOURCE/'receipt.json')
    require(checksum(args.browser)==args.browser_sha,'Browser receipt changed')
    browser=read(args.browser)
    require(browser['status']=='PASS' and browser['accepted_receipt_sha256']==args.acceptance_sha
            and browser['accepted_html_rerendered'] is False and browser['document_count']==10,'Browser check does not bind accepted bytes')
    index=ROOT/'records/rpa_scoped_001/browser_index_001/receipt.json'
    index_check=read(index)
    require(checksum(index)==args.index_sha and index_check['status']=='PASS'
            and index_check['accepted_receipt_sha256']==args.acceptance_sha
            and index_check['index_sha256']==checksum(SOURCE/'index.html'),'Index check changed or failed')
    preserved={name:snapshot(HOME/'output'/name) for name in ('rpa_compound_001','rpa_cube_001')}
    OUTPUT.mkdir(exist_ok=False)
    rows=[]
    for row in receipt['files']:
        source=SOURCE/row['path'];target=OUTPUT/row['path']
        require(source.resolve().is_relative_to(SOURCE.resolve()) and target.resolve().is_relative_to(OUTPUT.resolve()),'Unsafe manifest path')
        require(source.stat().st_size==row['bytes'] and checksum(source)==row['sha256'],'Accepted file changed')
        shutil.copyfile(source,target);require(checksum(target)==row['sha256'],'Delivery byte mismatch')
        rows.append(row)
    for source,target_name in ((SOURCE/'receipt.json','receipt.json'),(args.browser,'browser_checks.json'),(index,'index_browser_checks.json')):
        target=OUTPUT/target_name;shutil.copyfile(source,target)
        require(checksum(target)==checksum(source),'Receipt copy mismatch')
        rows.append({'path':target_name,'bytes':target.stat().st_size,'sha256':checksum(target)})
    text=('Open index.html to enter the saved procedure structures.\n\n'
          'Enter changes inspection depth; breadcrumbs return through declared containment.\n'
          'The actual execution-state identity stays fixed. Inspect reads a record.\n'
          'A leaf has no invented interior. Exact JSON and offline browser evidence are included.\n\n'
          'This establishes scoped inspection over ten accepted compound0.5 examples.\n'
          'It does not establish improved reasoning, neural learning, measured geometry,\n'
          'or the complete CNCM. No profile40 measurements or overlap certificates are\n'
          'assigned in these ten inputs. The original deliveries remain unchanged.\n')
    with (OUTPUT/'README.txt').open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
    rows.append({'path':'README.txt','bytes':(OUTPUT/'README.txt').stat().st_size,'sha256':checksum(OUTPUT/'README.txt')})
    require(preserved=={name:snapshot(HOME/'output'/name) for name in preserved},'An old delivery changed')
    result={'status':'EXACT_CHECKED_BYTES_DELIVERED','destination':str(OUTPUT),
        'acceptance_sha256':args.acceptance_sha,'browser_sha256':args.browser_sha,'index_browser_sha256':args.index_sha,
        'files':rows,'preserved_deliveries':preserved,'prior_deliveries_unchanged':True}
    with (Path(__file__).parent/'delivery_001.json').open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,sort_keys=True,separators=(',',':'));stream.write('\n')
    print(json.dumps({'files':len(rows),'destination':str(OUTPUT),'prior_deliveries_unchanged':True}))

if __name__=='__main__':main()
