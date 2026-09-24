"""Build the pinned HISTORICAL REFUSAL ALLOWLIST (Codex decision R3-B, reader revision 4). Pure Python, git only.

WHY. Codex (POLICY_DECISIONS_20260924.md, R3-B): "Only an exact plain `ValueError` whose FULL message is a historical
POINTER_/TYPED_ refusal code from an explicit allowlist extracted from the pinned public historical source is a model
refusal record. Publish the allowlist and its source hash before acceptance." Before revision 4 the evidence module
cut the message to 300 characters and then checked a loose pattern, so `"POINTER_" + "A" * 292 + "\\nCUDA fault"` read
as a refusal (READER_STATIC_REVIEW_20260924.md, first P2 finding).

WHAT IT READS. Only the pinned historical package archive, from git: `package_20208c92/source.zip` at commit 3da10d84
(git blob 50201036..., sha256 c42370c4...). Inside it, every Python member under
`research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/` (the learner package the prediction route runs through).

HOW A MESSAGE IS FOUND (static, `ast` only; nothing from the archive is imported or executed):
  * a function "raises a reason" when its body does `raise ValueError(<param>)` or `raise ValueError('<PREFIX>' +
    <param>)` (for example `source.require` -> no prefix, `matched_contract.require` -> `TYPED_MATCHED:`), or when it
    passes one of its own parameters as the reason to such a function (for example `tokenization._require`,
    `source._closed`); names bound by `x = module.require` or tuple assignments are followed;
  * every call to such a function whose reason is not a forwarded parameter gives one message form, and so does every
    direct `raise ValueError(<expression>)`;
  * a literal reason gives an EXACT message. A reason built with `+`, `%` or an f-string gives a PATTERN: the literal
    parts are kept exactly, `%d` becomes `-?[0-9]{1,20}`, and any other dynamic part becomes DETAIL (1 to 200
    printable ASCII characters, no space, no newline);
  * only forms that START with a literal `POINTER_` or `TYPED_` (after the prefix) are kept; any other form is not a
    historical refusal code (it stays an infrastructure fault);
  * a reason expression the extractor cannot turn into a form is listed under `unresolved` with its member and line.
    Such a message reads as an infrastructure fault (INVALID), which is the conservative direction.

RUN (from the worktree root; reads the 6 MB archive blob; writes ONE file, create-only):
    python -B "<this folder>/build_refusal_allowlist.py"            # refuses if the allowlist file exists
    python -B "<this folder>/build_refusal_allowlist.py" --verify   # rebuilds in memory and compares with the file

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED.
"""
import argparse
import ast
import io
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repro_common as common  # noqa: E402

stop_unless = common.make_stop('REFUSAL_ALLOWLIST_STOPPED:')
OUTPUT = HERE / common.REFUSAL_ALLOWLIST_NAME
SCOPE = 'research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/'
ARCHIVE_REL = common.PACKAGE_REL + '/source.zip'
INTEGER = '-?[0-9]{1,20}'
FORMAT_SPEC = re.compile(r'%(?:\([A-Za-z_]\w*\))?[-#0 +]*\d*(?:\.\d+)?([diouxXeEfFgGcrsa%])')


def archive_bytes():
    """The pinned archive, from git at the package commit, checked by blob id, sha256 and size."""
    stop_unless(common.blob_id(common.PACKAGE_COMMIT, ARCHIVE_REL) == common.PACKAGE_BLOBS['source.zip'],
                'ARCHIVE_BLOB_IS_NOT_THE_PINNED_ONE')
    raw = common.show(common.PACKAGE_COMMIT, ARCHIVE_REL)
    stop_unless(common.git_object_id(raw) == common.PACKAGE_BLOBS['source.zip']
                and common.digest(raw) == common.ARCHIVE_SHA256 and len(raw) == common.ARCHIVE_BYTES,
                'ARCHIVE_BYTES_ARE_NOT_THE_PINNED_ARCHIVE')
    return raw


# ---------------------------------------------------------------------------------------------------------------------
# Static analysis of the scoped members.
# ---------------------------------------------------------------------------------------------------------------------
class Member:
    def __init__(self, path, source):
        self.path, self.name = path, path[len(SCOPE):-3]
        self.tree = ast.parse(source)
        self.functions = {node.name: node for node in self.tree.body if isinstance(node, ast.FunctionDef)}
        self.modules, self.names = {}, {}          # alias -> member name; local name -> (member name, attribute)
        for node in self.tree.body:
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module is None:
                for alias in node.names:
                    self.modules[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.level == 1:
                for alias in node.names:
                    self.names[alias.asname or alias.name] = (node.module, alias.name)
        for node in self.tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target, value = node.targets[0], node.value
            pairs = (list(zip(target.elts, value.elts)) if isinstance(target, ast.Tuple)
                     and isinstance(value, ast.Tuple) and len(target.elts) == len(value.elts) else [(target, value)])
            for left, right in pairs:
                if (isinstance(left, ast.Name) and isinstance(right, ast.Attribute)
                        and isinstance(right.value, ast.Name) and right.value.id in self.modules):
                    self.names[left.id] = (self.modules[right.value.id], right.attr)


def parameters(function):
    return [arg.arg for arg in function.args.posonlyargs + function.args.args]


class Analysis:
    def __init__(self, members):
        self.members = {member.name: member for member in members}
        self.raisers = {}                          # (member, function) -> (reason parameter, prefix)
        self._fixpoint()

    def resolve(self, member, func):
        """The (member, function) a call's `func` names, or None."""
        if isinstance(func, ast.Name):
            if func.id in member.functions:
                return member.name, func.id
            target = member.names.get(func.id)
            if target is not None and target[0] in self.members:
                return self.resolve_attribute(target[0], target[1])
        if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                and func.value.id in member.modules and member.modules[func.value.id] in self.members):
            return self.resolve_attribute(member.modules[func.value.id], func.attr)
        return None

    def resolve_attribute(self, name, attribute, depth=0):
        other = self.members[name]
        if attribute in other.functions:
            return name, attribute
        target = other.names.get(attribute)
        if depth < 8 and target is not None and target[0] in self.members:
            return self.resolve_attribute(target[0], target[1], depth + 1)
        return None

    @staticmethod
    def reason_argument(call, function, parameter):
        names = parameters(function)
        for keyword in call.keywords:
            if keyword.arg == parameter:
                return keyword.value
        index = names.index(parameter)
        return call.args[index] if index < len(call.args) else None

    def _fixpoint(self):
        for member in self.members.values():                     # direct raisers
            for name, function in member.functions.items():
                names = parameters(function)
                for node in ast.walk(function):
                    if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
                            and isinstance(node.exc.func, ast.Name) and node.exc.func.id == 'ValueError'
                            and len(node.exc.args) == 1):
                        continue
                    argument = node.exc.args[0]
                    if isinstance(argument, ast.Name) and argument.id in names:
                        self.raisers[(member.name, name)] = (argument.id, '')
                    elif (isinstance(argument, ast.BinOp) and isinstance(argument.op, ast.Add)
                          and isinstance(argument.left, ast.Constant) and type(argument.left.value) is str
                          and isinstance(argument.right, ast.Name) and argument.right.id in names):
                        self.raisers[(member.name, name)] = (argument.right.id, argument.left.value)
        changed = True
        while changed:                                            # forwarders
            changed = False
            for member in self.members.values():
                for name, function in member.functions.items():
                    if (member.name, name) in self.raisers:
                        continue
                    names = parameters(function)
                    for node in ast.walk(function):
                        target = self.resolve(member, node.func) if isinstance(node, ast.Call) else None
                        if target is None or target not in self.raisers:
                            continue
                        parameter, prefix = self.raisers[target]
                        callee = self.members[target[0]].functions[target[1]]
                        argument = self.reason_argument(node, callee, parameter)
                        if isinstance(argument, ast.Name) and argument.id in names:
                            self.raisers[(member.name, name)] = (argument.id, prefix)
                            changed = True
                            break

    def forms(self):
        """`(exact, patterns, unresolved, excluded_count)` over every call site and direct raise."""
        exact, patterns, unresolved, excluded = set(), set(), [], 0

        def add(member, node, expression, prefix, enclosing):
            nonlocal excluded
            if (enclosing is not None and isinstance(expression, ast.Name)
                    and expression.id in parameters(enclosing)
                    and (member.name, enclosing.name) in self.raisers):
                return                                            # a forwarded parameter: its callers give forms
            found = pieces(expression)
            if found is None:
                unresolved.append({'member': member.path, 'line': node.lineno,
                                   'expression': ast.unparse(expression)[:160]})
                return
            for parts in found:
                parts = [('lit', prefix)] + parts if prefix else parts
                parts = merge(parts)
                if not parts or parts[0][0] != 'lit' or not parts[0][1].startswith(common.REFUSAL_CODE_HEADS):
                    excluded += 1
                    continue
                if all(kind == 'lit' for kind, _ in parts):
                    exact.add(parts[0][1])
                else:
                    patterns.add(''.join(re.escape(text) if kind == 'lit' else text for kind, text in parts))

        for member in self.members.values():
            enclosing_of = {}
            for function in [node for node in ast.walk(member.tree) if isinstance(node, ast.FunctionDef)]:
                for node in ast.walk(function):
                    enclosing_of.setdefault(id(node), function)
            for node in ast.walk(member.tree):
                enclosing = enclosing_of.get(id(node))
                if isinstance(node, ast.Call):
                    target = self.resolve(member, node.func)
                    if target is None or target not in self.raisers:
                        continue
                    parameter, prefix = self.raisers[target]
                    callee = self.members[target[0]].functions[target[1]]
                    argument = self.reason_argument(node, callee, parameter)
                    if argument is not None:
                        add(member, node, argument, prefix, enclosing)
                elif (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
                      and isinstance(node.exc.func, ast.Name) and node.exc.func.id == 'ValueError'
                      and len(node.exc.args) == 1):
                    raiser = self.raisers.get((member.name, enclosing.name)) if enclosing is not None else None
                    if raiser is not None and any(isinstance(item, ast.Name) and item.id == raiser[0]
                                                  for item in ast.walk(node.exc.args[0])):
                        continue                                  # the raiser's own raise: its callers give forms
                    add(member, node, node.exc.args[0], '', enclosing)
        return sorted(exact), sorted(patterns), sorted(unresolved, key=lambda row: (row['member'], row['line'])), \
            excluded


def merge(parts):
    out = []
    for kind, text in parts:
        if kind == 'lit' and out and out[-1][0] == 'lit':
            out[-1] = ('lit', out[-1][1] + text)
        elif kind == 'lit' and not text:
            continue
        else:
            out.append((kind, text))
    return out


def pieces(expression):
    """A list of alternatives, each a list of ('lit', text) / ('dyn', regex) pieces; None when not formable."""
    if isinstance(expression, ast.Constant) and type(expression.value) is str:
        return [[('lit', expression.value)]]
    if isinstance(expression, ast.IfExp):
        body, other = pieces(expression.body), pieces(expression.orelse)
        return None if body is None or other is None else body + other
    if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Add):
        left, right = pieces(expression.left), pieces(expression.right)
        left = left if left is not None else [[('dyn', common.REFUSAL_DETAIL)]]
        right = right if right is not None else [[('dyn', common.REFUSAL_DETAIL)]]
        return [a + b for a in left for b in right]
    if (isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Mod)
            and isinstance(expression.left, ast.Constant) and type(expression.left.value) is str):
        text, parts, position = expression.left.value, [], 0
        for match in FORMAT_SPEC.finditer(text):
            parts.append(('lit', text[position:match.start()]))
            kind = match.group(1)
            parts.append(('lit', '%') if kind == '%' else ('dyn', INTEGER if kind in 'diu' else common.REFUSAL_DETAIL))
            position = match.end()
        parts.append(('lit', text[position:]))
        return [parts]
    if isinstance(expression, ast.JoinedStr):
        parts = []
        for value in expression.values:
            if isinstance(value, ast.Constant) and type(value.value) is str:
                parts.append(('lit', value.value))
            else:
                parts.append(('dyn', common.REFUSAL_DETAIL))
        return [parts]
    return None


def build(raw=None):
    raw = archive_bytes() if raw is None else raw
    members = []
    with ZipFile(io.BytesIO(raw)) as bundle:
        names = sorted(name for name in bundle.namelist() if name.startswith(SCOPE) and name.endswith('.py'))
        stop_unless(names, 'NO_SCOPED_MEMBERS')
        scanned = []
        for name in names:
            data = bundle.read(name)
            scanned.append({'path': name, 'sha256': common.digest(data), 'bytes': len(data)})
            members.append(Member(name, data.decode('utf-8')))
    exact, patterns, unresolved, excluded = Analysis(members).forms()
    stop_unless(exact and patterns, 'EMPTY_ALLOWLIST')
    return {'schema': common.REFUSAL_ALLOWLIST_SCHEMA, 'label': common.LABEL,
            'rule': ('A panel record is a model REFUSAL only when the prediction raised an exception whose type is '
                     'exactly ValueError and whose COMPLETE message (never a truncated display) equals one `exact` '
                     'entry or fullmatches one `patterns` entry. Anything else is an infrastructure fault: the '
                     'evidence is invalid (ADMISSION_INVALID_STOP), never a valid mismatch.'),
            'detail_class': common.REFUSAL_DETAIL, 'integer_class': INTEGER,
            'source': {'package_commit': common.PACKAGE_COMMIT, 'archive_path': common.GIT_PREFIX + ARCHIVE_REL,
                       'archive_git_blob': common.PACKAGE_BLOBS['source.zip'],
                       'archive_sha256': common.ARCHIVE_SHA256, 'archive_bytes': common.ARCHIVE_BYTES,
                       'scope': SCOPE + '*.py', 'scanned_members': scanned},
            'exact': exact, 'patterns': patterns, 'unresolved': unresolved,
            'counts': {'exact': len(exact), 'patterns': len(patterns), 'unresolved': len(unresolved),
                       'excluded_not_code_shaped': excluded, 'scanned_members': len(scanned)}}


def encode(document):
    return (json.dumps(document, sort_keys=True, indent=1, ensure_ascii=True) + '\n').encode('ascii')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args(argv)
    raw = encode(build())
    if args.verify:
        stop_unless(OUTPUT.is_file() and OUTPUT.read_bytes() == raw, 'THE_FILE_IS_NOT_THE_REBUILD')
        print(json.dumps({'verified': str(OUTPUT), 'sha256': common.digest(raw)}))
        return 0
    stop_unless(not OUTPUT.exists(), 'OUTPUT_EXISTS_NO_OVERWRITE:' + str(OUTPUT))
    with OUTPUT.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'written': str(OUTPUT), 'sha256': common.digest(raw), 'bytes': len(raw)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
