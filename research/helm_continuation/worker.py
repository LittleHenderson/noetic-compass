"""Admitted AWS entry point for CONT19 proof or one continuation, never both.

No imports of torch or scientific code until the Linux venue and immutable
package have been verified. The original scorer and sealed-training path are
called unchanged; public receipts contain only hashes and aggregate scores.
"""
from dataclasses import asdict
from hashlib import sha256
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import time

from . import continuation as c

MANIFEST_SHA = 'f083fb087ce2eac2394b81856a2aea8f239e7b7d327d27a71160e4dcb6bc2b5d'


def write(path, value):
    with Path(path).open('x', encoding='utf8') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())


def environment(root):
    c.require(sys.platform == 'linux' and os.environ.get('HELM_CONT19_VENUE') == 'ADMITTED_AWS',
              'ADMITTED_AWS_REQUIRED')
    c.require(str(root.resolve()) == '/opt/cas-graph6curr/package', 'ORIGINAL_RESTORE_ROOT_REQUIRED')
    candidates = [p for p in root.glob('*manifest*.json')
                  if sha256(p.read_bytes()).hexdigest() == MANIFEST_SHA]
    c.require(len(candidates) == 1, 'PINNED_LEGACY_MANIFEST_REQUIRED')
    manifest = json.loads(candidates[0].read_bytes())
    c.require(manifest['source_sha'] == c.SOURCE, 'LEGACY_SOURCE_MISMATCH')
    sys.path[:0] = [str(root), str(root / 'research/CAS_META_2_COMPOSITION')]
    # The unchanged attestor checks imports and owned source bytes.
    import importlib.util
    p = root / 'cncm/typed_source_attestation.py'
    row, = [v for v in manifest['inputs'] if v['path'] == 'cncm/typed_source_attestation.py']
    c.require(sha256(p.read_bytes()).hexdigest() == row['sha256'], 'ATTESTOR_PIN')
    spec = importlib.util.spec_from_file_location('_continuation_verified_attestor', p)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    attestor = module.install(root, manifest['inputs'])
    os.environ['CAS_META2_RUN_TEACHING_CYCLE'] = '1'
    from cncm import typed_pointer_worker as w
    runtime = {}
    torch, device, loaded, packages = w._preflight(root, attestor, runtime)
    frozen, tokenizer, development = w.contract.load_material(root)
    return w, torch, device, frozen, tokenizer, development, attestor, runtime


def run(root, parent, plan, out, mode):
    began = time.monotonic()
    out.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'helm.cont19.worker/1', 'status': 'FAILED', 'mode': mode,
              'job_id': plan.job_id, 'plan': asdict(plan), 'started_utc': datetime.datetime.now(
                  datetime.timezone.utc).isoformat(), 'automatic_retry': False,
              'scores': {}, 'development_scores': [], 'checkpoints': {}, 'validation_work': []}
    def progress(phase, **values):
        row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'phase': phase, 'job_id': plan.job_id, **values}
        with (out / 'progress.jsonl').open('a', encoding='utf8') as f:
            f.write(json.dumps(row) + '\n'); f.flush(); os.fsync(f.fileno())
        print(json.dumps(row), flush=True)
    try:
        w, torch, device, frozen, tokenizer, development, attestor, runtime = environment(root)
        report['runtime'] = runtime
        legacy = w.pointer_module
        batches = c.extend_batch_stream(w.contract, frozen)
        packets = dict(w.contract.public_packets(frozen))
        held, trained, excluded = w.contract.split(frozen)
        sides = {'held_back': set(held), 'trained': set(trained), 'excluded': set(excluded)}
        dev = w.contract.development_packets(development)
        report['schedule'] = {'sha256': c.digest(batches), 'next_batch': batches[c.START],
                              'total_main_updates': len(batches), 'additional_main_updates': 2940}
        write(out / 'schedule.json', batches)
        def components():
            encoder = w.encoder_module.build_frozen_typed_encoder(torch, tokenizer,
                seed=w.contract.DESIGN['encoder_seed'], d_model=64, device=device)
            framework = w.matched._framework(torch, device, 20260919)
            return framework, encoder
        def start():
            framework, encoder = components()
            restored, metadata = c.restore_parent(legacy, torch, framework, encoder, parent, device)
            return c.adopt_new_lineage(legacy, restored, metadata, plan)
        def clone(pin):
            framework, encoder = components()
            return c.restore_child(legacy, torch, framework, encoder, parent_path=parent,
                path=pin['path'], expected_sha256=pin['sha256'], plan=plan, device=device)
        main = start()
        before = c.state_snapshot(main, legacy)
        initial = main.export_checkpoint(out / 'pass20.pt')
        write(out / 'pass20_checkpoint.json', initial)
        report['checkpoints']['2940'] = initial
        progress('parent_restored', main_updates=main.cursor, parent_sha256=c.PARENT_SHA,
                 optimizer_state_identity=before['optimizer'])
        staging = out / 'staging'; staging.mkdir()
        if mode == 'proof':
            # Same initial child, with vs without a real prediction-only validation.
            sample = dict(list(packets.items())[:8])
            c.isolated_validation(main, legacy, lambda: clone(initial),
                                  lambda model: [model.predict(p, 8) for p in sample.values()])
            c.require(c.state_snapshot(main, legacy) == before, 'PROOF_VALIDATION_STATE')
            _, update_a = w.practice_worker._stage_and_train(main, batches[c.START], packets,
                staging / 'next_a.json', started=began, deadline=lambda _: main._budget())
            after_a = c.state_snapshot(main, legacy)
            twin = clone(initial)
            _, update_b = w.practice_worker._stage_and_train(twin, batches[c.START], packets,
                staging / 'next_b.json', started=began, deadline=lambda _: twin._budget())
            after_b = c.state_snapshot(twin, legacy)
            c.require(after_a == after_b and main.cursor == c.START + 1,
                      'PROOF_NEXT_STEP_NOT_BITWISE_EQUAL')
            c.require(after_a['optimizer'] != before['optimizer'] and after_a['model'] != before['model'],
                      'PROOF_NEXT_STEP_DID_NOT_TRAIN')
            proof_pin = main.export_checkpoint(out / 'proof2941.pt')
            reload = clone(proof_pin)
            c.require(c.state_snapshot(reload, legacy) == after_a, 'PROOF_CHILD_RELOAD')
            post_update_rng = c.rng_snapshot(torch)
            # Refuse the next stage at the actual new ceiling before any forward.
            limit_clone = clone(initial)
            limit_clone.cursor = limit_clone.model_revision = c.FINAL
            limit_clone.counters['optimizer_updates'] = c.FINAL
            limit_before = c.state_snapshot(limit_clone, legacy)
            try:
                limit_clone.stage_batch([packets[k] for k in batches[c.START]['record_ids']],
                    batches[c.START]['depth'], cursor=c.FINAL,
                    occurrence_ids=batches[c.START]['occurrence_ids'])
            except ValueError as error:
                c.require('TYPED_LEARNER_BATCH_CURSOR_OR_BUDGET' in str(error), 'WRONG_LIMIT_REFUSAL')
            else:
                raise ValueError('CHILD_FINAL_LIMIT_DID_NOT_STOP')
            c.require(c.state_snapshot(limit_clone, legacy) == limit_before, 'LIMIT_REFUSAL_CHANGED_STATE')
            c.restore_rng(torch, post_update_rng)
            report['proof'] = {'parent_state': before, 'next_state': after_a,
                'bitwise_next_step_equal_with_and_without_validation': True,
                'child_reload_exact': True, 'next_batch_sha256': c.digest(batches[c.START]),
                'final_limit_refuses_before_forward': True,
                'next_update': 2941, 'main_parent_hash_unchanged': sha256(parent.read_bytes()).hexdigest() == c.PARENT_SHA,
                'preparation_updates': 2, 'training_job_updates': 0,
                'loss_a': update_a['raw_batch_loss'], 'loss_b': update_b['raw_batch_loss']}
            report['status'] = 'PASS_RESTORE_NEXT_STEP_ONLY'
        else:
            def evaluate(number, pin):
                def operation(model):
                    work = []
                    # Full public aggregate populations stay separate at each readout.
                    _, scored = w._evaluate(model, packets, 'course_p%02d' % number, out,
                        started=time.monotonic(), progress=progress, work=work)
                    score = {'correct': scored['correct'], 'total': scored['total'],
                             **w._split_score(scored, sides)}
                    _, d = w._evaluate(model, dev, 'development_p%02d' % number, out,
                        started=time.monotonic(), progress=progress, work=work)
                    return score, {'pass': number, 'cursor': main.cursor,
                                   'correct': d['correct'], 'total': d['total']}, work
                score, d, work = c.isolated_validation(main, legacy, lambda: clone(pin), operation)
                report['scores'][str(number)], report['validation_work'] = score, report['validation_work'] + work
                report['development_scores'].append(d)
                write(out / ('readout_%d.json' % number), {'score': score, 'development': d,
                    'main_state': c.state_snapshot(main, legacy), 'validation_work': work})
            evaluate(20, initial)
            for number in range(21, 41):
                logs = [staging / ('pass_%02d_%s.jsonl' % (number, label)) for label in ('batches', 'updates')]
                for path in logs: path.touch(exist_ok=False)
                losses = []
                for batch in (b for b in batches if b['pass'] == number):
                    c.require(main.cursor == batch['cursor'], 'NEXT_BATCH_POSITION')
                    _, update = w.practice_worker._train_logged(main, batch, packets, staging, *logs,
                        started=began, deadline=lambda _: main._budget())
                    losses.append(update['raw_batch_loss'])
                    if main.cursor % 10 == 0:
                        progress('training', main_updates=main.cursor, final_main_updates=c.FINAL, current_pass=number)
                for path in logs: path.rename(out / path.name)
                write(out / ('pass_%02d_summary.json' % number), {'pass': number, 'cursor': main.cursor,
                    'updates': len(losses), 'mean_raw_batch_loss': sum(losses)/len(losses),
                    'loss_definition': 'Unchanged c45 train_sealed_batch raw_batch_loss; arithmetic mean across this pass batches.'})
                if main.cursor in c.READOUTS:
                    pin = main.export_checkpoint(out / ('pass%d.pt' % number))
                    write(out / ('pass%d_checkpoint.json' % number), pin)
                    report['checkpoints'][str(main.cursor)] = pin
                    evaluate(number, pin)
            c.require(main.cursor == c.FINAL and main.counters['optimizer_updates']
                      - main.parent_counters['optimizer_updates'] == 2940, 'CHILD_INCOMPLETE')
            report['final_state'] = c.state_snapshot(main, legacy)
            report['status'] = 'COMPLETED_CONTINUATION_MEASURED_NOT_CERTIFIED'
        report['loaded_sources'] = attestor.snapshot()
        c.require(sha256(parent.read_bytes()).hexdigest() == c.PARENT_SHA, 'PARENT_CHANGED')
    except BaseException as error:
        report['error_type'], report['error'] = type(error).__name__, str(error)
        progress('failed', error_type=type(error).__name__, error=str(error))
    finally:
        report['elapsed_seconds'] = time.monotonic() - began
        write(out / 'public_result.json', report)
        files = [{'path': p.relative_to(out).as_posix(), 'sha256': sha256(p.read_bytes()).hexdigest(),
                  'bytes': p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file()]
        write(out / 'receiver_inventory.json', {'schema': 'helm.cont19.inventory/1', 'files': files,
            'required_readouts': list(c.READOUTS), 'terminal_status': report['status']})
    return 1 if report['status'] == 'FAILED' else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('proof', 'train'), required=True)
    args = parser.parse_args()
    value = json.loads(args.plan.read_bytes()); value['readouts'] = tuple(value['readouts'])
    raise SystemExit(run(args.root, args.parent, c.ChildPlan(**value).validate(), args.out, args.mode))
