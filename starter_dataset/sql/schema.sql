-- Generated from the data dictionary. Foreign keys are DEFERRABLE so circular references load in one transaction.
PRAGMA foreign_keys = ON;
CREATE TABLE "holiday_calendar" (
  "holiday_id" TEXT NOT NULL,
  "holiday_date" TEXT NOT NULL UNIQUE,
  "holiday_name" TEXT NOT NULL,
  "region" TEXT NOT NULL,
  "holiday_type" TEXT NOT NULL,
  PRIMARY KEY ("holiday_id")
);
CREATE TABLE "skills" (
  "skill_id" TEXT NOT NULL,
  "skill_name" TEXT NOT NULL UNIQUE,
  "skill_category" TEXT NOT NULL,
  "is_certification" INTEGER NOT NULL,
  PRIMARY KEY ("skill_id")
);
CREATE TABLE "shift_templates" (
  "template_id" TEXT NOT NULL,
  "template_code" TEXT NOT NULL UNIQUE,
  "template_name" TEXT NOT NULL,
  "start_time" TEXT NOT NULL,
  "end_time" TEXT NOT NULL,
  "crosses_midnight" INTEGER NOT NULL,
  "duration_hours" REAL NOT NULL,
  "effective_from" TEXT NOT NULL,
  "effective_to" TEXT,
  PRIMARY KEY ("template_id")
);
CREATE TABLE "employees" (
  "employee_id" TEXT NOT NULL,
  "team_id" TEXT,
  "manager_id" TEXT,
  "role" TEXT NOT NULL,
  "employment_type" TEXT NOT NULL,
  "is_rostered" INTEGER NOT NULL,
  "primary_shift_code" TEXT,
  "weekly_hour_cap" REAL NOT NULL,
  "overtime_cap_hours" REAL NOT NULL,
  "hire_date" TEXT NOT NULL,
  "end_date" TEXT,
  "status" TEXT NOT NULL,
  "work_email" TEXT NOT NULL UNIQUE,
  PRIMARY KEY ("employee_id"),
  FOREIGN KEY ("team_id") REFERENCES "teams"("team_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("manager_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "teams" (
  "team_id" TEXT NOT NULL,
  "team_name" TEXT NOT NULL UNIQUE,
  "domain" TEXT NOT NULL,
  "manager_employee_id" TEXT NOT NULL,
  "max_concurrent_leave" INTEGER NOT NULL,
  "effective_from" TEXT NOT NULL,
  "effective_to" TEXT,
  "status" TEXT NOT NULL,
  PRIMARY KEY ("team_id"),
  FOREIGN KEY ("manager_employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "team_shift_templates" (
  "team_id" TEXT NOT NULL,
  "template_id" TEXT NOT NULL,
  "effective_from" TEXT NOT NULL,
  PRIMARY KEY ("team_id", "template_id"),
  FOREIGN KEY ("team_id") REFERENCES "teams"("team_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("template_id") REFERENCES "shift_templates"("template_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "employee_skills" (
  "employee_id" TEXT NOT NULL,
  "skill_id" TEXT NOT NULL,
  "proficiency_level" INTEGER NOT NULL,
  "effective_from" TEXT NOT NULL,
  "effective_to" TEXT,
  PRIMARY KEY ("employee_id", "skill_id"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("skill_id") REFERENCES "skills"("skill_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "coverage_requirements" (
  "requirement_id" TEXT NOT NULL,
  "team_id" TEXT NOT NULL,
  "template_id" TEXT NOT NULL,
  "skill_id" TEXT,
  "min_staff" INTEGER NOT NULL,
  "holiday_min_staff" INTEGER NOT NULL,
  "effective_from" TEXT NOT NULL,
  "effective_to" TEXT,
  PRIMARY KEY ("requirement_id"),
  FOREIGN KEY ("team_id") REFERENCES "teams"("team_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("template_id") REFERENCES "shift_templates"("template_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("skill_id") REFERENCES "skills"("skill_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "leave_requests" (
  "leave_id" TEXT NOT NULL,
  "employee_id" TEXT NOT NULL,
  "leave_type" TEXT NOT NULL,
  "start_date" TEXT NOT NULL,
  "end_date" TEXT NOT NULL,
  "days_requested" INTEGER NOT NULL,
  "status" TEXT NOT NULL,
  "submitted_at" TEXT NOT NULL,
  "decided_at" TEXT,
  "decided_by" TEXT,
  "decision_reason" TEXT,
  "cancelled_at" TEXT,
  PRIMARY KEY ("leave_id"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("decided_by") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "leave_request_events" (
  "event_id" TEXT NOT NULL,
  "leave_id" TEXT NOT NULL,
  "from_status" TEXT,
  "to_status" TEXT NOT NULL,
  "event_ts" TEXT NOT NULL,
  "actor_employee_id" TEXT NOT NULL,
  PRIMARY KEY ("event_id"),
  FOREIGN KEY ("leave_id") REFERENCES "leave_requests"("leave_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("actor_employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "shift_assignments" (
  "assignment_id" TEXT NOT NULL,
  "shift_id" TEXT NOT NULL,
  "team_id" TEXT NOT NULL,
  "employee_id" TEXT NOT NULL,
  "template_id" TEXT NOT NULL,
  "shift_date" TEXT NOT NULL,
  "start_ts" TEXT NOT NULL,
  "end_ts" TEXT NOT NULL,
  "scheduled_hours" REAL NOT NULL,
  "status" TEXT NOT NULL,
  "assignment_source" TEXT NOT NULL,
  "source_swap_id" TEXT,
  "created_at" TEXT NOT NULL,
  PRIMARY KEY ("assignment_id"),
  FOREIGN KEY ("team_id") REFERENCES "teams"("team_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("template_id") REFERENCES "shift_templates"("template_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("source_swap_id") REFERENCES "swap_requests"("swap_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "assignment_events" (
  "event_id" TEXT NOT NULL,
  "assignment_id" TEXT NOT NULL,
  "event_type" TEXT NOT NULL,
  "event_ts" TEXT NOT NULL,
  "actor_employee_id" TEXT,
  "swap_id" TEXT,
  PRIMARY KEY ("event_id"),
  FOREIGN KEY ("assignment_id") REFERENCES "shift_assignments"("assignment_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("actor_employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("swap_id") REFERENCES "swap_requests"("swap_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "swap_requests" (
  "swap_id" TEXT NOT NULL,
  "requester_employee_id" TEXT NOT NULL,
  "counterpart_employee_id" TEXT NOT NULL,
  "requester_assignment_id" TEXT NOT NULL,
  "new_assignment_id" TEXT,
  "team_id" TEXT NOT NULL,
  "shift_id" TEXT NOT NULL,
  "shift_date" TEXT NOT NULL,
  "swap_type" TEXT NOT NULL,
  "reason_code" TEXT NOT NULL,
  "status" TEXT NOT NULL,
  "requested_at" TEXT NOT NULL,
  "decided_at" TEXT,
  "decided_by" TEXT,
  "decision_reason" TEXT,
  "applied_at" TEXT,
  PRIMARY KEY ("swap_id"),
  FOREIGN KEY ("requester_employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("counterpart_employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("requester_assignment_id") REFERENCES "shift_assignments"("assignment_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("new_assignment_id") REFERENCES "shift_assignments"("assignment_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("team_id") REFERENCES "teams"("team_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("decided_by") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "swap_events" (
  "event_id" TEXT NOT NULL,
  "swap_id" TEXT NOT NULL,
  "from_status" TEXT,
  "to_status" TEXT NOT NULL,
  "event_ts" TEXT NOT NULL,
  "actor_employee_id" TEXT NOT NULL,
  PRIMARY KEY ("event_id"),
  FOREIGN KEY ("swap_id") REFERENCES "swap_requests"("swap_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("actor_employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "attendance_events" (
  "attendance_id" TEXT NOT NULL,
  "employee_id" TEXT NOT NULL,
  "assignment_id" TEXT,
  "event_type" TEXT NOT NULL,
  "event_ts" TEXT NOT NULL,
  "source" TEXT NOT NULL,
  "absence_reason" TEXT,
  "variance_minutes" INTEGER,
  PRIMARY KEY ("attendance_id"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("assignment_id") REFERENCES "shift_assignments"("assignment_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "coverage_results" (
  "result_id" TEXT NOT NULL,
  "requirement_id" TEXT NOT NULL,
  "team_id" TEXT NOT NULL,
  "shift_id" TEXT NOT NULL,
  "shift_date" TEXT NOT NULL,
  "template_id" TEXT NOT NULL,
  "skill_id" TEXT,
  "is_holiday" INTEGER NOT NULL,
  "required_staff" INTEGER NOT NULL,
  "scheduled_staff" INTEGER NOT NULL,
  "present_staff" INTEGER NOT NULL,
  "scheduled_gap" INTEGER NOT NULL,
  "actual_gap" INTEGER NOT NULL,
  PRIMARY KEY ("result_id"),
  FOREIGN KEY ("requirement_id") REFERENCES "coverage_requirements"("requirement_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("team_id") REFERENCES "teams"("team_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("template_id") REFERENCES "shift_templates"("template_id") DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY ("skill_id") REFERENCES "skills"("skill_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "weekly_hours" (
  "employee_id" TEXT NOT NULL,
  "iso_week" TEXT NOT NULL,
  "week_start" TEXT NOT NULL,
  "scheduled_hours" REAL NOT NULL,
  "worked_hours" REAL NOT NULL,
  "contract_cap_hours" REAL NOT NULL,
  "overtime_cap_hours" REAL NOT NULL,
  "hard_limit_hours" REAL NOT NULL,
  "overtime_hours" REAL NOT NULL,
  "scheduled_exceeds_limit" INTEGER NOT NULL,
  "worked_exceeds_limit" INTEGER NOT NULL,
  PRIMARY KEY ("employee_id", "iso_week"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE "leave_balances" (
  "employee_id" TEXT NOT NULL,
  "leave_type" TEXT NOT NULL,
  "opening_balance_days" INTEGER NOT NULL,
  "approved_days" INTEGER NOT NULL,
  "closing_balance_days" INTEGER NOT NULL,
  PRIMARY KEY ("employee_id", "leave_type"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id") DEFERRABLE INITIALLY DEFERRED
);
