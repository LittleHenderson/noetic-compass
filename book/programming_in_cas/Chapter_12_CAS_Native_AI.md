# Chapter 12: CAS-Native AI

Throughout this book, we have referenced "CAS-Native" AI models. What makes an AI "native" to CAS?

A standard Large Language Model (LLM) is trained to predict the next word. It has no internal concept of "Drive" or "Domain." It simulates these concepts only by mimicking human text.

A **CAS-Native AI** is fundamentally different at the architectural level. It does not predict words directly from words. It predicts *cognitive structure* from context, and then translates that structure into words. 

This chapter introduces the deep-learning architecture required to build a CAS-Native model.

## The Simplex Encoder

In CAS-Native architectures (like the v1 and B3 experimental branches), the input text is not just passed to a standard transformer block. It first passes through a **Simplex Encoder**.

Recall from Chapter 7 that the 40 base cognitive states form a "probability simplex." The encoder maps the user's input onto this 40-dimensional geometry. It asks: "Where is the user's mind currently located within the 40 states?"

Instead of outputting a flat vector of hidden dimensions, the encoder outputs a probability distribution over the CAS states. This grounds the model's understanding in the formal framework before it does any reasoning.

## Fisher-Rao Loss

When training a standard LLM, we use Cross-Entropy Loss to penalize the model when it guesses the wrong word. 

When training a CAS-Native model to predict structural states, Cross-Entropy is insufficient. The distance between `^2^C` (Abstract logic) and `^3^C` (Concrete logic) is not the same as the distance between `^2^C` and `^5^E` (Emotional empathy). 

We use **Fisher-Rao Loss**, a metric from information geometry. Fisher-Rao respects the curved geometry of the cognitive state space. It penalizes the model much harder for making catastrophic structural errors (e.g., responding to grief with operational logic) than for making minor adjacent errors.

## The Typed Fiber Decoder

Once the model has decided on its next structural state (e.g., "I must execute `^5^E_{F4}|f`"), how does it generate the text?

In older architectures, we just used the state as a prompt prefix ("Act like you are in state..."). This is brittle.

Modern CAS-Native designs use a **Typed Fiber Decoder**. The decoder is split into distinct "fibers" or pathways, one for each Domain or Register. 
- If the model is in `^E` (Evaluative), the text generation flows exclusively through the `^E` fiber, which has been fine-tuned strictly on emotional and value-laden vocabulary.
- If it is in `^C` (Cognitive), it flows through the `^C` fiber, ensuring strict logical vocabulary.

This physical separation in the neural architecture guarantees that the model cannot "hallucinate" logical jargon when it is supposed to be expressing empathy. The structure dictates the output at a hardware level.

## SSM / S6 Integration

Recent experiments in CAS-Native design incorporate State Space Models (SSMs like Mamba) rather than pure Transformers.

Transformers struggle with infinite context; they forget the beginning of the conversation. SSMs, particularly the S6 variant, maintain a compressed, rolling state. Because CAS memory is naturally compressed into structural coordinates (Chapter 9), SSMs are an ideal substrate for tracking long-term psychological attractors and maintaining a coherent "personality" over millions of tokens without context-window collapse.

By combining the structural rigor of CAS with the efficient tracking of SSMs, we move closer to AI that possesses genuine, auditable cognitive continuity.