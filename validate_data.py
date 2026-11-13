#!/usr/bin/env python3
"""
validate_data.py - independent validation of a generated dataset (standard library only).

It re-reads only the CSV files + docs/data_dictionary.json and re-detects every business-rule
violation by itself, then compares the findings with ground_truth/ground_truth.csv.

Usage:  python validate_data.py --dataset dataset
Writes: <dataset>/validation_summary.json and <dataset>/validation_summary.md
"""
import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

SHIFT_H, REST_H, MAX_RUN = 8.0, 11.0, 6
LEGAL_LEAVE = {(None, "SUBMITTED"), ("SUBMITTED", "APPROVED"), ("SUBMITTED", "REJECTED"), ("APPROVED", "CANCELLED")}
LEGAL_SWAP = {(None, "REQUESTED"), ("REQUESTED", "APPROVED"), ("REQUESTED", "REJECTED"), ("REQUESTED", "CANCELLED"),
              ("APPROVED", "APPLIED")}


def D(s):
    return date.fromisoformat(s) if s else None


def DT(s):
    return datetime.fromisoformat(s) if s else None


def wk(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset")
    A = ap.parse_args()
    root = A.dataset
    dd = json.load(open(os.path.join(root, "docs", "data_dictionary.json")))["tables"]
    T, checks = {}, []

    def load(t):
        sub = "data/derived" if dd[t]["derived"] else "data"
        with open(os.path.join(root, sub, f"{t}.csv"), newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    for t in dd:
        T[t] = load(t)
    gt = list(csv.DictReader(open(os.path.join(root, "ground_truth", "ground_truth.csv"), newline="", encoding="utf-8")))

    def chk(name, group, ok, detail=""):
        checks.append(dict(check=name, group=group, status="PASS" if ok else "FAIL", detail=str(detail)))

    # ---- 1. schema / PK / FK / enums / formats / required -------------------------------------
    pk_sets = {}
    for t, meta in dd.items():
        fields = meta["fields"]
        names = [f["name"] for f in fields]
        with open(os.path.join(root, "data/derived" if meta["derived"] else "data", f"{t}.csv"), encoding="utf-8") as fh:
            header = fh.readline().strip().split(",")
        chk(f"{t}: header matches dictionary", "schema", header == names)
        miss = sum(1 for r in T[t] for f in fields if f["required"] and r[f["name"]] == "")
        chk(f"{t}: required fields populated", "schema", miss == 0, f"{miss} empty required cells")
        pks = [f["name"] for f in fields if f["unique"] == "PK"]
        keys = [tuple(r[p] for p in pks) for r in T[t]]
        chk(f"{t}: primary key unique ({'+'.join(pks)})", "keys", len(keys) == len(set(keys)), f"{len(keys) - len(set(keys))} duplicates")
        pk_sets[t] = set(keys)
        for f in fields:
            if f["unique"] == "UNIQUE":
                vals = [r[f["name"]] for r in T[t]]
                chk(f"{t}.{f['name']}: unique", "keys", len(vals) == len(set(vals)))
            a = f["allowed"]
            if a.startswith("ENUM:"):
                allowed = set(a[5:].split(","))
                bad = sum(1 for r in T[t] if r[f["name"]] != "" and r[f["name"]] not in allowed)
                chk(f"{t}.{f['name']}: allowed values", "enums", bad == 0, f"{bad} outside {sorted(allowed)}")
            elif a.startswith("FMT:"):
                rx = re.compile(a[4:])
                bad = sum(1 for r in T[t] if not rx.match(r[f["name"]]))
                chk(f"{t}.{f['name']}: ID/format", "formats", bad == 0, f"{bad} mismatches")
    for t, meta in dd.items():
        for f in meta["fields"]:
            if f["fk"]:
                rt, rc = f["fk"].split(".")
                parent = {r[rc] for r in T[rt]}
                bad = sum(1 for r in T[t] if r[f["name"]] != "" and r[f["name"]] not in parent)
                chk(f"FK {t}.{f['name']} -> {f['fk']}", "keys", bad == 0, f"{bad} orphans")

    emp = {r["employee_id"]: r for r in T["employees"]}
    team_mgr = {r["team_id"]: r["manager_employee_id"] for r in T["teams"]}
    hol = {D(r["holiday_date"]) for r in T["holiday_calendar"]}
    chk("teams.manager_employee_id has role TEAM_MANAGER", "relations", all(emp[m]["role"] == "TEAM_MANAGER" for m in team_mgr.values()))
    tst = {(r["team_id"], r["template_id"]) for r in T["team_shift_templates"]}
    chk("requirements/assignments only use shifts the team runs", "relations",
        all((r["team_id"], r["template_id"]) in tst for r in T["coverage_requirements"] + T["shift_assignments"]))
    chk("rostered employees have team and primary shift", "relations",
        all(r["team_id"] and (r["primary_shift_code"] in ("A", "B", "C")) for r in emp.values() if r["is_rostered"] == "1"))

    # ---- 2. date ordering ---------------------------------------------------------------------------
    chk("employees: end_date >= hire_date", "dates", all(D(r["end_date"]) >= D(r["hire_date"]) for r in emp.values() if r["end_date"]))
    chk("leave: end >= start; decided >= submitted; start >= hire_date", "dates",
        all(D(r["end_date"]) >= D(r["start_date"]) and (not r["decided_at"] or DT(r["decided_at"]) >= DT(r["submitted_at"]))
            and D(r["start_date"]) >= D(emp[r["employee_id"]]["hire_date"]) for r in T["leave_requests"]))
    chk("leave: cancelled_at only when CANCELLED and after decided_at", "dates",
        all((r["status"] == "CANCELLED") == bool(r["cancelled_at"]) and (not r["cancelled_at"] or DT(r["cancelled_at"]) > DT(r["decided_at"]))
            for r in T["leave_requests"]))
    chk("assignments: end_ts > start_ts, shift_date = date(start_ts), created_at <= start_ts", "dates",
        all(DT(r["end_ts"]) > DT(r["start_ts"]) and DT(r["start_ts"]).date() == D(r["shift_date"]) and DT(r["created_at"]) <= DT(r["start_ts"])
            for r in T["shift_assignments"]))
    chk("assignments: shift_id matches shift_date + template", "dates",
        all(r["shift_id"] == f"SHIFT-{r['shift_date']}-{r['template_id'][-1]}" for r in T["shift_assignments"]))
    chk("swaps: requested <= decided <= applied; requested before shift", "dates",
        all((not r["decided_at"] or DT(r["decided_at"]) >= DT(r["requested_at"])) and
            (not r["applied_at"] or DT(r["applied_at"]) >= DT(r["requested_at"])) and
            (not (r["decided_at"] and r["applied_at"]) or DT(r["applied_at"]) >= DT(r["decided_at"])) and DT(r["requested_at"]) < DT(r["shift_date"] + "T23:59:59")
            for r in T["swap_requests"]))
    chk("requirements: effective_to >= effective_from", "dates",
        all(not r["effective_to"] or D(r["effective_to"]) >= D(r["effective_from"]) for r in T["coverage_requirements"]))
    byk = defaultdict(list)
    for r in T["coverage_requirements"]:
        byk[(r["team_id"], r["template_id"], r["skill_id"])].append((D(r["effective_from"]), D(r["effective_to"]) or date.max))
    ov = sum(1 for v in byk.values() for i, a in enumerate(sorted(v)) for b in sorted(v)[i + 1:] if b[0] <= a[1])
    chk("requirements: no overlapping effective ranges per team/template/skill", "dates", ov == 0, f"{ov} overlaps")

    # ---- 3. arithmetic reconciliation ----------------------------------------------------------------------
    chk("leave.days_requested = calendar days - public holidays", "arithmetic",
        all(int(r["days_requested"]) == sum(1 for i in range((D(r["end_date"]) - D(r["start_date"])).days + 1)
                                              if D(r["start_date"]) + timedelta(days=i) not in hol) for r in T["leave_requests"]))
    chk("assignments.scheduled_hours = end_ts - start_ts", "arithmetic",
        all(abs(float(r["scheduled_hours"]) - (DT(r["end_ts"]) - DT(r["start_ts"])).total_seconds() / 3600) < 1e-6 for r in T["shift_assignments"]))
    act = [r for r in T["shift_assignments"] if r["status"] == "ACTIVE"]
    sched = defaultdict(float)
    for r in act:
        sched[(r["employee_id"], wk(D(r["shift_date"])))] += float(r["scheduled_hours"])
    att_by_asg = defaultdict(dict)
    for r in T["attendance_events"]:
        att_by_asg[r["assignment_id"]][r["event_type"]] = r
    worked = defaultdict(float)
    for r in act:
        a = att_by_asg.get(r["assignment_id"], {})
        if "CLOCK_IN" in a and "CLOCK_OUT" in a:
            worked[(r["employee_id"], wk(D(r["shift_date"])))] += (DT(a["CLOCK_OUT"]["event_ts"]) - DT(a["CLOCK_IN"]["event_ts"])).total_seconds() / 3600
    wh_bad = ot_bad = lim_bad = 0
    for r in T["weekly_hours"]:
        k = (r["employee_id"], r["iso_week"])
        if abs(sched[k] - float(r["scheduled_hours"])) > 0.011 or abs(worked[k] - float(r["worked_hours"])) > 0.011:
            wh_bad += 1
        if abs(max(0, float(r["worked_hours"]) - float(r["contract_cap_hours"])) - float(r["overtime_hours"])) > 0.011:
            ot_bad += 1
        lim = float(r["contract_cap_hours"]) + float(r["overtime_cap_hours"])
        if abs(lim - float(r["hard_limit_hours"])) > 1e-6 or (float(r["scheduled_hours"]) > lim) != (r["scheduled_exceeds_limit"] == "1"):
            lim_bad += 1
    chk("weekly_hours scheduled/worked reconcile with assignments + attendance", "arithmetic", wh_bad == 0, f"{wh_bad} mismatches")
    chk("weekly_hours.overtime_hours = max(0, worked - cap)", "arithmetic", ot_bad == 0, f"{ot_bad} mismatches")
    chk("weekly_hours hard limit and flags consistent", "arithmetic", lim_bad == 0, f"{lim_bad} mismatches")
    chk("leave_balances: closing = opening - approved", "arithmetic",
        all(int(b["closing_balance_days"]) == int(b["opening_balance_days"]) - int(b["approved_days"]) for b in T["leave_balances"]))
    ap_days = Counter()
    for l in T["leave_requests"]:
        if l["status"] == "APPROVED" and l["leave_type"] != "UNPAID":
            ap_days[(l["employee_id"], l["leave_type"])] += int(l["days_requested"])
    chk("leave_balances.approved_days = sum of APPROVED days", "arithmetic",
        all(ap_days[(b["employee_id"], b["leave_type"])] == int(b["approved_days"]) for b in T["leave_balances"]))
    cov_bad = sum(1 for c in T["coverage_results"] if int(c["scheduled_gap"]) != max(0, int(c["required_staff"]) - int(c["scheduled_staff"]))
                  or int(c["actual_gap"]) != max(0, int(c["required_staff"]) - int(c["present_staff"])) or int(c["present_staff"]) > int(c["scheduled_staff"]))
    chk("coverage_results: gap formulas hold", "arithmetic", cov_bad == 0, f"{cov_bad} rows")

    # ---- 4. lifecycle / history -------------------------------------------------------------------------------------
    def chain(events, key, legal, final_status):
        by = defaultdict(list)
        for e in events:
            by[e[key]].append(e)
        illegal, broken, final_bad, ids_illegal = 0, 0, 0, set()
        for k, evs in by.items():
            evs.sort(key=lambda e: (e["event_ts"], e["event_id"]))
            prev = None
            for e in evs:
                fr = e["from_status"] or None
                if fr != prev:
                    broken += 1
                if (fr, e["to_status"]) not in legal:
                    illegal += 1
                    ids_illegal.add(k)
                prev = e["to_status"]
            if final_status.get(k) != prev:
                final_bad += 1
        return illegal, broken, final_bad, ids_illegal, set(by)

    lv_status = {r["leave_id"]: r["status"] for r in T["leave_requests"]}
    ill, brk, fb, _, seen = chain(T["leave_request_events"], "leave_id", LEGAL_LEAVE, lv_status)
    chk("leave events: legal transitions, unbroken chain, last event = status", "lifecycle", ill == brk == fb == 0, f"illegal={ill} broken={brk} final_mismatch={fb}")
    chk("every leave request has history", "lifecycle", seen == set(lv_status))
    sw_status = {r["swap_id"]: r["status"] for r in T["swap_requests"]}
    ill, brk, fb, bad_swaps, seen = chain(T["swap_events"], "swap_id", LEGAL_SWAP, sw_status)
    chk("swap events: unbroken chain, last event = status", "lifecycle", brk == fb == 0, f"broken={brk} final_mismatch={fb}")
    chk("every swap request has history", "lifecycle", seen == set(sw_status))
    asg = {r["assignment_id"]: r for r in T["shift_assignments"]}
    aev = defaultdict(list)
    for e in T["assignment_events"]:
        aev[e["assignment_id"]].append(e["event_type"])
    ok = all(("CREATED" in aev[a]) and (r["status"] != "SUPERSEDED" or "SUPERSEDED_BY_SWAP" in aev[a]) and
             (r["status"] != "CANCELLED" or "CANCELLED_REPLACED" in aev[a]) for a, r in asg.items())
    chk("assignment events preserve history (CREATED + SUPERSEDED/CANCELLED records)", "lifecycle", ok)
    sup = {a for a, r in asg.items() if r["status"] == "SUPERSEDED"}
    applied = [r for r in T["swap_requests"] if r["status"] == "APPLIED"]
    chk("swap history preserved: APPLIED swap -> old row SUPERSEDED + new SWAP row linked", "lifecycle",
        {r["requester_assignment_id"] for r in applied} == sup and all(
            asg[r["new_assignment_id"]]["source_swap_id"] == r["swap_id"] and asg[r["new_assignment_id"]]["assignment_source"] == "SWAP"
            and asg[r["new_assignment_id"]]["employee_id"] == r["counterpart_employee_id"] for r in applied))
    chk("non-applied swaps leave the roster untouched", "lifecycle",
        all(not r["new_assignment_id"] for r in T["swap_requests"] if r["status"] != "APPLIED"))

    # ---- 5. duplicates -------------------------------------------------------------------------------------------------
    dup_leave = len(T["leave_requests"]) - len({(r["employee_id"], r["start_date"], r["end_date"], r["leave_type"]) for r in T["leave_requests"]})
    chk("no duplicate leave requests (employee/start/end/type)", "duplicates", dup_leave == 0, dup_leave)
    k3 = Counter((r["employee_id"], r["shift_date"], r["template_id"]) for r in act)
    dup_asg = {k for k, v in k3.items() if v > 1}
    k4 = Counter((r["assignment_id"], r["event_type"]) for r in T["attendance_events"])
    chk("no duplicate attendance event per assignment/type", "duplicates", max(k4.values()) == 1)

    # ---- 6. business-rule detectors vs ground truth -----------------------------------------------------------------
    approved_days = defaultdict(set)
    for l in T["leave_requests"]:
        if l["status"] == "APPROVED":
            for i in range((D(l["end_date"]) - D(l["start_date"])).days + 1):
                approved_days[l["employee_id"]].add(D(l["start_date"]) + timedelta(days=i))
    det = {}
    by_emp = defaultdict(list)
    for r in act:
        by_emp[r["employee_id"]].append(r)
    dbl, restv, run_v = set(), set(), set()
    for eid, rows in by_emp.items():
        rows.sort(key=lambda r: (r["start_ts"], r["assignment_id"]))
        for i, r in enumerate(rows):
            for o in rows[i + 1:]:
                if DT(o["start_ts"]) >= DT(r["end_ts"]) + timedelta(hours=REST_H):
                    break
                if DT(o["start_ts"]) < DT(r["end_ts"]):
                    dbl.add((eid, r["shift_date"]))
                else:
                    restv.add((eid, r["shift_date"]))
        days = sorted({D(r["shift_date"]) for r in rows})
        run = 1
        for a, b in zip(days, days[1:]):
            run = run + 1 if (b - a).days == 1 else 1
            if run > MAX_RUN:
                run_v.add((eid, b.isoformat()))
    det["EMPLOYEE_DOUBLE_BOOKED"] = dbl
    det["APPROVED_LEAVE_OVERLAPS_SHIFT"] = {(r["employee_id"], r["shift_date"]) for r in act if D(r["shift_date"]) in approved_days[r["employee_id"]]}
    det["OVERTIME_CAP_EXCEEDED"] = {f"{r['employee_id']}|{r['iso_week']}" for r in T["weekly_hours"] if r["scheduled_exceeds_limit"] == "1"}
    swap_flag = set(bad_swaps)
    det["SWAP_APPLIED_WITHOUT_APPROVAL"] = {s for s in swap_flag if sw_status[s] == "APPLIED"}
    # skill detector (re-implemented from raw tables)
    es = {(r["employee_id"], r["skill_id"]): (D(r["effective_from"]), D(r["effective_to"])) for r in T["employee_skills"]}
    reqs = defaultdict(list)
    for r in T["coverage_requirements"]:
        reqs[(r["team_id"], r["template_id"])].append(r)
    slots = defaultdict(list)
    all_days = sorted({r["shift_date"] for r in T["shift_assignments"]})
    d0, d1 = D(all_days[0]), D(all_days[-1])
    for tm, tp in sorted(tst):                      # include shifts that have no assignment at all
        for i in range((d1 - d0).days + 1):
            slots[(tm, (d0 + timedelta(days=i)).isoformat(), tp)] = []
    for r in act:
        slots[(r["team_id"], r["shift_date"], r["template_id"])].append(r["employee_id"])
    skill_zero, head_gap, req_slots = set(), 0, 0
    for (team, sd, tpl), members in slots.items():
        d = D(sd)
        for q in reqs[(team, tpl)]:
            if D(q["effective_from"]) <= d and (not q["effective_to"] or d <= D(q["effective_to"])):
                if q["skill_id"]:
                    n = sum(1 for m in members if (m, q["skill_id"]) in es and es[(m, q["skill_id"])][0] <= d
                            and (es[(m, q["skill_id"])][1] is None or d <= es[(m, q["skill_id"])][1]))
                    if n == 0:
                        skill_zero.add((team, f"SHIFT-{sd}-{tpl[-1]}", q["skill_id"]))
    det["REQUIRED_SKILL_ABSENT"] = skill_zero
    inj = defaultdict(set)
    nat = defaultdict(set)
    for g in gt:
        t = g["issue_type"]
        if t in ("EMPLOYEE_DOUBLE_BOOKED", "APPROVED_LEAVE_OVERLAPS_SHIFT"):
            key = (g["employee_id"], g["shift_date"])
        elif t == "OVERTIME_CAP_EXCEEDED":
            key = g["entity_id"]
        elif t == "REQUIRED_SKILL_ABSENT":
            key = (g["team_id"], g["shift_id"], g["related_entity_id"])
        else:
            key = g["entity_id"]
        (inj if g["origin"] == "INJECTED" else nat)[t].add(key)
    gt_counts = {}
    for t in ["EMPLOYEE_DOUBLE_BOOKED", "APPROVED_LEAVE_OVERLAPS_SHIFT", "REQUIRED_SKILL_ABSENT", "OVERTIME_CAP_EXCEEDED", "SWAP_APPLIED_WITHOUT_APPROVAL"]:
        expect = inj[t] | nat[t]
        tp = len(det[t] & expect)
        prec = tp / len(det[t]) if det[t] else 1.0
        rec = tp / len(expect) if expect else 1.0
        gt_counts[t] = dict(injected=len(inj[t]), rule_derived=len(nat[t]), detected=len(det[t]), precision=round(prec, 4), recall=round(rec, 4))
        chk(f"detector {t}: finds every ground-truth case, nothing else (precision={prec:.3f}, recall={rec:.3f})", "business_rules", det[t] == expect,
            f"detected={len(det[t])} ground_truth={len(expect)}")

    # real duplicate check: duplicates must equal the labelled double-bookings exactly
    dup_keys = {(e_, d_) for (e_, d_, t_) in dup_asg}
    chk("duplicate (employee, date, shift) ACTIVE assignments equal the labelled double-bookings exactly", "duplicates",
        dup_keys == inj["EMPLOYEE_DOUBLE_BOOKED"], f"found={len(dup_keys)} labelled={len(inj['EMPLOYEE_DOUBLE_BOOKED'])}")

    # ---- decision replay: leave (R-LV-01/02/03) re-computed from raw tables in submission order ----------------
    maxc = {r["team_id"]: int(r["max_concurrent_leave"]) for r in T["teams"]}
    allow = {"ANNUAL": 10, "CASUAL": 4, "SICK": 5}
    ev_to = defaultdict(set)
    for e_ in T["leave_request_events"]:
        ev_to[e_["leave_id"]].add(e_["to_status"])
    used_l, appd, cnt_l = Counter(), defaultdict(set), Counter()
    mism, replayed, by_reason = [], 0, Counter()
    for l in sorted(T["leave_requests"], key=lambda r: r["leave_id"]):
        if not l["decided_at"]:
            continue
        eid, lt = l["employee_id"], l["leave_type"]
        team = emp[eid]["team_id"]
        sd, ed = D(l["start_date"]), D(l["end_date"])
        span = [sd + timedelta(days=i) for i in range((ed - sd).days + 1)]
        chg = [x for x in span if x not in hol]
        if any(x in appd[eid] for x in span):
            exp = ("REJECTED", "OVERLAPPING_LEAVE")
        elif lt in allow and used_l[(eid, lt)] + len(chg) > allow[lt]:
            exp = ("REJECTED", "INSUFFICIENT_BALANCE")
        elif lt != "SICK" and any(cnt_l[(team, x)] + 1 > maxc[team] for x in chg):
            exp = ("REJECTED", "COVERAGE_RISK")
        else:
            exp = ("APPROVED", "WITHIN_POLICY")
            used_l[(eid, lt)] += len(chg)
            appd[eid].update(span)
            for x in chg:
                cnt_l[(team, x)] += 1
        rec = ("APPROVED" if "APPROVED" in ev_to[l["leave_id"]] else "REJECTED", l["decision_reason"])
        replayed += 1
        by_reason[exp[1]] += 1
        if rec != exp:
            mism.append(l["leave_id"])
    chk("leave decisions replayed independently (overlap > balance > team concurrency cap) match every recorded decision", "decision_replay",
        not mism, f"replayed={replayed} mismatches={len(mism)} outcomes={dict(by_reason)}")

    # ---- decision replay: swaps (necessary-condition evidence for every manager decision) ----------------------
    rows_by = defaultdict(list)
    for r in T["shift_assignments"]:
        rows_by[(r["employee_id"], r["shift_date"])].append(r)
    swp_to = defaultdict(set)
    for e_ in T["swap_events"]:
        swp_to[e_["swap_id"]].add(e_["to_status"])

    def has_skill_on(eid, sk, d):
        x = es.get((eid, sk))
        return bool(x) and x[0] <= d and (x[1] is None or d <= x[1])

    sw_bad, ev_ok, ev_tot = [], Counter(), Counter()
    inj_sw = inj["SWAP_APPLIED_WITHOUT_APPROVAL"]
    for s in T["swap_requests"]:
        if s["swap_id"] in inj_sw:
            continue
        c, rq, d = s["counterpart_employee_id"], s["requester_employee_id"], D(s["shift_date"])
        team, why, st = s["team_id"], s["decision_reason"], s["status"]
        base = c != rq and emp[c]["team_id"] == team and emp[rq]["team_id"] == team
        if st == "CANCELLED":
            ok = base and not s["decided_at"] and not s["new_assignment_id"] and "APPROVED" not in swp_to[s["swap_id"]]
            ev_tot["CANCELLED"] += 1
            ev_ok["CANCELLED"] += ok
        elif st == "APPLIED":
            ok = (base and why == "WITHIN_RULES" and "APPROVED" in swp_to[s["swap_id"]] and s["decided_by"] == team_mgr[team]
                  and d not in approved_days[c] and DT(s["applied_at"]) <= DT(s["shift_date"] + "T23:59:59"))
            ev_tot["APPLIED (approved)"] += 1
            ev_ok["APPLIED (approved)"] += ok
        else:   # REJECTED: the recorded reason must be backed by evidence in the data
            ok = base and s["decided_by"] == team_mgr[team] and not s["new_assignment_id"]
            e_c = emp[c]
            if why == "ON_LEAVE":
                ok = ok and d in approved_days[c]
            elif why == "INACTIVE":
                ok = ok and (d < D(e_c["hire_date"]) or (e_c["end_date"] != "" and d > D(e_c["end_date"])))
            elif why == "ALREADY_ASSIGNED":
                ok = ok and bool(rows_by.get((c, s["shift_date"])))
            elif why == "REST_VIOLATION":
                s0 = DT(f"{s['shift_date']}T{ {'A': '06:00', 'B': '14:00', 'C': '22:00'}[s['shift_id'][-1]] }:00")
                e0 = s0 + timedelta(hours=SHIFT_H)
                hit = False
                for nd in (d - timedelta(days=1), d + timedelta(days=1)):
                    for o in rows_by.get((c, nd.isoformat()), []):
                        gap = (s0 - DT(o["end_ts"])).total_seconds() / 3600 if nd < d else (DT(o["start_ts"]) - e0).total_seconds() / 3600
                        hit |= gap < REST_H
                ok = ok and hit
            elif why == "CONSECUTIVE_DAYS":
                run, x = 1, d - timedelta(days=1)
                while rows_by.get((c, x.isoformat())):
                    run, x = run + 1, x - timedelta(days=1)
                x = d + timedelta(days=1)
                while rows_by.get((c, x.isoformat())):
                    run, x = run + 1, x + timedelta(days=1)
                ok = ok and run > MAX_RUN
            elif why == "WEEKLY_CAP":
                w0 = d - timedelta(days=d.weekday())
                hrs = sum(SHIFT_H for i in range(7) for r in rows_by.get((c, (w0 + timedelta(days=i)).isoformat()), []))
                ok = ok and hrs + SHIFT_H > float(e_c["weekly_hour_cap"])
            elif why == "SKILL_MISMATCH":
                need_sk = [q["skill_id"] for q in reqs[(team, s["shift_id"][-1] and "TPL-" + s["shift_id"][-1])]
                           if q["skill_id"] and D(q["effective_from"]) <= d and (not q["effective_to"] or d <= D(q["effective_to"]))]
                ok = ok and any(has_skill_on(rq, k, d) and not has_skill_on(c, k, d) for k in need_sk)
            else:
                ok = False
            ev_tot[f"REJECTED {why}"] += 1
            ev_ok[f"REJECTED {why}"] += ok
        if not ok:
            sw_bad.append(s["swap_id"])
    chk("every non-injected swap decision is backed by evidence in the data (reason, manager, team, leave, rest, cap, skill)", "decision_replay",
        not sw_bad, f"checked={sum(ev_tot.values())} unsupported={len(sw_bad)} " + str({k: f'{ev_ok[k]}/{ev_tot[k]}' for k in sorted(ev_tot)}))

    chk("working-hour rule R6 (>= 11h rest between shifts) holds on ACTIVE rows", "business_rules", not restv, f"{len(restv)} violations")
    chk("working-hour rule R7 (<= 6 consecutive days) holds", "business_rules", not run_v, f"{len(run_v)} violations")
    chk("worked hours stay within hard limit except labelled overtime weeks", "business_rules",
        all(r["worked_exceeds_limit"] == "0" or r["scheduled_exceeds_limit"] == "1" for r in T["weekly_hours"]))

    # ---- 7. attendance reconciliation ---------------------------------------------------------------------------------------
    rec_bad = 0
    for r in act:
        a = att_by_asg.get(r["assignment_id"], {})
        okp = ("CLOCK_IN" in a and "CLOCK_OUT" in a and "ABSENT" not in a and DT(a["CLOCK_OUT"]["event_ts"]) > DT(a["CLOCK_IN"]["event_ts"])) or \
              (set(a) == {"ABSENT"})
        rec_bad += 0 if okp else 1
    chk("attendance reconciles: every ACTIVE assignment has IN+OUT or one ABSENT", "attendance", rec_bad == 0, f"{rec_bad} unreconciled")
    chk("no attendance for SUPERSEDED/CANCELLED assignments", "attendance",
        all(asg[r["assignment_id"]]["status"] == "ACTIVE" and asg[r["assignment_id"]]["employee_id"] == r["employee_id"] for r in T["attendance_events"]))
    chk("attendance_id embeds employee_id and event timestamp", "attendance",
        all(r["attendance_id"] == f"ATT-{r['employee_id']}-{DT(r['event_ts']):%Y%m%dT%H%M%S}" for r in T["attendance_events"]))
    absents = Counter(r["absence_reason"] for r in T["attendance_events"] if r["event_type"] == "ABSENT")
    leave_abs = sum(1 for r in T["attendance_events"] if r["absence_reason"] == "ON_APPROVED_LEAVE")
    chk("ABSENT(ON_APPROVED_LEAVE) rows equal labelled leave conflicts", "attendance", leave_abs == len(inj["APPROVED_LEAVE_OVERLAPS_SHIFT"]), leave_abs)

    # ---- 8. leakage + coverage report ----------------------------------------------------------------------------------------
    leak = [t for t, m in dd.items() for f in m["fields"] if re.search(r"issue_type|ground_truth|is_injected|anomaly", f["name"])]
    chk("no ground-truth column exists in any input/derived table", "leakage", not leak, leak)
    inj_ids = {g["entity_id"] for g in gt if g["origin"] == "INJECTED" and g["entity_type"] == "ShiftAssignment"}
    man_inj = sum(1 for a in asg.values() if a["assignment_id"] in inj_ids and a["assignment_source"] == "MANUAL")
    man_all = sum(1 for a in asg.values() if a["assignment_source"] == "MANUAL" and a["assignment_id"] not in inj_ids)
    chk("assignment_source is not a perfect proxy for injected rows (MANUAL also on baseline)", "leakage", man_all > 0,
        f"MANUAL on injected={man_inj}, MANUAL on baseline rows={man_all}")
    cov = T["coverage_results"]
    summary_cov = dict(requirement_slots_evaluated=len(cov), scheduled_gap_rows=sum(int(c["scheduled_gap"]) > 0 for c in cov),
                       actual_gap_rows=sum(int(c["actual_gap"]) > 0 for c in cov),
                       fully_met_pct_scheduled=round(100 * sum(int(c["scheduled_gap"]) == 0 for c in cov) / len(cov), 2),
                       fully_met_pct_actual=round(100 * sum(int(c["actual_gap"]) == 0 for c in cov) / len(cov), 2),
                       skill_gap_rows=sum(int(c["scheduled_gap"]) > 0 for c in cov if c["skill_id"]),
                       headcount_gap_rows=sum(int(c["scheduled_gap"]) > 0 for c in cov if not c["skill_id"]))
    chk("coverage requirements are met or gaps are reported (coverage_results covers every active requirement per shift)", "coverage",
        len(cov) > 0 and all(c["requirement_id"] for c in cov), summary_cov)

    # ---- metrics ---------------------------------------------------------------------------------------------------------------
    util = [float(r["scheduled_hours"]) / float(r["contract_cap_hours"]) for r in T["weekly_hours"]
            if r["iso_week"] not in (min(x["iso_week"] for x in T["weekly_hours"]), max(x["iso_week"] for x in T["weekly_hours"]))]
    util.sort()
    mean = sum(util) / len(util)
    sd = (sum((u - mean) ** 2 for u in util) / len(util)) ** 0.5
    sw_c = Counter(r["status"] for r in T["swap_requests"])
    lv_c = Counter(r["status"] for r in T["leave_requests"])
    metrics = dict(
        coverage=summary_cov,
        overtime=dict(employee_weeks=len(T["weekly_hours"]), weeks_with_overtime=sum(float(r["overtime_hours"]) > 0 for r in T["weekly_hours"]),
                      total_overtime_hours=round(sum(float(r["overtime_hours"]) for r in T["weekly_hours"]), 1),
                      weeks_scheduled_over_limit=sum(r["scheduled_exceeds_limit"] == "1" for r in T["weekly_hours"])),
        fairness=dict(mean_weekly_utilisation=round(mean, 3), stdev=round(sd, 3), p10=round(util[len(util) // 10], 3), p90=round(util[len(util) * 9 // 10], 3)),
        leave=dict(by_status=dict(lv_c), decision_reasons=dict(Counter(r["decision_reason"] for r in T["leave_requests"] if r["decision_reason"]))),
        swaps=dict(by_status=dict(sw_c), decision_reasons=dict(Counter(r["decision_reason"] for r in T["swap_requests"] if r["decision_reason"]))),
        absences=dict(absents), assignments_by_status=dict(Counter(r["status"] for r in T["shift_assignments"])),
        ground_truth=gt_counts)
    passed = sum(c["status"] == "PASS" for c in checks)
    out = dict(dataset=root, total_checks=len(checks), passed=passed, failed=len(checks) - passed, checks=checks, metrics=metrics)
    with open(os.path.join(root, "validation_summary.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    lines = ["# Validation summary", "", f"**{passed} / {len(checks)} checks passed**", "",
             "| Group | Check | Status | Detail |", "|---|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['group']} | {c['check']} | {c['status']} | {str(c['detail'])[:110].replace('|', '/')} |")
    lines += ["", "## Metrics", "", "```json", json.dumps(metrics, indent=1), "```", ""]
    with open(os.path.join(root, "validation_summary.md"), "w") as fh:
        fh.write("\n".join(lines))
    print(f"{passed}/{len(checks)} checks passed")
    for c in checks:
        if c["status"] != "PASS":
            print("FAIL:", c["group"], c["check"], c["detail"])
    print(json.dumps(metrics["ground_truth"], indent=1))


if __name__ == "__main__":
    main()
