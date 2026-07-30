# Data Model ↔ Diagram Reconciliation — `relationship.md`

> **Purpose:** cross-check the Lucid ERD **"Sapio Data Models" → page "Foundation DataModel"**
> against the code models in `webhooks/commons/data_type_models.py`, entity by entity,
> field by field, relationship by relationship. Discrepancies that a human must
> adjudicate are marked **⚠️ HUMAN REVIEW**.
>
> - **Diagram source:** Lucid doc `734123cc-c438-475c-9c9c-e4166bc36bbf`, page `Foundation DataModel` — <https://lucid.app/lucidchart/734123cc-c438-475c-9c9c-e4166bc36bbf/edit?page=0_0>
> - **Code source:** `webhooks/commons/data_type_models.py` (auto-generated sapiopylib `WrappedRecordModel` wrappers, 258 classes)
> - **Generated:** 2026-07-30 · read live from Lucid via MCP + static read of the Python module.

## ⚠️ How to read the relationship / cardinality claims (important caveat)

`data_type_models.py` is generated tooling output. Two limits shape every verdict below —
both confirmed against the existing code-side reference `kb/data_type_model_relationships.md`:

1. **A `SIDE_LINK` field never records its *target* data type in code.** `WrapperField("C_SLChargeAward", FieldType.SIDE_LINK, …)` carries only the field name — the type it points at lives server-side in the Sapio tenant. Every "→ target" below is therefore a **name-based inference**, not a fact read from code.
2. **Cardinality is not declared in code.** Each `SIDE_LINK` getter is typed `Optional[int]` (a single linked record id), i.e. *-to-one from the declaring side*. The diagram's `1:1` / `1:Many` / `Many:Many` labels cannot be *proven* from the wrapper — only checked for plausibility.

So a "✅ consistent" verdict means *"the code has a relationship-capable field whose name matches the diagram edge, with no contradicting evidence"* — not a hard proof of cardinality or target.

---

## Summary of items needing human review

| ID | Severity | Where | Issue |
|----|----------|-------|-------|
| **HR-1** | 🔴 High | `Request.C_ScientificProjects` | Diagram draws a **SideLink** relationship Request → ScientificProject; code field is a **`PICKLIST`**, not a `SIDE_LINK`. Type/relationship contradiction. |
| **HR-2** | 🔴 High | Entity `ScientificProject` | First-class entity in the diagram (with M:M links to User & Department, 1:M from Request), but **no matching data type exists in code**. Only an unrelated `Project`/`ProjectModel` and the picklist field above. |
| **HR-3** | 🔴 High | Entity `Charge` | Diagram entity `Charge` (ChargeID, Units, Unit Prize, Total Prize) with a 1:1 link from Request — **no `Charge` data type or link field exists in code**. |
| **HR-4** | 🟠 Med | `User.Supervisor` | Diagram shows a **SideLink** `Supervisor` field directly on `User`; `VeloxUserModel` has **no such field**. In code the supervisor relation is modeled only via the separate `C_UserSupervisorMapping` junction. |
| **HR-5** | 🟠 Med | `User.Active` | Diagram shows `Active` (Boolean) on `User`; `VeloxUserModel` has **no `Active` field**. |
| **HR-6** | 🟡 Low | Diagram edges R4/R7 (ChargeAward/ChargeProject → BillableAccount) | Relationship exists but the **owning side is reversed**: the `SIDE_LINK` fields live on `BillableAccount` (`C_SLChargeAward`, `C_SLChargeProject`), pointing outward — the diagram draws the arrows the other way. |
| **HR-7** | 🟡 Low | `UserSupervisorMapping.User` | Diagram lists the field's data type as **`Test`** — an apparent typo for `Text`. Diagram-side fix. |
| **HR-8** | 🟡 Low | `CVT.RequestID` | Diagram lists `RequestID` as a field on `CVT`; `C_CVTRequest` has **no `RequestID` field** (CVT is an *extension* of Request — the id lives on the parent Request). |

Everything not listed above reconciled cleanly (see per-entity tables). Type-name cosmetics
(`Text` vs `STRING`, `Int` vs `INTEGER`, `List` vs `SELECTION`, `Email Address` vs `STRING`,
diagram names without the `C_` prefix) are treated as consistent and noted inline, not escalated.

---

## Entity map

| # | Diagram entity | Code model (`data type`) | Verdict |
|---|----------------|--------------------------|---------|
| 1 | `ScientificProject` | — none — (`ProjectModel`/`Project` is a *different* type) | ⚠️ **HR-2** |
| 2 | `UserSupervisorMapping` | `C_UserSupervisorMappingModel` (`C_UserSupervisorMapping`) | ✅ |
| 3 | `BillableAccount` | `C_BillableAccountModel` (`C_BillableAccount`) | ✅ |
| 4 | `Department` | `VeloxDepartmentModel` (`VeloxDepartment`) | ✅ |
| 5 | `ChargeAward` | `C_ChargeAwardModel` (`C_ChargeAward`) | ✅ |
| 6 | `User` | `VeloxUserModel` (`VeloxUser`) | ⚠️ field diffs (HR-4, HR-5) |
| 7 | `ChargeProject` | `C_ChargeProjectModel` (`C_ChargeProject`) | ✅ |
| 8 | `Request` | `RequestModel` (`Request`) | ⚠️ field diff (HR-1) |
| 9 | `CVT` | `C_CVTRequestModel` (`C_CVTRequest`) | ✅ (extension; HR-8) |
| 10 | `Charge` | — none — | ⚠️ **HR-3** |
| 11 | `DepartmentUserMapping` | `C_DepartmentUserMappingModel` (`C_DepartmentUserMapping`) | ✅ |

**Diagram type-category placeholders** (not real entities — legend boxes): `OOB Datatype`,
`ELNDataType`, `Custom Datatype`, `Custom HVDT Datatype`. No reconciliation needed.

**Code-only sibling not diagrammed:** `C_NGSRequestModel` (`C_NGSRequest`, "NGS Request")
is a second Request extension present in code alongside `C_CVTRequest`, but the diagram only
draws CVT. Informational — confirm whether NGS belongs on the diagram.

---

## Per-entity field reconciliation

Legend: ✅ match · 🟰 match, cosmetic type/name difference · ➕ code-only field (not in diagram) · ⚠️ discrepancy for review.

### 1. `ScientificProject` → ⚠️ no code counterpart (HR-2)

Diagram fields: `ProjectKey` (Text), `Name` (Text), `Creator` (List), `Primary Contact` (List), `Status` (Text), `Results Directory` (Text).

`ProjectModel` (data type `Project`) is **not** this entity — its fields are `ProjectId`,
`ProjectName`, `ProjectDesc`, `Leader`, `StartDate`, `EndDate`, `VeloxApprover`… — a different
concept. In code, "ScientificProjects" surfaces **only** as `Request.C_ScientificProjects`
(a `PICKLIST` field). **A human must decide** whether ScientificProject should be a real data
type or is intentionally just a picklist on Request.

### 2. `UserSupervisorMapping` → `C_UserSupervisorMappingModel` ✅

| Diagram field (type) | Code field (`FieldType`) | Note |
|---|---|---|
| SLSupervisor (SideLink) | `C_SLSupervisor` (SIDE_LINK) | ✅ |
| SLUser (SideLink) | `C_SLUser` (SIDE_LINK) | ✅ |
| Supervisor (Text) | `C_Supervisor` (STRING) | 🟰 |
| User (**Test**) | `C_User` (STRING) | ⚠️ **HR-7** — diagram type "Test" ≈ typo for "Text" |

### 3. `BillableAccount` → `C_BillableAccountModel` ✅

| Diagram field (type) | Code field (`FieldType`) | Note |
|---|---|---|
| CrossSystemGUID (Text) | `C_CrossSystemGUID` (STRING) | 🟰 |
| SLChargeProject (SideLink) | `C_SLChargeProject` (SIDE_LINK) | ✅ |
| SLChargeAward (SideLink) | `C_SLChargeAward` (SIDE_LINK) | ✅ |
| IsActive (Boolean) | `C_IsActive` (BOOLEAN) | ✅ |
| Project/Award (Text) | `C_ProjectAndAward` (STRING) | 🟰 |

### 4. `Department` → `VeloxDepartmentModel` ✅

| Diagram field (type) | Code field (`FieldType`) | Note |
|---|---|---|
| Department Name (Text) | `DepartmentName` (STRING) | 🟰 |
| LabCode (Text) | `C_LabCode` (STRING) | 🟰 |
| OrgID (Text) | `C_OrgID` (STRING) | 🟰 |
| CompanyName (Text) | `C_CompanyName` (STRING) | 🟰 |
| CompanyOrgID (Text) | `C_CompanyOrgID` (STRING) | 🟰 |
| CrossSystemGUID (Text) | `C_CrossSystemGUID` (STRING) | 🟰 |
| IsActive (Boolean) | `C_IsActive` (BOOLEAN) | ✅ |
| — | ➕ `InheritRolesFromParent` (BOOLEAN) | code-only |

### 5. `ChargeAward` → `C_ChargeAwardModel` ✅

| Diagram field (type) | Code field (`FieldType`) | Note |
|---|---|---|
| CrossSystemGUID (Text) | `C_CrossSystemGUID` (STRING) | 🟰 |
| Label (Text) | `C_Label` (STRING) | 🟰 |
| AwardNumber (Text) | `C_AwardNumber` (STRING) | 🟰 |
| IsActive (Boolean) | `C_IsActive` (BOOLEAN) | ✅ |

### 6. `User` → `VeloxUserModel` ⚠️

| Diagram field (type) | Code field (`FieldType`) | Note |
|---|---|---|
| FirstName (Text) | `FirstName` (STRING) | ✅ |
| MiddleName (Text) | `MiddleName` (STRING) | ✅ |
| LastName (Text) | `LastName` (STRING) | ✅ |
| Username (Text) | `Username` (STRING) | ✅ |
| EmailAddress (Email Address) | `EmailAddress` (STRING) | 🟰 (diagram "Email Address" → code STRING) |
| JobTitle (Text) | `JobTitle` (STRING) | ✅ |
| PhoneNumber (Long) | `C_PhoneNumber` (LONG) | 🟰 name prefix diff |
| CrossSystemGUID (Text) | `C_CrossSystemGUID` (STRING) | 🟰 |
| EmployeeID (Text) | `C_EmployeeID` (STRING) | 🟰 |
| **Supervisor (SideLink)** | — none — | ⚠️ **HR-4** |
| ActivatedAt (Date) | `C_ActivatedAt` (DATE) | 🟰 |
| **Active (Boolean)** | — none — | ⚠️ **HR-5** |
| — | ➕ `C_LoginName` (STRING) | code-only |

### 7. `ChargeProject` → `C_ChargeProjectModel` ✅

| Diagram field (type) | Code field (`FieldType`) | Note |
|---|---|---|
| CrossSystemGUID (Text) | `C_CrossSystemGUID` (STRING) | 🟰 |
| ProjectNumber (Text) | `C_ProjectNumber` (STRING) | 🟰 |
| Label (Text) | `C_Label` (STRING) | 🟰 |
| IsActive (Boolean) | `C_IsActive` (BOOLEAN) | ✅ |
| SLDepartment (SideLink) | `C_SLDepartment` (SIDE_LINK) | ✅ |
| — | ➕ `C_Department` (STRING) | code-only (text dept alongside the SideLink) |

### 8. `Request` → `RequestModel` ⚠️

Only the diagrammed fields are reconciled; `RequestModel` additionally defines ~35 standard/
extension fields (`Status`, `NumberOfSamples`, `ReceivedDate`, the `C_CVTRequest.*` / `C_NGSRequest.*`
extension columns, TAT fields, etc.) — expected, not escalated.

| Diagram field (type) | Code field (`FieldType`) | Note |
|---|---|---|
| RequestId (Text) | `RequestId` (AUTO_ACCESSION) | 🟰 (auto-accession renders as text) |
| RequestType (PickList) | `C_RequestType` (PICKLIST) | ✅ |
| RequestStatus (PickList) | `C_RequestStatus` (PICKLIST) | ✅ |
| RequestedFor (SelectionList) | `C_RequestedFor` (SELECTION) | 🟰 |
| **ScientificProjects (SideLink)** | `C_ScientificProjects` (**PICKLIST**) | ⚠️ **HR-1** — diagram SideLink vs code PICKLIST |
| Department (SelectionList) | `C_Department` (SELECTION) | 🟰 |
| BillableAccount (SelectionList) | `C_BillableAccount` (SELECTION) | 🟰 |
| RequestDate (Date) | `RequestDate` (DATE) | ✅ |
| Request Name (Text) | `RequestName` (STRING) | 🟰 |

### 9. `CVT` → `C_CVTRequestModel` ✅ (extension)

| Diagram field (type) | Code field (`FieldType`) | Note |
|---|---|---|
| RequestID (Text) | — none — | ⚠️ **HR-8** — not stored on the extension; lives on parent Request |
| NoOfSamples (Int) | `C_NoOfSamples` (INTEGER) | 🟰 |
| — | ➕ `C_Status` (PICKLIST) | code-only |

### 10. `Charge` → ⚠️ no code counterpart (HR-3)

Diagram fields: `ChargeID` (int), `Units` (Int), `Unit Prize` (Decimal), `Total Prize` (Decimal).
No `Charge` / `C_Charge` data type exists in `data_type_models.py`. Note the existing
`ChargeAward` and `ChargeProject` are **different** entities. **A human must decide** whether
`Charge` is unbuilt, renamed, or out of scope.

### 11. `DepartmentUserMapping` → `C_DepartmentUserMappingModel` ✅

| Diagram field (type) | Code field (`FieldType`) | Note |
|---|---|---|
| SLDepartment (SideLink) | `C_SLDepartment` (SIDE_LINK) | ✅ |
| SLUser (SideLink) | `C_SLUser` (SIDE_LINK) | ✅ |
| IsPrimaryDepartment (Boolean) | `C_IsPrimaryDepartment` (BOOLEAN) | ✅ |
| IsDepartmentHead (Boolean) | `C_IsDepartmentHead` (BOOLEAN) | ✅ |
| Department (Text) | `C_Department` (STRING) | 🟰 |
| User (Text) | `C_User` (STRING) | 🟰 |

---

## Relationship reconciliation

Diagram edges (source → target) vs. the `SIDE_LINK` fields found in code. Remember the caveat:
targets are inferred from field names, cardinality is not provable from code.

| # | Diagram edge | Diagram card. | Code evidence | Verdict |
|---|--------------|---------------|---------------|---------|
| R1 | Request → CVT | 1:1 (extension) | `C_CVTRequest` fields surface on `Request` as `C_CVTRequest.*` — an extension, not a link | ✅ consistent |
| R2 | DepartmentUserMapping → Department | 1:1 | `C_DepartmentUserMapping.C_SLDepartment` (SIDE_LINK) | ✅ |
| R3 | DepartmentUserMapping → User | 1:1 | `C_DepartmentUserMapping.C_SLUser` (SIDE_LINK) | ✅ |
| R4 | ChargeAward → BillableAccount | 1:1 | `C_BillableAccount.C_SLChargeAward` (SIDE_LINK) — link on **BillableAccount** side | ⚠️ **HR-6** direction reversed |
| R5 | Request → ScientificProject | 1:Many | `Request.C_ScientificProjects` is a **PICKLIST**; no ScientificProject type | ⚠️ **HR-1 / HR-2** |
| R6 | Request → Charge | 1:1 | no `Charge` type; no link field on Request | ⚠️ **HR-3** |
| R7 | ChargeProject → BillableAccount | 1:1 | `C_BillableAccount.C_SLChargeProject` (SIDE_LINK) — link on **BillableAccount** side | ⚠️ **HR-6** direction reversed |
| R8 | UserSupervisorMapping → User (supervisor) | 1:1 | `C_UserSupervisorMapping.C_SLSupervisor` (SIDE_LINK) | ✅ |
| R9 | UserSupervisorMapping → User (user) | 1:1 | `C_UserSupervisorMapping.C_SLUser` (SIDE_LINK) | ✅ |
| R10 | ScientificProject ↔ User | Many:Many | no ScientificProject type; no junction found | ⚠️ **HR-2** |
| R11 | ScientificProject ↔ Department | Many:Many | no ScientificProject type; no junction found | ⚠️ **HR-2** |
| R12 | ChargeProject → Department | 1:1 | `C_ChargeProject.C_SLDepartment` (SIDE_LINK) | ✅ |

---

## Appendix — diagram annotations (business rules, not code-representable)

Sticky notes / callouts on the diagram, authored by **Siva Rakesh**, captured here so they aren't
lost in reconciliation. These are design intent / open questions — a human should confirm each is
implemented (likely as ACL config or webhook logic, not as fields in `data_type_models.py`):

- **ACL:** "ACL on ScientificProject (SP) propagates to Requests and children."
- **Open question:** "Can a user access records of other departments using searches?"
- **Open question:** "Module + User Profile?"
- **Note:** "User groups are not global records." (with a `User Group` terminator node)

---

*This file is generated. Re-run the `lucid-model-reconcile` skill to regenerate after either the
diagram or `data_type_models.py` changes. Resolve every ⚠️ HUMAN REVIEW row before treating the
diagram and code as in agreement.*
