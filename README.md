# Workforce Shift-Scheduling Synthetic Dataset

Combines **leave requests, shift coverage, skills and labour constraints** into feasible schedules, with
exceptions, full history, measurable outputs and labelled anomalies. Standard-library Python only.

## Quick start
```bash
# full dataset (2,000 employees, 100 teams, 90 days, 5,000 leave requests) ~21 s
python generate_data.py --employees 2000 --teams 100 --days 90 --leaves 5000 --seed 20261022 --start 2026-01-01 --out dataset
# starter dataset (same generator, smaller scale)
python generate_data.py --employees 200 --teams 10 --days 30 --leaves 500 --seed 20261022 --out starter_dataset
python validate_data.py --dataset dataset            # 195 independent checks
python reproducibility_check.py --dataset dataset    # regenerates twice, compares SHA-256
```
Scale is fully parameterised (`--employees --teams --days --leaves --swaps --absence-rate --inject-scale --formats`).
Every random phase uses its own `random.Random("<seed>:<phase>")` stream, so output is identical across runs and machines.

## Folder layout
| Path | Content |
|---|---|
| `data/*.csv` | 15 input tables (master, transactions, events) |
| `data/derived/*.csv` | 3 derived outputs: `coverage_results`, `weekly_hours` (overtime), `leave_balances` |
| `ground_truth/` | `ground_truth.csv/json` - **kept apart; never join into features** |
| `json/`, `sql/` | same tables as JSON; `schema.sql` (DDL with PK/FK) and `seed.sql` (DDL + INSERTs) |
| `docs/` | `data_dictionary.md/json` (type, required, allowed values, unit, uniqueness, validation rule, FK for every field) |
| `source_manifest.json` | command, seed, parameters, row counts, SHA-256 per file, provenance |
| `validation_summary.md/json`, `reproducibility_report.md` | evidence for Steps 8 and 10 |

## Entities and relationships
```
Team 1─N Employee            Team N─M ShiftTemplate (team_shift_templates)   Employee N─M Skill (employee_skills)
Team 1─N CoverageRequirement N─1 ShiftTemplate ; CoverageRequirement N─0..1 Skill (NULL skill = headcount rule)
Employee 1─N LeaveRequest 1─N leave_request_events            HolidayCalendar (date) reduces required staffing
Employee 1─N ShiftAssignment N─1 Team, N─1 ShiftTemplate ; ShiftAssignment 1─N assignment_events
SwapRequest N─1 requester ShiftAssignment ; SwapRequest 0..1─1 new ShiftAssignment ; SwapRequest 1─N swap_events
Employee 1─N AttendanceEvent N─0..1 ShiftAssignment
Employee 0..1─N Employee (manager_id) ; Team 1─1 manager Employee
```
Optional relationships: `employees.team_id` (HR/IT/admin actors have none), `coverage_requirements.skill_id`, `swap_requests.new_assignment_id`,
`attendance_events.assignment_id`. Effective dating: `employee_skills` (certificate expiry), `coverage_requirements` (15 % of shifts get a mid-window revision),
`employees.hire_date/end_date`, `teams`, `shift_templates`. Lifecycles: leave `SUBMITTED>APPROVED|REJECTED`, `APPROVED>CANCELLED`;
swap `REQUESTED>APPROVED>APPLIED` | `REJECTED` | `CANCELLED`; assignment `ACTIVE>SUPERSEDED|CANCELLED`. **Nothing is overwritten**: every change is a new
event row and swapped/cancelled assignments stay in the table.

**IDs** (zero-padded, immutable): `EMP-000001`, `SHIFT-2026-01-01-A`, `LVE-2026-000001`, `ATT-<employee-id>-<YYYYMMDDTHHMMSS>`, `SWP-2026-000001`
(plus `TEAM-001`, `SKL-001`, `TPL-A`, `REQ-000001`, `ASG-0000001`, `HOL-2026-01-01`).
`SHIFT-...` identifies the **calendar slot** (date + template letter) and is shared by all people on that shift, so the unique row key of
`shift_assignments` is `assignment_id`; the team is a separate column.

## Documented business rules (everything is derived from these, not from independent random labels)
| Rule | Statement |
|---|---|
| R-LV-01/02/03 | Leave is approved unless: it overlaps other approved leave (`OVERLAPPING_LEAVE`), the type allowance is used up (`INSUFFICIENT_BALANCE`; ANNUAL 10, CASUAL 4, SICK 5 days for the window), or approved leave on any day would exceed the team's `max_concurrent_leave` = 20 % of roster (`COVERAGE_RISK`; sick leave bypasses this test). `days_requested` excludes public holidays. |
| Scheduling | Greedy, constraint-aware: satisfy skill minimums first (scarcest skill first), then headcount; prefer the employee's primary shift, then the lowest utilisation (fairness). Holidays use `holiday_min_staff`. |
| R1 | No two ACTIVE assignments of one employee overlap in time. |
| R2 | No ACTIVE assignment on a day covered by APPROVED leave. |
| R3 | Every skill requirement (min >= 1) has a scheduled person whose skill is valid (effective dates) on that day, or the gap is reported in `coverage_results`. |
| R4 | Scheduled weekly hours <= `weekly_hour_cap` (FT 40 / PT 24) + 4 h overtime cap. Overtime = worked - contract cap. |
| R5 | A swap may be APPLIED only after an APPROVED event by the team manager. Manager approves iff the counterpart is active, not on leave, not already working, keeps >= 11 h rest (R6) and <= 6 consecutive days (R7), stays within the weekly cap, and skill coverage does not drop. |
| R6/R7 | >= 11 h rest between shifts; <= 6 consecutive working days. |
| R8 | Attendance reconciles: each ACTIVE assignment has exactly CLOCK_IN+CLOCK_OUT or one ABSENT; SUPERSEDED/CANCELLED assignments have none. |

## Labelled edge cases (`ground_truth/ground_truth.csv`)
| issue_type | How injected (rest of the data stays valid) | Count |
|---|---|---|
| `EMPLOYEE_DOUBLE_BOOKED` | same employee, same slot, second team (cross-team loan) | 30 |
| `APPROVED_LEAVE_OVERLAPS_SHIFT` | extra ACTIVE assignment inside an APPROVED leave | 30 |
| `REQUIRED_SKILL_ABSENT` | skill holders replaced by non-holders (originals kept as CANCELLED rows) | 25 |
| `OVERTIME_CAP_EXCEEDED` | one extra shift on top of an already full week | 25 |
| `SWAP_APPLIED_WITHOUT_APPROVAL` | APPLIED with no APPROVED event (half: never decided, half: REJECTED then applied) | 20 |

`origin` = `INJECTED` (deliberate) or `RULE_DERIVED` (natural skill gaps (a few hundred) from leave/roster limits, reported not hidden).
The injected counts scale with `employees/2000`. Ground truth carries `rule_reference` and `expected_decision` (e.g. `REVERT_SWAP_AND_REQUIRE_APPROVAL`).
Leakage controls: no label columns exist in any data table; `assignment_source=MANUAL` also appears on ~4 % of ordinary rows, so it is not a perfect proxy.

## Results (full dataset; see `validation_summary.md`)
* **195 / 195 validation checks pass**: PK uniqueness, FK integrity (also `PRAGMA foreign_key_check` = 0), enums/ID formats, date ordering, arithmetic
  reconciliation (leave days, hours, weekly totals, overtime, balances, gap formulas), lifecycle chains, duplicates (must equal the labelled double-bookings exactly),
  attendance reconciliation, leakage, and an **independent decision replay**: all 5,000 leave decisions are recomputed from the raw tables in submission order
  (overlap > balance > team concurrency cap) and match; all 700 non-injected swap decisions are checked against evidence in the data (manager, team, leave, rest, consecutive days, weekly cap, skills).
* Independent detectors re-find every injected case: precision = recall = 1.0 for all five types.
* Coverage: 56,520 requirement-slots evaluated; 98.8 % fully met on the schedule, 97.1 % met by people who actually clocked in (gaps listed in `coverage_results.csv`).
* Leave: 4,159 approved / 667 rejected / 174 cancelled. Swaps: 720 requests -> 261 applied, 403 rejected (top reasons REST_VIOLATION, ON_LEAVE, WEEKLY_CAP), 56 cancelled.
* Overtime: 4,749 of 25,304 employee-weeks have some overtime (3,416 h total); 25 weeks scheduled above the hard limit (all labelled).
* **Robustness**: the validator was also run on other seeds (6 full-scale, 12 small); all pass 195 / 195. This found and fixed a timestamp-ordering bug in the injected swap cases.
* **Reproducibility**: two regenerations with seed 20261022 are byte-identical (row counts and SHA-256) to the delivered files.

## Provenance and lawful use
Fully synthetic; no external, scraped or personal data. Emails use the reserved `example.invalid` domain. The holiday list is an
*illustrative* synthetic calendar (modelled on common Indian public holidays) - do not use it as an authoritative holiday source.
No source URLs/licences apply; `source_manifest.json` records `external_sources: []`.

## Known simplifications
* Swaps are one-way **shift covers** (counterpart takes the shift), not two-way exchanges.
* Utilisation is demand-driven, so part-time and low-demand teams show lower hours (mean weekly utilisation 0.73).
* Some leave rejections for `OVERLAPPING_LEAVE` are higher than real life because requests are sampled independently per employee.
* Attendance timestamps use naive local time; weeks at the window edges are partial.

## Suggested next steps (matches your Python -> ML / Django / REST / WebSocket / Webhook path)
1. **Python/pandas**: load `data/*.csv`, rebuild `weekly_hours` yourself and compare with the derived file.
2. **Django**: turn `docs/data_dictionary.md` into models (the FKs are already defined); import the CSVs with a management command.
3. **REST API**: endpoints for leave requests, swap requests, `GET /coverage?team=&date=`.
4. **Webhook**: fire an event when a leave/swap decision is recorded (the `*_events` tables are the payload source).
5. **WebSocket**: push live coverage-gap alerts to a manager dashboard.
6. **ML**: predict `actual_gap` or absence from schedule features; evaluate anomaly detection against `ground_truth/` only (never as input features).
