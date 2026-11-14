# Prompt history

Prompts I sent to Claude (Anthropic) in one chat session, in order. Short prompts are verbatim (typos kept). Pasted terminal output and
screenshots are described in brackets. Claude's replies are not copied here; the full conversation can be exported or shared on request.

**Profile preference set in the chat tool:** "I am beginner learning python programmming. I want learn ML, Django, REST API, Websocket, Webhook. So guide me according to it."

## 1. Task prompt (verbatim)
```
## Problem statement

Read it carefully. Your build should cover every point below.

Business Context / Problem Combine leave requests, shift coverage, skills and labor constraints to create fair and feasible schedules.  Objective and Scope Build a working solution for this end-to-end workflow: Combine leave requests, shift coverage, skills and labor constraints to create fair and feasible schedules. The solution should expose key decisions and exceptions, preserve traceability, and produce measurable outputs. Medium complexity means multiple related entities, conditional rules, at least one exception path and meaningful evaluation metrics.  Primary Actors / Systems Employee/candidate, manager, HR partner, IT/operations partner and system administrator  Business Workflow and Rules 1. Generate/reference master data first: Employee, Team, Skill, ShiftTemplate, ShiftAssignment. 2. Generate dependent transaction/event records using valid parent IDs. 3. Apply business logic: Create teams, skills and shift templates; define minimum staffing per shift and skill; generate leave requests and approval outcomes; create attendance events; assign shifts; handle swaps with manager approval; compute overtime and coverage gaps. 4. Persist state changes as explicit records/events where relevant; do not overwrite history. 5. Generate outcomes and ground-truth labels from documented rules, not independent random assignment.  Entities and Relationships Core entities: Employee, Team, Skill, ShiftTemplate, ShiftAssignment, LeaveRequest, HolidayCalendar, AttendanceEvent, CoverageRequirement, SwapRequest. Define a primary key for every entity and foreign keys for every relationship. Document cardinality (1:1, 1:N, N:M), optional relationships, effective dates and lifecycle states. Use bridge tables for many-to-many relationships; retain event history for state changes; validate all joins. For deliberate anomaly cases, keep an issue_type/ground_truth label rather than silently corrupting unrelated rows.  ID / Nomenclature Conventions EMP-000001; SHIFT-2026-01-01-A; LVE-2026-000001; ATT-<employee-id>-<timestamp>; SWP-2026-000001.  Synthetic Data Generation Instructions (Granular) Step 1 — Write a data dictionary for: Employee, Team, Skill, ShiftTemplate, ShiftAssignment, LeaveRequest, HolidayCalendar, AttendanceEvent, CoverageRequirement, SwapRequest. For each field specify type, required/optional, allowed values, units, uniqueness and validation rule. Step 2 — Create parent/master tables first, then child and event tables. Apply this domain-specific generation logic: Create teams, skills and shift templates; define minimum staffing per shift and skill; generate leave requests and approval outcomes; create attendance events; assign shifts; handle swaps with manager approval; compute overtime and coverage gaps. Step 3 — Apply deterministic IDs and naming: EMP-000001; SHIFT-2026-01-01-A; LVE-2026-000001; ATT-<employee-id>-<timestamp>; SWP-2026-000001. Keep counters zero-padded, IDs immutable, and referenced IDs exactly consistent across files. Step 4 — Generate the baseline volume: Generate 2,000 employees, 100 teams, 90 days of shifts and 5,000 leave requests. Include public holidays, absences, overtime caps and skill-specific staffing requirements. Use a fixed seed (e.g. 20261022) and parameterize scale so starter and full datasets use the same generator. Step 5 — Generate valid baseline records first, then inject labelled edge cases: Employee double-booked; approved leave overlaps assigned shift; required skill absent; overtime cap exceeded; swap applied without approval. Step 6 — Calculate derived values (totals, balances, scores, statuses and dates) from source records rather than generating them independently. Step 7 — Produce a separate ground_truth.csv/json for known anomalies, expected decisions or labels; never leak it into input features. Step 8 — Run validation: primary-key uniqueness, foreign-key integrity, allowed enums, date ordering, arithmetic reconciliation, lifecycle transitions and duplicate checks. Step 9 — Export CSV/JSON/SQL seed data plus README, schema/data dictionary, generator command, fixed seed, source manifest and validation summary. Step 10 — Regenerate twice with the same seed and compare row counts/checksums to demonstrate reproducibility.  Suggested Volume and Coverage Generate 2,000 employees, 100 teams, 90 days of shifts and 5,000 leave requests. Include public holidays, absences, overtime caps and skill-specific staffing requirements.  Required Edge Cases / Negative Scenarios Employee double-booked; approved leave overlaps assigned shift; required skill absent; overtime cap exceeded; swap applied without approval.  Validation Rules / Acceptance Criteria Coverage requirements are met or gaps reported; working-hour constraints hold; attendance reconciles with schedules; swap history is preserved.  Evaluation Focus for Generated Data Review: (a) realistic distributions and meaningful variation; (b) consistent IDs and valid joins; (c) dependency/lifecycle consistency across entities; (d) correct derived values and reconciliation; (e) normal, boundary, failure and exception coverage; (f) separate ground truth; (g) fixed-seed reproducibility, documentation and lawful provenance.  Public Data Guidance / Lawful Use External data is optional. If used, record source URL, dataset/version, retrieval date, license/terms, attribution, transformations and fields discarded. Use only data you are legally permitted to access and redistribute; do not bypass access controls or collect confidential/personal information. If licensing or suitability is unclear, use synthetic data and cite public reference data only for schema inspiration.
```

## 2. Follow-up prompts
| # | Prompt (verbatim or described) |
|---|---|
| 2 | "how to run" |
| 3 | "Where should I open this all" |
| 4 | [Screenshot of VS Code terminal showing `python --version` = 3.10.11] |
| 5 | [Screenshot of terminal showing the reproducibility check PASS] |
| 6 | [Screenshot of VS Code with the project folders open] |
| 7 | "all ok how to run this and check" |
| 8 | "done that's it" |
| 9 | "all completed" |
| 10 | "I want to know all requirements are stastified for this" |
| 11 | "Create a spreadsheet from your last answer." |
| 12 | "it is my task from yottaflex ai from forward deployment engineer so I need to submit and if it is ok I will move to next round otherwise not" |
| 13 | "yes fix" (fix the validator weaknesses Claude had listed) |
| 14 | "how to run this all I have downloaded again" |
| 15 | "ok done" |
| 16 | "how to test this all while it is working properly are not" |
| 17 | [Pasted output of my corrupted-data test: 191/195 checks passed with 4 FAIL lines] |
| 18 | "give that" (asked for the remaining tests) |
| 19 | [Pasted output of running with `--seed 1`] |
| 20 | [Pasted validator output for seed 1: 194/195, swap-event lifecycle failure] -> led to the bug fix |
| 21 | "Tell each and every step I should do know" |
| 22 | "how to test this" |
| 23 | [Pasted output of the final run: generator, 195/195 checks, reproducibility PASS] |
| 24 | "ok know it submit on github" |
| 25 | [Pasted PowerShell error from putting `.gitignore` lines in the terminal] |
| 26 | [Pasted `git init / add / status` output] |
| 27 | [Pasted `git commit` output] |
| 28 | [Pasted YottaFlex submission guidelines] "please make shore and confire me that I have followed are are not according to the project we have done" |
