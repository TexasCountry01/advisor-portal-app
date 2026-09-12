# Fact Finder PDF Modernization — Analysis & Options
Date: 2026-09-06
Scope: Research document for improving the Fact Finder PDF generation process currently owned by `benefits-software` (legacy Python application, TCPDF-based rendering).

## Executive summary

There are really **two separate problems** tangled together in the current system, and they need two separate fixes:

1. **A content/verbiage maintenance problem** — wording changes yearly, is hardcoded, and is painful to update.
2. **A logic-duplication problem** — the PDF template re-derives/replicates calculation logic that already exists (and is authoritative) elsewhere in `benefits-software`.

A verbiage panel alone (Option A below) only fixes problem #1. Fixing problem #2 requires establishing a **single source of truth for computed facts** that the PDF renderer consumes but never recalculates. The strongest long-term option (Option B) fixes both at once by extracting PDF rendering into a service built on this app's (advisor-portal's) Django stack — while leaving `benefits-software`'s actual calculation engine completely untouched.

This document lays out the problem more precisely, then gives you a tiered set of options — from lowest-risk/incremental to full extraction — plus a PDF-engine comparison, a data-contract pattern to eliminate the logic duplication, and a phased rollout plan that avoids a risky big-bang rewrite.

---

## Root cause breakdown

| Symptom | Root cause |
|---|---|
| Wording is hard to update yearly | Verbiage is hardcoded as string literals inside the PDF template/blade file, mixed with control flow |
| Template logic is "extremely difficult to maintain" | Presentation logic (what text to show) and business logic (conditions for showing it) are not separated |
| Some logic "replicates or recreates" calculation logic | There is no single authoritative "computed facts" contract — the renderer re-derives values/conditions instead of consuming already-computed results |
| TCPDF is undesirable | TCPDF is a low-level, imperative, coordinate-based PDF API — every layout tweak requires code changes; there's no separation between content and layout |
| Previous panel attempt still hard to maintain | A verbiage table alone doesn't fix the *conditional logic* problem — you likely still need code to decide *which* verbiage block applies, and that logic was probably left where it was |

**The key insight:** the verbiage panel you already tried is the right instinct, but it's addressing the *symptom* (wording), not the *cause* (logic duplication + tight coupling between calculation and presentation). Any durable fix needs to also address the second row of that table.

---

## Recommended target architecture: a Fact Finder "Data Contract"

Regardless of which option below you pick, the single highest-leverage change is this:

> `benefits-software`'s calculation engine should emit one versioned, well-defined JSON/dict structure — the **Fact Finder Data Contract** — containing every computed value, flag, and boolean condition the PDF could ever need. The renderer (old or new) is only allowed to consume this structure. It is never allowed to recompute or re-derive anything from raw inputs.

Example shape (illustrative, not literal):

```json
{
  "schema_version": "2026.1",
  "case_id": 1234,
  "plan_year": 2026,
  "member": { "first_name": "...", "workshop_code": "PF" },
  "computed": {
    "eligible_for_fers_supplement": true,
    "survivor_benefit_election": "max",
    "tsp_projection_at_62": 812345.00,
    "show_fehb_into_medicare_paragraph": true,
    "show_special_category_paragraph": false
  },
  "verbiage_context": {
    "retirement_system": "fers",
    "category": "leo"
  }
}
```

With this contract in place:
- The PDF renderer becomes a **pure function**: `render(data_contract, verbiage_templates) -> PDF`. It contains zero business logic.
- Any conditional logic that decides *content selection* (which paragraph to show) can live as **declarative rules** evaluated against `computed`/`verbiage_context` fields — not imperative code.
- You get a natural regression-testing seam: feed the same data contract into old and new renderers and diff the output.
- Historical PDFs remain reproducible — regenerating a 2024 Fact Finder just needs the 2024-dated verbiage + the stored data contract for that case, not the current code.

This is the piece worth prioritizing even before choosing a new PDF library — it's what makes everything else safe and maintainable.

---

## Option A — Verbiage/Rules Panel only (lowest risk, incremental)

**What it is:** Build a content management panel (in this app, using the existing Django/admin patterns already in `advisor-portal`) that manages:
- Versioned verbiage blocks, keyed by a stable identifier (e.g. `fehb_medicare_transition_paragraph`), with an **effective date/plan-year range** so historical wording is preserved.
- Declarative **display rules** per block — simple boolean expressions evaluated against fields from the Data Contract (e.g. `computed.eligible_for_fers_supplement == true`), not free-form code.
- A draft → review → publish workflow (leveraging the `AuditLog` pattern already used elsewhere in this app) so wording changes are tracked and approved before they go live — important since this content has compliance/legal implications.

`benefits-software` calls a small internal read API exposed by this app:
```
POST /api/fact-finder/resolve-content/
body: { "plan_year": 2026, "data_contract": {...} }
response: { "blocks": [ {"key": "...", "text": "...", "order": 1}, ... ] }
```
`benefits-software` still assembles the final PDF via TCPDF, but the *text and the decision of which blocks to include* now live in one governed place instead of scattered in code.

**Pros**
- Smallest change — doesn't touch the calculation engine or the PDF rendering pipeline at all.
- Immediately solves the "wording changes yearly and is painful" pain point.
- Can ship independently and iteratively; low risk of breaking existing PDFs.
- Reuses infrastructure you already have in `advisor-portal` (Django admin, auth, audit logging).

**Cons**
- Doesn't get you off TCPDF.
- Rule evaluation still needs to happen somewhere — if you evaluate rules in `advisor-portal` and just return resolved text, `benefits-software`'s template still needs a matching structural placeholder for every possible block (order, pagination, page-break logic stay in the old code).
- Doesn't fully eliminate the "the template recreates calculation logic" problem — it *centralizes* the decision logic but the two systems must still agree on what the Data Contract contains.

**Best if:** you want a quick, safe win this year, and a full rendering rewrite isn't in the budget yet.

---

## Option B — Extract PDF rendering into a service on this app's stack (recommended long-term)

**What it is:** `benefits-software` keeps 100% ownership of calculations. Once it finishes computing a case, it POSTs the Data Contract to an endpoint in `advisor-portal`:

```
POST /api/fact-finder/render/
body: { "data_contract": {...} }
response: application/pdf (binary) or a signed download URL
```

`advisor-portal` (already the receiving end of documents in this system based on `case_documents/`) renders the actual PDF using a modern HTML/CSS-based engine (see comparison below) and returns the finished file, which `benefits-software` then attaches/uploads exactly as it does today.

This turns PDF generation into a **strangler-fig** migration: you're not rewriting `benefits-software`, you're peeling one well-defined responsibility (rendering) off of it and re-hosting it somewhere better suited to maintain it — content team included.

**Pros**
- Fully removes TCPDF from the equation.
- Templates become HTML + CSS (or a proper templating language) instead of imperative drawing code — dramatically easier for non-engineers to help maintain layout, and for engineers to maintain logic.
- Verbiage panel (Option A) becomes a *natural part of the same app* instead of a cross-system dependency — no API round-trip needed for content resolution, since rendering and content live together.
- You get modern, testable, versioned rendering: same input (Data Contract) always produces the same PDF — trivial to unit test, diff, and regression-test.
- Leverages a stack (Django) your team already knows well and actively maintains, instead of investing further in the legacy Python app.

**Cons**
- Larger effort than Option A — needs a new service/module, an API contract, and a migration period running old and new renderers side-by-side.
- Requires `benefits-software` to change (it must call out to a new endpoint instead of rendering in-process) — some integration work on that side, though scoped narrowly.
- You'll want a validation phase (see rollout plan) before fully cutting over, to avoid subtle formatting regressions.

**Best if:** you're willing to invest moderate effort now to eliminate the underlying pain permanently rather than re-papering over it.

---

## Option C — Hybrid: verbiage panel now, extraction later

Practically, **A and B are not mutually exclusive — A is a subset of B.** A sensible path:

1. Build the Data Contract schema first (small, high-leverage, no UI needed).
2. Build the verbiage/rules panel in `advisor-portal` (Option A) against that schema. Ship it — get the yearly-wording pain resolved now.
3. Once the panel is live and the Data Contract is proven out in production, build the rendering service (Option B) reusing the *same* verbiage/rules data — you're not throwing away Option A's work, you're relocating where rendering happens.

This gives you a real win in the near term without foreclosing the bigger fix.

---

## PDF rendering engine comparison (for Option B)

| Engine | Language | Model | Maintainability | Notes |
|---|---|---|---|---|
| **WeasyPrint** | Python | HTML + CSS → PDF | High | Most natural fit for a Django app; templates are just Django/Jinja HTML templates with CSS for layout (page breaks, headers/footers via `@page` rules). Actively maintained, pure Python (no external binary dependency headaches). **Best default choice.** |
| **ReportLab** | Python | Code-first (draw calls) | Low–Medium | Same imperative drawing-API problem as TCPDF, just in Python. Would not solve the core maintainability complaint. |
| **Playwright/Chromium print-to-PDF** | Python (subprocess/binding) | HTML + CSS → PDF via headless Chrome | High (best fidelity) | Excellent CSS/JS support and pixel-perfect rendering, but adds a browser-engine dependency to deploy/maintain (heavier ops footprint than WeasyPrint). |
| **Prince XML / DocRaptor** | Commercial (HTML+CSS) | HTML + CSS → PDF | High | Best-in-class CSS Paged Media support (running headers, footnotes, complex TOCs) but adds licensing cost or a hosted dependency. |
| **LaTeX (via a Python wrapper)** | LaTeX | Markup → PDF | Medium | Superb typographic control, but a much steeper authoring curve for anyone who isn't already comfortable with LaTeX — likely a poor fit for a content team maintaining yearly wording. |

**Recommendation:** start with **WeasyPrint**. It directly replaces "hardcoded drawing code" with "HTML templates + CSS," which is the single biggest maintainability unlock relative to TCPDF, and it's a native Python library — no extra runtime/binary to manage in deployment. If you hit a specific advanced layout requirement it can't handle (e.g., very complex running headers or footnotes), evaluate Playwright print-to-PDF as a fallback for just that document type.

---

## Handling the "conditional logic" problem specifically

Today, the hardcoded conditionals likely look something like (pseudocode):

```python
if member.retirement_system == 'FERS' and member.years_of_service >= 20 and member.age >= 50:
    text += "Special category verbiage..."
```

The fix is to **externalize the condition, not just the text**, as a declarative rule stored alongside the verbiage block:

```json
{
  "block_key": "special_category_paragraph",
  "condition": "computed.retirement_system == 'FERS' and computed.is_special_category == true",
  "text_2026": "..."
}
```

Two implementation approaches for evaluating `condition`:
1. **Safe expression evaluator** (e.g., a restricted evaluator like `simpleeval`, or a small custom AST-based evaluator) — lets an admin write conditions in the panel without deploying code, while staying safe (no arbitrary code execution).
2. **JSON Logic** (a well-known, safe, declarative rule format with libraries in both Python and JS) — slightly more verbose but battle-tested for exactly this "non-engineers configure business rules safely" use case.

Either way: **the boolean facts referenced in the condition (`is_special_category`, `retirement_system`, etc.) must come from the Data Contract, computed once by the calculation engine — never recalculated in the rule or in the template.** This is what actually kills the duplication problem, not just moving text into a table.

---

## Governance & yearly-change workflow

Since wording changes are seasonal/annual and have compliance implications, the panel (whichever option) should support:
- **Plan-year-scoped content**: never overwrite last year's wording — add a new version effective for the new plan year, keep the old one for regenerating historical documents.
- **Draft → Review → Publish** states, so a second person can approve wording before it goes live (pattern already used for review workflows elsewhere in `advisor-portal`).
- **Audit trail** of who changed what and when (reuse the existing `AuditLog` model/pattern in this app).
- **Preview/sandbox rendering**: let the content owner render a sample PDF with draft wording against a real or synthetic Data Contract before publishing.

---

## Suggested rollout plan (de-risked, incremental)

| Phase | Deliverable | Risk |
|---|---|---|
| 1 | Define the Fact Finder Data Contract schema (version 1) in collaboration with whoever owns the calculation logic today | Low — no production changes |
| 2 | Instrument `benefits-software` to *emit* the Data Contract for every case (log it, don't use it yet) | Low — read-only, non-invasive |
| 3 | Build the verbiage/rules panel in `advisor-portal` (Option A), driven by the Data Contract | Medium — new feature, but isolated |
| 4 | Wire `benefits-software`'s existing TCPDF template to pull resolved text from the new panel via API, replacing hardcoded strings block-by-block | Medium — do this incrementally, block by block, not all at once |
| 5 | Once stable, prototype the WeasyPrint-based rendering service (Option B) using the same Data Contract + verbiage panel | Medium |
| 6 | Run old (TCPDF) and new (WeasyPrint) renderers in parallel for a sample of real cases; diff output (text-extraction diff, not just visual) | Low — parallel run, no cutover yet |
| 7 | Cut over renderer by document type or by workshop code cohort, monitoring for issues, with an easy rollback to the old renderer | Medium, but reversible |
| 8 | Decommission the old TCPDF template once confidence is high | Low, if phases 1–7 were followed |

This avoids ever having a single "big bang" cutover date, which is usually where legacy-replacement projects like this go wrong.

---

## Summary recommendation

1. **Do the Data Contract first** — it's the cheapest step and unlocks everything else, including safer testing of the current TCPDF template as-is.
2. **Build the verbiage/rules panel in `advisor-portal`** (Option A) next — it directly solves your most painful, recurring problem (yearly wording updates) and reuses infrastructure (admin UI, auth, audit logging) you already have.
3. **Treat full PDF-rendering extraction (Option B, WeasyPrint-based) as the follow-on phase**, not a prerequisite — you get to decommission TCPDF on your own timeline once the panel and Data Contract have proven themselves, rather than needing to solve everything at once.
4. **Externalize conditions, not just text** — this is the detail that actually eliminates the "logic duplication" complaint, rather than just relocating the maintenance burden.
