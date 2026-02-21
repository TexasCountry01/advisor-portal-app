# Implementation Plan: Case Details Page Redesign

## Phase 1: Database Model Changes
- [ ] Add SubCase model to cases/models.py
- [ ] Create migration for SubCase model
- [ ] Add relationship fields to Case model

## Phase 2: View Changes
- [ ] Update case_detail() view to handle sub-cases
- [ ] Create request_modification() view (handles modal pop-up)
- [ ] Update put_case_on_hold() for sub-case compatibility
- [ ] Update accept_case() view to handle sub-case logic

## Phase 3: Template Changes
- [ ] Update case_detail.html - resubmit button logic
- [ ] Create modification request modal template
- [ ] Restructure notes section to dialogue format
- [ ] Hide upload section until after completion

## Phase 4: Styling
- [ ] Add CSS for dialogue-style notes (left/right offset)
- [ ] Style modification modal
- [ ] Add sub-case display styling

## Phase 5: Testing & Validation
- [ ] Test resubmit button visibility by case status
- [ ] Test modification request submission
- [ ] Test sub-case creation and tracking
- [ ] Test notes dialogue display

---

## BLOCKED - AWAITING CLARIFICATION

Before implementing, need answers to:

1. **Sub-case vs Associated Cases**: Confirm sub-case approach is preferred?
2. **Multiple Modifications**: Can a member request multiple modifications on same case?
3. **Due Date Handling**: Should modification inherit original due date or get new one?
4. **Dashboard Display**: Should sub-cases appear in main dashboard queue or separate "Modifications" section?
5. **Assigned Technician**: For modifications, keep same technician or allow reassignment?
6. **Modification Type**: What categories? (new_scenario, fix_mistake, additional_docs, etc.)
7. **Notes Format**: Offset (left/right) or bold/regular text?
8. **Upload Modal**: Same modal for both initial upload and modification requests?

## Current Blockers

- Large codebase (3987 lines in views.py, 864 lines in models.py)
- Need to ensure backward compatibility with existing cases
- Complex business logic around status transitions
- Need migration strategy for existing "resubmitted" cases

**RECOMMENDATION**: Before proceeding with full implementation, clarify the 8 questions above so changes align with exact business requirements.

