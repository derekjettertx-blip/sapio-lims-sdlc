---
name: lucid-model-reconcile
description: >-
  Reconcile a Lucid ERD/data-model diagram against the code data models in
  webhooks/commons/data_type_models.py and emit a relationship.md that maps
  every diagram entity/field/relationship to its code counterpart, flagging
  contradictions as ⚠️ HUMAN REVIEW. Use when the user asks to "read the
  lucid and create relationship.md", compare a diagram to the data models,
  check the ERD against code, or find where the diagram and code disagree.
---

# Lucid ↔ Code Model Reconciliation

Produce (or refresh) `relationship.md`: a diagram-vs-code cross-check between a **Lucid
ERD** and the Sapio LIMS data models in `webhooks/commons/data_type_models.py`. Every
diagram entity, field, and relationship is matched to code, and anything that disagrees is
flagged **⚠️ HUMAN REVIEW** rather than silently reconciled or "fixed".

This is a **read-and-report** task. Never edit `data_type_models.py` or the diagram to make
them agree — surface the disagreement for a human.

## Inputs

- A Lucid document — the user gives a URL, an id, or a title to search for.
- `webhooks/commons/data_type_models.py` — the auto-generated `WrappedRecordModel` wrappers
  (one class per Sapio Data Type; ~2.9 MB, **too large to read whole** — always target it).
- Optional prior art: `kb/data_type_model_relationships.md` is the code-only relationship
  reference; reuse its caveats and field facts, don't duplicate its work.

## The two hard constraints (state them in the output)

`data_type_models.py` is generated tooling output, so:

1. **`SIDE_LINK` fields do not record their target type in code** — `WrapperField("C_SLFoo",
   FieldType.SIDE_LINK, …)` carries only the field name. Every "→ target" is a **name-based
   inference**, never a proven fact.
2. **Cardinality is not declared** — a `SIDE_LINK` getter typed `Optional[int]` is only
   *-to-one from the declaring side*. Diagram `1:1` / `1:Many` / `M:M` labels can be checked
   for plausibility, not proven.

A "✅ consistent" verdict therefore means "code has a matching relationship-capable field, no
contradicting evidence" — not a hard proof.

## Procedure

1. **Locate the diagram.** `mcp__claude_ai_Lucid__search` by title/keyword if not given a URL.
   Confirm the match with the user if ambiguous.
2. **Size it up, then fetch.** `mcp__claude_ai_Lucid__fetch` with `metadata_only: true` to get
   `page_count` / `page_region_counts`. Then fetch content by `page_index` (and `region_index`
   for large pages). ERD content comes back as JSON with `erds[].entities[]` (each with
   `label`, `attributes[].name`, `attributes[].dataType`) and `erds[].relationships[]` (each
   with `sourceId`, `targetId`, `sourceMultiplicity`, `targetMultiplicity`). Also capture
   `standaloneClusters` — legend boxes (ignore) and sticky notes (business rules → appendix).
   Optionally `lucid_export_document_as_PNG` to eyeball layout.
3. **Map entities → models.** Diagram labels usually drop the `C_` prefix and `Model` suffix,
   and may use display names. For each diagram entity, `Grep` `data_type_models.py` for
   candidate `^class \w*<Name>\w*Model`. Watch for false friends — e.g. a diagram
   "ScientificProject" is **not** `ProjectModel` (`Project`); verify by fields, not name alone.
   Read each matched class's header block (docstring `Fields:` line + the `WrapperField(...)`
   declarations) with a targeted `Read` offset/limit — you don't need the getters/setters.
4. **Diff fields.** Per entity, table the diagram field (+ its diagram dataType) against the
   code field (+ `FieldType`). Classify each: ✅ match · 🟰 cosmetic type/name diff
   (`Text`↔`STRING`, `Int`↔`INTEGER`, `List`/`SelectionList`↔`SELECTION`, `PickList`↔`PICKLIST`,
   `Email Address`↔`STRING`, missing `C_` prefix) · ➕ code-only field · ⚠️ real discrepancy.
   **Type-kind mismatches are contradictions**, e.g. diagram `SideLink` vs code `PICKLIST`.
5. **Diff relationships.** For each diagram edge, resolve `sourceId`/`targetId` to entity
   labels, then find the `SIDE_LINK` field in code that backs it. Note when the **owning side
   is reversed** (link declared on the other entity) — that's a discrepancy, not a match. A
   diagram edge whose target entity or backing field is absent in code is a contradiction.
6. **Flag for review.** An entity, field, or relationship in the diagram with no code
   counterpart — or with a conflicting type/kind — is **⚠️ HUMAN REVIEW**. So is a diagram-side
   error (typo in a dataType, a field shown on an extension that lives on the parent). Do **not**
   escalate purely cosmetic diffs or expected code-only standard columns (`CreatedBy`,
   `DataRecordName`, `DateCreated`, `Velox*`, extension `.*` columns).
7. **Write `relationship.md`** at the repo root using the layout below. Lead with a
   **Summary of items needing human review** table (ID, severity, location, issue) so a human
   sees the conflicts first.

## Output layout (`relationship.md`)

- Header: purpose, diagram source (id + URL + page), code source, generation date, and the
  two hard-constraint caveats.
- **Summary of items needing human review** — `HR-#` rows, severity 🔴/🟠/🟡, ranked worst first.
- **Entity map** — diagram entity → code model (data type) → verdict; call out placeholder/
  legend boxes and code-only siblings not diagrammed.
- **Per-entity field reconciliation** — one small table each, with the ✅/🟰/➕/⚠️ legend.
- **Relationship reconciliation** — one table: `R#`, diagram edge, diagram cardinality, code
  evidence (the `SIDE_LINK` field or "none"), verdict.
- **Appendix** — diagram sticky notes / callouts (business rules, ACL, open questions) verbatim
  with attribution, since they aren't code-representable.
- Footer: note the file is generated and to re-run this skill after either side changes.

## Guardrails

- Read-only against both sources. Never mutate the diagram or the models to force agreement.
- Never invent a `SIDE_LINK` target or a cardinality — mark inferred things as inferred.
- The model file is huge: always `Grep`/targeted-`Read`, never a full read.
- If the user names a diagram that has multiple plausible matches, confirm before proceeding.
- Prefer the live MCP Lucid tools (they use the user's Lucid login); the `LUCID_API_TOKEN`
  REST path in `.env` is only for headless/cron runs without an interactive MCP session.
