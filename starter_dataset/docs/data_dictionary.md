# Data dictionary

Generated from the single dictionary inside `generate_data.py`. `PK` = primary key (composite when several fields carry it), `FK` = foreign key, `ENUM:` lists allowed values, `FMT:` is a regex. All timestamps are naive local time. Required = NOT NULL.

## holiday_calendar  (HolidayCalendar)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `holiday_id` | string | Y | FMT:^HOL-\d{4}-\d{2}-\d{2}$ | - | PK | - | HOL-<holiday_date>; immutable |
| `holiday_date` | date | Y | ISO-8601 date | - | UNIQUE | - | inside generated window; one row per date |
| `holiday_name` | string | Y | free text | - | - | - | non-empty; synthetic/illustrative calendar |
| `region` | string | Y | ENUM:IN-ALL | - | - | - | single national calendar |
| `holiday_type` | string | Y | ENUM:PUBLIC | - | - | - | public holidays use coverage_requirements.holiday_min_staff |

## skills  (Skill)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `skill_id` | string | Y | FMT:^SKL-\d{3}$ | - | PK | - | SKL-001 upward; immutable |
| `skill_name` | string | Y | free text | - | UNIQUE | - | non-empty |
| `skill_category` | string | Y | ENUM:SUPPORT,IT_OPS,LOGISTICS,FACILITIES | - | - | - | equals the team.domain that uses the skill |
| `is_certification` | bool | Y | ENUM:0,1 | - | - | - | 1 = certificate that can expire (employee_skills.effective_to) |

## shift_templates  (ShiftTemplate)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `template_id` | string | Y | FMT:^TPL-[ABC]$ | - | PK | - | TPL-<template_code> |
| `template_code` | string | Y | ENUM:A,B,C | - | UNIQUE | - | letter used inside shift_id |
| `template_name` | string | Y | ENUM:Day,Evening,Night | - | - | - | - |
| `start_time` | time | Y | HH:MM 24h | local time | - | - | - |
| `end_time` | time | Y | HH:MM 24h | local time | - | - | (end - start) mod 24h = duration_hours |
| `crosses_midnight` | bool | Y | ENUM:0,1 | - | - | - | 1 iff end_time < start_time |
| `duration_hours` | float | Y | 8.0 | hours | - | - | > 0; paid hours of one shift |
| `effective_from` | date | Y | ISO-8601 date | - | - | - | <= first schedule day |
| `effective_to` | date | N | ISO-8601 date | - | - | - | NULL = open ended; >= effective_from |

## employees  (Employee)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `employee_id` | string | Y | FMT:^EMP-\d{6}$ | - | PK | - | EMP-000001 upward; immutable |
| `team_id` | string | N | TEAM-NNN | - | - | teams.team_id | NULL for HR/IT/admin actors; required when is_rostered=1 |
| `manager_id` | string | N | EMP-NNNNNN | - | - | employees.employee_id | team manager of the employee; NULL for managers/partners |
| `role` | string | Y | ENUM:TEAM_MANAGER,TEAM_LEAD,SENIOR_ASSOCIATE,ASSOCIATE,HR_PARTNER,IT_OPS_PARTNER,SYSTEM_ADMIN | - | - | - | actor roles of the problem statement |
| `employment_type` | string | Y | ENUM:FULL_TIME,PART_TIME | - | - | - | drives weekly_hour_cap |
| `is_rostered` | bool | Y | ENUM:0,1 | - | - | - | 1 = can receive shift assignments |
| `primary_shift_code` | string | N | ENUM:A,B,C | - | - | - | NULL when is_rostered=0; must be a shift the team runs |
| `weekly_hour_cap` | float | Y | 40.0 or 24.0 | hours/week | - | - | contract hours: FULL_TIME 40, PART_TIME 24 |
| `overtime_cap_hours` | float | Y | 4.0 | hours/week | - | - | hard limit = weekly_hour_cap + overtime_cap_hours |
| `hire_date` | date | Y | ISO-8601 date | - | - | - | no assignment/leave before hire_date |
| `end_date` | date | N | ISO-8601 date | - | - | - | NULL = still employed; >= hire_date |
| `status` | string | Y | ENUM:ACTIVE,TERMINATED | - | - | - | TERMINATED iff end_date is not NULL |
| `work_email` | string | Y | emp-NNNNNN@example.invalid | - | UNIQUE | - | synthetic, non-routable |

## teams  (Team)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `team_id` | string | Y | FMT:^TEAM-\d{3}$ | - | PK | - | TEAM-001 upward; immutable |
| `team_name` | string | Y | free text | - | UNIQUE | - | non-empty |
| `domain` | string | Y | ENUM:SUPPORT,IT_OPS,LOGISTICS,FACILITIES | - | - | - | selects the 3-skill pool of the team |
| `manager_employee_id` | string | Y | EMP-NNNNNN | - | - | employees.employee_id | role must be TEAM_MANAGER; approves leave and swaps |
| `max_concurrent_leave` | int | Y | >=1 | people | - | - | rule R-LV-03: approved leave per day may not exceed this |
| `effective_from` | date | Y | ISO-8601 date | - | - | - | - |
| `effective_to` | date | N | ISO-8601 date | - | - | - | NULL = open ended |
| `status` | string | Y | ENUM:ACTIVE,INACTIVE | - | - | - | - |

## team_shift_templates  ((bridge) Team N:M ShiftTemplate)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `team_id` | string | Y | TEAM-NNN | - | PK | teams.team_id | bridge team N:M shift_template |
| `template_id` | string | Y | TPL-X | - | PK | shift_templates.template_id | shift runs for this team |
| `effective_from` | date | Y | ISO-8601 date | - | - | - | - |

## employee_skills  ((bridge) Employee N:M Skill)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `employee_id` | string | Y | EMP-NNNNNN | - | PK | employees.employee_id | bridge employee N:M skill |
| `skill_id` | string | Y | SKL-NNN | - | PK | skills.skill_id | - |
| `proficiency_level` | int | Y | ENUM:1,2,3 | level | - | - | 1 basic, 3 expert |
| `effective_from` | date | Y | ISO-8601 date | - | - | - | skill counts only from this date |
| `effective_to` | date | N | ISO-8601 date | - | - | - | certificate expiry; NULL = does not expire; >= effective_from |

## coverage_requirements  (CoverageRequirement)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `requirement_id` | string | Y | FMT:^REQ-\d{6}$ | - | PK | - | REQ-000001 upward; immutable |
| `team_id` | string | Y | TEAM-NNN | - | - | teams.team_id | - |
| `template_id` | string | Y | TPL-X | - | - | shift_templates.template_id | must be a shift the team runs |
| `skill_id` | string | N | SKL-NNN | - | - | skills.skill_id | NULL = headcount requirement (any skill) |
| `min_staff` | int | Y | >=1 | people per shift | - | - | minimum scheduled people (with the skill if skill_id set) |
| `holiday_min_staff` | int | Y | >=1, <= min_staff | people per shift | - | - | applies on public holidays |
| `effective_from` | date | Y | ISO-8601 date | - | - | - | ranges for the same team/template/skill never overlap |
| `effective_to` | date | N | ISO-8601 date | - | - | - | NULL = open ended |

## leave_requests  (LeaveRequest)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `leave_id` | string | Y | FMT:^LVE-\d{4}-\d{6}$ | - | PK | - | LVE-<schedule year>-<counter>, counter in submission order |
| `employee_id` | string | Y | EMP-NNNNNN | - | - | employees.employee_id | rostered employee |
| `leave_type` | string | Y | ENUM:ANNUAL,SICK,CASUAL,UNPAID | - | - | - | - |
| `start_date` | date | Y | ISO-8601 date | - | - | - | >= hire_date |
| `end_date` | date | Y | ISO-8601 date | - | - | - | >= start_date |
| `days_requested` | int | Y | >=0 | days | - | - | derived: calendar days start..end minus public holidays |
| `status` | string | Y | ENUM:SUBMITTED,APPROVED,REJECTED,CANCELLED | - | - | - | equals to_status of the last leave_request_events row |
| `submitted_at` | datetime | Y | ISO-8601 | local time | - | - | - |
| `decided_at` | datetime | N | ISO-8601 | local time | - | - | >= submitted_at; NULL while SUBMITTED |
| `decided_by` | string | N | EMP-NNNNNN | - | - | employees.employee_id | team manager |
| `decision_reason` | string | N | ENUM:WITHIN_POLICY,INSUFFICIENT_BALANCE,COVERAGE_RISK,OVERLAPPING_LEAVE | - | - | - | rule code that produced the decision |
| `cancelled_at` | datetime | N | ISO-8601 | local time | - | - | only when status=CANCELLED; > decided_at |

## leave_request_events  ((event history) LeaveRequest)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `event_id` | string | Y | FMT:^LEVT-\d{7}$ | - | PK | - | - |
| `leave_id` | string | Y | LVE-YYYY-NNNNNN | - | - | leave_requests.leave_id | - |
| `from_status` | string | N | ENUM:SUBMITTED,APPROVED,REJECTED,CANCELLED | - | - | - | NULL only for the first event |
| `to_status` | string | Y | ENUM:SUBMITTED,APPROVED,REJECTED,CANCELLED | - | - | - | legal: NULL>SUBMITTED, SUBMITTED>APPROVED/REJECTED, APPROVED>CANCELLED |
| `event_ts` | datetime | Y | ISO-8601 | local time | - | - | non-decreasing per leave |
| `actor_employee_id` | string | Y | EMP-NNNNNN | - | - | employees.employee_id | requester or manager |

## shift_assignments  (ShiftAssignment)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `assignment_id` | string | Y | FMT:^ASG-\d{7}$ | - | PK | - | surrogate key; one row per employee per shift |
| `shift_id` | string | Y | FMT:^SHIFT-\d{4}-\d{2}-\d{2}-[ABC]$ | - | - | - | SHIFT-<date>-<template_code>; identifies the calendar slot (many assignments share it) |
| `team_id` | string | Y | TEAM-NNN | - | - | teams.team_id | team whose requirement the employee covers |
| `employee_id` | string | Y | EMP-NNNNNN | - | - | employees.employee_id | - |
| `template_id` | string | Y | TPL-X | - | - | shift_templates.template_id | - |
| `shift_date` | date | Y | ISO-8601 date | - | - | - | date the shift starts; must match shift_id |
| `start_ts` | datetime | Y | ISO-8601 | local time | - | - | shift_date + template start_time |
| `end_ts` | datetime | Y | ISO-8601 | local time | - | - | > start_ts |
| `scheduled_hours` | float | Y | 8.0 | hours | - | - | derived: (end_ts - start_ts) in hours |
| `status` | string | Y | ENUM:ACTIVE,SUPERSEDED,CANCELLED | - | - | - | history is kept: swapped/cancelled rows are never deleted |
| `assignment_source` | string | Y | ENUM:SCHEDULER,MANUAL,SWAP | - | - | - | MANUAL also occurs on ordinary rows |
| `source_swap_id` | string | N | SWP-YYYY-NNNNNN | - | - | swap_requests.swap_id | set when assignment_source=SWAP |
| `created_at` | datetime | Y | ISO-8601 | local time | - | - | <= start_ts |

## assignment_events  ((event history) ShiftAssignment)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `event_id` | string | Y | FMT:^AEV-\d{7}$ | - | PK | - | - |
| `assignment_id` | string | Y | ASG-NNNNNNN | - | - | shift_assignments.assignment_id | - |
| `event_type` | string | Y | ENUM:CREATED,SUPERSEDED_BY_SWAP,CANCELLED_REPLACED | - | - | - | - |
| `event_ts` | datetime | Y | ISO-8601 | local time | - | - | - |
| `actor_employee_id` | string | N | EMP-NNNNNN | - | - | employees.employee_id | manager who changed the roster |
| `swap_id` | string | N | SWP-YYYY-NNNNNN | - | - | swap_requests.swap_id | set for swap-related events |

## swap_requests  (SwapRequest)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `swap_id` | string | Y | FMT:^SWP-\d{4}-\d{6}$ | - | PK | - | SWP-<schedule year>-<counter>, counter in request order |
| `requester_employee_id` | string | Y | EMP-NNNNNN | - | - | employees.employee_id | current owner of the assignment |
| `counterpart_employee_id` | string | Y | EMP-NNNNNN | - | - | employees.employee_id | teammate asked to take the shift; != requester |
| `requester_assignment_id` | string | Y | ASG-NNNNNNN | - | - | shift_assignments.assignment_id | the assignment handed over |
| `new_assignment_id` | string | N | ASG-NNNNNNN | - | - | shift_assignments.assignment_id | assignment created for the counterpart; only when APPLIED |
| `team_id` | string | Y | TEAM-NNN | - | - | teams.team_id | - |
| `shift_id` | string | Y | FMT:^SHIFT-\d{4}-\d{2}-\d{2}-[ABC]$ | - | - | - | slot being covered |
| `shift_date` | date | Y | ISO-8601 date | - | - | - | - |
| `swap_type` | string | Y | ENUM:COVER | - | - | - | one-way shift cover (counterpart takes the shift) |
| `reason_code` | string | Y | ENUM:PERSONAL,MEDICAL,FAMILY,TRANSPORT,OTHER | - | - | - | - |
| `status` | string | Y | ENUM:REQUESTED,APPROVED,REJECTED,CANCELLED,APPLIED | - | - | - | equals to_status of the last swap_events row |
| `requested_at` | datetime | Y | ISO-8601 | local time | - | - | before shift start |
| `decided_at` | datetime | N | ISO-8601 | local time | - | - | >= requested_at; NULL if no manager decision exists |
| `decided_by` | string | N | EMP-NNNNNN | - | - | employees.employee_id | team manager |
| `decision_reason` | string | N | ENUM:WITHIN_RULES,INACTIVE,ON_LEAVE,ALREADY_ASSIGNED,REST_VIOLATION,CONSECUTIVE_DAYS,WEEKLY_CAP,SKILL_MISMATCH | - | - | - | first failed rule, or WITHIN_RULES |
| `applied_at` | datetime | N | ISO-8601 | local time | - | - | >= decided_at; only when APPLIED |

## swap_events  ((event history) SwapRequest)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `event_id` | string | Y | FMT:^SWE-\d{6}$ | - | PK | - | - |
| `swap_id` | string | Y | SWP-YYYY-NNNNNN | - | - | swap_requests.swap_id | - |
| `from_status` | string | N | ENUM:REQUESTED,APPROVED,REJECTED,CANCELLED,APPLIED | - | - | - | NULL only for the first event |
| `to_status` | string | Y | ENUM:REQUESTED,APPROVED,REJECTED,CANCELLED,APPLIED | - | - | - | legal: NULL>REQUESTED, REQUESTED>APPROVED/REJECTED/CANCELLED, APPROVED>APPLIED |
| `event_ts` | datetime | Y | ISO-8601 | local time | - | - | non-decreasing per swap |
| `actor_employee_id` | string | Y | EMP-NNNNNN | - | - | employees.employee_id | requester or manager |

## attendance_events  (AttendanceEvent)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `attendance_id` | string | Y | FMT:^ATT-EMP-\d{6}-\d{8}T\d{6}$ | - | PK | - | ATT-<employee_id>-<YYYYMMDDTHHMMSS of event_ts> |
| `employee_id` | string | Y | EMP-NNNNNN | - | - | employees.employee_id | - |
| `assignment_id` | string | N | ASG-NNNNNNN | - | - | shift_assignments.assignment_id | always an ACTIVE assignment in this dataset |
| `event_type` | string | Y | ENUM:CLOCK_IN,CLOCK_OUT,ABSENT | - | - | - | each ACTIVE assignment has CLOCK_IN+CLOCK_OUT or one ABSENT |
| `event_ts` | datetime | Y | ISO-8601 | local time | - | - | CLOCK_OUT > CLOCK_IN |
| `source` | string | Y | ENUM:BADGE,MOBILE,MANUAL,SYSTEM | - | - | - | ABSENT rows use SYSTEM |
| `absence_reason` | string | N | ENUM:SICK_CALL,NO_SHOW,ON_APPROVED_LEAVE,DOUBLE_BOOKED_CONFLICT | - | - | - | only for ABSENT |
| `variance_minutes` | int | N | integer | minutes | - | - | derived: CLOCK_IN - scheduled start, CLOCK_OUT - scheduled end; NULL for ABSENT |

## coverage_results  ((derived) CoverageRequirement result)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `result_id` | string | Y | FMT:^CRES-\d{7}$ | - | PK | - | derived output, not an input feature table |
| `requirement_id` | string | Y | REQ-NNNNNN | - | - | coverage_requirements.requirement_id | requirement active on shift_date |
| `team_id` | string | Y | TEAM-NNN | - | - | teams.team_id | - |
| `shift_id` | string | Y | SHIFT-YYYY-MM-DD-X | - | - | - | - |
| `shift_date` | date | Y | ISO-8601 date | - | - | - | - |
| `template_id` | string | Y | TPL-X | - | - | shift_templates.template_id | - |
| `skill_id` | string | N | SKL-NNN | - | - | skills.skill_id | NULL = headcount |
| `is_holiday` | bool | Y | ENUM:0,1 | - | - | - | shift_date in holiday_calendar |
| `required_staff` | int | Y | >=1 | people | - | - | holiday_min_staff if is_holiday else min_staff |
| `scheduled_staff` | int | Y | >=0 | people | - | - | ACTIVE assignments in the slot (with the skill valid on the date) |
| `present_staff` | int | Y | >=0 | people | - | - | scheduled people with a CLOCK_IN |
| `scheduled_gap` | int | Y | >=0 | people | - | - | max(0, required - scheduled) |
| `actual_gap` | int | Y | >=0 | people | - | - | max(0, required - present) |

## weekly_hours  ((derived) weekly hours / overtime)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `employee_id` | string | Y | EMP-NNNNNN | - | PK | employees.employee_id | derived; one row per employee-week with activity |
| `iso_week` | string | Y | FMT:^\d{4}-W\d{2}$ | - | PK | - | ISO week of shift_date |
| `week_start` | date | Y | ISO-8601 date | - | - | - | Monday of the ISO week |
| `scheduled_hours` | float | Y | >=0 | hours | - | - | sum of ACTIVE scheduled_hours in the week |
| `worked_hours` | float | Y | >=0 | hours | - | - | sum of CLOCK_OUT - CLOCK_IN |
| `contract_cap_hours` | float | Y | >0 | hours | - | - | employees.weekly_hour_cap |
| `overtime_cap_hours` | float | Y | >=0 | hours | - | - | employees.overtime_cap_hours |
| `hard_limit_hours` | float | Y | >0 | hours | - | - | contract_cap + overtime_cap |
| `overtime_hours` | float | Y | >=0 | hours | - | - | max(0, worked_hours - contract_cap) |
| `scheduled_exceeds_limit` | bool | Y | ENUM:0,1 | - | - | - | scheduled_hours > hard_limit_hours |
| `worked_exceeds_limit` | bool | Y | ENUM:0,1 | - | - | - | worked_hours > hard_limit_hours |

## leave_balances  ((derived) leave balance)

| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |
|---|---|---|---|---|---|---|---|
| `employee_id` | string | Y | EMP-NNNNNN | - | PK | employees.employee_id | derived |
| `leave_type` | string | Y | ENUM:ANNUAL,SICK,CASUAL | - | PK | - | UNPAID has no balance |
| `opening_balance_days` | int | Y | >=0 | days | - | - | allowance for the generated window |
| `approved_days` | int | Y | >=0 | days | - | - | sum days_requested of APPROVED leaves of that type |
| `closing_balance_days` | int | Y | >=0 | days | - | - | opening - approved |
