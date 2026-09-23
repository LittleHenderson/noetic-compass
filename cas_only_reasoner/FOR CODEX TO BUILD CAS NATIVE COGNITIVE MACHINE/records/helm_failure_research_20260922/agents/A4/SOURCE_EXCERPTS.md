# A4 original source excerpts

Read from manifest-bound source.zip members; exact member line numbers. All 24 selected member checks equal the saved loaded_sources.json after entries. Source comments may contain historical interpretation; these comments are not accepted as causal evidence.

## Helm 1.0 cncm/typed_pointer_worker.py

SHA256: 0d801b675d837ebda8b4a64914a8de6494caceb446b2a7e62c1844ae17e24bd1
```text
857:     PointerCourseLearner, role_tagger = pointer_module.PointerCourseLearner, pointer_module.role_tagger
858:     encoder = build_frozen_typed_encoder(torch, ctx["tokenizer"], seed=design["encoder_seed"], d_model=64,
859:                                          device=device)
860:     limits = {"max_updates": ctx["stats"]["main_updates"]
861:               + (contract.INTERFERENCE_UPDATES if ctx["plan"]["interference"] else 0),
862:               "max_core_calls": contract.MAX_CORE_CALLS,
863:               "max_wall_seconds": contract.WORKER_DEADLINE_SECONDS}
864:     run_context = {"run_id": ctx["config"]["job"],
865:                    "course_sha256": contract.MATERIAL[ctx["course_path"]]["sha256"],
866:                    "condition": design["condition"], "source_seed": design["source_seed"]}
867:     tagger = role_tagger(str(root))
868:
869:     def build(model_seed):
870:         return PointerCourseLearner(torch, matched._framework(torch, device, model_seed), encoder,
871:                                     optimizer_config=design["optimizer_config"], run_context=run_context,
872:                                     limits=limits, device=device, tagger=tagger, python_seed=model_seed,
873:                                     root=str(root))
874:
875:     # R1-2. THE ORDERING IS MEASURED HERE, at the instant before the container is built, from two runtime
876:     # facts and nothing else: whether any pointer model was already attached to this run, and the run's own
877:     # monotonic reading of when phase A returned (`run()` records it). Nothing about this pair is written as
878:     # a literal, because a literal cannot vary and therefore is not evidence.
879:     model_seeded_at = time.monotonic()
880:     model_already_present = ctx.get("main") is not None
881:     main = build(seed)
882:     # (b) a SECOND, independent build of the WHOLE model: the container identity must be equal.
883:     second = build(seed)
884:     whole_first = _container_identity(torch, main.module)
885:     whole_second = _container_identity(torch, second.module)
886:     del second
887:     require(whole_first == whole_second, "POINTER_DOUBLE_BUILD_MISMATCH")
888:     core_identity = _core_identity(torch, main.module)
889:     # (c) the three seeds' `^6` starts must be pairwise different.
890:     seed_identities = {}
891:     for model_seed in contract.MODEL_SEEDS:
892:         probe = build(model_seed)
893:         seed_identities[str(model_seed)] = _core_identity(torch, probe.module)
894:         del probe
895:     require(len(set(seed_identities.values())) == len(seed_identities), "POINTER_SEED_IDENTITIES_NOT_DISTINCT")
896:     require(seed_identities[str(seed)] == core_identity, "POINTER_SEED_IDENTITY_STABLE")
897:     # (a) the three `^6` tensors must match THIS seed's recorded practice start. The practice value was
898:     # recorded by the practice study's own process, which ran no pointer checkpoint check and had a wholly
899:     # different RNG history, and `_framework` re-seeds all three streams, so the build is a pure function of
900:     # the seed -- which is exactly the "identical start with and without the checkpoint check" comparison
901:     # (M3 / DG4d). The model that trains is THIS one, built after phase A RETURNED. `run()` only calls this
902:     # function after `_checkpoint_check_phase_a` has returned, and the artifact MEASURES that ordering rather
903:     # than asserting it (R1-2); when phase A returned with anything other than `COMPLETE`, the reference
904:     # identity below comes from the practice sidecar directly and the ordering claim is recorded as false.
```
```text
1004:         _move_in(staging / (name + ".pt"), artifacts / (name + ".pt"))
1005:         ctx["checkpoint_pins"][name] = {**pin, "path": str(artifacts / (name + ".pt"))}
1006:         _publish(artifacts / (name + "_checkpoint.json"), ctx["checkpoint_pins"][name])
1007:
1008:     def evaluate_at(number):
1009:         if number in FULL:
1010:             name = "course_p%02d" % number
1011:             ctx["predictions"][name], scored = _evaluate(main, packets, name, artifacts, started=ctx["started"],
1012:                                                          progress=phase, work=work)
1013:             report["scores"][name] = {"correct": scored["correct"], "total": scored["total"],
1014:                                       **_split_score(scored, ctx["sides"])}
1015:         else:
1016:             name = "heldback_p%02d" % number
1017:             _, scored = _evaluate(main, ctx["held_packets"], name, artifacts, started=ctx["started"],
1018:                                   progress=phase, work=work)
1019:             report["scores"][name] = {"correct": scored["correct"], "total": scored["total"],
1020:                                       "held_back": {"correct": scored["correct"], "total": scored["total"]}}
1021:         name = "development_p%02d" % number
1022:         _, scored = _evaluate(main, ctx["development_packets"], name, artifacts, started=ctx["started"],
1023:                               progress=phase, work=work)
1024:         report["development_scores"].append({"pass": number, "cursor": main.cursor,
1025:                                              "correct": scored["correct"], "total": scored["total"]})
1026:
1027:     phase = ctx["phase"]
1028:     checkpoint("initial")
1029:     ctx["main_deltas"] = []
1030:     if 0 in plan["evaluations"]:
1031:         evaluate_at(0)
1032:     last_seal, pass_summaries, training_seconds, update_count = None, [], 0.0, 0
1033:     for number in range(1, plan["passes"] + 1):
1034:         _deadline(ctx["started"])
1035:         names = ("pass_%02d_batches.jsonl" % number, "pass_%02d_updates.jsonl" % number)
1036:         batches_log, updates_log = staging / names[0], staging / names[1]
1037:         batches_log.touch(exist_ok=False)
1038:         updates_log.touch(exist_ok=False)
1039:         losses, gradients = [], []
1040:         began = time.monotonic()
1041:         for batch in (item for item in ctx["batches"] if item["pass"] == number):
1042:             if batch["cursor"] == stats["main_updates"] - 1:
1043:                 checkpoint("prelast")
1044:             before = deepcopy(main.counters)
1045:             last_seal, update = _train_logged(main, batch, packets, staging, batches_log, updates_log,
1046:                                               started=ctx["started"])
1047:             ctx["main_deltas"].append(_counter_delta(main.counters, before))
1048:             losses.append(update["raw_batch_loss"])
1049:             gradients.append(update["gradient_squared_norm"])
1050:             update_count += 1
1051:             report["completed_main_updates"] = main.cursor
1052:             if main.cursor % 10 == 0:
1053:                 phase("main_training", completed_main_updates=main.cursor,
1054:                       total_main_updates=stats["main_updates"], current_pass=number)
1055:         training_seconds += time.monotonic() - began
1056:         _move_in(batches_log, artifacts / names[0])
1057:         _move_in(updates_log, artifacts / names[1])
1058:         require(bool(losses), "POINTER_EMPTY_PASS")
1059:         pass_summaries.append({"pass": number, "updates": len(losses), "cursor_end": main.cursor,
1060:                                "mean_raw_batch_loss": sum(losses) / len(losses),
1061:                                "first_raw_batch_loss": losses[0], "last_raw_batch_loss": losses[-1],
1062:                                "mean_gradient_squared_norm": sum(gradients) / len(gradients),
1063:                                "seconds": time.monotonic() - began})
1064:         if number < plan["passes"]:
1065:             _partial_checkpoint(main, ctx["results"], main.cursor)
1066:         if number == 1:
1067:             checkpoint("pass_01")
1068:         if number == plan["passes"]:
1069:             checkpoint("final")
1070:         if number in plan["evaluations"]:
1071:             evaluate_at(number)
1072:     require(main.cursor == stats["main_updates"] and not any(staging.iterdir()), "POINTER_MAIN_INCOMPLETE")
1073:     require(update_count == stats["main_updates"], "POINTER_INCOMPLETE_UPDATES")
1074:     report["pass_summaries"] = pass_summaries
1075:     report["training_seconds"] = training_seconds
1076:     report["main_training_delta"] = matched._sum_deltas(ctx["main_deltas"])
1077:     require(canonical(report["main_training_delta"]) == canonical(contract.expected_main_delta(stats)),
1078:             "MAIN_TRAINING_COUNTERS")
1079:     work.append({"phase": "main_training", "delta": report["main_training_delta"],
1080:                  "elapsed_seconds": training_seconds})
1081:     require(ctx["checkpoint_pins"]["initial"]["metadata"]["model_state_identity"]
1082:             != ctx["checkpoint_pins"]["final"]["metadata"]["model_state_identity"], "TRAINABLE_CORE_UNCHANGED")
1083:     ctx["last_seal"] = last_seal
1084:
1085:
1086: # ======================================================================================================
1087: # 8. PHASE: retention / interference.
1088: # ======================================================================================================
1089: def _retention_and_interference(ctx):
```
```text
1097:         _, before_score = _evaluate(main, ctx["retention_packets"], "retention_before", artifacts,
1098:                                     started=ctx["started"], progress=ctx["phase"], work=work)
1099:     else:
1100:         before_score = None
1101:     deltas = []
1102:     if plan["interference"]:
1103:         names = ("interference_batches.jsonl", "interference_updates.jsonl")
1104:         batches_log, updates_log = staging / names[0], staging / names[1]
1105:         batches_log.touch(exist_ok=False)
1106:         updates_log.touch(exist_ok=False)
1107:         for batch in ctx["interference"]:
1108:             before = deepcopy(main.counters)
1109:             _train_logged(main, batch, packets, staging, batches_log, updates_log, started=ctx["started"])
1110:             deltas.append(_counter_delta(main.counters, before))
1111:             ctx["phase"]("interference_training", completed_updates=main.cursor,
1112:                          total_updates=stats["main_updates"] + contract.INTERFERENCE_UPDATES)
1113:         _move_in(batches_log, artifacts / names[0])
1114:         _move_in(updates_log, artifacts / names[1])
1115:     report["interference_delta"] = matched._sum_deltas(deltas) if deltas else None
1116:     if plan["interference"]:
1117:         require(report["interference_delta"]["optimizer_updates"] == contract.INTERFERENCE_UPDATES
1118:                 and report["interference_delta"]["prediction_calls"]
1119:                 == contract.INTERFERENCE_UPDATES * contract.INTERFERENCE_BATCH, "INTERFERENCE_COUNTS")
1120:         work.append({"phase": "interference_training", "delta": report["interference_delta"]})
1121:     if plan["retention"]:
1122:         ctx["phase"]("retained_checkpoint", completed_updates=main.cursor)
1123:         pin = main.export_checkpoint(staging / "retained.pt")
1124:         _move_in(staging / "retained.pt", artifacts / "retained.pt")
1125:         ctx["checkpoint_pins"]["retained"] = {**pin, "path": str(artifacts / "retained.pt")}
1126:         _publish(artifacts / "retained_checkpoint.json", ctx["checkpoint_pins"]["retained"])
1127:         ctx["retained_predictions"], after_score = _evaluate(main, ctx["retention_packets"], "retention_after",
1128:                                                             artifacts, started=ctx["started"],
1129:                                                             progress=ctx["phase"], work=work)
1130:         report["retention_scores"] = {"before": {key: before_score[key] for key in ("correct", "total")},
1131:                                       "after": {key: after_score[key] for key in ("correct", "total")},
1132:                                       "before_by_side": _split_score(before_score, ctx["retention_sides"]),
1133:                                       "after_by_side": _split_score(after_score, ctx["retention_sides"]),
1134:                                       "starting_competence_met":
1135:                                           2 * before_score["correct"] >= before_score["total"],
1136:                                       "interference_updates": contract.INTERFERENCE_UPDATES
1137:                                       if plan["interference"] else 0}
1138:     ctx["encoding"]["final"] = _input_checks(ctx["root"], ctx["tokenizer"], ctx["packets"],
1139:                                              ctx["representatives"], artifacts, started=ctx["started"],
1140:                                              all_packets=False, progress=ctx["phase"],
1141:                                              phase="final_input_checks")
1142:     _deadline(ctx["started"])
1143:     _publish(artifacts / "encoding_checks.json", ctx["encoding"])
1144:
1145:
```
```text
1157:
1158:
1159: def _reloads_and_replays(ctx):
1160:     """Same-process reconstruction: the plan's reloads and the two prelast replays."""
1161:     artifacts, plan = ctx["artifacts"], ctx["plan"]
1162:     staging, stats, packets = ctx["staging"], ctx["stats"], ctx["packets"]
1163:     work = ctx["work"]
1164:     reloads, replays = [], []
1165:     for name in plan["reloads"]:
1166:         _deadline(ctx["started"])
1167:         ctx["phase"](name + "_reconstruction")
1168:         pin = ctx["checkpoint_pins"][name]
1169:         restored = _restore_pointer(ctx, path=artifacts / (name + ".pt"), pin=pin, encoder=ctx["encoder"])
1170:         before = deepcopy(restored.counters)
1171:         if name == "retained":
1172:             selected = list(ctx["retention_packets"])[:8]
1173:             source_packets = ctx["retention_packets"]
1174:             expected = ctx["retained_predictions"]
1175:         else:
1176:             selected = list(ctx["representatives"].values())
1177:             source_packets = packets
1178:             expected = ctx["predictions"]["course_p%02d" % (0 if name == "initial" else plan["passes"])]
1179:         rows = [restored.predict(source_packets[key], EVALUATION_DEPTH) for key in selected]
1180:         require(all(canonical(row) == canonical(expected[row["record_id"]]) for row in rows),
1181:                 "RELOAD_PREDICTION_MISMATCH")
1182:         _seal_predictions(artifacts / (name + "_reload_predictions.json"), rows, phase=name + "_reload",
1183:                           expected_ids=selected)
1184:         delta = _counter_delta(restored.counters, before)
1185:         require(delta["optimizer_updates"] == delta["backward_calls"] == 0, "RELOAD_UPDATED_MODEL")
1186:         work.append({"phase": name + "_reload", "delta": delta})
1187:         reloads.append({"phase": name, "checkpoint_sha256": pin["sha256"], "prediction_ids": selected,
1188:                         "delta": delta})
1189:         del restored
1190:     if plan["replays"]:
1191:         for branch in (1, 2):
1192:             _deadline(ctx["started"])
1193:             ctx["phase"]("replay_%d" % branch)
1194:             pin = ctx["checkpoint_pins"]["prelast"]
1195:             restored = _restore_pointer(ctx, path=artifacts / "prelast.pt", pin=pin, encoder=ctx["encoder"])
1196:             before = deepcopy(restored.counters)
1197:             staged_seal = staging / ("replay_%d_batch.json" % branch)
1198:             raw, update = _stage_and_train(restored, ctx["batches"][-1], packets, staged_seal,
1199:                                            started=ctx["started"])
1200:             require(raw == ctx["last_seal"], "REPLAY_PREUPDATE_MISMATCH")
1201:             _move_in(staged_seal, artifacts / ("replay_%d_batch.json" % branch))
1202:             _publish(artifacts / ("replay_%d_update.json" % branch), update)
1203:             base._check_state(ctx["torch"], restored, ctx["checkpoint_pins"]["final"])
1204:             expected = ctx["predictions"]["course_p%02d" % plan["passes"]]
1205:             rows = [restored.predict(packets[key], EVALUATION_DEPTH)
1206:                     for key in ctx["representatives"].values()]
1207:             require(all(canonical(row) == canonical(expected[row["record_id"]]) for row in rows),
1208:                     "REPLAY_FINAL_MISMATCH")
1209:             _seal_predictions(artifacts / ("replay_%d_predictions.json" % branch), rows,
1210:                               phase="replay_%d" % branch, expected_ids=list(ctx["representatives"].values()))
1211:             delta = _counter_delta(restored.counters, before)
1212:             require(delta["optimizer_updates"] == delta["backward_calls"] == 1, "REPLAY_COUNTS")
1213:             work.append({"phase": "replay_%d" % branch, "delta": delta})
1214:             replays.append({"branch": branch, "restored_cursor": stats["main_updates"] - 1,
1215:                             "committed_cursor": restored.cursor, "delta": delta})
1216:             del restored
1217:     _publish(artifacts / "replay_report.json",
1218:              {"schema": "cncm.typed-pointer-reload/0.1", "reloads": reloads, "replays": replays,
1219:               "passes": plan["passes"], "reload_selected": plan["reload"], "replays_selected": plan["replays"],
1220:               "boundary": "Same-process same-worker reconstruction only."})
1221:
1222:
1223: # ======================================================================================================
1224: # 10. PHASE: checkpoint check PHASE B -- last. Answers derived here and nowhere earlier.
1225: # ======================================================================================================
1226: def _ridge_probe(torch, features, targets, train_keys, test_keys, *, penalty=1.0):
1227:     """One closed-form ridge probe: fit on the trained keys, score the held keys. Never a gradient step."""
```

## Helm 1.0 research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py

SHA256: e0fe6dc8b523bc65eaaf0c7b287ee1d931db591180e2c19eaa3f8fdce687c6c2
```text
1524:         self.python_seed = python_seed
1525:         self.tagger = tagger
1526:         # ONE container. `scope_parameters` is never called on it (review RK2).
1527:         self.module = _build_container(torch, framework, self.device)
1528:         # The scope record is the container's own parameter list under the REGISTERED names, and it records
1529:         # that the shared freeze was deliberately not applied.
1530:         registered = _registered_names(self.module)
1531:         parameters = dict(self.module.named_parameters())
1532:         self.scope = {
1533:             "allowed": sorted(registered[name] for name, parameter in parameters.items()
1534:                               if parameter.requires_grad),
1535:             "frozen": sorted(registered[name] for name, parameter in parameters.items()
1536:                              if not parameter.requires_grad),
1537:             "contract_id": "cas.cjt.operation.^6.decompose/0.2", "role": "operation:^6",
1538:             "call": "NOT_CALLED_ON_THE_POINTER_CONTAINER",
1539:         }
1540:         require(set(self.scope["allowed"]) == set(self.module.state_dict())
1541:                 and not self.scope["frozen"], "POINTER_CONTAINER_SCOPE")
1542:         require(set(PARAMETERS) <= set(self.scope["allowed"]), "POINTER_CONTAINER_BLOCK_SCOPE")
1543:         self.encoder = encoder
1544:         encoder.verify_frozen()
```
```text
1529:         # that the shared freeze was deliberately not applied.
1530:         registered = _registered_names(self.module)
1531:         parameters = dict(self.module.named_parameters())
1532:         self.scope = {
1533:             "allowed": sorted(registered[name] for name, parameter in parameters.items()
1534:                               if parameter.requires_grad),
1535:             "frozen": sorted(registered[name] for name, parameter in parameters.items()
1536:                              if not parameter.requires_grad),
1537:             "contract_id": "cas.cjt.operation.^6.decompose/0.2", "role": "operation:^6",
1538:             "call": "NOT_CALLED_ON_THE_POINTER_CONTAINER",
1539:         }
1540:         require(set(self.scope["allowed"]) == set(self.module.state_dict())
1541:                 and not self.scope["frozen"], "POINTER_CONTAINER_SCOPE")
1542:         require(set(PARAMETERS) <= set(self.scope["allowed"]), "POINTER_CONTAINER_BLOCK_SCOPE")
1543:         self.encoder = encoder
1544:         encoder.verify_frozen()
1545:         parameters = dict(self.module.named_parameters())
1546:         require(all(parameter.device == self.device and parameter.dtype == torch.float32
1547:                     and parameter.requires_grad for parameter in parameters.values()),
1548:                 "POINTER_PARAMETER_DEVICE")
1549:         require(all(tuple(parameters[BLOCK_NAMES[name]].shape) == PARAMETER_SHAPES[name]
```
```text
1575:                 and type(run_context["source_seed"]) is int
1576:                 and run_context["source_seed"] in SOURCE_SEEDS, "TYPED_LEARNER_RUN_CONTEXT")
1577:         self.optimizer_config, self.limits = deepcopy(optimizer_config), deepcopy(limits)
1578:         self.optimizer = torch.optim.AdamW(list(self.module.parameters()),
1579:                                            lr=optimizer_config["learning_rate"],
1580:                                            weight_decay=optimizer_config["weight_decay"],
1581:                                            betas=tuple(optimizer_config["betas"]),
1582:                                            eps=optimizer_config["eps"], foreach=False, fused=False,
1583:                                            capturable=False)
1584:         self.run_identity = {
1585:             "context": deepcopy(run_context), "learner_profile": profile(),
1586:             "encoder_identity": deepcopy(encoder.identity),
1587:             "initial_model_identity": state_identity(torch, dict(self.module.state_dict())),
1588:             "scope": deepcopy(self.scope), "optimizer_config": deepcopy(optimizer_config),
1589:             "limits": deepcopy(limits),
1590:             "initialization": "BUILT_BY_cncm.typed_matched_worker._framework_TORCH_DEFAULT_SCHEME",
1591:             "core_rounds": CORE_ROUNDS, "readout": profile()["readout"],
1592:             "head_set": sorted(SCORED_FIELDS), "counters": list(COUNTER_KEYS),
1593:             "counter_units": dict(COUNTER_UNITS), "depth_is_not_an_input": True,
1594:             "prediction_depth": PREDICTION_DEPTH,
1595:             "normalisation_placement": profile()["normalisation_placement"],
```
```text
1762:             require(trained, "POINTER_GRADIENTS_ABSENT")
1763:             require(all(bool(self.torch.isfinite(parameters[name].grad).all().item())
1764:                         for name in trained), "TYPED_LEARNER_GRADIENTS")
1765:             gradient_squared = sum(float((parameters[name].grad.detach()
1766:                                          * parameters[name].grad.detach()).sum().cpu().item())
1767:                                    for name in trained)
1768:             require(math.isfinite(gradient_squared), "TYPED_LEARNER_GRADIENT_NORM_NONFINITE")
1769:             self._budget()
1770:             self.counters["optimizer_step_attempts"] += 1
1771:             self.optimizer.step()
1772:             self.counters["optimizer_updates"] += 1
1773:             require(all(bool(self.torch.isfinite(parameter).all().item())
1774:                         for parameter in parameters.values()), "TYPED_LEARNER_PARAMETERS_NONFINITE")
1775:             self.encoder.verify_frozen()
1776:             self.cursor += 1
1777:             self.model_revision += 1
1778:             result = {"schema": UPDATE_SCHEMA,
1779:                       "batch_id": self._pending["public"]["batch_id"],
1780:                       "public_seal_sha256": expected_sha256, "cursor_committed": self.cursor,
1781:                       "model_revision": self.model_revision, "tasks": reports,
1782:                       "raw_batch_loss": sum(row["raw_task_loss"] for row in reports) / len(reports),
```
```text
1768:             require(math.isfinite(gradient_squared), "TYPED_LEARNER_GRADIENT_NORM_NONFINITE")
1769:             self._budget()
1770:             self.counters["optimizer_step_attempts"] += 1
1771:             self.optimizer.step()
1772:             self.counters["optimizer_updates"] += 1
1773:             require(all(bool(self.torch.isfinite(parameter).all().item())
1774:                         for parameter in parameters.values()), "TYPED_LEARNER_PARAMETERS_NONFINITE")
1775:             self.encoder.verify_frozen()
1776:             self.cursor += 1
1777:             self.model_revision += 1
1778:             result = {"schema": UPDATE_SCHEMA,
1779:                       "batch_id": self._pending["public"]["batch_id"],
1780:                       "public_seal_sha256": expected_sha256, "cursor_committed": self.cursor,
1781:                       "model_revision": self.model_revision, "tasks": reports,
1782:                       "raw_batch_loss": sum(row["raw_task_loss"] for row in reports) / len(reports),
1783:                       "normalized_batch_loss": sum(row["normalized_task_loss"] for row in reports)
1784:                       / len(reports),
1785:                       "training_uses": "raw_batch_loss", "gradient_squared_norm": gradient_squared,
1786:                       "loss_plan_digests": loss_ids, "counters": deepcopy(self.counters),
1787:                       "gradient_parameter_names": trained,
1788:                       "gradient_parameter_count": len(trained),
```

## Helm 1.0 research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_contract.py

SHA256: 70be7ae7b7b3dbefd6a5d168b04ab7394718d7456a264614236d31b0c9c09b3d
```text
210: def _stratified_pass(frozen, base, keep_set):
211:     """One pass in which every batch carries ALL EIGHT KINDS: eight records, one per kind.
212:
213:     Owner decision 2026-09-19. Built from the SAME MIXED base batch slots the practice study uses, so the depth
214:     distribution, the phase structure and the round numbering are the base's and unchanged; only the membership
215:     and the ids are this study's.
216:
217:       * slot selection is the same rule as the practice pass -- every base slot holding at least one TRAINED
218:         record -- so the update count stays 147 per pass;
219:       * inside a slot, exactly one record per kind is taken from that kind's TRAINED pool (sorted), chosen by a
220:         deterministic round-robin cursor over that pool that persists across slots within the pass, which is
221:         `lb11_economics.py`'s branch B and the measurement REVIEW_SYNTHESIS section 4.7 reports as
222:         presentations_per_pass 1176;
223:       * `round`, `phase`, `depth` and `source_cursor` come from the base batch (the requirement is explicit);
224:       * `occurrence_ids` and `presentation_ids` are generated from (slot index, kind index) alone, so they are
225:         reproducible without the base ids and are UNIQUE INSIDE A BATCH -- which is what this contract's own
226:         `OCCURRENCE_UNIQUE` check requires, and is all the pass loop's re-digest needs. They are formed in the
227:         practice schedule's own style: an occurrence id is the `typed-occurrence-` prefix and a 64-hex digest, and a
228:         presentation id is the pass prefix, an 8-hex slot token and the ordinal of the kind inside the batch. The
229:         pass loop below still re-digests every occurrence id per pass, so the per-pass mechanism is untouched.
230:     """
231:     slots = [batch for batch in base if any(key in keep_set for key in batch["record_ids"])]
232:     pools = _kind_pools(frozen)
233:     cursor = {kind: 0 for kind in KINDS}
234:     one_pass = []
235:     for index, batch in enumerate(slots):
236:         token = source.digest({"domain": "typed-pointer-stratified-v1", "slot": index})[:8]
237:         records, occurrences, presentations = [], [], []
238:         for at, kind in enumerate(KINDS):
239:             pool = pools[kind]
240:             records.append(pool[cursor[kind] % len(pool)])
241:             cursor[kind] += 1
242:             occurrences.append("typed-occurrence-" + source.digest({"domain": "typed-pointer-stratified-v1",
243:                                                                     "slot": index, "kind": kind}))
244:             presentations.append("pointer-stratified-%s-%02d" % (token, at))
245:         one_pass.append({"round": batch["round"], "phase": batch["phase"], "depth": batch["depth"],
246:                          "source_cursor": batch["cursor"], "record_ids": records,
247:                          "occurrence_ids": occurrences, "presentation_ids": presentations})
248:     require(len(one_pass) == len(slots), "POINTER_STRATIFY_SLOTS")
```
```text
285:     require(type(count) is int and 1 <= count <= MAX_PASSES_PERMITTED,
286:             "POINTER_PASSES_BOUND:" + str(count))
287:     base, base_stats = matched.schedule(frozen, CONDITION)
288:     held, trained, excluded = split(frozen)
289:     keep_set = set(trained)
290:     one_pass = (_stratified_pass(frozen, base, keep_set) if layered
291:                 else _non_stratified_pass(frozen, base, keep_set))
292:     if layered:
293:         # Fail closed on composition drift: the stratified pass is a frozen artifact, so it may not silently
294:         # change under a re-derivation. This is pass-count independent, so it costs one digest per call.
295:         require(source.digest(one_pass) == STRATIFIED_PASS_DIGEST, "POINTER_STRATIFY_DIGEST")
296:         kinds_of = {row["record_id"]: row["query"]["kind"] for row in frozen["registry"]}
297:         require(all(len(b["record_ids"]) == len(KINDS)
298:                     and {kinds_of[key] for key in b["record_ids"]} == set(KINDS) for b in one_pass),
299:                 "POINTER_STRATIFY_COVERAGE")
300:     batches = []
301:     for number in range(1, count + 1):
302:         for batch in one_pass:
303:             occurrences = ["typed-occurrence-" + source.digest({"domain": "typed-practice-v1", "pass": number,
304:                                                                "occurrence": occurrence})
305:                            for occurrence in batch["occurrence_ids"]]
306:             batches.append({**deepcopy(batch), "cursor": len(batches), "pass": number,
307:                             "occurrence_ids": occurrences,
308:                             "presentation_ids": ["practice-p%02d-%s" % (number, p)
309:                                                  for p in batch["presentation_ids"]]})
310:     require(all(key in keep_set for b in batches for key in b["record_ids"]), "HOLDOUT_TRAINED")
311:     require(all(len(b["occurrence_ids"]) == len(set(b["occurrence_ids"])) for b in batches), "OCCURRENCE_UNIQUE")
```

## Helm 1.0 research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/learner.py

SHA256: d87b49caed6d59e1d9715066ef030f55e09228a474c3a67e2535a3c54b3619ca
```text
197:     def _tensor_loss(self, plan, loss, tensors):
198:         torch = self.torch
199:         by_id = {s["slot_id"]: s for s in plan["slots"]}
200:         fields, reports = [], []
201:         for field in loss["fields"]:
202:             if field["kind"] == "joint_correspondence":
203:                 mode = torch.log_softmax(tensors[plan["slots"][0]["slot_id"]], dim=0)
204:                 candidates = plan["correspondence_candidates"]
205:                 if len(candidates) == 1:
206:                     term = mode.sum() * 0
207:                 else:
208:                     node_alias = {n["ref"]: n["alias"] for w in plan["aliases"]["worlds"] for n in w["nodes"]}
209:                     row_by_source = {s["coordinates"][0]: s for s in plan["slots"][1:]}
210:                     sums = []
211:                     for candidate in candidates[1:]:
212:                         selected = []
213:                         for pair in candidate["value"]["pairs"]:
214:                             row = row_by_source[pair["source"]]
215:                             selected.append(tensors[row["slot_id"]][row["symbols"].index(node_alias[pair["target"]])])
216:                         sums.append(torch.stack(selected).sum())
217:                     mapping = torch.stack(sums)
218:                     joint = torch.cat((mode[0].reshape(1), mode[1] + mapping - torch.logsumexp(mapping, dim=0)))
219:                     indices = [i for i, c in enumerate(candidates) if c["candidate_id"] in field["valid_candidate_ids"]]
220:                     term = -torch.logsumexp(joint[indices], dim=0)
221:             else:
222:                 terms = []
223:                 for key in field["slot_ids"]:
224:                     logits, row = tensors[key], by_id[key]
225:                     indices = [row["symbols"].index(symbol) for symbol in field["targets"][key]]
226:                     terms.append(torch.logsumexp(logits, dim=0) - torch.logsumexp(logits[indices], dim=0))
227:                 term = torch.stack(terms).mean()
228:             require(term.requires_grad and bool(torch.isfinite(term).item()), "TYPED_LEARNER_LOSS_DETACHED_OR_NONFINITE")
229:             fields.append(term)
230:             raw, size = float(term.detach().cpu().item()), field["public_alphabet_size"]
231:             reports.append({"field": field["field"], "raw_loss": raw, "normalized_loss": raw / math.log(size) if size > 1 else 0.0,
232:                             "public_alphabet_size": size, "slot_count": len(field["slot_ids"]), "forced": size == 1})
233:         return torch.stack(fields).mean(), {"fields": reports,
234:             "raw_task_loss": sum(r["raw_loss"] for r in reports) / len(reports),
235:             "normalized_task_loss": sum(r["normalized_loss"] for r in reports) / len(reports)}
```

## Helm 2.0-experimental cncm/typed_pointer_worker.py

SHA256: 6d859630ef45bcc4ef969f1d7232e3e68270cc208da431dd25cddfbfadda34e2
```text
857: # 6. PHASE: seed + double build (the DG4 in-job checks).
858: # ======================================================================================================
859: def _seed_and_double_build(ctx):
860:     """Build the pointer model AFTER phase A, twice and independently, and record every DG4 identity."""
861:     torch, device, root = ctx["torch"], ctx["device"], ctx["root"]
862:     design, artifacts = ctx["design"], ctx["artifacts"]
863:     seed = design["model_seed"]
864:     build_frozen_typed_encoder = encoder_module.build_frozen_typed_encoder
865:     PointerCourseLearner, role_tagger = pointer_module.PointerCourseLearner, pointer_module.role_tagger
866:     encoder = build_frozen_typed_encoder(torch, ctx["tokenizer"], seed=design["encoder_seed"], d_model=64,
867:                                          device=device)
868:     limits = {"max_updates": ctx["stats"]["main_updates"]
869:               + (contract.INTERFERENCE_UPDATES if ctx["plan"]["interference"] else 0),
870:               "max_core_calls": contract.MAX_CORE_CALLS,
871:               "max_wall_seconds": contract.WORKER_DEADLINE_SECONDS}
872:     run_context = {"run_id": ctx["config"]["job"],
873:                    "course_sha256": contract.MATERIAL[ctx["course_path"]]["sha256"],
874:                    "condition": design["condition"], "source_seed": design["source_seed"]}
875:     tagger = role_tagger(str(root))
876:
877:     def build(model_seed):
878:         return PointerCourseLearner(torch, matched._framework(torch, device, model_seed), encoder,
879:                                     optimizer_config=design["optimizer_config"], run_context=run_context,
880:                                     limits=limits, device=device, tagger=tagger, python_seed=model_seed,
881:                                     root=str(root))
882:
883:     # R1-2. THE ORDERING IS MEASURED HERE, at the instant before the container is built, from two runtime
884:     # facts and nothing else: whether any pointer model was already attached to this run, and the run's own
885:     # monotonic reading of when phase A returned (`run()` records it). Nothing about this pair is written as
886:     # a literal, because a literal cannot vary and therefore is not evidence.
887:     model_seeded_at = time.monotonic()
888:     model_already_present = ctx.get("main") is not None
889:     main = build(seed)
890:     # (b) a SECOND, independent build of the WHOLE model: the container identity must be equal.
891:     second = build(seed)
892:     whole_first = _container_identity(torch, main.module)
893:     whole_second = _container_identity(torch, second.module)
894:     del second
895:     require(whole_first == whole_second, "POINTER_DOUBLE_BUILD_MISMATCH")
896:     core_identity = _core_identity(torch, main.module)
897:     # (c) the three seeds' `^6` starts must be pairwise different.
898:     seed_identities = {}
899:     for model_seed in contract.MODEL_SEEDS:
900:         probe = build(model_seed)
901:         seed_identities[str(model_seed)] = _core_identity(torch, probe.module)
902:         del probe
903:     require(len(set(seed_identities.values())) == len(seed_identities), "POINTER_SEED_IDENTITIES_NOT_DISTINCT")
904:     require(seed_identities[str(seed)] == core_identity, "POINTER_SEED_IDENTITY_STABLE")
```
```text
1004:     """The plan's passes: one sealed-then-trained update at a time, evaluated at the plan's checkpoints."""
1005:     main, artifacts, plan = ctx["main"], ctx["artifacts"], ctx["plan"]
1006:     staging, stats, packets = ctx["staging"], ctx["stats"], ctx["packets"]
1007:     report, work = ctx["report"], ctx["work"]
1008:
1009:     def checkpoint(name):
1010:         phase(name + "_checkpoint", completed_updates=main.cursor)
1011:         pin = main.export_checkpoint(staging / (name + ".pt"))
1012:         _move_in(staging / (name + ".pt"), artifacts / (name + ".pt"))
1013:         ctx["checkpoint_pins"][name] = {**pin, "path": str(artifacts / (name + ".pt"))}
1014:         _publish(artifacts / (name + "_checkpoint.json"), ctx["checkpoint_pins"][name])
1015:
1016:     def evaluate_at(number):
1017:         if number in FULL:
1018:             name = "course_p%02d" % number
1019:             ctx["predictions"][name], scored = _evaluate(main, packets, name, artifacts, started=ctx["started"],
1020:                                                          progress=phase, work=work)
1021:             report["scores"][name] = {"correct": scored["correct"], "total": scored["total"],
1022:                                       **_split_score(scored, ctx["sides"])}
1023:         else:
1024:             name = "heldback_p%02d" % number
1025:             _, scored = _evaluate(main, ctx["held_packets"], name, artifacts, started=ctx["started"],
1026:                                   progress=phase, work=work)
1027:             report["scores"][name] = {"correct": scored["correct"], "total": scored["total"],
1028:                                       "held_back": {"correct": scored["correct"], "total": scored["total"]}}
1029:         name = "development_p%02d" % number
1030:         _, scored = _evaluate(main, ctx["development_packets"], name, artifacts, started=ctx["started"],
1031:                               progress=phase, work=work)
1032:         report["development_scores"].append({"pass": number, "cursor": main.cursor,
1033:                                              "correct": scored["correct"], "total": scored["total"]})
1034:
1035:     phase = ctx["phase"]
1036:     checkpoint("initial")
1037:     ctx["main_deltas"] = []
1038:     if 0 in plan["evaluations"]:
1039:         evaluate_at(0)
1040:     last_seal, pass_summaries, training_seconds, update_count = None, [], 0.0, 0
1041:     for number in range(1, plan["passes"] + 1):
1042:         _deadline(ctx["started"])
1043:         names = ("pass_%02d_batches.jsonl" % number, "pass_%02d_updates.jsonl" % number)
1044:         batches_log, updates_log = staging / names[0], staging / names[1]
1045:         batches_log.touch(exist_ok=False)
1046:         updates_log.touch(exist_ok=False)
1047:         losses, gradients = [], []
1048:         began = time.monotonic()
1049:         for batch in (item for item in ctx["batches"] if item["pass"] == number):
1050:             if batch["cursor"] == stats["main_updates"] - 1:
1051:                 checkpoint("prelast")
1052:             before = deepcopy(main.counters)
1053:             last_seal, update = _train_logged(main, batch, packets, staging, batches_log, updates_log,
1054:                                               started=ctx["started"])
1055:             ctx["main_deltas"].append(_counter_delta(main.counters, before))
1056:             losses.append(update["raw_batch_loss"])
1057:             gradients.append(update["gradient_squared_norm"])
1058:             update_count += 1
1059:             report["completed_main_updates"] = main.cursor
1060:             if main.cursor % 10 == 0:
1061:                 phase("main_training", completed_main_updates=main.cursor,
1062:                       total_main_updates=stats["main_updates"], current_pass=number)
1063:         training_seconds += time.monotonic() - began
1064:         _move_in(batches_log, artifacts / names[0])
1065:         _move_in(updates_log, artifacts / names[1])
1066:         require(bool(losses), "POINTER_EMPTY_PASS")
1067:         pass_summaries.append({"pass": number, "updates": len(losses), "cursor_end": main.cursor,
1068:                                "mean_raw_batch_loss": sum(losses) / len(losses),
1069:                                "first_raw_batch_loss": losses[0], "last_raw_batch_loss": losses[-1],
1070:                                "mean_gradient_squared_norm": sum(gradients) / len(gradients),
1071:                                "seconds": time.monotonic() - began})
1072:         if number < plan["passes"]:
1073:             _partial_checkpoint(main, ctx["results"], main.cursor)
1074:         if number == 1:
1075:             checkpoint("pass_01")
1076:         if number == plan["passes"]:
1077:             checkpoint("final")
1078:         if number in plan["evaluations"]:
1079:             evaluate_at(number)
1080:     require(main.cursor == stats["main_updates"] and not any(staging.iterdir()), "POINTER_MAIN_INCOMPLETE")
1081:     require(update_count == stats["main_updates"], "POINTER_INCOMPLETE_UPDATES")
1082:     report["pass_summaries"] = pass_summaries
1083:     report["training_seconds"] = training_seconds
1084:     report["main_training_delta"] = matched._sum_deltas(ctx["main_deltas"])
1085:     require(canonical(report["main_training_delta"]) == canonical(contract.expected_main_delta(stats)),
1086:             "MAIN_TRAINING_COUNTERS")
1087:     work.append({"phase": "main_training", "delta": report["main_training_delta"],
1088:                  "elapsed_seconds": training_seconds})
1089:     require(ctx["checkpoint_pins"]["initial"]["metadata"]["model_state_identity"]
```
```text
1097: def _retention_and_interference(ctx):
1098:     """The retention panel before and after the trained-record-only interference interval."""
1099:     main, artifacts, plan = ctx["main"], ctx["artifacts"], ctx["plan"]
1100:     staging, stats, packets = ctx["staging"], ctx["stats"], ctx["packets"]
1101:     report, work = ctx["report"], ctx["work"]
1102:     if plan["retention"]:
1103:         ctx["retention_sides"] = {"held_world": ctx["retention_held"],
1104:                                   "trained_world": set(ctx["retention_packets"]) - ctx["retention_held"]}
1105:         _, before_score = _evaluate(main, ctx["retention_packets"], "retention_before", artifacts,
1106:                                     started=ctx["started"], progress=ctx["phase"], work=work)
1107:     else:
1108:         before_score = None
1109:     deltas = []
1110:     if plan["interference"]:
1111:         names = ("interference_batches.jsonl", "interference_updates.jsonl")
1112:         batches_log, updates_log = staging / names[0], staging / names[1]
1113:         batches_log.touch(exist_ok=False)
1114:         updates_log.touch(exist_ok=False)
1115:         for batch in ctx["interference"]:
1116:             before = deepcopy(main.counters)
1117:             _train_logged(main, batch, packets, staging, batches_log, updates_log, started=ctx["started"])
1118:             deltas.append(_counter_delta(main.counters, before))
1119:             ctx["phase"]("interference_training", completed_updates=main.cursor,
1120:                          total_updates=stats["main_updates"] + contract.INTERFERENCE_UPDATES)
1121:         _move_in(batches_log, artifacts / names[0])
1122:         _move_in(updates_log, artifacts / names[1])
1123:     report["interference_delta"] = matched._sum_deltas(deltas) if deltas else None
1124:     if plan["interference"]:
1125:         require(report["interference_delta"]["optimizer_updates"] == contract.INTERFERENCE_UPDATES
1126:                 and report["interference_delta"]["prediction_calls"]
1127:                 == contract.INTERFERENCE_UPDATES * contract.INTERFERENCE_BATCH, "INTERFERENCE_COUNTS")
1128:         work.append({"phase": "interference_training", "delta": report["interference_delta"]})
1129:     if plan["retention"]:
1130:         ctx["phase"]("retained_checkpoint", completed_updates=main.cursor)
1131:         pin = main.export_checkpoint(staging / "retained.pt")
1132:         _move_in(staging / "retained.pt", artifacts / "retained.pt")
1133:         ctx["checkpoint_pins"]["retained"] = {**pin, "path": str(artifacts / "retained.pt")}
1134:         _publish(artifacts / "retained_checkpoint.json", ctx["checkpoint_pins"]["retained"])
1135:         ctx["retained_predictions"], after_score = _evaluate(main, ctx["retention_packets"], "retention_after",
1136:                                                             artifacts, started=ctx["started"],
1137:                                                             progress=ctx["phase"], work=work)
1138:         report["retention_scores"] = {"before": {key: before_score[key] for key in ("correct", "total")},
1139:                                       "after": {key: after_score[key] for key in ("correct", "total")},
1140:                                       "before_by_side": _split_score(before_score, ctx["retention_sides"]),
1141:                                       "after_by_side": _split_score(after_score, ctx["retention_sides"]),
1142:                                       "starting_competence_met":
1143:                                           2 * before_score["correct"] >= before_score["total"],
1144:                                       "interference_updates": contract.INTERFERENCE_UPDATES
1145:                                       if plan["interference"] else 0}
```
```text
1157: def _restore_pointer(ctx, *, path, pin, encoder):
1158:     """Restore ONE pointer checkpoint into a freshly built framework, and require the exact state back."""
1159:     restored = pointer_module.PointerCourseLearner.restore_checkpoint(
1160:         ctx["torch"], matched._framework(ctx["torch"], ctx["device"], ctx["design"]["model_seed"]), encoder,
1161:         path=path, expected_sha256=pin["sha256"],
1162:         expected_run_identity_digest=ctx["main"].run_identity_digest, device=ctx["device"])
1163:     base._check_state(ctx["torch"], restored, pin)
1164:     return restored
1165:
1166:
1167: def _reloads_and_replays(ctx):
1168:     """Same-process reconstruction: the plan's reloads and the two prelast replays."""
1169:     artifacts, plan = ctx["artifacts"], ctx["plan"]
1170:     staging, stats, packets = ctx["staging"], ctx["stats"], ctx["packets"]
1171:     work = ctx["work"]
1172:     reloads, replays = [], []
1173:     for name in plan["reloads"]:
1174:         _deadline(ctx["started"])
1175:         ctx["phase"](name + "_reconstruction")
1176:         pin = ctx["checkpoint_pins"][name]
1177:         restored = _restore_pointer(ctx, path=artifacts / (name + ".pt"), pin=pin, encoder=ctx["encoder"])
1178:         before = deepcopy(restored.counters)
1179:         if name == "retained":
1180:             selected = list(ctx["retention_packets"])[:8]
1181:             source_packets = ctx["retention_packets"]
1182:             expected = ctx["retained_predictions"]
1183:         else:
1184:             selected = list(ctx["representatives"].values())
1185:             source_packets = packets
1186:             expected = ctx["predictions"]["course_p%02d" % (0 if name == "initial" else plan["passes"])]
1187:         rows = [restored.predict(source_packets[key], EVALUATION_DEPTH) for key in selected]
1188:         require(all(canonical(row) == canonical(expected[row["record_id"]]) for row in rows),
1189:                 "RELOAD_PREDICTION_MISMATCH")
1190:         _seal_predictions(artifacts / (name + "_reload_predictions.json"), rows, phase=name + "_reload",
1191:                           expected_ids=selected)
1192:         delta = _counter_delta(restored.counters, before)
1193:         require(delta["optimizer_updates"] == delta["backward_calls"] == 0, "RELOAD_UPDATED_MODEL")
1194:         work.append({"phase": name + "_reload", "delta": delta})
1195:         reloads.append({"phase": name, "checkpoint_sha256": pin["sha256"], "prediction_ids": selected,
1196:                         "delta": delta})
1197:         del restored
1198:     if plan["replays"]:
1199:         for branch in (1, 2):
1200:             _deadline(ctx["started"])
1201:             ctx["phase"]("replay_%d" % branch)
1202:             pin = ctx["checkpoint_pins"]["prelast"]
1203:             restored = _restore_pointer(ctx, path=artifacts / "prelast.pt", pin=pin, encoder=ctx["encoder"])
1204:             before = deepcopy(restored.counters)
1205:             staged_seal = staging / ("replay_%d_batch.json" % branch)
1206:             raw, update = _stage_and_train(restored, ctx["batches"][-1], packets, staged_seal,
1207:                                            started=ctx["started"])
1208:             require(raw == ctx["last_seal"], "REPLAY_PREUPDATE_MISMATCH")
1209:             _move_in(staged_seal, artifacts / ("replay_%d_batch.json" % branch))
1210:             _publish(artifacts / ("replay_%d_update.json" % branch), update)
1211:             base._check_state(ctx["torch"], restored, ctx["checkpoint_pins"]["final"])
1212:             expected = ctx["predictions"]["course_p%02d" % plan["passes"]]
1213:             rows = [restored.predict(packets[key], EVALUATION_DEPTH)
1214:                     for key in ctx["representatives"].values()]
1215:             require(all(canonical(row) == canonical(expected[row["record_id"]]) for row in rows),
1216:                     "REPLAY_FINAL_MISMATCH")
1217:             _seal_predictions(artifacts / ("replay_%d_predictions.json" % branch), rows,
1218:                               phase="replay_%d" % branch, expected_ids=list(ctx["representatives"].values()))
1219:             delta = _counter_delta(restored.counters, before)
1220:             require(delta["optimizer_updates"] == delta["backward_calls"] == 1, "REPLAY_COUNTS")
1221:             work.append({"phase": "replay_%d" % branch, "delta": delta})
1222:             replays.append({"branch": branch, "restored_cursor": stats["main_updates"] - 1,
1223:                             "committed_cursor": restored.cursor, "delta": delta})
1224:             del restored
1225:     _publish(artifacts / "replay_report.json",
1226:              {"schema": "cncm.typed-pointer-reload/0.1", "reloads": reloads, "replays": replays,
1227:               "passes": plan["passes"], "reload_selected": plan["reload"], "replays_selected": plan["replays"],
```

## Helm 2.0-experimental research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py

SHA256: 21dabd21bb2909ff5990e2b11fd45b75558dce82992c34edfe12f8f556cd5084
```text
1717:         # ONE container. `scope_parameters` is never called on it (review RK2).
1718:         self.module = _build_container(torch, framework, self.device)
1719:         # The scope record is the container's own parameter list under the REGISTERED names, and it records
1720:         # that the shared freeze was deliberately not applied.
1721:         registered = _registered_names(self.module)
1722:         parameters = dict(self.module.named_parameters())
1723:         self.scope = {
1724:             "allowed": sorted(registered[name] for name, parameter in parameters.items()
1725:                               if parameter.requires_grad),
1726:             "frozen": sorted(registered[name] for name, parameter in parameters.items()
1727:                              if not parameter.requires_grad),
1728:             "contract_id": "cas.cjt.operation.^6.decompose/0.2", "role": "operation:^6",
1729:             "call": "NOT_CALLED_ON_THE_POINTER_CONTAINER",
1730:         }
1731:         require(set(self.scope["allowed"]) == set(self.module.state_dict())
1732:                 and not self.scope["frozen"], "POINTER_CONTAINER_SCOPE")
1733:         require(set(PARAMETERS) <= set(self.scope["allowed"]), "POINTER_CONTAINER_BLOCK_SCOPE")
1734:         self.encoder = encoder
1735:         encoder.verify_frozen()
1736:         parameters = dict(self.module.named_parameters())
1737:         require(all(parameter.device == self.device and parameter.dtype == torch.float32
1738:                     and parameter.requires_grad for parameter in parameters.values()),
1739:                 "POINTER_PARAMETER_DEVICE")
1740:         require(all(tuple(parameters[BLOCK_NAMES[name]].shape) == PARAMETER_SHAPES[name]
1741:                     for name in PARAMETERS)
1742:                 and tuple(encoder.readout_rows.shape) == (90, 64)
1743:                 and not encoder.readout_rows.requires_grad, "POINTER_PARAMETER_SHAPE")
1744:         require(type(optimizer_config) is dict
1745:                 and set(optimizer_config) == {"learning_rate", "weight_decay", "betas", "eps"},
1746:                 "TYPED_OPTIMIZER_FIELDS")
1747:         require(type(optimizer_config["betas"]) is list and len(optimizer_config["betas"]) == 2,
1748:                 "TYPED_OPTIMIZER_BETAS")
1749:         values = [optimizer_config["learning_rate"], optimizer_config["weight_decay"],
1750:                   optimizer_config["eps"], *optimizer_config["betas"]]
1751:         require(all(type(value) in (int, float) and math.isfinite(value) for value in values)
1752:                 and 0 < values[0] <= 1 and 0 <= values[1] <= 1 and 0 < values[2] <= 1
1753:                 and all(0 <= value < 1 for value in values[3:]), "TYPED_OPTIMIZER_RANGE")
1754:         require(type(limits) is dict and set(limits) == {"max_updates", "max_core_calls", "max_wall_seconds"}
1755:                 and type(limits["max_updates"]) is int and 0 < limits["max_updates"] <= MAX_UPDATES_CEILING
1756:                 and type(limits["max_core_calls"]) is int and 0 < limits["max_core_calls"] <= 1000000
1757:                 and type(limits["max_wall_seconds"]) in (int, float)
1758:                 and 0 < limits["max_wall_seconds"] <= 86400, "TYPED_LEARNER_LIMITS")
1759:         require(type(run_context) is dict
1760:                 and set(run_context) == {"run_id", "course_sha256", "condition", "source_seed"}
1761:                 and type(run_context["run_id"]) is str
1762:                 and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_context["run_id"])
1763:                 and type(run_context["course_sha256"]) is str
1764:                 and re.fullmatch("[0-9a-f]{64}", run_context["course_sha256"])
1765:                 and run_context["condition"] in CONDITIONS
1766:                 and type(run_context["source_seed"]) is int
1767:                 and run_context["source_seed"] in SOURCE_SEEDS, "TYPED_LEARNER_RUN_CONTEXT")
1768:         self.optimizer_config, self.limits = deepcopy(optimizer_config), deepcopy(limits)
1769:         # HELM 2.0 (F4). The schedule needs to know how many updates the run plans, and the learner is
1770:         # not told that today. `limits["planned_main_updates"]` is the seam: when a caller supplies it
1771:         # the rate warms up and then decays; when it is ABSENT the rate is the configured constant, which
1772:         # is bitwise what Helm 1.0 did. So this change cannot alter an existing run's arithmetic unless
1773:         # that run opts in, and `learning_rate_schedule` records which of the two was in force.
1774:         planned = limits.get("planned_main_updates") if type(limits) is dict else None
1775:         require(planned is None or (type(planned) is int and planned > 0),
1776:                 "TYPED_LEARNER_PLANNED_MAIN_UPDATES")
1777:         self.planned_main_updates = planned
1778:         self.learning_rate_schedule = ("CONSTANT_AS_HELM_1_0" if planned is None
1779:                                        else "WARMUP_%g_THEN_COSINE_TO_%g_OVER_%d"
1780:                                        % (LR_WARMUP_FRACTION, LR_FINAL_FRACTION, planned))
1781:         self.optimizer = torch.optim.AdamW(list(self.module.parameters()),
1782:                                            lr=optimizer_config["learning_rate"],
1783:                                            weight_decay=optimizer_config["weight_decay"],
1784:                                            betas=tuple(optimizer_config["betas"]),
1785:                                            eps=optimizer_config["eps"], foreach=False, fused=False,
```
```text
1811:     def _learning_rate(self):
1812:         """This step's learning rate. HELM 2.0 (F4).
1813:
1814:         With no `planned_main_updates` this returns the configured constant, so a caller that does not
1815:         opt in gets Helm 1.0's arithmetic exactly. With one, the rate warms LINEARLY from zero over the
1816:         first `LR_WARMUP_FRACTION` of the plan and then follows a cosine down to `LR_FINAL_FRACTION` of
1817:         the configured rate. The floor is deliberately not zero: a rate that reaches zero makes a
1818:         converged model and a stalled one look identical in the loss curve, which is precisely the
1819:         reading Helm 1.0's flat pass 4-10 stretch already made hard.
1820:
1821:         `self.cursor` is the count of updates COMMITTED so far, so the first step asks with cursor 0 and
1822:         the last with cursor `planned - 1`. A run that overruns its plan holds the floor rather than
1823:         walking off the end of the cosine.
1824:         """
1825:         base = float(self.optimizer_config["learning_rate"])
1826:         planned = self.planned_main_updates
1827:         if planned is None:
1828:             return base
1829:         step, warmup = int(self.cursor), max(1, int(planned * LR_WARMUP_FRACTION))
1830:         if step < warmup:
1831:             return base * (step + 1) / warmup
1832:         span = max(1, planned - warmup)
1833:         progress = min(1.0, (step - warmup) / span)
1834:         cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
1835:         return base * (LR_FINAL_FRACTION + (1.0 - LR_FINAL_FRACTION) * cosine)
```
```text
1936:     def _tensor_loss(self, plan, loss, tensors):
1937:         """`TypedCourseLearner._tensor_loss`, CALLED so the joint correspondence loss is unchanged."""
1938:         return TypedCourseLearner._tensor_loss(self, plan, loss, tensors)
1939:
1940:     def train_sealed_batch(self, path, *, expected_sha256, target_receipts):
1941:         """Read the exact durable public seal BEFORE accessing private targets, then update.
1942:
1943:         The gradient gate is the RK1 replacement: finiteness is required only on the parameters that actually
1944:         received a gradient, at least ONE parameter must have received one, and the parameter names that did
1945:         are recorded per update. `optimizer.zero_grad(set_to_none=True)` leaves `p.grad is None` for a head no
1946:         field of the batch touched, and AdamW with a `None` gradient applies NEITHER an update NOR a weight-decay
1947:         term to that parameter for that step -- so a kind that was absent from a batch is simply not trained by
1948:         it, which is the whole point of the replacement.
1949:         """
1950:         self._budget()
1951:         require(self._pending is not None, "TYPED_LEARNER_NO_PENDING_BATCH")
1952:         seal = Path(path)
1953:         require(seal.is_file() and not seal.is_symlink() and seal.stat().st_size <= 16 * 1024 * 1024,
1954:                 "TYPED_LEARNER_SEAL_PATH")
1955:         raw = seal.read_bytes()
1956:         require(type(expected_sha256) is str and sha256(raw).hexdigest() == expected_sha256
1957:                 and raw == self._pending["raw"], "TYPED_LEARNER_SEAL_MISMATCH")
1958:         require(state_identity(self.torch, dict(self.module.state_dict()))
1959:                 == self._pending["model_identity"], "TYPED_LEARNER_MODEL_CHANGED_AFTER_PREDICTION")
1960:         self.encoder.verify_frozen()
1961:         # No target object has been iterated or validated before this point.
1962:         from . import loss_plan
1963:         require(type(target_receipts) is list and len(target_receipts) == len(self._pending["results"]),
1964:                 "TYPED_LEARNER_TARGET_COUNT")
1965:         tasks, reports, loss_ids = [], [], []
1966:         try:
1967:             for result, target in zip(self._pending["results"], target_receipts):
1968:                 packet, plan, rows = result["packet"], result["plan"], result["rows"]
1969:                 prediction_raw = (canonical(result["prediction"]) + "\n").encode()
1970:                 self.counters["private_loss_plan_calls"] += 1
1971:                 loss = loss_plan.compile_loss_plan(
1972:                     packet, target, sealed_prediction_bytes=prediction_raw,
1973:                     expected_prediction_sha256=sha256(prediction_raw).hexdigest())
1974:                 task, report = self._tensor_loss(plan, loss, rows)
1975:                 scalar = loss_plan.scalar_report(packet, loss, result["prediction"]["scores"])
1976:                 require(math.isclose(report["raw_task_loss"], scalar["raw_task_loss"], rel_tol=2e-5,
1977:                                      abs_tol=2e-5), "TYPED_LEARNER_SCALAR_TENSOR_LOSS_MISMATCH")
1978:                 report.update({"record_id": plan["record_id"], "loss_plan_digest": loss["loss_plan_digest"],
1979:                                "admissible_answer_count": loss["admissible_answer_count"]})
1980:                 tasks.append(task)
1981:                 reports.append(report)
1982:                 loss_ids.append(loss["loss_plan_digest"])
1983:             self._budget()
1984:             total = self.torch.stack(tasks).mean()
1985:             self.counters["backward_attempts"] += 1
1986:             total.backward()
1987:             self.counters["backward_calls"] += 1
1988:             parameters = dict(self.module.named_parameters())
1989:             trained = sorted(name for name, parameter in parameters.items()
1990:                              if parameter.grad is not None)
1991:             require(trained, "POINTER_GRADIENTS_ABSENT")
1992:             require(all(bool(self.torch.isfinite(parameters[name].grad).all().item())
1993:                         for name in trained), "TYPED_LEARNER_GRADIENTS")
1994:             gradient_squared = sum(float((parameters[name].grad.detach()
1995:                                          * parameters[name].grad.detach()).sum().cpu().item())
1996:                                    for name in trained)
1997:             require(math.isfinite(gradient_squared), "TYPED_LEARNER_GRADIENT_NORM_NONFINITE")
1998:             self._budget()
1999:             # HELM 2.0 (F4). Clip, then set this step's rate. Both are MEASURED into the row below.
2000:             # `clip_grad_norm_` returns the norm it SAW, before any scaling, so `gradient_norm_before_clip`
2001:             # is the real reading and `gradient_was_clipped` is derived from it rather than asserted.
2002:             clip_norm = float(self.torch.nn.utils.clip_grad_norm_(
2003:                 [parameter for parameter in parameters.values() if parameter.grad is not None],
2004:                 GRADIENT_CLIP_NORM))
2005:             require(math.isfinite(clip_norm), "TYPED_LEARNER_GRADIENT_NORM_NONFINITE")
2006:             step_learning_rate = self._learning_rate()
2007:             for group in self.optimizer.param_groups:
2008:                 group["lr"] = step_learning_rate
2009:             self.counters["optimizer_step_attempts"] += 1
2010:             self.optimizer.step()
2011:             self.counters["optimizer_updates"] += 1
2012:             require(all(bool(self.torch.isfinite(parameter).all().item())
2013:                         for parameter in parameters.values()), "TYPED_LEARNER_PARAMETERS_NONFINITE")
2014:             self.encoder.verify_frozen()
2015:             self.cursor += 1
2016:             self.model_revision += 1
2017:             result = {"schema": UPDATE_SCHEMA,
2018:                       "batch_id": self._pending["public"]["batch_id"],
2019:                       "public_seal_sha256": expected_sha256, "cursor_committed": self.cursor,
2020:                       "model_revision": self.model_revision, "tasks": reports,
2021:                       "raw_batch_loss": sum(row["raw_task_loss"] for row in reports) / len(reports),
2022:                       "normalized_batch_loss": sum(row["normalized_task_loss"] for row in reports)
2023:                       / len(reports),
2024:                       "training_uses": "raw_batch_loss", "gradient_squared_norm": gradient_squared,
2025:                       # HELM 2.0 (F4), recorded so the guards are auditable rather than trusted.
2026:                       "gradient_norm_before_clip": clip_norm,
2027:                       "gradient_clip_norm": GRADIENT_CLIP_NORM,
2028:                       "gradient_was_clipped": bool(clip_norm > GRADIENT_CLIP_NORM),
2029:                       "learning_rate_this_step": step_learning_rate,
2030:                       "learning_rate_schedule": self.learning_rate_schedule,
2031:                       "loss_plan_digests": loss_ids, "counters": deepcopy(self.counters),
2032:                       "gradient_parameter_names": trained,
2033:                       "gradient_parameter_count": len(trained),
2034:                       "gradient_parameter_total": len(parameters),
2035:                       "none_gradient_parameters_update_and_decay_skipped":
```
```text
2085:     def restore_checkpoint(cls, torch, framework, encoder, *, path, expected_sha256,
2086:                            expected_run_identity_digest, device, expected_learnable_names=None):
2087:         """Restore a POINTER checkpoint. A practice checkpoint is refused, not silently half-loaded.
2088:
2089:         `framework` must be the freshly built pointer framework for this run's seed and must NOT have had the
2090:         saved state loaded into it: the container is the thing that owns the state, so loading it into
2091:         `framework.module` first (which is what `TypedCourseLearner.restore_checkpoint` does at
2092:         `learner.py:341`) would put the container's names into the three-key `^6` module and raise
2093:         `POINTER_CHECKPOINT_BLOCK_MISMATCH`. Pass `expected_learnable_names` to assert which parameters a run
2094:         is willing to restore; the recorded name set is checked against it either way.
2095:         """
2096:         from ..teaching_cycle.gpu_adapter import execution_guard
2097:         execution_guard()
2098:         _require_cuda_device(torch, device)
2099:         target = Path(path)
2100:         require(target.is_file() and not target.is_symlink()
2101:                 and 0 < target.stat().st_size <= 256 * 1024 * 1024, "TYPED_CHECKPOINT_FILE_BOUND")
2102:         raw = target.read_bytes()
2103:         require(type(expected_sha256) is str and sha256(raw).hexdigest() == expected_sha256,
2104:                 "TYPED_CHECKPOINT_SHA")
2105:         payload = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
2106:         require(type(payload) is dict
2107:                 and set(payload) == {"schema", "metadata", "model_state", "optimizer_state",
2108:                                      "encoder_state", "rng_state"}, "TYPED_CHECKPOINT_FIELDS")
2109:         require(payload["schema"] == CHECKPOINT_SCHEMA, "POINTER_CHECKPOINT_SCHEMA")
2110:         metadata = payload["metadata"]
2111:         require(type(metadata) is dict and set(metadata) == set(METADATA_FIELDS),
2112:                 "TYPED_CHECKPOINT_METADATA")
2113:         identity = metadata["run_identity"]
2114:         require(digest(identity) == metadata["run_identity_digest"] == expected_run_identity_digest
2115:                 and canonical(identity["learner_profile"]) == canonical(profile()),
2116:                 "TYPED_CHECKPOINT_RUN_IDENTITY")
2117:         for field in ("model", "optimizer", "encoder", "rng"):
2118:             require(state_identity(torch, payload[field + "_state"])
2119:                     == metadata[field + "_state_identity"], "TYPED_CHECKPOINT_STATE_DIGEST:" + field)
2120:         pointer_names = _fingerprint(torch, payload["model_state"])
2121:         require(pointer_names, "POINTER_CHECKPOINT_CONTAINER_EMPTY")
2122:         require(set(PARAMETERS) <= {row.split(":", 1)[0] for row in pointer_names}
2123:                 and len(pointer_names) > len(PARAMETERS), "POINTER_CHECKPOINT_BLOCK_MISMATCH")
2124:         require(list(metadata["learnable_names"]) == sorted(row.split(":", 1)[0] for row in pointer_names),
2125:                 "POINTER_CHECKPOINT_LEARNABLE_NAMES")
2126:         if expected_learnable_names is not None:
2127:             require(sorted(expected_learnable_names) == list(metadata["learnable_names"]),
2128:                     "POINTER_CHECKPOINT_EXPECTED_NAMES")
2129:         init_args = _validate_init_args(metadata["init_args"], str(device))
2130:         container = _build_container(torch, framework, device)
2131:         # The two questions are asked SEPARATELY. "Did the container produce any layout at all" is not the same
2132:         # question as "does it equal the saved layout", and while they shared one `require` the empty answer
2133:         # passed for a comparison -- the exact failure that cost the seventh run its reload. A container built by
2134:         # `_build_container` always has more parameters than `PARAMETERS`, so an empty live fingerprint is a
2135:         # defect in the fingerprinting, not a layout mismatch, and it now says so.
2136:         container_names = _fingerprint(torch, container.state_dict())
2137:         require(container_names, "POINTER_CHECKPOINT_CONTAINER_EMPTY")
2138:         require(container_names == pointer_names, "POINTER_CHECKPOINT_LAYOUT")
2139:         restored = cls(torch, framework, encoder,
2140:                        optimizer_config=init_args["optimizer_config"],
2141:                        run_context=init_args["run_context"], limits=init_args["limits"],
2142:                        device=device, tagger=role_tagger(init_args["root"]),
2143:                        python_seed=init_args["python_seed"], root=init_args["root"])
2144:         restored.module.load_state_dict(payload["model_state"], strict=True)
2145:         restored.optimizer.load_state_dict(payload["optimizer_state"])
2146:         require(state_identity(torch, dict(restored.module.state_dict()))
2147:                 == metadata["model_state_identity"]
2148:                 and state_identity(torch, restored.optimizer.state_dict())
2149:                 == metadata["optimizer_state_identity"], "TYPED_CHECKPOINT_RESTORED_VALUES")
2150:         require(type(metadata["cursor"]) is int and type(metadata["model_revision"]) is int
2151:                 and 0 <= metadata["cursor"] == metadata["model_revision"]
2152:                 <= restored.limits["max_updates"], "TYPED_CHECKPOINT_CURSOR")
2153:         require(type(metadata["counters"]) is dict and set(metadata["counters"]) == set(restored.counters)
2154:                 and all(type(value) is int and value >= 0 for value in metadata["counters"].values())
2155:                 and metadata["counters"]["optimizer_updates"] == metadata["cursor"],
2156:                 "TYPED_CHECKPOINT_COUNTERS")
2157:         require(type(metadata["elapsed_seconds"]) in (int, float)
2158:                 and math.isfinite(metadata["elapsed_seconds"])
2159:                 and 0 <= metadata["elapsed_seconds"] <= restored.limits["max_wall_seconds"]
2160:                 and type(metadata["training_mode"]) is bool, "TYPED_CHECKPOINT_RUNTIME_METADATA")
2161:         restored.run_identity = deepcopy(identity)
2162:         restored.run_identity_digest = expected_run_identity_digest
2163:         restored.cursor = metadata["cursor"]
2164:         restored.model_revision = metadata["model_revision"]
2165:         restored.counters = deepcopy(metadata["counters"])
2166:         restored._elapsed_before, restored._started = metadata["elapsed_seconds"], time.monotonic()
2167:         restored.module.train(metadata["training_mode"])
2168:         rng = payload["rng_state"]
2169:         require(type(rng) is dict and set(rng) == {"torch_cpu", "torch_cuda", "python"},
2170:                 "TYPED_CHECKPOINT_RNG_FIELDS")
2171:         torch.set_rng_state(rng["torch_cpu"])
2172:         torch.cuda.set_rng_state_all(rng["torch_cuda"])
2173:         random.setstate(rng["python"])
2174:         current = {"torch_cpu": torch.get_rng_state(),
2175:                    "torch_cuda": torch.cuda.get_rng_state_all(), "python": random.getstate()}
2176:         require(state_identity(torch, current) == metadata["rng_state_identity"],
2177:                 "TYPED_CHECKPOINT_RNG_VALUES")
2178:         restored.encoder.verify_frozen()
2179:         return restored
```

## Helm 2.0-experimental research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_contract.py

SHA256: 70be7ae7b7b3dbefd6a5d168b04ab7394718d7456a264614236d31b0c9c09b3d
```text
210: def _stratified_pass(frozen, base, keep_set):
211:     """One pass in which every batch carries ALL EIGHT KINDS: eight records, one per kind.
212:
213:     Owner decision 2026-09-19. Built from the SAME MIXED base batch slots the practice study uses, so the depth
214:     distribution, the phase structure and the round numbering are the base's and unchanged; only the membership
215:     and the ids are this study's.
216:
217:       * slot selection is the same rule as the practice pass -- every base slot holding at least one TRAINED
218:         record -- so the update count stays 147 per pass;
219:       * inside a slot, exactly one record per kind is taken from that kind's TRAINED pool (sorted), chosen by a
220:         deterministic round-robin cursor over that pool that persists across slots within the pass, which is
221:         `lb11_economics.py`'s branch B and the measurement REVIEW_SYNTHESIS section 4.7 reports as
222:         presentations_per_pass 1176;
223:       * `round`, `phase`, `depth` and `source_cursor` come from the base batch (the requirement is explicit);
224:       * `occurrence_ids` and `presentation_ids` are generated from (slot index, kind index) alone, so they are
225:         reproducible without the base ids and are UNIQUE INSIDE A BATCH -- which is what this contract's own
226:         `OCCURRENCE_UNIQUE` check requires, and is all the pass loop's re-digest needs. They are formed in the
227:         practice schedule's own style: an occurrence id is the `typed-occurrence-` prefix and a 64-hex digest, and a
228:         presentation id is the pass prefix, an 8-hex slot token and the ordinal of the kind inside the batch. The
229:         pass loop below still re-digests every occurrence id per pass, so the per-pass mechanism is untouched.
230:     """
231:     slots = [batch for batch in base if any(key in keep_set for key in batch["record_ids"])]
232:     pools = _kind_pools(frozen)
233:     cursor = {kind: 0 for kind in KINDS}
234:     one_pass = []
235:     for index, batch in enumerate(slots):
236:         token = source.digest({"domain": "typed-pointer-stratified-v1", "slot": index})[:8]
237:         records, occurrences, presentations = [], [], []
238:         for at, kind in enumerate(KINDS):
239:             pool = pools[kind]
240:             records.append(pool[cursor[kind] % len(pool)])
241:             cursor[kind] += 1
242:             occurrences.append("typed-occurrence-" + source.digest({"domain": "typed-pointer-stratified-v1",
243:                                                                     "slot": index, "kind": kind}))
244:             presentations.append("pointer-stratified-%s-%02d" % (token, at))
245:         one_pass.append({"round": batch["round"], "phase": batch["phase"], "depth": batch["depth"],
246:                          "source_cursor": batch["cursor"], "record_ids": records,
247:                          "occurrence_ids": occurrences, "presentation_ids": presentations})
248:     require(len(one_pass) == len(slots), "POINTER_STRATIFY_SLOTS")
```
```text
285:     require(type(count) is int and 1 <= count <= MAX_PASSES_PERMITTED,
286:             "POINTER_PASSES_BOUND:" + str(count))
287:     base, base_stats = matched.schedule(frozen, CONDITION)
288:     held, trained, excluded = split(frozen)
289:     keep_set = set(trained)
290:     one_pass = (_stratified_pass(frozen, base, keep_set) if layered
291:                 else _non_stratified_pass(frozen, base, keep_set))
292:     if layered:
293:         # Fail closed on composition drift: the stratified pass is a frozen artifact, so it may not silently
294:         # change under a re-derivation. This is pass-count independent, so it costs one digest per call.
295:         require(source.digest(one_pass) == STRATIFIED_PASS_DIGEST, "POINTER_STRATIFY_DIGEST")
296:         kinds_of = {row["record_id"]: row["query"]["kind"] for row in frozen["registry"]}
297:         require(all(len(b["record_ids"]) == len(KINDS)
298:                     and {kinds_of[key] for key in b["record_ids"]} == set(KINDS) for b in one_pass),
299:                 "POINTER_STRATIFY_COVERAGE")
300:     batches = []
301:     for number in range(1, count + 1):
302:         for batch in one_pass:
303:             occurrences = ["typed-occurrence-" + source.digest({"domain": "typed-practice-v1", "pass": number,
304:                                                                "occurrence": occurrence})
305:                            for occurrence in batch["occurrence_ids"]]
306:             batches.append({**deepcopy(batch), "cursor": len(batches), "pass": number,
307:                             "occurrence_ids": occurrences,
308:                             "presentation_ids": ["practice-p%02d-%s" % (number, p)
309:                                                  for p in batch["presentation_ids"]]})
310:     require(all(key in keep_set for b in batches for key in b["record_ids"]), "HOLDOUT_TRAINED")
311:     require(all(len(b["occurrence_ids"]) == len(set(b["occurrence_ids"])) for b in batches), "OCCURRENCE_UNIQUE")
```

## Helm 2.0-experimental research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/learner.py

SHA256: d87b49caed6d59e1d9715066ef030f55e09228a474c3a67e2535a3c54b3619ca
```text
197:     def _tensor_loss(self, plan, loss, tensors):
198:         torch = self.torch
199:         by_id = {s["slot_id"]: s for s in plan["slots"]}
200:         fields, reports = [], []
201:         for field in loss["fields"]:
202:             if field["kind"] == "joint_correspondence":
203:                 mode = torch.log_softmax(tensors[plan["slots"][0]["slot_id"]], dim=0)
204:                 candidates = plan["correspondence_candidates"]
205:                 if len(candidates) == 1:
206:                     term = mode.sum() * 0
207:                 else:
208:                     node_alias = {n["ref"]: n["alias"] for w in plan["aliases"]["worlds"] for n in w["nodes"]}
209:                     row_by_source = {s["coordinates"][0]: s for s in plan["slots"][1:]}
210:                     sums = []
211:                     for candidate in candidates[1:]:
212:                         selected = []
213:                         for pair in candidate["value"]["pairs"]:
214:                             row = row_by_source[pair["source"]]
215:                             selected.append(tensors[row["slot_id"]][row["symbols"].index(node_alias[pair["target"]])])
216:                         sums.append(torch.stack(selected).sum())
217:                     mapping = torch.stack(sums)
218:                     joint = torch.cat((mode[0].reshape(1), mode[1] + mapping - torch.logsumexp(mapping, dim=0)))
219:                     indices = [i for i, c in enumerate(candidates) if c["candidate_id"] in field["valid_candidate_ids"]]
220:                     term = -torch.logsumexp(joint[indices], dim=0)
221:             else:
222:                 terms = []
223:                 for key in field["slot_ids"]:
224:                     logits, row = tensors[key], by_id[key]
225:                     indices = [row["symbols"].index(symbol) for symbol in field["targets"][key]]
226:                     terms.append(torch.logsumexp(logits, dim=0) - torch.logsumexp(logits[indices], dim=0))
227:                 term = torch.stack(terms).mean()
228:             require(term.requires_grad and bool(torch.isfinite(term).item()), "TYPED_LEARNER_LOSS_DETACHED_OR_NONFINITE")
229:             fields.append(term)
230:             raw, size = float(term.detach().cpu().item()), field["public_alphabet_size"]
231:             reports.append({"field": field["field"], "raw_loss": raw, "normalized_loss": raw / math.log(size) if size > 1 else 0.0,
232:                             "public_alphabet_size": size, "slot_count": len(field["slot_ids"]), "forced": size == 1})
233:         return torch.stack(fields).mean(), {"fields": reports,
234:             "raw_task_loss": sum(r["raw_loss"] for r in reports) / len(reports),
235:             "normalized_task_loss": sum(r["normalized_loss"] for r in reports) / len(reports)}
```
