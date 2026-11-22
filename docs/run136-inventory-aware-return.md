# Run 136: inventory-aware preparation return

The full-health hero collected a mandatory golden potion at decision 276.
The existing bank history had been witnessed with amber plus known liquid flame.
Decision 277 rejected every return receipt because the potion inventory tuple
no longer matched. A successful mandatory pickup thus invalidated all remote
preparation options without scheduling a new storage feasibility check.

Return receipts now remain same-floor/same-branch navigation evidence when the
inventory changes. Before using one, a detached policy copy checks known terrain
for bank/water-escape and current-inventory storage feasibility. Only previously
observed terrain participates in the hypothetical reobservation. This check
does not alter real tile visibility, create a new receipt, drop an item, identify
a potion, or permit a drink. Existing transactions cannot be superseded.

The actual return still uses observed hazard-admitted transit, the existing
64-input progress bound and hunger admission, with an increased preparation
reserve for changed inventory. On arrival, current visible bank/storage checks
must pass; every other color is protected through the existing whole-stack
drop/retrieve controller before testing.

Source-pinned offline bookkeeping reproduced all 277 recorded selections
(action, reason, intent and controller). At the terminal observation the
candidate chooses a return step to 968 from 969, targeting remembered bank 254,
rather than exhausting due to inventory mismatch. No game/API replay was run
and no historical observations were consumed after that changed decision.
This establishes an admitted preparation return, not eventual survival.

Independent sequence tests cover the added two-dose color, unchanged real
visibility/history, missing DROP actions, occupied retrieval controllers,
unobserved geometry, route hazards, transit exhaustion, stale arrival rejection
and fresh arrival starting storage before drinking.
