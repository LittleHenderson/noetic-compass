"""Ask an outside model for one review round of the verdict plan and the labeling guide. BLOCKER/MAJOR only.

Sends only the two documents. Never prints or stores a key.
Usage: outside_review.py <provider> <model> <output.md> <file1> <file2> ...
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ENDPOINTS = {'deepseek': ('https://api.deepseek.com/chat/completions', 'DEEPSEEK_API_KEY')}
ASK = ('You are an independent reviewer of a study plan. You did not write it. Review the documents below for one purpose: '
       'find defects that would make the label-agreement verdict wrong, unfair, or unreadable. Report BLOCKER and MAJOR findings only; '
       'no style notes. Do not question the ten definitions in Part A of the guide: they are fixed canon and may not be changed. '
       'Check in particular: (1) whether any rule in Part B of the guide contradicts a definition in Part A or contradicts another rule; '
       '(2) whether the plan\'s measures, bars and outcomes are fully fixed in advance and leave no room to choose after seeing results; '
       '(3) whether the two label teams or the writer could share information they should not; '
       '(4) whether "strict agreement" and kappa as defined can be inflated or deflated by something other than real agreement '
       '(for example a Noetic that is present in almost every passage, or the uncertain marking under rule 15); '
       '(5) whether the passage kinds give a fair test for each Noetic, including enough passages where it is absent. '
       'For each finding give: severity, the exact place, why it matters, and the smallest fix. '
       'Start your reply with one line: VERDICT: ACCEPT, ACCEPT_WITH_NOTES, or REJECT. Keep the reply under 700 words.\n\n')


def main(provider, model, out_path, *files):
    url, key_name = ENDPOINTS[provider]
    key = None
    with open(os.path.join(os.path.expanduser('~'), '.cas_llm_keys.env'), encoding='utf-8') as stream:
        for line in stream:
            if line.strip().startswith(key_name + '='):
                key = line.split('=', 1)[1].strip().strip('"').strip("'")
    documents = '\n\n'.join('===== DOCUMENT: %s =====\n%s' % (Path(f).name, Path(f).read_text(encoding='utf-8')) for f in files)
    body = json.dumps({'model': model, 'max_tokens': 32000, 'messages': [{'role': 'user', 'content': ASK + documents}]}).encode('utf-8')
    request = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=600) as response:
        data = json.loads(response.read())
    text = data['choices'][0]['message']['content']
    Path(out_path).write_text('# Outside review (%s %s)\n\nFiles reviewed: %s\n\n%s\n' % (provider, model, ', '.join(Path(f).name for f in files), text),
                              encoding='utf-8', newline='\n')
    print(json.dumps({'model': model, 'usage': data.get('usage')}))
    print(text)


if __name__ == '__main__':
    main(*sys.argv[1:])
