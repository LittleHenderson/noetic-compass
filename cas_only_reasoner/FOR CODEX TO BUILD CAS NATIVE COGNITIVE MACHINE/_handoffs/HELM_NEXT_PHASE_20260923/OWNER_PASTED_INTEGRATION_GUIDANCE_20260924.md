# Owner-pasted guidance: a shared CAS record between Q4 and Helm, built on the CAS compiler (2026-09-24)

The owner pasted the text below into chat on 2026-09-24 (UTC), with no other words, while Claude was coordinating
the temporary takeover. It is copied here exactly. Claude treats it as the owner's direction. It does not
authorize new spending: every paid job still needs its own stated limit.

## How Claude applies it

- **A new, separate line: CAS-SHARED-RECORD-1.** It is not Q4-SDG-1, not the Helm repairs, and not the late-reach
  experiment. Nothing is pooled across lines.
- **Q4 and Helm are described as separate components, with a planned shared record. Never as integrated.**
- **Step 1 ($0, read-only).** A survey of what already exists:
  - the compiler output that keeps the original structure, fields, order, nesting and item references;
  - Helm's current input interface;
  - Q4's target format;
  - the PCBA reader and the CAS-Ohm/atlas connections.
- **Step 2.** A design, frozen before any build:
  - the smallest shared record, starting from the compiler's own structure;
  - one supported expression and one stated question;
  - how an experimental, opt-in Helm input reader would carry each field into the computation.

  The old Helm model and its historical tests stay unchanged.
- **Step 3.** Three separate scores, never merged:
  - Q4 reading;
  - Helm answering from reference structures, labelled as such;
  - the full chain from Q4's actual predictions, with its mistakes kept.
- **The compiler is the teacher and checker.** It never quietly replaces a wrong Q4 prediction.
- **Nothing is rebuilt.** The working compiler, atlas, PCBA reader, CAS-Ohm path and checker are reused.
- **Compiler versions stay pinned.** The historical snapshot `compiler_pre_ohm_61ed5a45.py` stays pinned for
  Q3/Q4 history. Any other compiler version is named in the record.
- **The current work continues:** Q4 recovery and the existing Helm repairs.

## The pasted text (verbatim)

**Yes. Those statements describe a real integration gap: you have working pieces, but not yet one connected CAS-learning system. Improving Q4 does not automatically improve Helm.**

However, **“they are intended to meet in Helm 3.0” should not mean waiting until some future version is finished before designing the connection. Building and testing that connection is part of how you get there.**

The reports identify Q4 as a separate expression-reading experiment, with no shared task, data, or weights with the tested Helm model. They identify Helm as the learning part of the CNCM pointer machine.  

## 1. The relationship, in plain English

| Piece        | Its role                                                                                                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **CNCM**     | The surrounding machine that organizes the supported work. Its existing pointer-machine implementation is built; that does not mean the whole long-term CAS vision is finished. |
| **Helm**     | The learning component that answers questions about supplied parts and their relationships.                                                                                     |
| **Q4**       | A separate experiment testing whether a learned model can read written CAS expressions and reconstruct their structure.                                                         |
| **Helm 3.0** | The intended future integration of richer CAS representations with learned processing. It is not simply Helm 2.0 plus a renamed Q4 model.                                       |

The existing runtime and atlas documents explicitly distinguish their implemented pieces from completion of the wider CNCM project. Q4’s actual run likewise states that it is not the complete Helm 3.0 result.  

**Also, Q4 taking “text” does not mean it already understands ordinary English. Its recorded task is reading written CAS notation.** Helm’s “diagram” is structured information about parts and connections, not a picture that it examines with a camera-like vision system.  

## 2. The missing connection is more than changing a file format

Here is the crucial issue.

Consider these two expressions:

```text
(^1^C + ^2^C)

(^1^C × ^2^C)
```

Both have the same simple arrangement:

```text
One operation
    ├── First state
    └── Second state
```

**If the connection between Q4 and Helm removes the operation and the state descriptions, those two different expressions become the same input.**

A model receiving identical inputs cannot reliably distinguish them just because we increase the penalty for a wrong answer. The required information has already been discarded.

That is why we need to distinguish:

**Unimportant names:** the arbitrary identifier assigned to a particular item.

**Important meaning:** which operation is present, which Noetic and Domain are involved, and which item occupies each position.

Renaming an item from `node_1` to `node_7` should not necessarily change the answer. Changing `+` to `×`, or exchanging two differently meaningful operands, may need to change it.

**The goal should be to remove dependence on arbitrary names, not remove the content needed to understand the problem.**

## 3. My recommendation: give both pieces a common CAS structure

I would design a small, shared way to record an expression that preserves:

**Its parts, their CAS descriptions, their order, their grouping, and the meaning of each connection.**

For example, the common record for the first expression above would preserve:

```text
Operation: PLUS

Left part:
    Noetic: ^1
    Domain: C

Right part:
    Noetic: ^2
    Domain: C
```

This is an illustration of the proposed information, not a claim that this exact shared format is already implemented.

Q4 would learn to produce that record from the written expression. A new Helm input reader would turn it into the numerical information that an experimental Helm model can use.

The intended chain would be:

```text
Written CAS expression
        ↓
Learned reader, developed through Q4
        ↓
Shared CAS structure
        ↓
Experimental Helm input reader
        ↓
Helm answers a specified question
        ↓
Separate checker evaluates the answer
```

**The shared structure is the meeting point. They do not need identical internal weights or identical kinds of neural network.**

And even if both models use vectors containing sixty-four numbers, those numbers do not automatically mean the same thing. Their meaning depends on how each model was trained and how its inputs and outputs are defined.

### Saving the information is not enough

The new Helm input reader must actually pass the relevant information into the computation.

Putting `operation: PLUS` in a saved file while the neural model ignores that field would reproduce the same problem in a prettier container.

The historical analogy investigation already demonstrated why this matters: the complete problem contained information that the answer-selection path did not receive in the required form. The repair therefore had to change that information path, not merely the report. 

## 4. CAS SDG could teach both sides from the same source

**This is another strong use for CAS SDG: generate two lessons from the same underlying expression.**

| Learner               | What it receives                                    | What it learns                                           |
| --------------------- | --------------------------------------------------- | -------------------------------------------------------- |
| **Q4**                | The written CAS expression                          | Reconstruct its parts, fields, order, and grouping.      |
| **Experimental Helm** | The corresponding structured record plus a question | Answer the question using those parts and relationships. |

The reference answers remain separate from the learner’s inputs.

For example, one generated expression could support:

> **Q4 lesson:** “Read this expression and preserve its exact structure.”

> **Helm lesson:** “Identify the operation inside the right-hand branch.”

Later lessons could ask about supported transformations or comparisons. Those require their own checked rules.

The project already has expression generation and compiler-derived structure targets. The existing compiler work also preserves nested expressions and set relationships. Those are resources to reuse, not features that need to be invented from nothing.  

**But this proposed paired teaching system is not already demonstrated merely because the separate generators and models exist.**

## 5. Test the connection without hiding which part failed

I would keep three separate scores:

| Test                                              | What it tells us                                             |
| ------------------------------------------------- | ------------------------------------------------------------ |
| **Q4 reads the expression**                       | Did the learned reader preserve the correct structure?       |
| **Helm receives the correct reference structure** | Can the reasoning model answer when its input is right?      |
| **Q4’s actual output goes to Helm**               | Does the combined learned system work from beginning to end? |

The second is a controlled test. Its correct structure comes from the reference program, not Q4, and must be labeled accordingly.

The third must use **Q4’s actual prediction**, including its mistakes. Do not quietly replace a wrong predicted tree with the correct one before handing it to Helm.

Otherwise, the demonstration could appear successful while the connection still depends on a hidden answer supply.

This separation is especially important now because Q4’s first recorded run produced the same wrong tree for all sixteen selected development expressions. Connecting that unchanged output to Helm would not recover the distinctions Q4 failed to preserve. 

## 6. What should happen now, while Claude is handling the work

**Continue repairing Q4’s learning, but define the small shared record and connection alongside that work. Do not postpone all integration planning until Q4 is “finished.”**

At the same time, **do not make Helm’s existing repairs wait for Q4**. They address separate, already-identified problems.

The first connection can be checked using small, compiler-produced reference structures. That establishes that the connecting code preserves the necessary information. Replacing the reference structure with Q4’s learned prediction is a later, separately measured step.

There is no need to force the current Q4 GRU to become the permanent reader if another tested design works better. **The required capability is a reliable learned reading path; this particular GRU is a candidate implementation.**

### The instruction I would give Claude

> **Treat Q4 and Helm as separate components with a planned shared CAS representation. Do not describe them as already integrated.**
>
> **Define and test the smallest shared record that preserves operation types, ordered parts, nesting, CAS state fields, and original-item references. Reuse the existing compiler structures where appropriate.**
>
> **Show exactly how the experimental Helm model will receive and use that information. Do not strip meaningful fields merely to fit the old word-free interface. Preserve the old model and its historical tests.**
>
> **Use CAS SDG to prepare paired reading and reasoning lessons from the same source expressions. Score Q4 reading, Helm reasoning from correct structures, and the complete learned connection separately.**
>
> **Continue the current Q4 recovery and existing Helm repairs without rebuilding the working compiler or atlas.**

**Your concern is correct: better isolated parts are not yet a better integrated machine. The missing milestone is not simply “Q4 scores higher.” It is “Q4 preserves the right CAS structure, Helm actually uses it, and the complete system answers correctly.”**
**Yes, Little. They can all make use of the CAS compiler, and I recommend using it as their shared foundation for reading, checking, and working with supported CAS expressions.**

**The common structure I proposed should start with what your compiler already produces, not with another competing language built from scratch.** I should have made that connection explicit.

The remaining work is to connect each component to the appropriate compiler output. **They do not all need to perform the same job to use the same compiler.**

## 1. Parts of this are already working

Your records establish that the compiler preserves nested expression structure and performs supported set operations. The PCBA reader already uses it to read and check complete CAS state descriptions. The atlas already displays results produced through the PCBA and CAS-Ohm compiler path.   

**So this is not a proposal to invent a central tool that does not exist. It is a proposal to extend the use of one you already have.**

Here is the division I recommend:

| Component    | How it can use the compiler                                                                                             |
| ------------ | ----------------------------------------------------------------------------------------------------------------------- |
| **CAS SDG**  | Check generated expressions and obtain reference structures or supported calculated answers for lessons.                |
| **Q4**       | Learn from the compiler’s example structures, then have its own reconstructions checked against them.                   |
| **Helm**     | Receive a model-ready version of the compiler’s structured description, preserving the information needed for its task. |
| **CNCM**     | Use checked descriptions and supported operations while its existing runtime manages the work.                          |
| **CAS PCBA** | Continue using the compiler for embedded CAS expressions, while the board reader handles components and connections.    |
| **CAS-RPA**  | Display the structured descriptions, predictions, calculations, and results of checks, each with its source.            |

This table is the **recommended arrangement**. It does not mean all six connections are already complete.

## 2. The compiler can be the common meeting point

For a supported written CAS expression, I would build toward this:

```text
Written CAS expression
        ↓
CAS compiler reads and checks it
        ↓
Structured record of its parts and relationships
        ↓
Small connector prepares the information Helm needs
        ↓
Helm makes its prediction
        ↓
The appropriate checker evaluates it
        ↓
CNCM records the result; CAS-RPA displays it
```

The **small connector** is the missing software that translates the compiler’s output into the model’s input format.

That is different from writing another CAS parser. It should reuse the existing structure and preserve its meaning.

For example:

```text
(^1^C + ^2^C)
```

The common record needs to retain:

```text
Operation: PLUS
Left part:  ^1^C
Right part: ^2^C
```

It must not become merely:

```text
One parent with two children.
```

The second description loses which operation is present and what the children contain.

**The compiler can preserve those distinctions. The new Helm connector must actually deliver them to the learned model.** Merely saving them in a file that Helm never reads would not solve the integration problem.

The original implementation directive already calls for operation identities, ordered relationships, and exact bindings to influence the model’s processing, rather than appear only in a report afterward. 

## 3. Use the compiler’s structure, not only its final answer

There is a crucial choice about **which compiler output gets shared**.

Suppose two different expressions produce the same calculated result. If we retain only that result, we may lose how each expression was constructed.

For your purposes, the shared record should preserve **the original expression and its organized parts**, alongside any calculated result.

That matters particularly for nesting. An earlier compiler review found that the stored expression tree preserved order while the calculated value could discard grouping. That is a reason to inspect and reuse the structure-preserving output, not assume the final value contains everything. 

**Reading an expression, calculating its result, and recording what actually executed should remain distinguishable.**

The same principle applies to PCBA. Its board reader must preserve connections and component settings; a single calculated number is not a replacement for the board.

## 4. This means Q4 does not have to block every useful integration

**For input that is already written in supported CAS notation, the compiler can read it directly. You do not need to wait for Q4 to learn that job before connecting structured CAS input to an experimental Helm model.**

I would keep two clearly named paths.

### Working-system path

Use the dependable program to read the expression, then let the learned model work on the resulting structure.

```text
CAS text → compiler-produced structure → learned processing
```

This would be a system combining programmed reading with learned processing. Its results should identify which part did which work.

### Learned-reading experiment

Keep testing whether Q4 can reconstruct the structure itself.

```text
CAS text → Q4’s predicted structure
                     ↓
Compare with the compiler’s reference structure
```

Here, the compiler remains the teacher and checker. It must not quietly replace Q4’s wrong prediction with the correct tree.

**The distinction is about what you are trying to measure, not whether using a compiler is allowed.**

If the task is “reconstruct this expression’s tree,” supplying that complete tree would supply the answer. If the task is “perform a supported operation on this supplied structure,” the structure can legitimately be the problem input.

Your actual Q4 task was the first kind: reconstruct the written expression. Its saved predictions were checked against reference trees.  

**Therefore, using the compiler directly would not repair Q4’s historical 0/16 result. It would create a useful separate path while Q4’s learning is improved.**

## 5. The compiler can also make Q4’s feedback more useful

This connects directly to your suggestion about raising the penalty.

Instead of reporting only:

> “Wrong tree.”

a comparison against the compiler’s reference structure could report:

```text
The outer operation is correct.
The left state has the wrong Register.
The right nested branch is missing.
The two operands were exchanged.
```

These are **proposed training diagnostics**, not a claim that the complete feedback system already exists.

That gives CAS SDG a specific job: create more practice examples that expose those distinctions. It also gives the training code a basis for emphasizing particular errors rather than multiplying every penalty equally.

The compiler does not update neural weights by itself. The training code must turn those reference differences into feedback that affects the learned values.

Also, checking that an answer is validly written is not enough. **Q4’s sixteen original outputs were all validly structured, but all were wrong for their respective inputs.** The check must compare the content and relationships, not merely accept the grammar.  

## 6. Sharing the compiler does not mean putting everything inside one giant program

I would share its supported operations and output formats without moving all of CNCM, Helm, PCBA, and the atlas into the compiler file.

The arrangement should be:

**One definition of each supported CAS operation. Clear interfaces for the different users of that operation.**

For example, the atlas should reuse a checked Ohm calculation rather than implement its own slightly different formula. That is already how the recorded atlas integration works. 

Likewise, the compiler should not silently become the authority that changes CNCM’s running state. The runtime still owns execution and commitment. A successfully read expression is not evidence that the requested action happened. The compound-runtime contract already preserves that distinction. 

And each connection should identify the compiler version it used. Your project already preserves an earlier compiler for historical Q3 and PCBA checks while the active compiler contains newer Ohm operations. **Sharing a foundation must not mean silently changing old results whenever the compiler changes.** 

## What I would tell Claude

> **Use the existing CAS compiler as the starting point for the shared CAS representation. Do not build another parser or invent a competing expression format without demonstrating a specific need.**
>
> **Identify the compiler output that preserves original structure, fields, order, nesting, and bindings. Build small, tested connections from that output to the experimental Helm input, Q4 teaching records, CNCM records, and the atlas. Reuse the existing PCBA and Ohm connections.**
>
> **Keep two paths separate: compiler-assisted operation of the system, and experiments measuring what the model learned to do itself. Do not make Q4’s unfinished reconstruction skill block every compiler-to-Helm integration. Do not feed Q4 its reconstruction answer and call that learned reading.**
>
> **Start with one supported expression and one specified question. Demonstrate that the required information survives the entire connection and reaches the model. Preserve historical models and compiler versions. Unsupported meanings remain explicit rather than being guessed.**

**So yes: the CAS compiler can be their shared reader, rule-checker, and calculator. The next design task is not to make every piece learn a different language. It is to make each piece use the compiler’s existing CAS structure correctly, while keeping programmed work and learned work clearly identified.**
