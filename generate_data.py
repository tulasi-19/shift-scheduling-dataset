#!/usr/bin/env python3
"""
generate_data.py  -  Synthetic workforce-scheduling dataset generator.

Standard library only (Python 3.9+).  Deterministic: the same --seed and
parameters always produce byte-identical files.

Pipeline (mirrors the problem statement):
  1. master data  : holidays, skills, shift templates, teams, employees, employee_skills,
                    coverage requirements
  2. transactions : leave requests + rule-based approvals -> shift assignments -> swaps
  3. injections   : 5 labelled edge cases (never silently corrupting other rows)
  4. events       : attendance, assignment/leave/swap history (state changes are new rows)
  5. derived      : coverage_results, weekly_hours (overtime), leave_balances
  6. outputs      : CSV, JSON, SQL seed, data dictionary, ground truth, manifest

Example:
  python generate_data.py --employees 2000 --teams 100 --days 90 --leaves 5000 \
      --seed 20261022 --start 2026-01-01 --out dataset
"""
import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta

# --------------------------------------------------------------------------------------
# DATA DICTIONARY  (single source of truth: drives docs, SQL DDL and the validator)
# columns: table|field|type|required|allowed|unit|unique|foreign_key|validation_rule
# allowed: ENUM:a,b,c  or  FMT:<regex>  or free text.   unique: PK | UNIQUE | -
# --------------------------------------------------------------------------------------
DICT_TEXT = r"""
holiday_calendar|holiday_id|string|Y|FMT:^HOL-\d{4}-\d{2}-\d{2}$|-|PK|-|HOL-<holiday_date>; immutable
holiday_calendar|holiday_date|date|Y|ISO-8601 date|-|UNIQUE|-|inside generated window; one row per date
holiday_calendar|holiday_name|string|Y|free text|-|-|-|non-empty; synthetic/illustrative calendar
holiday_calendar|region|string|Y|ENUM:IN-ALL|-|-|-|single national calendar
holiday_calendar|holiday_type|string|Y|ENUM:PUBLIC|-|-|-|public holidays use coverage_requirements.holiday_min_staff
skills|skill_id|string|Y|FMT:^SKL-\d{3}$|-|PK|-|SKL-001 upward; immutable
skills|skill_name|string|Y|free text|-|UNIQUE|-|non-empty
skills|skill_category|string|Y|ENUM:SUPPORT,IT_OPS,LOGISTICS,FACILITIES|-|-|-|equals the team.domain that uses the skill
skills|is_certification|bool|Y|ENUM:0,1|-|-|-|1 = certificate that can expire (employee_skills.effective_to)
shift_templates|template_id|string|Y|FMT:^TPL-[ABC]$|-|PK|-|TPL-<template_code>
shift_templates|template_code|string|Y|ENUM:A,B,C|-|UNIQUE|-|letter used inside shift_id
shift_templates|template_name|string|Y|ENUM:Day,Evening,Night|-|-|-|-
shift_templates|start_time|time|Y|HH:MM 24h|local time|-|-|-
shift_templates|end_time|time|Y|HH:MM 24h|local time|-|-|(end - start) mod 24h = duration_hours
shift_templates|crosses_midnight|bool|Y|ENUM:0,1|-|-|-|1 iff end_time < start_time
shift_templates|duration_hours|float|Y|8.0|hours|-|-|> 0; paid hours of one shift
shift_templates|effective_from|date|Y|ISO-8601 date|-|-|-|<= first schedule day
shift_templates|effective_to|date|N|ISO-8601 date|-|-|-|NULL = open ended; >= effective_from
employees|employee_id|string|Y|FMT:^EMP-\d{6}$|-|PK|-|EMP-000001 upward; immutable
employees|team_id|string|N|TEAM-NNN|-|-|teams.team_id|NULL for HR/IT/admin actors; required when is_rostered=1
employees|manager_id|string|N|EMP-NNNNNN|-|-|employees.employee_id|team manager of the employee; NULL for managers/partners
employees|role|string|Y|ENUM:TEAM_MANAGER,TEAM_LEAD,SENIOR_ASSOCIATE,ASSOCIATE,HR_PARTNER,IT_OPS_PARTNER,SYSTEM_ADMIN|-|-|-|actor roles of the problem statement
employees|employment_type|string|Y|ENUM:FULL_TIME,PART_TIME|-|-|-|drives weekly_hour_cap
employees|is_rostered|bool|Y|ENUM:0,1|-|-|-|1 = can receive shift assignments
employees|primary_shift_code|string|N|ENUM:A,B,C|-|-|-|NULL when is_rostered=0; must be a shift the team runs
employees|weekly_hour_cap|float|Y|40.0 or 24.0|hours/week|-|-|contract hours: FULL_TIME 40, PART_TIME 24
employees|overtime_cap_hours|float|Y|4.0|hours/week|-|-|hard limit = weekly_hour_cap + overtime_cap_hours
employees|hire_date|date|Y|ISO-8601 date|-|-|-|no assignment/leave before hire_date
employees|end_date|date|N|ISO-8601 date|-|-|-|NULL = still employed; >= hire_date
employees|status|string|Y|ENUM:ACTIVE,TERMINATED|-|-|-|TERMINATED iff end_date is not NULL
employees|work_email|string|Y|emp-NNNNNN@example.invalid|-|UNIQUE|-|synthetic, non-routable
teams|team_id|string|Y|FMT:^TEAM-\d{3}$|-|PK|-|TEAM-001 upward; immutable
teams|team_name|string|Y|free text|-|UNIQUE|-|non-empty
teams|domain|string|Y|ENUM:SUPPORT,IT_OPS,LOGISTICS,FACILITIES|-|-|-|selects the 3-skill pool of the team
teams|manager_employee_id|string|Y|EMP-NNNNNN|-|-|employees.employee_id|role must be TEAM_MANAGER; approves leave and swaps
teams|max_concurrent_leave|int|Y|>=1|people|-|-|rule R-LV-03: approved leave per day may not exceed this
teams|effective_from|date|Y|ISO-8601 date|-|-|-|-
teams|effective_to|date|N|ISO-8601 date|-|-|-|NULL = open ended
teams|status|string|Y|ENUM:ACTIVE,INACTIVE|-|-|-|-
team_shift_templates|team_id|string|Y|TEAM-NNN|-|PK|teams.team_id|bridge team N:M shift_template
team_shift_templates|template_id|string|Y|TPL-X|-|PK|shift_templates.template_id|shift runs for this team
team_shift_templates|effective_from|date|Y|ISO-8601 date|-|-|-|-
employee_skills|employee_id|string|Y|EMP-NNNNNN|-|PK|employees.employee_id|bridge employee N:M skill
employee_skills|skill_id|string|Y|SKL-NNN|-|PK|skills.skill_id|-
employee_skills|proficiency_level|int|Y|ENUM:1,2,3|level|-|-|1 basic, 3 expert
employee_skills|effective_from|date|Y|ISO-8601 date|-|-|-|skill counts only from this date
employee_skills|effective_to|date|N|ISO-8601 date|-|-|-|certificate expiry; NULL = does not expire; >= effective_from
coverage_requirements|requirement_id|string|Y|FMT:^REQ-\d{6}$|-|PK|-|REQ-000001 upward; immutable
coverage_requirements|team_id|string|Y|TEAM-NNN|-|-|teams.team_id|-
coverage_requirements|template_id|string|Y|TPL-X|-|-|shift_templates.template_id|must be a shift the team runs
coverage_requirements|skill_id|string|N|SKL-NNN|-|-|skills.skill_id|NULL = headcount requirement (any skill)
coverage_requirements|min_staff|int|Y|>=1|people per shift|-|-|minimum scheduled people (with the skill if skill_id set)
coverage_requirements|holiday_min_staff|int|Y|>=1, <= min_staff|people per shift|-|-|applies on public holidays
coverage_requirements|effective_from|date|Y|ISO-8601 date|-|-|-|ranges for the same team/template/skill never overlap
coverage_requirements|effective_to|date|N|ISO-8601 date|-|-|-|NULL = open ended
leave_requests|leave_id|string|Y|FMT:^LVE-\d{4}-\d{6}$|-|PK|-|LVE-<schedule year>-<counter>, counter in submission order
leave_requests|employee_id|string|Y|EMP-NNNNNN|-|-|employees.employee_id|rostered employee
leave_requests|leave_type|string|Y|ENUM:ANNUAL,SICK,CASUAL,UNPAID|-|-|-|-
leave_requests|start_date|date|Y|ISO-8601 date|-|-|-|>= hire_date
leave_requests|end_date|date|Y|ISO-8601 date|-|-|-|>= start_date
leave_requests|days_requested|int|Y|>=0|days|-|-|derived: calendar days start..end minus public holidays
leave_requests|status|string|Y|ENUM:SUBMITTED,APPROVED,REJECTED,CANCELLED|-|-|-|equals to_status of the last leave_request_events row
leave_requests|submitted_at|datetime|Y|ISO-8601|local time|-|-|-
leave_requests|decided_at|datetime|N|ISO-8601|local time|-|-|>= submitted_at; NULL while SUBMITTED
leave_requests|decided_by|string|N|EMP-NNNNNN|-|-|employees.employee_id|team manager
leave_requests|decision_reason|string|N|ENUM:WITHIN_POLICY,INSUFFICIENT_BALANCE,COVERAGE_RISK,OVERLAPPING_LEAVE|-|-|-|rule code that produced the decision
leave_requests|cancelled_at|datetime|N|ISO-8601|local time|-|-|only when status=CANCELLED; > decided_at
leave_request_events|event_id|string|Y|FMT:^LEVT-\d{7}$|-|PK|-|-
leave_request_events|leave_id|string|Y|LVE-YYYY-NNNNNN|-|-|leave_requests.leave_id|-
leave_request_events|from_status|string|N|ENUM:SUBMITTED,APPROVED,REJECTED,CANCELLED|-|-|-|NULL only for the first event
leave_request_events|to_status|string|Y|ENUM:SUBMITTED,APPROVED,REJECTED,CANCELLED|-|-|-|legal: NULL>SUBMITTED, SUBMITTED>APPROVED/REJECTED, APPROVED>CANCELLED
leave_request_events|event_ts|datetime|Y|ISO-8601|local time|-|-|non-decreasing per leave
leave_request_events|actor_employee_id|string|Y|EMP-NNNNNN|-|-|employees.employee_id|requester or manager
shift_assignments|assignment_id|string|Y|FMT:^ASG-\d{7}$|-|PK|-|surrogate key; one row per employee per shift
shift_assignments|shift_id|string|Y|FMT:^SHIFT-\d{4}-\d{2}-\d{2}-[ABC]$|-|-|-|SHIFT-<date>-<template_code>; identifies the calendar slot (many assignments share it)
shift_assignments|team_id|string|Y|TEAM-NNN|-|-|teams.team_id|team whose requirement the employee covers
shift_assignments|employee_id|string|Y|EMP-NNNNNN|-|-|employees.employee_id|-
shift_assignments|template_id|string|Y|TPL-X|-|-|shift_templates.template_id|-
shift_assignments|shift_date|date|Y|ISO-8601 date|-|-|-|date the shift starts; must match shift_id
shift_assignments|start_ts|datetime|Y|ISO-8601|local time|-|-|shift_date + template start_time
shift_assignments|end_ts|datetime|Y|ISO-8601|local time|-|-|> start_ts
shift_assignments|scheduled_hours|float|Y|8.0|hours|-|-|derived: (end_ts - start_ts) in hours
shift_assignments|status|string|Y|ENUM:ACTIVE,SUPERSEDED,CANCELLED|-|-|-|history is kept: swapped/cancelled rows are never deleted
shift_assignments|assignment_source|string|Y|ENUM:SCHEDULER,MANUAL,SWAP|-|-|-|MANUAL also occurs on ordinary rows
shift_assignments|source_swap_id|string|N|SWP-YYYY-NNNNNN|-|-|swap_requests.swap_id|set when assignment_source=SWAP
shift_assignments|created_at|datetime|Y|ISO-8601|local time|-|-|<= start_ts
assignment_events|event_id|string|Y|FMT:^AEV-\d{7}$|-|PK|-|-
assignment_events|assignment_id|string|Y|ASG-NNNNNNN|-|-|shift_assignments.assignment_id|-
assignment_events|event_type|string|Y|ENUM:CREATED,SUPERSEDED_BY_SWAP,CANCELLED_REPLACED|-|-|-|-
assignment_events|event_ts|datetime|Y|ISO-8601|local time|-|-|-
assignment_events|actor_employee_id|string|N|EMP-NNNNNN|-|-|employees.employee_id|manager who changed the roster
assignment_events|swap_id|string|N|SWP-YYYY-NNNNNN|-|-|swap_requests.swap_id|set for swap-related events
swap_requests|swap_id|string|Y|FMT:^SWP-\d{4}-\d{6}$|-|PK|-|SWP-<schedule year>-<counter>, counter in request order
swap_requests|requester_employee_id|string|Y|EMP-NNNNNN|-|-|employees.employee_id|current owner of the assignment
swap_requests|counterpart_employee_id|string|Y|EMP-NNNNNN|-|-|employees.employee_id|teammate asked to take the shift; != requester
swap_requests|requester_assignment_id|string|Y|ASG-NNNNNNN|-|-|shift_assignments.assignment_id|the assignment handed over
swap_requests|new_assignment_id|string|N|ASG-NNNNNNN|-|-|shift_assignments.assignment_id|assignment created for the counterpart; only when APPLIED
swap_requests|team_id|string|Y|TEAM-NNN|-|-|teams.team_id|-
swap_requests|shift_id|string|Y|FMT:^SHIFT-\d{4}-\d{2}-\d{2}-[ABC]$|-|-|-|slot being covered
swap_requests|shift_date|date|Y|ISO-8601 date|-|-|-|-
swap_requests|swap_type|string|Y|ENUM:COVER|-|-|-|one-way shift cover (counterpart takes the shift)
swap_requests|reason_code|string|Y|ENUM:PERSONAL,MEDICAL,FAMILY,TRANSPORT,OTHER|-|-|-|-
swap_requests|status|string|Y|ENUM:REQUESTED,APPROVED,REJECTED,CANCELLED,APPLIED|-|-|-|equals to_status of the last swap_events row
swap_requests|requested_at|datetime|Y|ISO-8601|local time|-|-|before shift start
swap_requests|decided_at|datetime|N|ISO-8601|local time|-|-|>= requested_at; NULL if no manager decision exists
swap_requests|decided_by|string|N|EMP-NNNNNN|-|-|employees.employee_id|team manager
swap_requests|decision_reason|string|N|ENUM:WITHIN_RULES,INACTIVE,ON_LEAVE,ALREADY_ASSIGNED,REST_VIOLATION,CONSECUTIVE_DAYS,WEEKLY_CAP,SKILL_MISMATCH|-|-|-|first failed rule, or WITHIN_RULES
swap_requests|applied_at|datetime|N|ISO-8601|local time|-|-|>= decided_at; only when APPLIED
swap_events|event_id|string|Y|FMT:^SWE-\d{6}$|-|PK|-|-
swap_events|swap_id|string|Y|SWP-YYYY-NNNNNN|-|-|swap_requests.swap_id|-
swap_events|from_status|string|N|ENUM:REQUESTED,APPROVED,REJECTED,CANCELLED,APPLIED|-|-|-|NULL only for the first event
swap_events|to_status|string|Y|ENUM:REQUESTED,APPROVED,REJECTED,CANCELLED,APPLIED|-|-|-|legal: NULL>REQUESTED, REQUESTED>APPROVED/REJECTED/CANCELLED, APPROVED>APPLIED
swap_events|event_ts|datetime|Y|ISO-8601|local time|-|-|non-decreasing per swap
swap_events|actor_employee_id|string|Y|EMP-NNNNNN|-|-|employees.employee_id|requester or manager
attendance_events|attendance_id|string|Y|FMT:^ATT-EMP-\d{6}-\d{8}T\d{6}$|-|PK|-|ATT-<employee_id>-<YYYYMMDDTHHMMSS of event_ts>
attendance_events|employee_id|string|Y|EMP-NNNNNN|-|-|employees.employee_id|-
attendance_events|assignment_id|string|N|ASG-NNNNNNN|-|-|shift_assignments.assignment_id|always an ACTIVE assignment in this dataset
attendance_events|event_type|string|Y|ENUM:CLOCK_IN,CLOCK_OUT,ABSENT|-|-|-|each ACTIVE assignment has CLOCK_IN+CLOCK_OUT or one ABSENT
attendance_events|event_ts|datetime|Y|ISO-8601|local time|-|-|CLOCK_OUT > CLOCK_IN
attendance_events|source|string|Y|ENUM:BADGE,MOBILE,MANUAL,SYSTEM|-|-|-|ABSENT rows use SYSTEM
attendance_events|absence_reason|string|N|ENUM:SICK_CALL,NO_SHOW,ON_APPROVED_LEAVE,DOUBLE_BOOKED_CONFLICT|-|-|-|only for ABSENT
attendance_events|variance_minutes|int|N|integer|minutes|-|-|derived: CLOCK_IN - scheduled start, CLOCK_OUT - scheduled end; NULL for ABSENT
coverage_results|result_id|string|Y|FMT:^CRES-\d{7}$|-|PK|-|derived output, not an input feature table
coverage_results|requirement_id|string|Y|REQ-NNNNNN|-|-|coverage_requirements.requirement_id|requirement active on shift_date
coverage_results|team_id|string|Y|TEAM-NNN|-|-|teams.team_id|-
coverage_results|shift_id|string|Y|SHIFT-YYYY-MM-DD-X|-|-|-|-
coverage_results|shift_date|date|Y|ISO-8601 date|-|-|-|-
coverage_results|template_id|string|Y|TPL-X|-|-|shift_templates.template_id|-
coverage_results|skill_id|string|N|SKL-NNN|-|-|skills.skill_id|NULL = headcount
coverage_results|is_holiday|bool|Y|ENUM:0,1|-|-|-|shift_date in holiday_calendar
coverage_results|required_staff|int|Y|>=1|people|-|-|holiday_min_staff if is_holiday else min_staff
coverage_results|scheduled_staff|int|Y|>=0|people|-|-|ACTIVE assignments in the slot (with the skill valid on the date)
coverage_results|present_staff|int|Y|>=0|people|-|-|scheduled people with a CLOCK_IN
coverage_results|scheduled_gap|int|Y|>=0|people|-|-|max(0, required - scheduled)
coverage_results|actual_gap|int|Y|>=0|people|-|-|max(0, required - present)
weekly_hours|employee_id|string|Y|EMP-NNNNNN|-|PK|employees.employee_id|derived; one row per employee-week with activity
weekly_hours|iso_week|string|Y|FMT:^\d{4}-W\d{2}$|-|PK|-|ISO week of shift_date
weekly_hours|week_start|date|Y|ISO-8601 date|-|-|-|Monday of the ISO week
weekly_hours|scheduled_hours|float|Y|>=0|hours|-|-|sum of ACTIVE scheduled_hours in the week
weekly_hours|worked_hours|float|Y|>=0|hours|-|-|sum of CLOCK_OUT - CLOCK_IN
weekly_hours|contract_cap_hours|float|Y|>0|hours|-|-|employees.weekly_hour_cap
weekly_hours|overtime_cap_hours|float|Y|>=0|hours|-|-|employees.overtime_cap_hours
weekly_hours|hard_limit_hours|float|Y|>0|hours|-|-|contract_cap + overtime_cap
weekly_hours|overtime_hours|float|Y|>=0|hours|-|-|max(0, worked_hours - contract_cap)
weekly_hours|scheduled_exceeds_limit|bool|Y|ENUM:0,1|-|-|-|scheduled_hours > hard_limit_hours
weekly_hours|worked_exceeds_limit|bool|Y|ENUM:0,1|-|-|-|worked_hours > hard_limit_hours
leave_balances|employee_id|string|Y|EMP-NNNNNN|-|PK|employees.employee_id|derived
leave_balances|leave_type|string|Y|ENUM:ANNUAL,SICK,CASUAL|-|PK|-|UNPAID has no balance
leave_balances|opening_balance_days|int|Y|>=0|days|-|-|allowance for the generated window
leave_balances|approved_days|int|Y|>=0|days|-|-|sum days_requested of APPROVED leaves of that type
leave_balances|closing_balance_days|int|Y|>=0|days|-|-|opening - approved
"""

ENTITY_NAMES = {
    "employees": "Employee", "teams": "Team", "skills": "Skill", "shift_templates": "ShiftTemplate",
    "shift_assignments": "ShiftAssignment", "leave_requests": "LeaveRequest",
    "holiday_calendar": "HolidayCalendar", "attendance_events": "AttendanceEvent",
    "coverage_requirements": "CoverageRequirement", "swap_requests": "SwapRequest",
    "team_shift_templates": "(bridge) Team N:M ShiftTemplate", "employee_skills": "(bridge) Employee N:M Skill",
    "leave_request_events": "(event history) LeaveRequest", "assignment_events": "(event history) ShiftAssignment",
    "swap_events": "(event history) SwapRequest", "coverage_results": "(derived) CoverageRequirement result",
    "weekly_hours": "(derived) weekly hours / overtime", "leave_balances": "(derived) leave balance",
}
INPUT_TABLES = ["holiday_calendar", "skills", "shift_templates", "employees", "teams", "team_shift_templates",
                "employee_skills", "coverage_requirements", "leave_requests", "leave_request_events",
                "shift_assignments", "assignment_events", "swap_requests", "swap_events", "attendance_events"]
DERIVED_TABLES = ["coverage_results", "weekly_hours", "leave_balances"]
TABLE_ORDER = INPUT_TABLES + DERIVED_TABLES


def parse_dict():
    schema = {t: [] for t in TABLE_ORDER}
    for line in DICT_TEXT.strip().splitlines():
        if not line.strip():
            continue
        parts = [x.strip() for x in line.split("|")]
        assert len(parts) == 9, line
        t, f, ty, req, allowed, unit, uniq, fk, rule = parts
        schema[t].append(dict(name=f, type=ty, required=req == "Y", allowed=allowed, unit=unit,
                              unique=uniq, fk=None if fk == "-" else fk, rule=rule))
    return schema


SCHEMA = parse_dict()

# --------------------------------------------------------------------------------------
# Business constants
# --------------------------------------------------------------------------------------
SKILLS = [("SKL-001", "Tier-1 Support", "SUPPORT", 0), ("SKL-002", "Tier-2 Escalation", "SUPPORT", 0),
          ("SKL-003", "Billing Queries", "SUPPORT", 0), ("SKL-004", "Incident Response", "IT_OPS", 1),
          ("SKL-005", "Database Administration", "IT_OPS", 0), ("SKL-006", "Network Monitoring", "IT_OPS", 0),
          ("SKL-007", "Forklift Operation", "LOGISTICS", 1), ("SKL-008", "Inventory Control", "LOGISTICS", 0),
          ("SKL-009", "Dispatch Planning", "LOGISTICS", 0), ("SKL-010", "First Aid Responder", "FACILITIES", 1),
          ("SKL-011", "Security Patrol", "FACILITIES", 0), ("SKL-012", "Equipment Maintenance", "FACILITIES", 0)]
DOMAINS = ["SUPPORT", "IT_OPS", "LOGISTICS", "FACILITIES"]
TEMPLATES = [("A", "Day", "06:00", "14:00", 0), ("B", "Evening", "14:00", "22:00", 0), ("C", "Night", "22:00", "06:00", 1)]
STARTS = {"A": time(6), "B": time(14), "C": time(22)}
SHIFT_HOURS = 8.0
MIN_REST_HOURS = 11.0
MAX_CONSECUTIVE_DAYS = 6
OVERTIME_CAP = 4.0
LEAVE_ALLOWANCE = {"ANNUAL": 10, "CASUAL": 4, "SICK": 5}
# Illustrative synthetic calendar (dates modelled on common Indian public holidays; NOT an authoritative source)
HOLIDAYS = [("01-01", "New Year's Day"), ("01-14", "Makar Sankranti"), ("01-26", "Republic Day"),
            ("02-15", "Maha Shivaratri"), ("03-04", "Holi"), ("03-19", "Ugadi"), ("03-26", "Rama Navami"),
            ("04-14", "Ambedkar Jayanti"), ("05-01", "Labour Day"), ("08-15", "Independence Day"),
            ("10-02", "Gandhi Jayanti"), ("12-25", "Christmas Day")]
INJECTION_BASE = {"EMPLOYEE_DOUBLE_BOOKED": 30, "APPROVED_LEAVE_OVERLAPS_SHIFT": 30, "REQUIRED_SKILL_ABSENT": 25,
                  "OVERTIME_CAP_EXCEEDED": 25, "SWAP_APPLIED_WITHOUT_APPROVAL": 20}
RULES = {"EMPLOYEE_DOUBLE_BOOKED": "R1", "APPROVED_LEAVE_OVERLAPS_SHIFT": "R2", "REQUIRED_SKILL_ABSENT": "R3",
         "OVERTIME_CAP_EXCEEDED": "R4", "SWAP_APPLIED_WITHOUT_APPROVAL": "R5"}
DECISIONS = {"EMPLOYEE_DOUBLE_BOOKED": "REJECT_DUPLICATE_ASSIGNMENT_AND_REASSIGN",
             "APPROVED_LEAVE_OVERLAPS_SHIFT": "REMOVE_ASSIGNMENT_AND_BACKFILL",
             "REQUIRED_SKILL_ABSENT": "ESCALATE_COVERAGE_GAP_TO_MANAGER",
             "OVERTIME_CAP_EXCEEDED": "BLOCK_ASSIGNMENT_AND_FLAG_HR",
             "SWAP_APPLIED_WITHOUT_APPROVAL": "REVERT_SWAP_AND_REQUIRE_APPROVAL"}


def wk(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def fmtv(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float):
        return repr(round(v, 4))
    return str(v)


def jv(v):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    return v


# --------------------------------------------------------------------------------------
# Roster: holds ACTIVE assignments and answers "may this person work this shift?"
# --------------------------------------------------------------------------------------
class Roster:
    def __init__(self, emp, leave_days):
        self.emp, self.leave_days = emp, leave_days
        self.by_emp_date = defaultdict(list)
        self.slot = defaultdict(list)
        self.week_hours = defaultdict(float)
        self.total_hours = defaultdict(float)
        self.assignments = []

    def check(self, eid, d, code, skip=()):
        """Return None if allowed, else the first violated rule code."""
        e = self.emp[eid]
        if d < e["_hire"] or (e["_end"] is not None and d > e["_end"]):
            return "INACTIVE"
        if "LEAVE" not in skip and d in self.leave_days.get(eid, ()):
            return "ON_LEAVE"
        if self.by_emp_date.get((eid, d)):
            return "ALREADY_ASSIGNED"
        s = datetime.combine(d, STARTS[code])
        en = s + timedelta(hours=SHIFT_HOURS)
        for nd in (d - timedelta(days=1), d + timedelta(days=1)):
            for o in self.by_emp_date.get((eid, nd), ()):
                gap = (s - o["_end"]).total_seconds() / 3600 if nd < d else (o["_start"] - en).total_seconds() / 3600
                if gap < MIN_REST_HOURS:
                    return "REST_VIOLATION"
        run, x = 1, d - timedelta(days=1)
        while self.by_emp_date.get((eid, x)):
            run += 1
            x -= timedelta(days=1)
        x = d + timedelta(days=1)
        while self.by_emp_date.get((eid, x)):
            run += 1
            x += timedelta(days=1)
        if run > MAX_CONSECUTIVE_DAYS:
            return "CONSECUTIVE_DAYS"
        if "WEEK" not in skip and self.week_hours[(eid, wk(d))] + SHIFT_HOURS > e["_cap"]:
            return "WEEKLY_CAP"
        return None

    def new(self, eid, team, d, code, source, created, actor, swap=None, inj=None):
        s = datetime.combine(d, STARTS[code])
        a = dict(employee_id=eid, team_id=team, shift_date=d, template_code=code, _start=s,
                 _end=s + timedelta(hours=SHIFT_HOURS), status="ACTIVE", assignment_source=source,
                 created_at=created, _swap=swap, _inj=inj, _lock=False, _idx=len(self.assignments),
                 _events=[("CREATED", created, actor, swap)])
        self.assignments.append(a)
        self.by_emp_date[(eid, d)].append(a)
        self.slot[(team, d, code)].append(a)
        self.week_hours[(eid, wk(d))] += SHIFT_HOURS
        self.total_hours[eid] += SHIFT_HOURS
        return a

    def drop(self, a, new_status):
        a["status"] = new_status
        self.by_emp_date[(a["employee_id"], a["shift_date"])].remove(a)
        self.slot[(a["team_id"], a["shift_date"], a["template_code"])].remove(a)
        self.week_hours[(a["employee_id"], wk(a["shift_date"]))] -= SHIFT_HOURS
        self.total_hours[a["employee_id"]] -= SHIFT_HOURS


# --------------------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------------------
def generate(P):
    start = date.fromisoformat(P.start)
    dates = [start + timedelta(days=i) for i in range(P.days)]
    end = dates[-1]
    year = start.year
    cutoff = datetime.combine(end, time(23, 59, 59))
    N, T = P.employees, P.teams
    scale = N / 2000.0

    def R(phase):
        return random.Random(f"{P.seed}:{phase}")

    # ---- holidays, skills, templates -------------------------------------------------
    hol_rows, hol_set = [], set()
    for y in range(start.year, end.year + 1):
        for md, name in HOLIDAYS:
            d = date(y, int(md[:2]), int(md[3:]))
            if start <= d <= end:
                hol_rows.append(dict(holiday_id=f"HOL-{d.isoformat()}", holiday_date=d, holiday_name=name,
                                     region="IN-ALL", holiday_type="PUBLIC"))
                hol_set.add(d)
    skill_rows = [dict(skill_id=s[0], skill_name=s[1], skill_category=s[2], is_certification=s[3]) for s in SKILLS]
    tpl_rows = [dict(template_id=f"TPL-{c}", template_code=c, template_name=n, start_time=st, end_time=et,
                     crosses_midnight=cm, duration_hours=SHIFT_HOURS, effective_from=start, effective_to=None)
                for c, n, st, et, cm in TEMPLATES]

    # ---- teams & employees -------------------------------------------------------------
    r = R("master")
    n_hr, n_it, n_adm = max(1, round(5 * scale)), max(1, round(3 * scale)), 1
    n_staff = N - T - n_hr - n_it - n_adm
    if n_staff < 8 * T:
        raise SystemExit("Need >= 8 rostered staff per team: raise --employees or lower --teams")
    wts = [r.uniform(0.6, 1.4) for _ in range(T)]
    sizes = [max(8, int(n_staff * w / sum(wts))) for w in wts]
    diff, i = n_staff - sum(sizes), 0
    while diff != 0:
        j, step = i % T, (1 if diff > 0 else -1)
        if step > 0 or sizes[j] > 8:
            sizes[j] += step
            diff -= step
        i += 1
    teams = []
    for k in range(T):
        domain = DOMAINS[k % 4]
        shifts = r.choices([("A",), ("A", "B"), ("A", "B", "C")], [0.2, 0.3, 0.5])[0]
        size, s = sizes[k], len(shifts)
        demand = max(1, round(0.40 * size / s))
        buf = 1 if s * (demand + 1) <= 0.8 * 0.714 * size else 0
        teams.append(dict(team_id=f"TEAM-{k + 1:03d}", team_name=f"{domain.replace('_', ' ').title()} Team {k + 1:03d}",
                          domain=domain, manager_employee_id=f"EMP-{k + 1:06d}", max_concurrent_leave=max(1, int(0.2 * size)),
                          effective_from=start, effective_to=None, status="ACTIVE", _shifts=list(shifts), _size=size,
                          _demand=demand, _buf=buf, _staff=[]))
    team_by_id = {t["team_id"]: t for t in teams}

    emps = []

    def add_emp(i, **kw):
        base = dict(employee_id=f"EMP-{i:06d}", team_id=None, manager_id=None, employment_type="FULL_TIME", is_rostered=0,
                    primary_shift_code=None, weekly_hour_cap=40.0, overtime_cap_hours=OVERTIME_CAP, end_date=None,
                    status="ACTIVE", work_email=f"emp-{i:06d}@example.invalid", _skills={})
        base.update(kw)
        base["_cap"], base["_hire"], base["_end"] = base["weekly_hour_cap"], base["hire_date"], base["end_date"]
        emps.append(base)
        return base

    for k, t in enumerate(teams):
        add_emp(k + 1, team_id=t["team_id"], role="TEAM_MANAGER", hire_date=start - timedelta(days=r.randint(400, 3000)))
    idx = T
    for role, cnt in (("HR_PARTNER", n_hr), ("IT_OPS_PARTNER", n_it), ("SYSTEM_ADMIN", n_adm)):
        for _ in range(cnt):
            idx += 1
            add_emp(idx, role=role, hire_date=start - timedelta(days=r.randint(400, 3000)))
    for t in teams:
        for j in range(t["_size"]):
            idx += 1
            ft = r.random() < 0.8
            roll = 1.0 if j == 0 else r.random()
            hire, end_d = start - timedelta(days=r.randint(30, 2500)), None
            if roll < 0.03:
                hire = start + timedelta(days=r.randint(1, max(2, P.days - 30)))
            elif roll < 0.05:
                end_d = start + timedelta(days=r.randint(min(20, P.days - 1), P.days - 1))
            role = "TEAM_LEAD" if j == 0 else ("SENIOR_ASSOCIATE" if r.random() < 0.15 else "ASSOCIATE")
            e = add_emp(idx, team_id=t["team_id"], manager_id=t["manager_employee_id"], role=role,
                        employment_type="FULL_TIME" if ft else "PART_TIME", is_rostered=1,
                        primary_shift_code=t["_shifts"][j % len(t["_shifts"])], weekly_hour_cap=40.0 if ft else 24.0,
                        hire_date=hire, end_date=end_d, status="TERMINATED" if end_d else "ACTIVE")
            t["_staff"].append(e["employee_id"])
    emp = {e["employee_id"]: e for e in emps}

    # ---- bridge tables -----------------------------------------------------------------
    tst_rows = [dict(team_id=t["team_id"], template_id=f"TPL-{c}", effective_from=start) for t in teams for c in t["_shifts"]]
    es_rows = []
    for t in teams:
        pool = [s for s in SKILLS if s[2] == t["domain"]]
        for j, eid in enumerate(t["_staff"]):
            e, prim = emp[eid], pool[j % 3]
            chosen = [(prim, True)]
            if r.random() < 0.35:
                chosen.append((r.choice([p for p in pool if p != prim]), False))
            for sk, is_prim in chosen:
                eff_from = e["hire_date"]
                if not is_prim and r.random() < 0.3:
                    eff_from = start + timedelta(days=r.randint(5, max(6, P.days // 2)))
                eff_to = None
                if sk[3] and r.random() < 0.08:
                    eff_to = start + timedelta(days=r.randint(10, max(11, P.days - 10)))
                    if eff_to < eff_from:
                        eff_to = None
                e["_skills"][sk[0]] = (eff_from, eff_to)
                es_rows.append(dict(employee_id=eid, skill_id=sk[0], proficiency_level=r.choice([1, 2, 2, 3]),
                                    effective_from=eff_from, effective_to=eff_to))

    def has_skill(eid, sk, d):
        v = emp[eid]["_skills"].get(sk)
        return bool(v) and v[0] <= d and (v[1] is None or d <= v[1])

    # ---- coverage requirements -----------------------------------------------------------
    rr = R("requirements")
    reqs, req_by = [], defaultdict(list)
    rev_date = start + timedelta(days=P.days // 2)

    def add_req(team, code, skill, mn, eff_from, eff_to):
        row = dict(requirement_id=f"REQ-{len(reqs) + 1:06d}", team_id=team, template_id=f"TPL-{code}", skill_id=skill,
                   min_staff=mn, holiday_min_staff=max(1, (mn + 1) // 2), effective_from=eff_from, effective_to=eff_to)
        reqs.append(row)
        req_by[(team, code)].append(row)

    for t in teams:
        pool = [s[0] for s in SKILLS if s[2] == t["domain"]]
        d0 = t["_demand"]
        nsk = 1 if d0 < 3 else (2 if d0 < 6 else 3)
        for code in t["_shifts"]:
            revise = rr.random() < 0.15
            newd = max(1, d0 + rr.choice([-1, 1])) if revise else d0
            if revise and newd != d0:
                add_req(t["team_id"], code, None, d0, start, rev_date - timedelta(days=1))
                add_req(t["team_id"], code, None, newd, rev_date, None)
            else:
                add_req(t["team_id"], code, None, d0, start, None)
            for q in range(nsk):
                add_req(t["team_id"], code, pool[q], max(1, d0 // 3), start, None)

    def req_active(team, code, d):
        return [q for q in req_by[(team, code)] if q["effective_from"] <= d and (q["effective_to"] is None or d <= q["effective_to"])]

    def need(q, d):
        return q["holiday_min_staff"] if d in hol_set else q["min_staff"]

    # ---- leave requests + rule-based approval ---------------------------------------------
    rl = R("leave")
    staff = [e for e in emps if e["is_rostered"]]
    ltypes, lweights = ["ANNUAL", "SICK", "CASUAL", "UNPAID"], [0.40, 0.25, 0.25, 0.10]
    dur_opts = {"ANNUAL": (list(range(1, 11)), [3, 4, 4, 4, 5, 3, 3, 2, 1, 1]), "SICK": ([1, 2, 3], [6, 3, 1]),
                "CASUAL": ([1, 2], [7, 3]), "UNPAID": (list(range(1, 6)), [3, 3, 2, 1, 1])}
    raw, seen_leave = [], set()
    for n in range(P.leaves):
        while True:
            e = rl.choice(staff)
            lt = rl.choices(ltypes, lweights)[0]
            dur = rl.choices(*dur_opts[lt])[0]
            last_day = min(end, e["_end"]) if e["_end"] else end
            lo, hi = max(start, e["_hire"] + timedelta(days=1)), last_day - timedelta(days=dur - 1)
            if lo > hi:
                continue
            sd = lo + timedelta(days=rl.randint(0, (hi - lo).days))
            key = (e["employee_id"], sd, lt)
            if key not in seen_leave:          # a resubmission of identical dates/type would be a duplicate record
                seen_leave.add(key)
                break
        ed = sd + timedelta(days=dur - 1)
        if lt == "SICK":
            sub = datetime.combine(sd, time(5)) + timedelta(minutes=rl.randint(0, 239))
        else:
            lead = {"ANNUAL": (7, 45), "CASUAL": (1, 7), "UNPAID": (3, 20)}[lt]
            sub_d = max(sd - timedelta(days=rl.randint(*lead)), e["_hire"])
            sub = datetime.combine(sub_d, time(9)) + timedelta(minutes=rl.randint(0, 600))
        raw.append(dict(employee_id=e["employee_id"], leave_type=lt, start_date=sd, end_date=ed, submitted_at=sub, _n=n))
    raw.sort(key=lambda x: (x["submitted_at"], x["_n"]))
    used, approved_dates, team_cnt = defaultdict(int), defaultdict(set), defaultdict(int)
    leaves, lev = [], []
    for k, q in enumerate(raw):
        e = emp[q["employee_id"]]
        team = team_by_id[e["team_id"]]
        mgr = team["manager_employee_id"]
        span = [q["start_date"] + timedelta(days=i) for i in range((q["end_date"] - q["start_date"]).days + 1)]
        chargeable = [x for x in span if x not in hol_set]
        lv = dict(leave_id=f"LVE-{year}-{k + 1:06d}", employee_id=q["employee_id"], leave_type=q["leave_type"],
                  start_date=q["start_date"], end_date=q["end_date"], days_requested=len(chargeable), status="SUBMITTED",
                  submitted_at=q["submitted_at"], decided_at=None, decided_by=None, decision_reason=None,
                  cancelled_at=None, _span=span)
        events = [(None, "SUBMITTED", q["submitted_at"], q["employee_id"])]
        if q["leave_type"] == "SICK":
            dec = q["submitted_at"] + timedelta(minutes=rl.randint(30, 240))
        else:
            dec = q["submitted_at"] + timedelta(minutes=rl.randint(180, 4300))
            dec = max(q["submitted_at"] + timedelta(minutes=30), min(dec, datetime.combine(q["start_date"], time(0)) - timedelta(hours=1)))
        if dec <= cutoff:
            lt = q["leave_type"]
            if any(x in approved_dates[q["employee_id"]] for x in span):
                st, why = "REJECTED", "OVERLAPPING_LEAVE"
            elif lt in LEAVE_ALLOWANCE and used[(q["employee_id"], lt)] + len(chargeable) > LEAVE_ALLOWANCE[lt]:
                st, why = "REJECTED", "INSUFFICIENT_BALANCE"
            elif lt != "SICK" and any(team_cnt[(team["team_id"], x)] + 1 > team["max_concurrent_leave"] for x in chargeable):
                st, why = "REJECTED", "COVERAGE_RISK"
            else:
                st, why = "APPROVED", "WITHIN_POLICY"
                used[(q["employee_id"], lt)] += len(chargeable)
                approved_dates[q["employee_id"]].update(span)
                for x in chargeable:
                    team_cnt[(team["team_id"], x)] += 1
            lv.update(status=st, decided_at=dec, decided_by=mgr, decision_reason=why)
            events.append(("SUBMITTED", st, dec, mgr))
            if st == "APPROVED" and lt != "SICK" and rl.random() < 0.06:
                latest = datetime.combine(q["start_date"], time(0)) - timedelta(hours=1)
                if dec + timedelta(hours=2) < latest:
                    ct = dec + timedelta(minutes=rl.randint(60, int((latest - dec).total_seconds() / 60)))
                    lv.update(status="CANCELLED", cancelled_at=ct)
                    events.append(("APPROVED", "CANCELLED", ct, q["employee_id"]))
        lv["_events"] = events
        leaves.append(lv)
    leave_days = defaultdict(set)
    for lv in leaves:
        if lv["status"] == "APPROVED":
            leave_days[lv["employee_id"]].update(lv["_span"])
    lev_rows = []
    for lv in leaves:
        for fr, to, ts, actor in lv["_events"]:
            lev_rows.append(dict(leave_id=lv["leave_id"], from_status=fr, to_status=to, event_ts=ts, actor_employee_id=actor))
    lev_rows.sort(key=lambda x: (x["event_ts"], x["leave_id"]))
    for n, row in enumerate(lev_rows):
        row["event_id"] = f"LEVT-{n + 1:07d}"

    # ---- schedule (greedy, constraint aware, fairness = lowest utilisation first) -----------
    W = Roster(emp, leave_days)
    rs = R("schedule")
    for d in dates:
        hol = d in hol_set
        for t in teams:
            mgr = t["manager_employee_id"]
            for code in t["_shifts"]:
                reqs_now = req_active(t["team_id"], code, d)
                head = [q for q in reqs_now if q["skill_id"] is None]
                skr = [q for q in reqs_now if q["skill_id"]]
                cands = [x for x in t["_staff"] if W.check(x, d, code) is None]
                keyed = sorted(((emp[x]["primary_shift_code"] != code, W.total_hours[x] / emp[x]["_cap"], rs.random(), x) for x in cands))
                cands = [k[3] for k in keyed]
                sel = []
                for q in sorted(skr, key=lambda q: sum(1 for x in cands if has_skill(x, q["skill_id"], d))):
                    have = sum(1 for x in sel if has_skill(x, q["skill_id"], d))
                    for x in cands:
                        if have >= need(q, d):
                            break
                        if x not in sel and has_skill(x, q["skill_id"], d):
                            sel.append(x)
                            have += 1
                target = (need(head[0], d) if head else 0) + (0 if hol else t["_buf"])
                for x in cands:
                    if len(sel) >= target:
                        break
                    if x not in sel:
                        sel.append(x)
                created = datetime.combine(d - timedelta(days=14), time(8))
                for x in sel:
                    src = "MANUAL" if rs.random() < 0.04 else "SCHEDULER"
                    W.new(x, t["team_id"], d, code, src, created, mgr)
    base_assignments = list(W.assignments)

    # ---- swaps (one-way shift cover, manager decides by documented rules) ---------------------
    rw = R("swaps")
    swaps = []

    def skill_ok(a, cid):
        d, code = a["shift_date"], a["template_code"]
        slot = W.slot[(a["team_id"], d, code)]
        for q in req_active(a["team_id"], code, d):
            if q["skill_id"] is None:
                continue
            before = sum(1 for x in slot if has_skill(x["employee_id"], q["skill_id"], d))
            after = before - (1 if has_skill(a["employee_id"], q["skill_id"], d) else 0) + (1 if has_skill(cid, q["skill_id"], d) else 0)
            if after < min(need(q, d), before):
                return False
        return True

    def eval_swap(a, cid):
        why = W.check(cid, a["shift_date"], a["template_code"])
        if why:
            return why
        return None if skill_ok(a, cid) else "SKILL_MISMATCH"

    def pick_counterpart(a, rng, must_be_eligible=False):
        mates = [x for x in team_by_id[a["team_id"]]["_staff"] if x != a["employee_id"]]
        off = [x for x in mates if not W.by_emp_date.get((x, a["shift_date"]))]
        if must_be_eligible:
            ok = [x for x in off if eval_swap(a, x) is None]
            return rng.choice(ok) if ok else None
        pool = off if (off and rng.random() < 0.85) else mates
        return rng.choice(pool)

    def make_swap(a, cid, requested_at, injected=None):
        sw = dict(requester_employee_id=a["employee_id"], counterpart_employee_id=cid, _req=a, _new=None,
                  team_id=a["team_id"], shift_id=f"SHIFT-{a['shift_date']:%Y-%m-%d}-{a['template_code']}",
                  shift_date=a["shift_date"], swap_type="COVER", reason_code=rw.choice(["PERSONAL", "MEDICAL", "FAMILY", "TRANSPORT", "OTHER"]),
                  status="REQUESTED", requested_at=requested_at, decided_at=None, decided_by=None, decision_reason=None,
                  applied_at=None, _events=[(None, "REQUESTED", requested_at, a["employee_id"])], _inj=injected, _idx=len(swaps))
        swaps.append(sw)
        return sw

    def apply_swap(sw, a, applied_at, mgr):
        W.drop(a, "SUPERSEDED")
        a["_events"].append(("SUPERSEDED_BY_SWAP", applied_at, mgr, sw))
        b = W.new(sw["counterpart_employee_id"], a["team_id"], a["shift_date"], a["template_code"], "SWAP", applied_at, mgr, swap=sw)
        b["_events"][0] = ("CREATED", applied_at, mgr, sw)
        sw["_new"] = b
        sw["applied_at"] = applied_at
        return b

    n_swaps = P.swaps if P.swaps is not None else round(0.35 * N)
    pool = [a for a in base_assignments if a["shift_date"] >= start + timedelta(days=2)]
    plan = []
    for a in rw.sample(pool, min(n_swaps, len(pool))):
        hrs_before = rw.randint(12, 13 * 24)
        plan.append((a["_start"] - timedelta(hours=hrs_before), a))
    plan.sort(key=lambda x: (x[0], x[1]["_idx"]))
    for req_at, a in plan:
        cid = pick_counterpart(a, rw)
        sw = make_swap(a, cid, req_at)
        mgr = team_by_id[a["team_id"]]["manager_employee_id"]
        last_ok = a["_start"] - timedelta(hours=1)
        if rw.random() < 0.08:
            ts = min(req_at + timedelta(hours=rw.randint(1, 12)), last_ok)
            sw["_events"].append(("REQUESTED", "CANCELLED", ts, a["employee_id"]))
            sw["status"] = "CANCELLED"
            continue
        dec = max(req_at + timedelta(minutes=30), min(req_at + timedelta(hours=rw.randint(2, 48)), last_ok))
        why = eval_swap(a, cid)
        sw.update(decided_at=dec, decided_by=mgr)
        if why:
            sw.update(status="REJECTED", decision_reason=why)
            sw["_events"].append(("REQUESTED", "REJECTED", dec, mgr))
        else:
            sw.update(decision_reason="WITHIN_RULES")
            sw["_events"].append(("REQUESTED", "APPROVED", dec, mgr))
            app = min(dec + timedelta(minutes=rw.randint(5, 120)), a["_start"] - timedelta(minutes=30))
            apply_swap(sw, a, max(app, dec), mgr)
            sw["status"] = "APPLIED"
            sw["_events"].append(("APPROVED", "APPLIED", sw["applied_at"], mgr))

    # ---- labelled edge-case injection -------------------------------------------------------
    ri = R("inject")
    cnt = {k: max(2, round(v * (P.inject_scale if P.inject_scale is not None else scale))) for k, v in INJECTION_BASE.items()}
    inj_emp, inj_log = set(), []
    roster_ids = [e["employee_id"] for e in staff]

    def free_pick(a):
        return a["status"] == "ACTIVE" and not a["_inj"] and not a["_lock"] and a["employee_id"] not in inj_emp

    # (1) approved leave overlaps assigned shift
    appr = [lv for lv in leaves if lv["status"] == "APPROVED"]
    done = 0
    for _ in range(4000):
        if done >= cnt["APPROVED_LEAVE_OVERLAPS_SHIFT"] or not appr:
            break
        lv = ri.choice(appr)
        eid = lv["employee_id"]
        days = [x for x in lv["_span"] if x not in hol_set]
        if eid in inj_emp or not days:
            continue
        d, code = ri.choice(days), emp[eid]["primary_shift_code"]
        if W.check(eid, d, code, skip=("LEAVE",)) is None:
            a = W.new(eid, emp[eid]["team_id"], d, code, "MANUAL", datetime.combine(d - timedelta(days=3), time(10)),
                      team_by_id[emp[eid]["team_id"]]["manager_employee_id"], inj="APPROVED_LEAVE_OVERLAPS_SHIFT")
            inj_log.append(dict(type="APPROVED_LEAVE_OVERLAPS_SHIFT", asg=a, related=lv["leave_id"], employee_id=eid, d=d))
            inj_emp.add(eid)
            done += 1

    # (2) employee double-booked (same slot loaned to a second team)
    done = 0
    for _ in range(20000):
        if done >= cnt["EMPLOYEE_DOUBLE_BOOKED"]:
            break
        a = ri.choice(base_assignments)
        eid = a["employee_id"]
        if not free_pick(a) or W.week_hours[(eid, wk(a["shift_date"]))] + SHIFT_HOURS > emp[eid]["_cap"]:
            continue
        others = [t["team_id"] for t in teams if t["team_id"] != a["team_id"] and a["template_code"] in t["_shifts"]]
        if not others:
            continue
        t2 = ri.choice(others)
        b = W.new(eid, t2, a["shift_date"], a["template_code"], "MANUAL", datetime.combine(a["shift_date"] - timedelta(days=3), time(10)),
                  team_by_id[t2]["manager_employee_id"], inj="EMPLOYEE_DOUBLE_BOOKED")
        a["_lock"] = True
        inj_log.append(dict(type="EMPLOYEE_DOUBLE_BOOKED", asg=b, related=a, employee_id=eid, d=a["shift_date"]))
        inj_emp.add(eid)
        done += 1

    # (3) overtime cap exceeded (one extra shift on top of a full week)
    done, used_weeks = 0, set()
    for _ in range(40000):
        if done >= cnt["OVERTIME_CAP_EXCEEDED"]:
            break
        eid = ri.choice(roster_ids)
        e = emp[eid]
        d0 = ri.choice(dates)
        w = wk(d0)
        if eid in inj_emp or W.week_hours[(eid, w)] < e["_cap"]:
            continue
        free = [x for x in dates if wk(x) == w and W.check(eid, x, e["primary_shift_code"], skip=("WEEK",)) is None]
        if not free:
            continue
        d = ri.choice(free)
        a = W.new(eid, e["team_id"], d, e["primary_shift_code"], "MANUAL", datetime.combine(d - timedelta(days=2), time(10)),
                  team_by_id[e["team_id"]]["manager_employee_id"], inj="OVERTIME_CAP_EXCEEDED")
        inj_log.append(dict(type="OVERTIME_CAP_EXCEEDED", asg=a, related=None, employee_id=eid, d=d, week=w))
        inj_emp.add(eid)
        done += 1

    # (4) required skill absent (skill holders replaced by non-holders; history kept as CANCELLED rows)
    done, skill_tags = 0, set()
    for _ in range(40000):
        if done >= cnt["REQUIRED_SKILL_ABSENT"]:
            break
        a0 = ri.choice(base_assignments)
        if a0["status"] != "ACTIVE" or a0["shift_date"] in hol_set:
            continue
        key = (a0["team_id"], a0["shift_date"], a0["template_code"])
        slot = list(W.slot[key])
        if any(not free_pick(x) for x in slot):
            continue
        sk_reqs = [q for q in req_active(key[0], key[2], key[1]) if q["skill_id"]]
        if not sk_reqs:
            continue
        q = ri.choice(sk_reqs)
        holders = [x for x in slot if has_skill(x["employee_id"], q["skill_id"], key[1])]
        if not holders:
            continue
        taken, repl = set(x["employee_id"] for x in slot), []
        ok = True
        for h in holders:
            elig = [x for x in team_by_id[key[0]]["_staff"] if x not in taken and not has_skill(x, q["skill_id"], key[1])
                    and x not in inj_emp and W.check(x, key[1], key[2]) is None]
            if not elig:
                ok = False
                break
            c = ri.choice(elig)
            taken.add(c)
            repl.append(c)
        if not ok:
            continue
        mgr = team_by_id[key[0]]["manager_employee_id"]
        ts = datetime.combine(key[1] - timedelta(days=2), time(10))
        for h, c in zip(holders, repl):
            W.drop(h, "CANCELLED")
            h["_events"].append(("CANCELLED_REPLACED", ts, mgr, None))
            b = W.new(c, key[0], key[1], key[2], "MANUAL", ts, mgr, inj="REQUIRED_SKILL_ABSENT")
            b["_lock"] = True
        inj_log.append(dict(type="REQUIRED_SKILL_ABSENT", asg=None, related=q["requirement_id"], employee_id=None, d=key[1],
                            team=key[0], code=key[2], skill=q["skill_id"]))
        skill_tags.add((key[0], key[1], key[2], q["skill_id"]))
        done += 1

    # (5) swap applied without approval
    done = 0
    for _ in range(20000):
        if done >= cnt["SWAP_APPLIED_WITHOUT_APPROVAL"]:
            break
        a = ri.choice(base_assignments)
        if not free_pick(a) or a["shift_date"] < start + timedelta(days=2) or a["shift_date"] in hol_set:
            continue
        cid = pick_counterpart(a, ri, must_be_eligible=True)
        if cid is None or cid in inj_emp:
            continue
        mgr = team_by_id[a["team_id"]]["manager_employee_id"]
        req_at = a["_start"] - timedelta(hours=ri.randint(24, 10 * 24))
        sw = make_swap(a, cid, req_at, injected="SWAP_APPLIED_WITHOUT_APPROVAL")
        app = req_at + timedelta(hours=ri.randint(2, 20))
        if ri.random() < 0.5:     # variant A: no manager decision exists at all
            sw["_events"].append(("REQUESTED", "APPLIED", app, a["employee_id"]))
        else:                     # variant B: manager REJECTED, swap applied anyway
            dec = req_at + timedelta(hours=ri.randint(1, 5))
            app = max(app, dec + timedelta(minutes=30))     # applied_at must not precede the manager's decision
            sw.update(decided_at=dec, decided_by=mgr, decision_reason=ri.choice(["WEEKLY_CAP", "SKILL_MISMATCH", "REST_VIOLATION"]))
            sw["_events"].append(("REQUESTED", "REJECTED", dec, mgr))
            sw["_events"].append(("REJECTED", "APPLIED", app, a["employee_id"]))
        apply_swap(sw, a, app, a["employee_id"])
        sw["status"] = "APPLIED"
        sw["_new"]["_lock"] = True
        inj_log.append(dict(type="SWAP_APPLIED_WITHOUT_APPROVAL", asg=None, related=sw, employee_id=a["employee_id"], d=a["shift_date"]))
        done += 1

    # ---- finalise IDs (deterministic ordering) ---------------------------------------------
    for n, a in enumerate(sorted(W.assignments, key=lambda x: (x["shift_date"], x["template_code"], x["team_id"], x["_idx"]))):
        a["assignment_id"] = f"ASG-{n + 1:07d}"
        a["shift_id"] = f"SHIFT-{a['shift_date']:%Y-%m-%d}-{a['template_code']}"
        a["template_id"] = f"TPL-{a['template_code']}"
        a["start_ts"], a["end_ts"], a["scheduled_hours"] = a["_start"], a["_end"], SHIFT_HOURS
    for n, sw in enumerate(sorted(swaps, key=lambda x: (x["requested_at"], x["_idx"]))):
        sw["swap_id"] = f"SWP-{year}-{n + 1:06d}"
    for sw in swaps:
        sw["requester_assignment_id"] = sw["_req"]["assignment_id"]
        sw["new_assignment_id"] = sw["_new"]["assignment_id"] if sw["_new"] else None
    for a in W.assignments:
        a["source_swap_id"] = a["_swap"]["swap_id"] if a["_swap"] else None

    asg_rows = sorted(W.assignments, key=lambda x: x["assignment_id"])
    aev_rows = []
    for a in asg_rows:
        for et, ts, actor, sw in a["_events"]:
            aev_rows.append(dict(assignment_id=a["assignment_id"], event_type=et, event_ts=ts, actor_employee_id=actor,
                                 swap_id=sw["swap_id"] if sw else None))
    aev_rows.sort(key=lambda x: (x["event_ts"], x["assignment_id"], x["event_type"]))
    for n, row in enumerate(aev_rows):
        row["event_id"] = f"AEV-{n + 1:07d}"
    swap_rows = sorted(swaps, key=lambda x: x["swap_id"])
    swe_rows = []
    for sw in swap_rows:
        for fr, to, ts, actor in sw["_events"]:
            swe_rows.append(dict(swap_id=sw["swap_id"], from_status=fr, to_status=to, event_ts=ts, actor_employee_id=actor))
    swe_rows.sort(key=lambda x: (x["event_ts"], x["swap_id"]))
    for n, row in enumerate(swe_rows):
        row["event_id"] = f"SWE-{n + 1:06d}"

    # ---- attendance ------------------------------------------------------------------------
    ra = R("attendance")
    active = sorted([a for a in asg_rows if a["status"] == "ACTIVE"], key=lambda a: (a["_start"], a["assignment_id"]))
    acc, last_end, used_ts, att, present, worked_by_asg = defaultdict(float), {}, set(), [], set(), {}

    def add_att(eid, aid, etype, ts, source, reason, var):
        while (eid, ts) in used_ts:
            ts += timedelta(seconds=1)
        used_ts.add((eid, ts))
        att.append(dict(attendance_id=f"ATT-{eid}-{ts:%Y%m%dT%H%M%S}", employee_id=eid, assignment_id=aid, event_type=etype,
                        event_ts=ts, source=source, absence_reason=reason, variance_minutes=var))
        return ts

    for a in active:
        eid, s, en, d = a["employee_id"], a["_start"], a["_end"], a["shift_date"]
        reason = None
        if d in leave_days.get(eid, ()):
            reason = "ON_APPROVED_LEAVE"
        elif eid in last_end and s < last_end[eid]:
            reason = "DOUBLE_BOOKED_CONFLICT"
        elif ra.random() < P.absence_rate:
            reason = ra.choice(["SICK_CALL", "NO_SHOW"])
        if reason:
            add_att(eid, a["assignment_id"], "ABSENT", s, "SYSTEM", reason, None)
            continue
        off = ra.gauss(1.0, 4.0)
        if ra.random() < 0.08:
            off += ra.uniform(5, 25)
        off = max(-25.0, min(60.0, off))
        extra = ra.gauss(6.0, 5.0)
        if ra.random() < 0.08:
            extra = ra.uniform(30, 90)
        extra = max(-8.0, extra)
        cin = s + timedelta(seconds=int(off * 60))
        e = emp[eid]
        key = (eid, wk(d))
        limit_min = (e["_cap"] + e["_cap"] * 0 + OVERTIME_CAP) * 60
        if W.week_hours[key] <= e["_cap"] + OVERTIME_CAP:      # baseline weeks: keep actual hours inside the hard limit
            allowed = limit_min - acc[key]
            out = en + timedelta(minutes=extra)
            nominal = (out - cin).total_seconds() / 60
            if nominal > allowed:
                extra = max(0.0, extra - (nominal - allowed))
                out = en + timedelta(minutes=extra)
                if (out - cin).total_seconds() / 60 > allowed:
                    cin = out - timedelta(minutes=allowed)
        cout = en + timedelta(minutes=extra)
        src = ra.choices(["BADGE", "MOBILE", "MANUAL"], [0.80, 0.15, 0.05])[0]
        t_in = add_att(eid, a["assignment_id"], "CLOCK_IN", cin, src, None, round((cin - s).total_seconds() / 60))
        t_out = add_att(eid, a["assignment_id"], "CLOCK_OUT", cout, src, None, round((cout - en).total_seconds() / 60))
        present.add(a["assignment_id"])
        worked = (t_out - t_in).total_seconds()
        worked_by_asg[a["assignment_id"]] = worked
        acc[key] += worked / 60
        last_end[eid] = en
    for row in att:
        pass
    att.sort(key=lambda x: (x["event_ts"], x["attendance_id"]))
    # variance for ABSENT stays NULL; recompute variance for clock rows against the (possibly shifted) timestamps
    a_by_id = {a["assignment_id"]: a for a in asg_rows}
    for row in att:
        if row["event_type"] == "CLOCK_IN":
            row["variance_minutes"] = round((row["event_ts"] - a_by_id[row["assignment_id"]]["_start"]).total_seconds() / 60)
        elif row["event_type"] == "CLOCK_OUT":
            row["variance_minutes"] = round((row["event_ts"] - a_by_id[row["assignment_id"]]["_end"]).total_seconds() / 60)

    # ---- derived: coverage results, weekly hours, leave balances -----------------------------
    cov, n = [], 0
    for d in dates:
        for t in teams:
            for code in t["_shifts"]:
                slot = W.slot[(t["team_id"], d, code)]
                for q in req_active(t["team_id"], code, d):
                    mem = [x for x in slot if q["skill_id"] is None or has_skill(x["employee_id"], q["skill_id"], d)]
                    req_n = need(q, d)
                    sched, pres = len(mem), sum(1 for x in mem if x["assignment_id"] in present)
                    n += 1
                    cov.append(dict(result_id=f"CRES-{n:07d}", requirement_id=q["requirement_id"], team_id=t["team_id"],
                                    shift_id=f"SHIFT-{d:%Y-%m-%d}-{code}", shift_date=d, template_id=f"TPL-{code}",
                                    skill_id=q["skill_id"], is_holiday=int(d in hol_set), required_staff=req_n,
                                    scheduled_staff=sched, present_staff=pres, scheduled_gap=max(0, req_n - sched),
                                    actual_gap=max(0, req_n - pres)))
    sched_h, work_h = defaultdict(float), defaultdict(float)
    for a in active:
        sched_h[(a["employee_id"], wk(a["shift_date"]))] += a["scheduled_hours"]
        if a["assignment_id"] in worked_by_asg:
            work_h[(a["employee_id"], wk(a["shift_date"]))] += worked_by_asg[a["assignment_id"]] / 3600.0
    wh = []
    for key in sorted(set(sched_h) | set(work_h)):
        eid, w = key
        e = emp[eid]
        y, wn = int(w[:4]), int(w[-2:])
        wsd = date.fromisocalendar(y, wn, 1)
        sh, wo = round(sched_h[key], 2), round(work_h[key], 2)
        lim = e["_cap"] + OVERTIME_CAP
        wh.append(dict(employee_id=eid, iso_week=w, week_start=wsd, scheduled_hours=sh, worked_hours=wo,
                       contract_cap_hours=e["_cap"], overtime_cap_hours=OVERTIME_CAP, hard_limit_hours=lim,
                       overtime_hours=round(max(0.0, wo - e["_cap"]), 2), scheduled_exceeds_limit=int(sh > lim),
                       worked_exceeds_limit=int(wo > lim)))
    appr_days = defaultdict(int)
    for lv in leaves:
        if lv["status"] == "APPROVED" and lv["leave_type"] in LEAVE_ALLOWANCE:
            appr_days[(lv["employee_id"], lv["leave_type"])] += lv["days_requested"]
    lb = []
    for e in staff:
        for lt in ("ANNUAL", "CASUAL", "SICK"):
            ap = appr_days[(e["employee_id"], lt)]
            lb.append(dict(employee_id=e["employee_id"], leave_type=lt, opening_balance_days=LEAVE_ALLOWANCE[lt],
                           approved_days=ap, closing_balance_days=LEAVE_ALLOWANCE[lt] - ap))

    # ---- ground truth (kept in a separate folder; never joined into input tables) --------------
    gt, ginj = [], []
    for it in inj_log:
        ty = it["type"]
        if ty == "EMPLOYEE_DOUBLE_BOOKED":
            a = it["asg"]
            ginj.append(dict(issue_type=ty, entity_type="ShiftAssignment", entity_id=a["assignment_id"], employee_id=it["employee_id"],
                             team_id=a["team_id"], shift_id=a["shift_id"], shift_date=it["d"], related_entity_id=it["related"]["assignment_id"],
                             details="same employee, same shift slot, two teams"))
        elif ty == "APPROVED_LEAVE_OVERLAPS_SHIFT":
            a = it["asg"]
            ginj.append(dict(issue_type=ty, entity_type="ShiftAssignment", entity_id=a["assignment_id"], employee_id=it["employee_id"],
                             team_id=a["team_id"], shift_id=a["shift_id"], shift_date=it["d"], related_entity_id=it["related"],
                             details="ACTIVE assignment on a day covered by an APPROVED leave"))
        elif ty == "OVERTIME_CAP_EXCEEDED":
            a = it["asg"]
            ginj.append(dict(issue_type=ty, entity_type="EmployeeWeek", entity_id=f"{it['employee_id']}|{it['week']}", employee_id=it["employee_id"],
                             team_id=a["team_id"], shift_id=a["shift_id"], shift_date=it["d"], related_entity_id=a["assignment_id"],
                             details="scheduled hours exceed weekly_hour_cap + overtime_cap_hours"))
        elif ty == "REQUIRED_SKILL_ABSENT":
            ginj.append(dict(issue_type=ty, entity_type="CoverageSlot", entity_id=it["related"], employee_id="", team_id=it["team"],
                             shift_id=f"SHIFT-{it['d']:%Y-%m-%d}-{it['code']}", shift_date=it["d"], related_entity_id=it["skill"],
                             details="no scheduled person holds the required skill on this date"))
        else:
            sw = it["related"]
            ginj.append(dict(issue_type=ty, entity_type="SwapRequest", entity_id=sw["swap_id"], employee_id=it["employee_id"],
                             team_id=sw["team_id"], shift_id=sw["shift_id"], shift_date=it["d"], related_entity_id=sw["new_assignment_id"],
                             details="APPLIED without a preceding APPROVED event"))
    for g in ginj:
        g["origin"] = "INJECTED"
    natural = []
    for c in cov:
        if c["skill_id"] and c["required_staff"] > 0 and c["scheduled_staff"] == 0:
            tag = (c["team_id"], c["shift_date"], c["shift_id"][-1], c["skill_id"])
            if tag not in skill_tags:
                natural.append(dict(issue_type="REQUIRED_SKILL_ABSENT", entity_type="CoverageSlot", entity_id=c["requirement_id"],
                                    employee_id="", team_id=c["team_id"], shift_id=c["shift_id"], shift_date=c["shift_date"],
                                    related_entity_id=c["skill_id"], details="skill gap arising from leave/roster limits (not injected)",
                                    origin="RULE_DERIVED"))
    for n, g in enumerate(sorted(ginj + natural, key=lambda x: (x["issue_type"], str(x["shift_date"]), x["entity_id"]))):
        g["issue_id"] = f"GT-{n + 1:06d}"
        g["rule_reference"] = RULES[g["issue_type"]]
        g["expected_decision"] = DECISIONS[g["issue_type"]]
        gt.append(g)

    tables = dict(
        holiday_calendar=hol_rows, skills=skill_rows, shift_templates=tpl_rows,
        employees=emps, teams=teams, team_shift_templates=tst_rows,
        employee_skills=sorted(es_rows, key=lambda x: (x["employee_id"], x["skill_id"])),
        coverage_requirements=reqs, leave_requests=leaves, leave_request_events=lev_rows,
        shift_assignments=asg_rows, assignment_events=aev_rows, swap_requests=swap_rows, swap_events=swe_rows,
        attendance_events=att, coverage_results=cov, weekly_hours=wh, leave_balances=lb)
    return tables, gt


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------
GT_FIELDS = ["issue_id", "issue_type", "entity_type", "entity_id", "employee_id", "team_id", "shift_id", "shift_date",
             "related_entity_id", "origin", "rule_reference", "expected_decision", "details"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sql_value(v, ftype):
    if v is None:
        return None
    if ftype == "bool":
        return int(v)
    if isinstance(v, (datetime, date)):
        return fmtv(v)
    return v


def make_ddl():
    out = ["-- Generated from the data dictionary. Foreign keys are DEFERRABLE so circular references load in one transaction.",
           "PRAGMA foreign_keys = ON;"]
    tmap = {"string": "TEXT", "int": "INTEGER", "float": "REAL", "date": "TEXT", "datetime": "TEXT", "time": "TEXT", "bool": "INTEGER"}
    for t in TABLE_ORDER:
        cols, pks, fks = [], [f["name"] for f in SCHEMA[t] if f["unique"] == "PK"], []
        for f in SCHEMA[t]:
            c = f'  "{f["name"]}" {tmap[f["type"]]}'
            if f["required"]:
                c += " NOT NULL"
            if f["unique"] == "UNIQUE":
                c += " UNIQUE"
            cols.append(c)
            if f["fk"]:
                rt, rc = f["fk"].split(".")
                fks.append(f'  FOREIGN KEY ("{f["name"]}") REFERENCES "{rt}"("{rc}") DEFERRABLE INITIALLY DEFERRED')
        if pks:
            cols.append("  PRIMARY KEY (" + ", ".join(f'"{p}"' for p in pks) + ")")
        out.append(f'CREATE TABLE "{t}" (\n' + ",\n".join(cols + fks) + "\n);")
    return "\n".join(out) + "\n"


def write_docs(path):
    lines = ["# Data dictionary", "",
             "Generated from the single dictionary inside `generate_data.py`. `PK` = primary key (composite when several fields carry it), "
             "`FK` = foreign key, `ENUM:` lists allowed values, `FMT:` is a regex. All timestamps are naive local time. "
             "Required = NOT NULL.", ""]
    for t in TABLE_ORDER:
        lines += [f"## {t}  ({ENTITY_NAMES[t]})", "",
                  "| Field | Type | Req | Allowed values / format | Unit | Unique | Foreign key | Validation rule |",
                  "|---|---|---|---|---|---|---|---|"]
        for f in SCHEMA[t]:
            al = f["allowed"].replace("|", "/")
            lines.append(f"| `{f['name']}` | {f['type']} | {'Y' if f['required'] else 'N'} | {al} | {f['unit']} | {f['unique']} | "
                         f"{f['fk'] or '-'} | {f['rule']} |")
        lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def write_outputs(P, tables, gt):
    out = P.out
    for sub in ("data", "data/derived", "ground_truth", "json", "sql", "docs"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    files, counts = {}, {}
    for t in TABLE_ORDER:
        names = [f["name"] for f in SCHEMA[t]]
        sub = "data/derived" if t in DERIVED_TABLES else "data"
        p = os.path.join(out, sub, f"{t}.csv")
        with open(p, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(names)
            for row in tables[t]:
                w.writerow([fmtv(row.get(n)) for n in names])
        counts[t] = len(tables[t])
        files[os.path.relpath(p, out)] = dict(rows=counts[t])
        if "json" in P.formats:
            jp = os.path.join(out, "json", f"{t}.json")
            with open(jp, "w", encoding="utf-8") as fh:
                fh.write("[\n" + ",\n".join(json.dumps({n: jv(row.get(n)) for n in names}, separators=(",", ":")) for row in tables[t]) + "\n]\n")
            files[os.path.relpath(jp, out)] = dict(rows=counts[t])
    # ground truth (separate folder)
    gp = os.path.join(out, "ground_truth", "ground_truth.csv")
    with open(gp, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(GT_FIELDS)
        for g in gt:
            w.writerow([fmtv(g.get(k)) for k in GT_FIELDS])
    files[os.path.relpath(gp, out)] = dict(rows=len(gt))
    if "json" in P.formats:
        gj = os.path.join(out, "ground_truth", "ground_truth.json")
        with open(gj, "w", encoding="utf-8") as fh:
            fh.write("[\n" + ",\n".join(json.dumps({k: jv(g.get(k)) for k in GT_FIELDS}, separators=(",", ":")) for g in gt) + "\n]\n")
        files[os.path.relpath(gj, out)] = dict(rows=len(gt))
    # docs + sql
    write_docs(os.path.join(out, "docs", "data_dictionary.md"))
    dj = os.path.join(out, "docs", "data_dictionary.json")
    with open(dj, "w", encoding="utf-8") as fh:
        json.dump({"tables": {t: dict(entity=ENTITY_NAMES[t], derived=t in DERIVED_TABLES, fields=SCHEMA[t]) for t in TABLE_ORDER}}, fh, indent=1)
    ddl = make_ddl()
    with open(os.path.join(out, "sql", "schema.sql"), "w", encoding="utf-8") as fh:
        fh.write(ddl)
    conn = sqlite3.connect(":memory:")
    conn.executescript(ddl)
    conn.execute("PRAGMA defer_foreign_keys = ON")
    for t in TABLE_ORDER:
        names = [f["name"] for f in SCHEMA[t]]
        types = {f["name"]: f["type"] for f in SCHEMA[t]}
        conn.executemany(f'INSERT INTO "{t}" VALUES ({",".join("?" * len(names))})',
                         ([sql_value(r.get(n), types[n]) for n in names] for r in tables[t]))
    conn.commit()
    fk_viol = conn.execute("PRAGMA foreign_key_check").fetchall()
    if "sql" in P.formats:
        with open(os.path.join(out, "sql", "seed.sql"), "w", encoding="utf-8") as fh:
            for line in conn.iterdump():
                fh.write(line + "\n")
    conn.close()
    for rel in ("docs/data_dictionary.md", "docs/data_dictionary.json", "sql/schema.sql") + (("sql/seed.sql",) if "sql" in P.formats else ()):
        files[rel] = dict(rows=None)
    for rel in files:
        p = os.path.join(out, rel)
        files[rel]["sha256"], files[rel]["bytes"] = sha256(p), os.path.getsize(p)
    manifest = dict(
        dataset="synthetic_workforce_shift_scheduling", schema_version="1.0", seed=P.seed,
        parameters=dict(employees=P.employees, teams=P.teams, days=P.days, leaves=P.leaves, start=P.start, swaps=P.swaps,
                        absence_rate=P.absence_rate, inject_scale=P.inject_scale, formats=sorted(P.formats)),
        generator_command=(f"python generate_data.py --employees {P.employees} --teams {P.teams} --days {P.days} --leaves {P.leaves} "
                           f"--seed {P.seed} --start {P.start} --formats {','.join(sorted(P.formats))} --out <dir>"),
        python_version=sys.version.split()[0],
        external_sources=[],
        provenance=("Fully synthetic. No external or personal data used. Holiday names/dates form an illustrative synthetic calendar "
                    "(inspired by common Indian public holidays) and must not be used as an authoritative holiday source. "
                    "Emails use the reserved example.invalid domain."),
        sqlite_foreign_key_check_violations=len(fk_viol), row_counts=counts, files=files)
    with open(os.path.join(out, "source_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    return counts, len(fk_viol)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--employees", type=int, default=2000)
    ap.add_argument("--teams", type=int, default=100)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--leaves", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20261022)
    ap.add_argument("--start", default="2026-01-01")
    ap.add_argument("--swaps", type=int, default=None, help="baseline swap requests (default 0.35 x employees)")
    ap.add_argument("--absence-rate", dest="absence_rate", type=float, default=0.025)
    ap.add_argument("--inject-scale", dest="inject_scale", type=float, default=None,
                    help="multiplier for injected edge-case counts (default employees/2000)")
    ap.add_argument("--formats", default="csv,json,sql", help="comma list; csv is always written")
    ap.add_argument("--out", default="dataset")
    P = ap.parse_args()
    P.formats = set(P.formats.split(","))
    tables, gt = generate(P)
    counts, fkv = write_outputs(P, tables, gt)
    print("row counts:")
    for t in TABLE_ORDER:
        print(f"  {t:24s}{counts[t]:>9,}")
    print(f"  {'ground_truth':24s}{len(gt):>9,}")
    print(f"sqlite PRAGMA foreign_key_check violations: {fkv}")
    print(f"written to: {os.path.abspath(P.out)}")


if __name__ == "__main__":
    main()
