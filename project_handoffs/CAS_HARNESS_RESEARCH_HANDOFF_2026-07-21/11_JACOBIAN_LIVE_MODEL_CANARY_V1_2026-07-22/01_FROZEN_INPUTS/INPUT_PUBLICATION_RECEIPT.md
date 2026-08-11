# V1 frozen-input publication receipt

These files were generated from immutable public revisions and reopened by the
actual read-only consumer. They authorize only a future research-shadow
technical execution.

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `model/pythia_160m_model_manifest_v1.json` | 1,157 | `e78edf3255f59a69c03659585da04e6a6ca624c707b1567556180873fd54be17` |
| `model/pythia_160m_model_manifest_v1.json.publication.json` | 405 | `7207dd18ce0a77d49f443007677527dc486d4317318e187a4f96ea11f88f10df` |
| `source/acquisition_v2/jspace_provider_metadata.json` | 5,894 | `8a16fab2fd7b1a268a42759cbde5c0162571e4a4166ac975fe69bbf8a96e39ca` |
| `source/acquisition_v2/jspace_source_attestation.json` | 4,404 | `6a133cae284710669f5a46acb9a990c0c200f64a9213a0a2271555001c031755` |
| `source/acquisition_v2/jspace_source_snapshot_v1.json.verified.publication.json` | 548 | `8e214cc1c8a6869a7fc8b6707693d2f26b80110d20ee979dc13f45f20f641cce` |
| `source/jspace_source_snapshot_v1.json` | 2,152 | `624f9c31208343ca9ea514d1abbd1c8d7a7af953ecd71337ce07e8390189886b` |
| `source/jspace_source_snapshot_v1.json.publication.json` | 486 | `60db401e353edf53f8fbc3faedfae40f056d8dec59ac78fa7dac8124f6d7a609` |
| `tokens_v2/jspace_wikitext_blocks_v1.json` | 975,400 | `9cf4549abfaf6b8e44bce8a2578428d27b45f3e207a32f0472b2f53adeb54b28` |
| `tokens_v2/jspace_wikitext_blocks_v1.json.publication.json` | 666 | `a953a9f3180391f21bfbb4763c47cba8d9df5669e7b3637a650823c4217d1c5f` |

Token Merkle root:
`3c2af26f72738de116aae2cd3d106346eaef9e5a2e41dc71b1ca7485dc1c031f`.

The earlier `source/acquisition/` and `tokens/` publications are retained as
superseded negative-history artifacts. They passed the first contract, but the
first attestation discarded the per-file provider/local comparison details.
They must not be used for V1 execution. The controlling `acquisition_v2` file
retains and revalidates all eleven materialized file identities; `tokens_v2`
binds that stronger marker while preserving the byte-identical token manifest.

The large provider bytes are intentionally not duplicated into OneDrive. The
current local caches are:

- WikiText:
  `C:\tmp\cas-jacobian-v1-hf\hub\datasets--Salesforce--wikitext\snapshots\b08601e04326c79dfdd32d625aee71d232d685c3`
- Pythia:
  `C:\Users\wakil\.cache\huggingface\hub\models--EleutherAI--pythia-160m\snapshots\50f5173d932e8e61f858120bcb800b97af589f46`

The manifests contain every required per-file size/hash so those caches can be
recreated and independently checked. Cache presence alone is not proof;
consumers must re-inventory the bytes.

Important vocabulary distinction: the tokenizer length is `50,277`; the model
embedding/output table has `50,304` rows. Both are correct and have different
roles. Exact input IDs must be below `50,277`; output token indices may range
over the `50,304` model rows.
