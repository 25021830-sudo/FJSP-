import json
import os
import time
from collections import deque
from pysat.solvers import Solver


# ======================= PARSE (giữ nguyên logic cũ) =======================
def parse_dataset(file_path, verbose=False):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if verbose:
        print(f"--- {os.path.basename(file_path)} ---")
        print(f"Jobs: {len(data['jobs'])} | Resources: {len(data['resources'])} | Ops: {len(data['operations'])}")
    return data


def get_operation_details(data):
    operation_jobs = data["operations_jobs"]
    operation_types = data["operations_operation_types"]
    operation_classes = data["operation_classes"]
    parse_operations = {}
    for operation in data["operations"]:
        is_assembly = operation_classes.get(operation, 1)
        parse_operations[operation] = {
            "job": operation_jobs[operation],
            "type": operation_types[operation],
            "is_assembly": is_assembly,
            "class_name": "Assembly" if is_assembly == 1 else "Component",
        }
    return parse_operations


def get_precedence(data):
    operations = data["operations"]
    precedence_data = data.get("precedence_constraints", {})
    predecessors = {op: [] for op in operations}
    successors = {op: [] for op in operations}
    for job, job_matrix in precedence_data.items():
        for u, successor_dict in job_matrix.items():
            if u not in successors:
                continue
            for v, is_before in successor_dict.items():
                if is_before == 1 and v in successors:
                    successors[u].append(v)
                    predecessors[v].append(u)
    return predecessors, successors


def get_processing_times(data):
    raw = data.get("processing_times", {})
    proc_times, eligible_machines = {}, {}
    for op in data["operations"]:
        m_times = raw.get(op, {})
        proc_times[op] = m_times
        eligible_machines[op] = list(m_times.keys())
    return proc_times, eligible_machines


def upgraded_parse_dataset(file_path, verbose=False):
    data = parse_dataset(file_path, verbose)
    operation_details = get_operation_details(data)
    predecessors, successors = get_precedence(data)
    processing_times, eligible_machines = get_processing_times(data)
    return {
        "raw_data": data,
        "jobs": data["jobs"],
        "resources": data["resources"],
        "operations": data["operations"],
        "operation_types": data["operation_types"],
        "operation_details": operation_details,
        "predecessors": predecessors,
        "successors": successors,
        "processing_times": processing_times,
        "eligible_machines": eligible_machines,
        "setup_times": data.get("setup_times", {}),
        "transport_times": data.get("transport_times", {}),
        "blocked_times": data.get("blocked_times", {}),
    }


# ======================= HÀM DÙNG CHUNG (MỚI) =======================
def st_time(instance, type_a, type_b, k):
    return instance["setup_times"].get(type_a, {}).get(type_b, {}).get(k, 0)


def tt_time(instance, k1, k2):
    return instance["transport_times"].get(k1, {}).get(k2, 0)


def delay_between(instance, type_a, k1, type_b, k2):
    """Độ trễ giữa end(a) và start(b): setup nếu cùng máy, transport nếu khác máy."""
    if k1 == k2:
        return st_time(instance, type_a, type_b, k1)
    return tt_time(instance, k1, k2)


def compute_reachable(instance):
    """Tập (u, v) sao cho có đường đi u -> ... -> v trong DAG."""
    reachable = set()
    for op in instance["operations"]:
        stack = list(instance["successors"][op])
        while stack:
            cur = stack.pop()
            if (op, cur) not in reachable:
                reachable.add((op, cur))
                stack.extend(instance["successors"][cur])
    return reachable


def add_geq(clauses, prefix, x_var, op, t, UB):
    """Thêm mệnh đề: prefix ∨ (start_op >= t)."""
    if t > UB + 1:                      # start >= t là bất khả thi -> chỉ còn prefix
        clauses.append(prefix)
    else:
        clauses.append(prefix + [x_var[(op, t)]])


def get_y(y_var, y_base, u, v):
    """Cấp id cho y(u,v), id nằm SAU toàn bộ biến m, x, s."""
    if (u, v) not in y_var:
        y_var[(u, v)] = y_base + len(y_var)
    return y_var[(u, v)]


# ======================= PRE-PROCESSING =======================
def pre_processing(instance, UB):
    operations = instance["operations"]
    predecessors = instance["predecessors"]
    successors = instance["successors"]
    proc_times = instance["processing_times"]
    eligible = instance["eligible_machines"]
    details = instance["operation_details"]

    def p_min_op(op):
        return min(proc_times[op].values()) if proc_times[op] else 0

    gap = {}
    for u in operations:
        for v in successors[u]:
            gaps = [proc_times[u][k1] + delay_between(instance, details[u]["type"], k1, details[v]["type"], k2)
                    for k1 in eligible[u] for k2 in eligible[v]]
            gap[(u, v)] = min(gaps) if gaps else p_min_op(u)

    in_degree = {op: len(predecessors[op]) for op in operations}
    q = deque(op for op in operations if in_degree[op] == 0)
    topo = []
    while q:
        u = q.popleft()
        topo.append(u)
        for v in successors[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                q.append(v)
    if len(topo) != len(operations):
        raise ValueError("Đồ thị precedence có chu trình")

    ES = {op: 0 for op in operations}
    for u in topo:
        for v in successors[u]:
            ES[v] = max(ES[v], ES[u] + gap[(u, v)])

    LS = {op: UB - p_min_op(op) for op in operations}
    for u in reversed(topo):
        for v in successors[u]:
            LS[u] = min(LS[u], LS[v] - gap[(u, v)])

    for op in operations:
        if ES[op] > LS[op]:
            raise ValueError(f"UB={UB} quá chặt: ES({op})={ES[op]} > LS({op})={LS[op]}")
    return ES, LS


# ======================= 4.1 =======================
def encode_time_constraints(instance, UB, ES, LS, start_id=1):
    x_var, s_var, clauses = {}, {}, []
    cur_id = start_id
    for op in instance["operations"]:
        for t in range(0, UB + 2):      # x: 0..UB+1
            x_var[(op, t)] = cur_id
            cur_id += 1
        for t in range(0, UB + 1):      # s: 0..UB (bỏ s(UB+1) vô nghĩa)
            s_var[(op, t)] = cur_id
            cur_id += 1

    for op in instance["operations"]:
        clauses.append([x_var[(op, ES[op])]])        # start >= ES
        clauses.append([-x_var[(op, LS[op] + 1)]])   # start <= LS
        for t in range(0, UB + 1):
            x_t, x_next, s_t = x_var[(op, t)], x_var[(op, t + 1)], s_var[(op, t)]
            clauses.append([-x_next, x_t])
            clauses.append([-s_t, x_t])
            clauses.append([-s_t, -x_next])
            clauses.append([-x_t, x_next, s_t])
    return clauses, x_var, s_var, cur_id


# ======================= 4.2 (giữ nguyên) =======================
def EO_operation(instance):
    var_map, clauses = {}, []
    for op, machines in instance["eligible_machines"].items():
        for m in machines:
            var_map[(op, m)] = len(var_map) + 1
    for op, machines in instance["eligible_machines"].items():
        ids = [var_map[(op, m)] for m in machines]
        clauses.append(ids)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                clauses.append([-ids[i], -ids[j]])
    return clauses, var_map


# ======================= 4.3 =======================
def precedence_constraints(instance, m_var, x_var, s_var, ES, LS, UB):
    clauses = []
    details = instance["operation_details"]
    proc = instance["processing_times"]
    for u in instance["operations"]:
        for v in instance["successors"][u]:
            for k1 in instance["eligible_machines"][u]:
                p_u = proc[u][k1]
                for k2 in instance["eligible_machines"][v]:
                    dt = delay_between(instance, details[u]["type"], k1, details[v]["type"], k2)
                    for t in range(ES[u], LS[u] + 1):
                        prefix = [-s_var[(u, t)], -m_var[(u, k1)], -m_var[(v, k2)]]
                        add_geq(clauses, prefix, x_var, v, t + p_u + dt, UB)   # x(v, t+p+dt)  (đã sửa)
    return clauses


# ======================= 4.4 =======================
def setup_and_non_overlap(instance, m_var, x_var, s_var, y_var, y_base, ES, LS, UB, reachable):
    clauses = []
    ops = instance["operations"]
    details = instance["operation_details"]
    proc = instance["processing_times"]
    eligible = instance["eligible_machines"]

    for i in range(len(ops)):
        u = ops[i]
        for j in range(i + 1, len(ops)):
            v = ops[j]
            if (u, v) in reachable or (v, u) in reachable:
                continue
            common = set(eligible[u]) & set(eligible[v])
            if not common:
                continue
            y_uv = get_y(y_var, y_base, u, v)
            type_u, type_v = details[u]["type"], details[v]["type"]
            for k in common:
                m_uk, m_vk = m_var[(u, k)], m_var[(v, k)]
                d_uv = proc[u][k] + st_time(instance, type_u, type_v, k)
                d_vu = proc[v][k] + st_time(instance, type_v, type_u, k)
                for t in range(ES[u], LS[u] + 1):   # u trước v
                    add_geq(clauses, [-m_uk, -m_vk, -y_uv, -s_var[(u, t)]], x_var, v, t + d_uv, UB)
                for t in range(ES[v], LS[v] + 1):   # v trước u
                    add_geq(clauses, [-m_uk, -m_vk, y_uv, -s_var[(v, t)]], x_var, u, t + d_vu, UB)
    return clauses


# ======================= 4.5 =======================
def assembly_constraints(instance, m_var, x_var, s_var, y_var, y_base, ES, LS, UB, reachable):
    clauses = []
    details = instance["operation_details"]
    proc = instance["processing_times"]
    eligible = instance["eligible_machines"]

    job_asm = {}
    for op in instance["operations"]:
        if details[op]["is_assembly"] == 1:          # đã sửa: trước đây luôn rỗng
            job_asm.setdefault(details[op]["job"], []).append(op)

    for asm in job_asm.values():
        for i in range(len(asm)):
            u = asm[i]
            for j in range(i + 1, len(asm)):
                v = asm[j]
                if (u, v) in reachable or (v, u) in reachable:
                    continue
                y_uv = get_y(y_var, y_base, u, v)
                for k1 in eligible[u]:
                    for k2 in eligible[v]:
                        if k1 == k2:                 # cùng máy: 4.4 đã lo
                            continue
                        m1, m2 = m_var[(u, k1)], m_var[(v, k2)]
                        d_uv = proc[u][k1] + tt_time(instance, k1, k2)
                        d_vu = proc[v][k2] + tt_time(instance, k2, k1)
                        for t in range(ES[u], LS[u] + 1):
                            add_geq(clauses, [-m1, -m2, -y_uv, -s_var[(u, t)]], x_var, v, t + d_uv, UB)
                        for t in range(ES[v], LS[v] + 1):
                            add_geq(clauses, [-m1, -m2, y_uv, -s_var[(v, t)]], x_var, u, t + d_vu, UB)
    return clauses


# ======================= 4.6 =======================
def encode_cmax(instance, m_var, x_var, UB):
    clauses = []
    for op in instance["operations"]:
        if not instance["successors"][op]:
            for m in instance["eligible_machines"][op]:
                t_banned = UB - instance["processing_times"][op][m] + 1
                if t_banned <= 0:
                    clauses.append([-m_var[(op, m)]])
                else:
                    clauses.append([-m_var[(op, m)], -x_var[(op, t_banned)]])
    return clauses


# ======================= UB (viết lại cho đúng mô hình) =======================
def get_ub(instance):
    ops = instance["operations"]
    succs, preds = instance["successors"], instance["predecessors"]
    proc, eligible = instance["processing_times"], instance["eligible_machines"]
    details = instance["operation_details"]

    in_degree = {op: len(preds[op]) for op in ops}
    ready = deque(op for op in ops if in_degree[op] == 0)
    op_start, op_end, op_mach = {}, {}, {}
    mach_ops = {m: [] for m in instance["resources"]}
    asm_by_job = {}

    while ready:
        op = ready.popleft()
        type_op, job = details[op]["type"], details[op]["job"]
        is_asm = details[op]["is_assembly"] == 1

        best = None
        for m in eligible[op]:
            start = 0
            for p in preds[op]:                                   # precedence (transport / setup)
                dt = delay_between(instance, details[p]["type"], op_mach[p], type_op, m)
                start = max(start, op_end[p] + dt)
            for u in mach_ops[m]:                                 # mọi cặp trên cùng máy (setup)
                start = max(start, op_end[u] + st_time(instance, details[u]["type"], type_op, m))
            if is_asm:                                            # assembly cùng job nối tiếp
                for u in asm_by_job.get(job, []):
                    dt = delay_between(instance, details[u]["type"], op_mach[u], type_op, m)
                    start = max(start, op_end[u] + dt)
            end = start + proc[op][m]
            if best is None or end < best[0]:
                best = (end, start, m)

        end, start, m = best
        op_start[op], op_end[op], op_mach[op] = start, end, m
        mach_ops[m].append(op)
        if is_asm:
            asm_by_job.setdefault(job, []).append(op)

        for v in succs[op]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                ready.append(v)

    return max(op_end.values())


# ======================= DECODE + VERIFY (MỚI) =======================
def decode_solution(model_set, instance, m_var, x_var, s_var, ub):
    """Đọc model SAT -> {op: {machine, start, end}} và kiểm tra tính nhất quán của biến."""
    sol, errors = {}, []
    proc = instance["processing_times"]
    for op in instance["operations"]:
        ms = [m for m in instance["eligible_machines"][op] if m_var[(op, m)] in model_set]
        ts = [t for t in range(ub + 1) if s_var[(op, t)] in model_set]
        if len(ms) != 1:
            errors.append(f"[{op}] gán {len(ms)} máy: {ms}")
        if len(ts) != 1:
            errors.append(f"[{op}] có {len(ts)} thời điểm bắt đầu: {ts}")
        if len(ts) == 1:
            t0 = ts[0]
            for t in range(ub + 2):                 # x(t) phải đúng bằng (t <= start)
                if (x_var[(op, t)] in model_set) != (t <= t0):
                    errors.append(f"[{op}] x_var không khớp s_var tại t={t} (start={t0})")
                    break
        if len(ms) == 1 and len(ts) == 1:
            sol[op] = {"machine": ms[0], "start": ts[0], "end": ts[0] + proc[op][ms[0]]}
    return sol, errors


def verify_solution(instance, sol, ub=None, ES=None, LS=None):
    """Kiểm tra lịch decode được có thoả MỌI ràng buộc của bài toán hay không (độc lập với CNF)."""
    errors = []
    ops = instance["operations"]
    details = instance["operation_details"]
    reachable = compute_reachable(instance)

    if len(sol) != len(ops):
        errors.append(f"Thiếu operation trong lịch: {len(sol)}/{len(ops)}")
        return False, errors, None

    # 0. miền hợp lệ
    for op in ops:
        s = sol[op]
        if s["machine"] not in instance["eligible_machines"][op]:
            errors.append(f"[{op}] máy {s['machine']} không tương thích")
        if s["start"] < 0:
            errors.append(f"[{op}] start < 0")
        if ub is not None and s["end"] > ub:
            errors.append(f"[{op}] end={s['end']} > UB={ub}")
        if ES is not None and not (ES[op] <= s["start"] <= LS[op]):
            errors.append(f"[{op}] start={s['start']} ngoài [ES,LS]=[{ES[op]},{LS[op]}]")

    def gap(a, b):  # độ trễ tối thiểu end(a) -> start(b)
        return delay_between(instance, details[a]["type"], sol[a]["machine"],
                             details[b]["type"], sol[b]["machine"])

    # 1. precedence
    for u in ops:
        for v in instance["successors"][u]:
            need = sol[u]["end"] + gap(u, v)
            if sol[v]["start"] < need:
                errors.append(f"[PREC] {u}->{v}: start({v})={sol[v]['start']} < {need}")

    # 2. không chồng lấp + setup trên cùng máy
    by_machine = {}
    for op in ops:
        by_machine.setdefault(sol[op]["machine"], []).append(op)
    for m, lst in by_machine.items():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a, b = lst[i], lst[j]
                ab = sol[b]["start"] >= sol[a]["end"] + gap(a, b)
                ba = sol[a]["start"] >= sol[b]["end"] + gap(b, a)
                if (a, b) in reachable or (b, a) in reachable:
                    ab = sol[b]["start"] >= sol[a]["end"]      # đã có chuỗi precedence, chỉ cần không chồng
                    ba = sol[a]["start"] >= sol[b]["end"]
                if not (ab or ba):
                    errors.append(f"[MACHINE {m}] {a} và {b} chồng lấp / thiếu setup")

    # 3. assembly cùng job phải tuyến tính (kể cả khác máy)
    job_asm = {}
    for op in ops:
        if details[op]["is_assembly"] == 1:
            job_asm.setdefault(details[op]["job"], []).append(op)
    for job, lst in job_asm.items():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a, b = lst[i], lst[j]
                if (a, b) in reachable or (b, a) in reachable:
                    continue
                ab = sol[b]["start"] >= sol[a]["end"] + gap(a, b)
                ba = sol[a]["start"] >= sol[b]["end"] + gap(b, a)
                if not (ab or ba):
                    errors.append(f"[ASSEMBLY {job}] {a} và {b} không nối tiếp")

    cmax = max(s["end"] for s in sol.values())
    return len(errors) == 0, errors, cmax


# ======================= GIẢI 1 LẦN VỚI UB =======================
def build_and_solve(instance, ub):
    try:
        ES, LS = pre_processing(instance, ub)
    except ValueError:
        return "UNSAT", None, None, None
    eo_clauses, m_var = EO_operation(instance)
    time_clauses, x_var, s_var, next_id = encode_time_constraints(instance, ub, ES, LS, start_id=len(m_var) + 1)
    y_var = {}
    reachable = compute_reachable(instance)
    c43 = precedence_constraints(instance, m_var, x_var, s_var, ES, LS, ub)
    c44 = setup_and_non_overlap(instance, m_var, x_var, s_var, y_var, next_id, ES, LS, ub, reachable)
    c45 = assembly_constraints(instance, m_var, x_var, s_var, y_var, next_id, ES, LS, ub, reachable)
    c46 = encode_cmax(instance, m_var, x_var, ub)
    all_clauses = eo_clauses + time_clauses + c43 + c44 + c45 + c46

    solver = Solver(name="cadical195", bootstrap_with=all_clauses)
    t0 = time.perf_counter()
    sat = solver.solve()
    elapsed = time.perf_counter() - t0
    result = ("UNSAT", None, len(all_clauses), elapsed)
    if sat:
        model = set(solver.get_model())
        sol, dec_err = decode_solution(model, instance, m_var, x_var, s_var, ub)
        result = ("SAT", (sol, dec_err, ES, LS), len(all_clauses), elapsed)
    solver.delete()
    return result


def main(file_path=os.path.join("sm", "sm_0_2.json")):
    t_total = time.perf_counter()
    instance = upgraded_parse_dataset(file_path)
    ub = get_ub(instance)

    best, solve_time = None, 0.0
    while ub > 0:
        status, payload, n_clauses, elapsed = build_and_solve(instance, ub)
        solve_time += elapsed or 0.0              # chỉ cộng thời gian solver.solve()
        if status != "SAT":
            break
        sol, dec_err, ES, LS = payload
        if dec_err:
            print("!! Decode lỗi:", dec_err)
            break
        ok, errs, cmax = verify_solution(instance, sol, ub, ES, LS)
        if not ok:
            print("!! Lịch không hợp lệ:", errs)
            break
        best = (sol, cmax)
        ub = cmax - 1

    total_time = time.perf_counter() - t_total    # gồm parse + sinh CNF + giải

    # in chi tiết lịch (có thể comment lại nếu chạy hàng loạt)
    if best:
        for op, s in best[0].items():
            print(f"[{op:20s}] Máy: {str(s['machine']):12s} Start: {s['start']:4d} Finish: {s['end']:4d}")

    name = os.path.basename(file_path)
    cmax_str = best[1] if best else "N/A"
    print(f"RESULT | {name} | Makespan={cmax_str} | SAT_time={solve_time:.2f}s | Total_time={total_time:.2f}s")
    return name, cmax_str, solve_time, total_time

if __name__ == "__main__":
    main()