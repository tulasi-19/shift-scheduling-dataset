# Validation summary

**195 / 195 checks passed**

| Group | Check | Status | Detail |
|---|---|---|---|
| schema | holiday_calendar: header matches dictionary | PASS |  |
| schema | holiday_calendar: required fields populated | PASS | 0 empty required cells |
| keys | holiday_calendar: primary key unique (holiday_id) | PASS | 0 duplicates |
| formats | holiday_calendar.holiday_id: ID/format | PASS | 0 mismatches |
| keys | holiday_calendar.holiday_date: unique | PASS |  |
| enums | holiday_calendar.region: allowed values | PASS | 0 outside ['IN-ALL'] |
| enums | holiday_calendar.holiday_type: allowed values | PASS | 0 outside ['PUBLIC'] |
| schema | skills: header matches dictionary | PASS |  |
| schema | skills: required fields populated | PASS | 0 empty required cells |
| keys | skills: primary key unique (skill_id) | PASS | 0 duplicates |
| formats | skills.skill_id: ID/format | PASS | 0 mismatches |
| keys | skills.skill_name: unique | PASS |  |
| enums | skills.skill_category: allowed values | PASS | 0 outside ['FACILITIES', 'IT_OPS', 'LOGISTICS', 'SUPPORT'] |
| enums | skills.is_certification: allowed values | PASS | 0 outside ['0', '1'] |
| schema | shift_templates: header matches dictionary | PASS |  |
| schema | shift_templates: required fields populated | PASS | 0 empty required cells |
| keys | shift_templates: primary key unique (template_id) | PASS | 0 duplicates |
| formats | shift_templates.template_id: ID/format | PASS | 0 mismatches |
| keys | shift_templates.template_code: unique | PASS |  |
| enums | shift_templates.template_code: allowed values | PASS | 0 outside ['A', 'B', 'C'] |
| enums | shift_templates.template_name: allowed values | PASS | 0 outside ['Day', 'Evening', 'Night'] |
| enums | shift_templates.crosses_midnight: allowed values | PASS | 0 outside ['0', '1'] |
| schema | employees: header matches dictionary | PASS |  |
| schema | employees: required fields populated | PASS | 0 empty required cells |
| keys | employees: primary key unique (employee_id) | PASS | 0 duplicates |
| formats | employees.employee_id: ID/format | PASS | 0 mismatches |
| enums | employees.role: allowed values | PASS | 0 outside ['ASSOCIATE', 'HR_PARTNER', 'IT_OPS_PARTNER', 'SENIOR_ASSOCIATE', 'SYSTEM_ADMIN', 'TEAM_LEAD', 'TEAM |
| enums | employees.employment_type: allowed values | PASS | 0 outside ['FULL_TIME', 'PART_TIME'] |
| enums | employees.is_rostered: allowed values | PASS | 0 outside ['0', '1'] |
| enums | employees.primary_shift_code: allowed values | PASS | 0 outside ['A', 'B', 'C'] |
| enums | employees.status: allowed values | PASS | 0 outside ['ACTIVE', 'TERMINATED'] |
| keys | employees.work_email: unique | PASS |  |
| schema | teams: header matches dictionary | PASS |  |
| schema | teams: required fields populated | PASS | 0 empty required cells |
| keys | teams: primary key unique (team_id) | PASS | 0 duplicates |
| formats | teams.team_id: ID/format | PASS | 0 mismatches |
| keys | teams.team_name: unique | PASS |  |
| enums | teams.domain: allowed values | PASS | 0 outside ['FACILITIES', 'IT_OPS', 'LOGISTICS', 'SUPPORT'] |
| enums | teams.status: allowed values | PASS | 0 outside ['ACTIVE', 'INACTIVE'] |
| schema | team_shift_templates: header matches dictionary | PASS |  |
| schema | team_shift_templates: required fields populated | PASS | 0 empty required cells |
| keys | team_shift_templates: primary key unique (team_id+template_id) | PASS | 0 duplicates |
| schema | employee_skills: header matches dictionary | PASS |  |
| schema | employee_skills: required fields populated | PASS | 0 empty required cells |
| keys | employee_skills: primary key unique (employee_id+skill_id) | PASS | 0 duplicates |
| enums | employee_skills.proficiency_level: allowed values | PASS | 0 outside ['1', '2', '3'] |
| schema | coverage_requirements: header matches dictionary | PASS |  |
| schema | coverage_requirements: required fields populated | PASS | 0 empty required cells |
| keys | coverage_requirements: primary key unique (requirement_id) | PASS | 0 duplicates |
| formats | coverage_requirements.requirement_id: ID/format | PASS | 0 mismatches |
| schema | leave_requests: header matches dictionary | PASS |  |
| schema | leave_requests: required fields populated | PASS | 0 empty required cells |
| keys | leave_requests: primary key unique (leave_id) | PASS | 0 duplicates |
| formats | leave_requests.leave_id: ID/format | PASS | 0 mismatches |
| enums | leave_requests.leave_type: allowed values | PASS | 0 outside ['ANNUAL', 'CASUAL', 'SICK', 'UNPAID'] |
| enums | leave_requests.status: allowed values | PASS | 0 outside ['APPROVED', 'CANCELLED', 'REJECTED', 'SUBMITTED'] |
| enums | leave_requests.decision_reason: allowed values | PASS | 0 outside ['COVERAGE_RISK', 'INSUFFICIENT_BALANCE', 'OVERLAPPING_LEAVE', 'WITHIN_POLICY'] |
| schema | leave_request_events: header matches dictionary | PASS |  |
| schema | leave_request_events: required fields populated | PASS | 0 empty required cells |
| keys | leave_request_events: primary key unique (event_id) | PASS | 0 duplicates |
| formats | leave_request_events.event_id: ID/format | PASS | 0 mismatches |
| enums | leave_request_events.from_status: allowed values | PASS | 0 outside ['APPROVED', 'CANCELLED', 'REJECTED', 'SUBMITTED'] |
| enums | leave_request_events.to_status: allowed values | PASS | 0 outside ['APPROVED', 'CANCELLED', 'REJECTED', 'SUBMITTED'] |
| schema | shift_assignments: header matches dictionary | PASS |  |
| schema | shift_assignments: required fields populated | PASS | 0 empty required cells |
| keys | shift_assignments: primary key unique (assignment_id) | PASS | 0 duplicates |
| formats | shift_assignments.assignment_id: ID/format | PASS | 0 mismatches |
| formats | shift_assignments.shift_id: ID/format | PASS | 0 mismatches |
| enums | shift_assignments.status: allowed values | PASS | 0 outside ['ACTIVE', 'CANCELLED', 'SUPERSEDED'] |
| enums | shift_assignments.assignment_source: allowed values | PASS | 0 outside ['MANUAL', 'SCHEDULER', 'SWAP'] |
| schema | assignment_events: header matches dictionary | PASS |  |
| schema | assignment_events: required fields populated | PASS | 0 empty required cells |
| keys | assignment_events: primary key unique (event_id) | PASS | 0 duplicates |
| formats | assignment_events.event_id: ID/format | PASS | 0 mismatches |
| enums | assignment_events.event_type: allowed values | PASS | 0 outside ['CANCELLED_REPLACED', 'CREATED', 'SUPERSEDED_BY_SWAP'] |
| schema | swap_requests: header matches dictionary | PASS |  |
| schema | swap_requests: required fields populated | PASS | 0 empty required cells |
| keys | swap_requests: primary key unique (swap_id) | PASS | 0 duplicates |
| formats | swap_requests.swap_id: ID/format | PASS | 0 mismatches |
| formats | swap_requests.shift_id: ID/format | PASS | 0 mismatches |
| enums | swap_requests.swap_type: allowed values | PASS | 0 outside ['COVER'] |
| enums | swap_requests.reason_code: allowed values | PASS | 0 outside ['FAMILY', 'MEDICAL', 'OTHER', 'PERSONAL', 'TRANSPORT'] |
| enums | swap_requests.status: allowed values | PASS | 0 outside ['APPLIED', 'APPROVED', 'CANCELLED', 'REJECTED', 'REQUESTED'] |
| enums | swap_requests.decision_reason: allowed values | PASS | 0 outside ['ALREADY_ASSIGNED', 'CONSECUTIVE_DAYS', 'INACTIVE', 'ON_LEAVE', 'REST_VIOLATION', 'SKILL_MISMATCH', |
| schema | swap_events: header matches dictionary | PASS |  |
| schema | swap_events: required fields populated | PASS | 0 empty required cells |
| keys | swap_events: primary key unique (event_id) | PASS | 0 duplicates |
| formats | swap_events.event_id: ID/format | PASS | 0 mismatches |
| enums | swap_events.from_status: allowed values | PASS | 0 outside ['APPLIED', 'APPROVED', 'CANCELLED', 'REJECTED', 'REQUESTED'] |
| enums | swap_events.to_status: allowed values | PASS | 0 outside ['APPLIED', 'APPROVED', 'CANCELLED', 'REJECTED', 'REQUESTED'] |
| schema | attendance_events: header matches dictionary | PASS |  |
| schema | attendance_events: required fields populated | PASS | 0 empty required cells |
| keys | attendance_events: primary key unique (attendance_id) | PASS | 0 duplicates |
| formats | attendance_events.attendance_id: ID/format | PASS | 0 mismatches |
| enums | attendance_events.event_type: allowed values | PASS | 0 outside ['ABSENT', 'CLOCK_IN', 'CLOCK_OUT'] |
| enums | attendance_events.source: allowed values | PASS | 0 outside ['BADGE', 'MANUAL', 'MOBILE', 'SYSTEM'] |
| enums | attendance_events.absence_reason: allowed values | PASS | 0 outside ['DOUBLE_BOOKED_CONFLICT', 'NO_SHOW', 'ON_APPROVED_LEAVE', 'SICK_CALL'] |
| schema | coverage_results: header matches dictionary | PASS |  |
| schema | coverage_results: required fields populated | PASS | 0 empty required cells |
| keys | coverage_results: primary key unique (result_id) | PASS | 0 duplicates |
| formats | coverage_results.result_id: ID/format | PASS | 0 mismatches |
| enums | coverage_results.is_holiday: allowed values | PASS | 0 outside ['0', '1'] |
| schema | weekly_hours: header matches dictionary | PASS |  |
| schema | weekly_hours: required fields populated | PASS | 0 empty required cells |
| keys | weekly_hours: primary key unique (employee_id+iso_week) | PASS | 0 duplicates |
| formats | weekly_hours.iso_week: ID/format | PASS | 0 mismatches |
| enums | weekly_hours.scheduled_exceeds_limit: allowed values | PASS | 0 outside ['0', '1'] |
| enums | weekly_hours.worked_exceeds_limit: allowed values | PASS | 0 outside ['0', '1'] |
| schema | leave_balances: header matches dictionary | PASS |  |
| schema | leave_balances: required fields populated | PASS | 0 empty required cells |
| keys | leave_balances: primary key unique (employee_id+leave_type) | PASS | 0 duplicates |
| enums | leave_balances.leave_type: allowed values | PASS | 0 outside ['ANNUAL', 'CASUAL', 'SICK'] |
| keys | FK employees.team_id -> teams.team_id | PASS | 0 orphans |
| keys | FK employees.manager_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK teams.manager_employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK team_shift_templates.team_id -> teams.team_id | PASS | 0 orphans |
| keys | FK team_shift_templates.template_id -> shift_templates.template_id | PASS | 0 orphans |
| keys | FK employee_skills.employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK employee_skills.skill_id -> skills.skill_id | PASS | 0 orphans |
| keys | FK coverage_requirements.team_id -> teams.team_id | PASS | 0 orphans |
| keys | FK coverage_requirements.template_id -> shift_templates.template_id | PASS | 0 orphans |
| keys | FK coverage_requirements.skill_id -> skills.skill_id | PASS | 0 orphans |
| keys | FK leave_requests.employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK leave_requests.decided_by -> employees.employee_id | PASS | 0 orphans |
| keys | FK leave_request_events.leave_id -> leave_requests.leave_id | PASS | 0 orphans |
| keys | FK leave_request_events.actor_employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK shift_assignments.team_id -> teams.team_id | PASS | 0 orphans |
| keys | FK shift_assignments.employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK shift_assignments.template_id -> shift_templates.template_id | PASS | 0 orphans |
| keys | FK shift_assignments.source_swap_id -> swap_requests.swap_id | PASS | 0 orphans |
| keys | FK assignment_events.assignment_id -> shift_assignments.assignment_id | PASS | 0 orphans |
| keys | FK assignment_events.actor_employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK assignment_events.swap_id -> swap_requests.swap_id | PASS | 0 orphans |
| keys | FK swap_requests.requester_employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK swap_requests.counterpart_employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK swap_requests.requester_assignment_id -> shift_assignments.assignment_id | PASS | 0 orphans |
| keys | FK swap_requests.new_assignment_id -> shift_assignments.assignment_id | PASS | 0 orphans |
| keys | FK swap_requests.team_id -> teams.team_id | PASS | 0 orphans |
| keys | FK swap_requests.decided_by -> employees.employee_id | PASS | 0 orphans |
| keys | FK swap_events.swap_id -> swap_requests.swap_id | PASS | 0 orphans |
| keys | FK swap_events.actor_employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK attendance_events.employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK attendance_events.assignment_id -> shift_assignments.assignment_id | PASS | 0 orphans |
| keys | FK coverage_results.requirement_id -> coverage_requirements.requirement_id | PASS | 0 orphans |
| keys | FK coverage_results.team_id -> teams.team_id | PASS | 0 orphans |
| keys | FK coverage_results.template_id -> shift_templates.template_id | PASS | 0 orphans |
| keys | FK coverage_results.skill_id -> skills.skill_id | PASS | 0 orphans |
| keys | FK weekly_hours.employee_id -> employees.employee_id | PASS | 0 orphans |
| keys | FK leave_balances.employee_id -> employees.employee_id | PASS | 0 orphans |
| relations | teams.manager_employee_id has role TEAM_MANAGER | PASS |  |
| relations | requirements/assignments only use shifts the team runs | PASS |  |
| relations | rostered employees have team and primary shift | PASS |  |
| dates | employees: end_date >= hire_date | PASS |  |
| dates | leave: end >= start; decided >= submitted; start >= hire_date | PASS |  |
| dates | leave: cancelled_at only when CANCELLED and after decided_at | PASS |  |
| dates | assignments: end_ts > start_ts, shift_date = date(start_ts), created_at <= start_ts | PASS |  |
| dates | assignments: shift_id matches shift_date + template | PASS |  |
| dates | swaps: requested <= decided <= applied; requested before shift | PASS |  |
| dates | requirements: effective_to >= effective_from | PASS |  |
| dates | requirements: no overlapping effective ranges per team/template/skill | PASS | 0 overlaps |
| arithmetic | leave.days_requested = calendar days - public holidays | PASS |  |
| arithmetic | assignments.scheduled_hours = end_ts - start_ts | PASS |  |
| arithmetic | weekly_hours scheduled/worked reconcile with assignments + attendance | PASS | 0 mismatches |
| arithmetic | weekly_hours.overtime_hours = max(0, worked - cap) | PASS | 0 mismatches |
| arithmetic | weekly_hours hard limit and flags consistent | PASS | 0 mismatches |
| arithmetic | leave_balances: closing = opening - approved | PASS |  |
| arithmetic | leave_balances.approved_days = sum of APPROVED days | PASS |  |
| arithmetic | coverage_results: gap formulas hold | PASS | 0 rows |
| lifecycle | leave events: legal transitions, unbroken chain, last event = status | PASS | illegal=0 broken=0 final_mismatch=0 |
| lifecycle | every leave request has history | PASS |  |
| lifecycle | swap events: unbroken chain, last event = status | PASS | broken=0 final_mismatch=0 |
| lifecycle | every swap request has history | PASS |  |
| lifecycle | assignment events preserve history (CREATED + SUPERSEDED/CANCELLED records) | PASS |  |
| lifecycle | swap history preserved: APPLIED swap -> old row SUPERSEDED + new SWAP row linked | PASS |  |
| lifecycle | non-applied swaps leave the roster untouched | PASS |  |
| duplicates | no duplicate leave requests (employee/start/end/type) | PASS | 0 |
| duplicates | no duplicate attendance event per assignment/type | PASS |  |
| business_rules | detector EMPLOYEE_DOUBLE_BOOKED: finds every ground-truth case, nothing else (precision=1.000, recall=1.000) | PASS | detected=3 ground_truth=3 |
| business_rules | detector APPROVED_LEAVE_OVERLAPS_SHIFT: finds every ground-truth case, nothing else (precision=1.000, recall=1.000) | PASS | detected=3 ground_truth=3 |
| business_rules | detector REQUIRED_SKILL_ABSENT: finds every ground-truth case, nothing else (precision=1.000, recall=1.000) | PASS | detected=19 ground_truth=19 |
| business_rules | detector OVERTIME_CAP_EXCEEDED: finds every ground-truth case, nothing else (precision=1.000, recall=1.000) | PASS | detected=2 ground_truth=2 |
| business_rules | detector SWAP_APPLIED_WITHOUT_APPROVAL: finds every ground-truth case, nothing else (precision=1.000, recall=1.000) | PASS | detected=2 ground_truth=2 |
| duplicates | duplicate (employee, date, shift) ACTIVE assignments equal the labelled double-bookings exactly | PASS | found=3 labelled=3 |
| decision_replay | leave decisions replayed independently (overlap > balance > team concurrency cap) match every recorded decision | PASS | replayed=500 mismatches=0 outcomes={'WITHIN_POLICY': 333, 'OVERLAPPING_LEAVE': 65, 'COVERAGE_RISK': 93, 'INSUF |
| decision_replay | every non-injected swap decision is backed by evidence in the data (reason, manager, team, leave, rest, cap, skill) | PASS | checked=70 unsupported=0 {'APPLIED (approved)': '19/19', 'CANCELLED': '3/3', 'REJECTED ON_LEAVE': '16/16', 'RE |
| business_rules | working-hour rule R6 (>= 11h rest between shifts) holds on ACTIVE rows | PASS | 0 violations |
| business_rules | working-hour rule R7 (<= 6 consecutive days) holds | PASS | 0 violations |
| business_rules | worked hours stay within hard limit except labelled overtime weeks | PASS |  |
| attendance | attendance reconciles: every ACTIVE assignment has IN+OUT or one ABSENT | PASS | 0 unreconciled |
| attendance | no attendance for SUPERSEDED/CANCELLED assignments | PASS |  |
| attendance | attendance_id embeds employee_id and event timestamp | PASS |  |
| attendance | ABSENT(ON_APPROVED_LEAVE) rows equal labelled leave conflicts | PASS | 3 |
| leakage | no ground-truth column exists in any input/derived table | PASS | [] |
| leakage | assignment_source is not a perfect proxy for injected rows (MANUAL also on baseline) | PASS | MANUAL on injected=6, MANUAL on baseline rows=109 |
| coverage | coverage requirements are met or gaps are reported (coverage_results covers every active requirement per shift) | PASS | {'requirement_slots_evaluated': 2010, 'scheduled_gap_rows': 22, 'actual_gap_rows': 59, 'fully_met_pct_schedule |

## Metrics

```json
{
 "coverage": {
  "requirement_slots_evaluated": 2010,
  "scheduled_gap_rows": 22,
  "actual_gap_rows": 59,
  "fully_met_pct_scheduled": 98.91,
  "fully_met_pct_actual": 97.06,
  "skill_gap_rows": 19,
  "headcount_gap_rows": 3
 },
 "overtime": {
  "employee_weeks": 887,
  "weeks_with_overtime": 154,
  "total_overtime_hours": 119.6,
  "weeks_scheduled_over_limit": 2
 },
 "fairness": {
  "mean_weekly_utilisation": 0.736,
  "stdev": 0.247,
  "p10": 0.4,
  "p90": 1.0
 },
 "leave": {
  "by_status": {
   "CANCELLED": 16,
   "APPROVED": 317,
   "REJECTED": 167
  },
  "decision_reasons": {
   "WITHIN_POLICY": 333,
   "OVERLAPPING_LEAVE": 65,
   "COVERAGE_RISK": 93,
   "INSUFFICIENT_BALANCE": 9
  }
 },
 "swaps": {
  "by_status": {
   "APPLIED": 21,
   "REJECTED": 48,
   "CANCELLED": 3
  },
  "decision_reasons": {
   "WITHIN_RULES": 19,
   "REST_VIOLATION": 23,
   "ON_LEAVE": 16,
   "WEEKLY_CAP": 7,
   "SKILL_MISMATCH": 3
  }
 },
 "absences": {
  "SICK_CALL": 34,
  "NO_SHOW": 27,
  "DOUBLE_BOOKED_CONFLICT": 3,
  "ON_APPROVED_LEAVE": 3
 },
 "assignments_by_status": {
  "ACTIVE": 2547,
  "SUPERSEDED": 21,
  "CANCELLED": 4
 },
 "ground_truth": {
  "EMPLOYEE_DOUBLE_BOOKED": {
   "injected": 3,
   "rule_derived": 0,
   "detected": 3,
   "precision": 1.0,
   "recall": 1.0
  },
  "APPROVED_LEAVE_OVERLAPS_SHIFT": {
   "injected": 3,
   "rule_derived": 0,
   "detected": 3,
   "precision": 1.0,
   "recall": 1.0
  },
  "REQUIRED_SKILL_ABSENT": {
   "injected": 2,
   "rule_derived": 17,
   "detected": 19,
   "precision": 1.0,
   "recall": 1.0
  },
  "OVERTIME_CAP_EXCEEDED": {
   "injected": 2,
   "rule_derived": 0,
   "detected": 2,
   "precision": 1.0,
   "recall": 1.0
  },
  "SWAP_APPLIED_WITHOUT_APPROVAL": {
   "injected": 2,
   "rule_derived": 0,
   "detected": 2,
   "precision": 1.0,
   "recall": 1.0
  }
 }
}
```
