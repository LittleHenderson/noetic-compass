"""Ask the outside reviewer one closing question: are its earlier BLOCKER findings closed in the revised documents?

Sends only the documents named. Never prints or stores a key.
Usage: outside_recheck.py <provider> <model> <output.md> <earlier_review.md> <file1> <file2> ...
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ENDPOINTS = {'deepseek': ('https://api.deepseek.com/chat/completions', 'DEEPSEEK_API_KEY')}
ASK = ('You are an independent reviewer. Earlier you (or a reviewer like you) rejected version 1.0 of a study plan and labeling guide. '
       'Your earlier findings are in the first document. The author has revised both and written a response. '
       'Your only job now: for each earlier finding 1 to 8, say CLOSED, PARTLY CLOSED or OPEN in the revised documents, with one sentence of reason, '
       'checking the revised text itself and not the author\'s claims. Then list any NEW BLOCKER the revision introduced (BLOCKER only). '
       'Where the author did not follow your proposed fix exactly (findings 2, 5 and 8), judge whether the substitute removes the risk. '
       'Do not question the ten definitions in Part A of the guide: they are fixed canon. '
       'Start your reply with one line: VERDICT: ACCEPT, ACCEPT_WITH_NOTES, or REJECT. Keep the reply under 500 words.\n\n')


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
    with urllib.request.urlopen(request, timeout=900) as response:
        data = json.loads(response.read())
    text = data['choices'][0]['message']['content']
    Path(out_path).write_text('# Outside re-check (%s %s)\n\nFiles: %s\n\n%s\n' % (provider, model, ', '.join(Path(f).name for f in files), text),
                              encoding='utf-8', newline='\n')
    print(json.dumps({'model': model, 'usage': data.get('usage')}))
    print(text)


if __name__ == '__main__':
    main(*sys.argv[1:])
