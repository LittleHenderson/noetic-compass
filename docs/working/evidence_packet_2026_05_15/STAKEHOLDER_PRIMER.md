# Evidence Packet — Stakeholder Primer

> **CAS does not just show an answer. It turns each idea into an inspectable object: meaning, structure, origin, and model evidence.**

This primer explains what that means, what you can audit, and how.

---

## 1. Why this document exists — naming the credibility problem directly

This project was built by a single founder without a traditional computer science degree (30 CS credits, not a full degree), using AI development tools (Claude and Codex) extensively as collaborators throughout the build. Treating either of those facts as something to hide would be a mistake. We treat them as problems to engineer around.

The engineering response is the **Evidence Packet**. Every model output, every classification, every reasoning trace, every test result is bundled with the cryptographic fingerprints of the artifacts that produced it, the exact code version that ran it, and the precise command needed to reproduce it. As one of our development collaborators put it: *"Yes, AI assisted the build. That is why every important claim is backed by reproducible traces, tests, hashes, evaluator reports, and exported audit packets. You do not need to trust me. You can inspect the artifact."* A reviewer does not need to trust the builder. They open the packet, they verify the fingerprints themselves, they re-run the command, they read the evaluator report. The artifact's auditability replaces the builder's credentials.

This is honest. It is also a stronger posture than degree-based or institution-based trust would be — because credentials can be wrong and institutions can be biased, but a SHA-256 fingerprint (a cryptographic checksum that acts like a file's unique signature) either matches or it doesn't. The result is **tamper-evident, reproducible, and independently inspectable**.

---

## 2. What you see when you click "Open Evidence"

When a reviewer opens the Evidence drawer on any single output, they see seven sections. Each one answers two questions: **what is this?** and **how do I check it?**

1. **Input** — the verbatim text the user typed. *Check:* compare it to the words in your own session transcript. If it matches, the system did not silently rewrite your question.

2. **CAS expression** — the structured form the model used internally. CAS (Cognitive Architecture System) is a small, rule-bound notation that names the moving parts of a thought (what kind of idea, what motivation, what register). *Check:* re-run the expression through the open-source compiler at `api/notation/compiler.py`. It will either parse cleanly under the published rules or it won't.

3. **Output** — what the model produced in plain language. *Check:* re-run the same input on the same model version using the command in section 5. With a fixed random seed, you get the same output.

4. **Copy / slot trace** — when the model emits a name, number, or identifier in its reply, the system records which specific input token it pointed at. *Check:* this is what we call a "hard trace" — the model can literally show you which words from your prompt it pulled into its answer.

5. **Provenance** — which model checkpoint produced this, which code commit was running, which command was issued. *Check:* the commit hash is a real git commit you can `git log`. The checkpoint file lives on disk at the path shown.

6. **Hashes** — the SHA-256 fingerprints of every artifact involved: the model weights, the tokenizer, the training corpus, the evaluation pack. SHA-256 is a cryptographic checksum — like a fingerprint of a file's contents. If even one byte changes, the SHA-256 changes too. *Check:* run `sha256sum` on the file yourself. Compare it to the value in the packet.

7. **Claim levels** — for each piece of evidence, the packet tells you how strong the claim is. These four tiers are the credibility spine of the system and deserve their own section.

---

## 3. The four claim-level tiers — in plain English

Most AI products lump everything together under "the model decided." We separate.

- **CAS hard trace.** Produced by the formal compiler that defines the CAS notation. If a row says CAS hard trace, the claim is mathematically checkable: the structure either matches the published rules or it doesn't. There is no interpretation involved.

- **Source copy evidence.** When the model emits a name or identifier in the output, the system records which input token it pointed at. This is concrete: the model literally has a pointer from output back to input. Not inference, not estimate — a recorded pointer.

- **Derived trace.** Reconstructed after the fact from log files or runtime state. Believable, but not the model's primary internal signal. Useful for understanding what happened during a run; less useful for proving the model "really did" something at the neural level.

- **Neural attribution estimate.** Data from techniques that try to identify which parts of the model contributed to a specific output. Treat this as **evidence, not proof**. The science of looking inside neural networks is young; estimates are sometimes wrong. The packet labels these clearly so a reviewer never confuses them with hard claims.

The discipline of labeling each row at the right tier IS the credibility win. A skeptical reader can immediately tell the difference between *"this is mathematically verifiable"* and *"this is our best current estimate of what the model is doing internally."*

---

## 4. The reviewer playbook — 5 steps to verify any single thought

1. **Find the trace.** Every thought carries a `trace_id` in the Evidence Packet header. *Success looks like:* you can copy that ID and locate the corresponding file on disk.

2. **Read the JSON.** Open the file at the path shown in section 5 of the packet. The drawer's on-screen content should match the file's contents exactly. *Success looks like:* no surprises between what the UI shows and what is written to disk.

3. **Verify the hashes.** Either click "Verify Hashes" in the packet or run `sha256sum` yourself against the model weights, tokenizer, and corpus files. *Success looks like:* every hash listed in the packet matches what `sha256sum` produces on your machine.

4. **Reproduce the run.** Copy the exact command from section 5 and execute it against the same checkpoint, with the documented random seed. *Success looks like:* same input plus same code plus same seed produces the same output.

5. **Read the evaluator.** Section 5 links to the evaluator report that gated this model's release. Read the gates and the held-out test numbers (held-out means data the model never saw during training). *Success looks like:* you can see exactly what the model was tested against, what score it had to clear, and what score it actually got.

If all five steps pass, you have done more independent verification than the average buyer has ever been able to do on an AI system.

---

## 5. What is NOT claimed — being explicit about the boundary

The Evidence Packet does **not** claim:

- That the model is correct on inputs outside its tested range.
- That the neural attribution data tells the full causal story of why the model said what it said.
- That the model is conscious or has intent.
- That matching hashes prove the model's reasoning is sound — only that the artifacts haven't been swapped between the time of the run and the time of the audit.
- That any single Evidence Packet replaces independent benchmarking on your own held-out test data.

Stating these limits explicitly makes the things the packet **does** claim more believable.

---

## 6. The pitch

Most AI products ask you to trust the brand, the team's credentials, or a marketing-grade demo. This one asks you to trust the artifact — and the artifact comes with everything you need to verify it yourself. If you find a mismatch, the evidence will show you. If everything checks out, you'll have done more diligence than the average buyer has ever been able to do on an AI system.

That is the offer. Open the packet. Run the commands. Check the fingerprints. Decide for yourself.
