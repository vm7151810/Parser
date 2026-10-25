# AI Agent & Pair-Programming Transcripts

This directory contains the cleaned, auditable Markdown transcripts of the end-to-end AI collaboration sessions used to build, evaluate, and verify the **Japanese Financial Statement PDF Parser** for UrAI.

---

## 1. Multi-Session Engineering Architecture

To ensure zero-leakage, strict separation of concerns, and mathematical rigor, the project was executed across independent, specialized agent sessions:

```
+-------------------------------------------------------------------------------------------------+
|                                    PHASE 1: CREATION                                            |
+-------------------------------------------------------------------------------------------------+
|  [Session 1: Ground Truth & Eval]                   [Session 2: Inductive Parser]               |
|  - 2-pass human visual transcription                - 12-stage inductive pipeline               |
|  - Minimal parser-agnostic schema                   - Glyph-relative clustering                 |
|  - Baseline evaluation harness                      - Accounting checks engine                  |
+-------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+-------------------------------------------------------------------------------------------------+
|                                    PHASE 2: AUDIT & HARDENING                                   |
+-------------------------------------------------------------------------------------------------+
|  [Session 3: Chat A]  ---> Parser Agnosticism Audit, Ablations & Invariance Testing             |
|  [Session 4: Chat B]  ---> Independent Accounting Verification & Rounding Mathematics           |
|  [Session 5: Chat C]  ---> Evaluator Discrepancy Ledger, Taxonomy, Waivers & Fault Suite       |
|  [Session 6: Chat D]  ---> Formal Normative Specification (SPEC.md v2.1) & 4-Way Consistency    |
+-------------------------------------------------------------------------------------------------+
```

---

## 2. Directory Index of Chat Sessions

| # | File | Session ID | Core Scope & Deliverables |
|---|---|---|---|
| **01** | [`01_creation_eval_ground_truth.md`](01_creation_eval_ground_truth.md) | `23451162` | **Ground Truth & Baseline Eval**: Transcribed `eval/gold.json` visually from 200 DPI image; authored `transcription_log.md` and initial evaluation harness. |
| **02** | [`02_creation_parser_pipeline.md`](02_creation_parser_pipeline.md) | `761b43c2` | **Parser Engineering**: Built the 12-stage inductive pipeline (`parser/`), column detection, indent clustering, triplet pairing, and CLI (`main.py`). |
| **03** | [`03_audit_chat_a_parser_agnosticism.md`](03_audit_chat_a_parser_agnosticism.md) | `4462182d` | **Audit A (Agnosticism)**: Eliminated hardcoded page assumptions; ran ablations and in-memory coordinate invariance tests; generalized dynamic subtotal addends. |
| **04** | [`04_audit_chat_b_accounting_verification.md`](04_audit_chat_b_accounting_verification.md) | `d62f7b15` | **Audit B (Accounting)**: Reconciled all 10 accounting checks independently; investigated directional truncation vs symmetric rounding; proved non-gating diagnostic rule. |
| **05** | [`05_audit_chat_c_evaluator_discrepancy_ledger.md`](05_audit_chat_c_evaluator_discrepancy_ledger.md) | `7a59a704` | **Audit C (Discrepancy Ledger)**: Implemented closed taxonomy, waiver file ingestion, exit codes, and 18-scenario fault injection suite in `eval/evaluate.py`. |
| **06** | [`06_audit_chat_d_specification_audit.md`](06_audit_chat_d_specification_audit.md) | `4036f768` | **Audit D (Normative Spec)**: Authored normative `eval/SPEC.md v2.1`, decision log, claims verification table, and synchronized all project documentation. |

---

## 3. Transcript Cleaning & Curation Protocol

To provide an optimal evaluation experience without hiding technical details, the raw JSONL event streams have been formatted according to the following protocol:
1. **Preserved Prompt Integrity**: All user requests, engineering constraints, edge-case directions, and architectural questions are preserved verbatim (minus internal system envelope tags `<USER_REQUEST>`, `<ADDITIONAL_METADATA>`).
2. **Preserved Engineering Rationale**: Assistant implementation plans, architectural trade-off evaluations, mathematical analyses, and post-execution summaries are fully retained.
3. **Cleaned Execution Traces**: Raw file-view dumps and repetitive terminal logs were condensed into concise command-and-output blocks, highlighting pytest results, git commits, and file modifications.
4. **Noise Removal**: Transient system compactions, hook block notices, and immediate one-off syntax fixes were omitted to maintain focus on the core engineering dialogue.
