import json
import os
from collections import deque
import time
from pysat.solvers import Solver

#file data json thi dung luon thu vien
def parse_dataset(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    jobs = data["jobs"]
    resources = data["resources"]
    operations = data["operations"]
    ## IN TEST phần này
    print(f"--- {os.path.basename(file_path)} ---")
    print(f"Tổng số Jobs: {len(jobs)} -> {jobs}")
    print(f"Tổng số Resources (máy): {len(resources)} -> {resources}")
    print(f"Tổng số operations: {len(operations)}")
    return data #tra ve du lieu


#lay thong tin ve nguyen cong
def get_operation_details(data):
    operations = data["operations"]
    operation_jobs = data["operations_jobs"]
    operation_types = data["operations_operation_types"]
    operation_classes = data["operation_classes"]
    parse_operations = {}
    for operation in operations:
        job = operation_jobs[operation]
        operation_type = operation_types[operation]
        is_assembly = operation_classes.get(operation, 1)
        parse_operations[operation] = { #nhet vao trong parse_operations duoi dang json
            "job": job,
            "type": operation_type,
            "is_assembly": is_assembly,
            "class_name": "Assembly" if is_assembly == 1 else "Component" #toan tu 3 ngoi
        }
    return parse_operations


#lay danh sach cac op theo trinh tu
def get_precedence(data):
    operations = data["operations"]
    preccedence_data = data.get("precedence_constraints", {})

    predecessors = {op: [] for op in operations} #thang
    successors = {op: [] for op in operations}

    for job, job_matrix in preccedence_data.items():
        for u, successor_dict in job_matrix.items():
            if u not in operations:
                continue
            for v, is_before in successor_dict.items():
                if is_before == 1 and v in operations:
                    successors[u].append(v)     # u phải xong trước v
                    predecessors[v].append(u)   # v phải đợi u xong
    return predecessors, successors


#lay thoi gian gia cong
def get_processing_times(data):
    operations = data["operations"]
    raw_processing_times = data.get("processing_times", {})

    # thoi gian gia cong tren tung may
    proc_times = {}
    # DS may co the chay duoc operation nao
    eligible_machines = {}

    for op in operations:
        # dict cac may thuc hien duoc op nay
        m_times = raw_processing_times.get(op, {})
        proc_times[op] = m_times
        eligible_machines[op] = list(m_times.keys())

    return proc_times, eligible_machines


#lay thoi gian setup va van chhuyem
def get_setup_and_transport(data):
    setup_times = data.get("setup_times", {})
    transport_times = data.get("transport_times", {})
    return setup_times, transport_times


#tong hop het cac ham
def upgraded_parse_dataset(file_path):
    data = parse_dataset(file_path) #1
    operation_details = get_operation_details(data) #2
    predecessors, successors = get_precedence(data) #3
    processing_times, eligible_machines = get_processing_times(data) #4
    setup_times, transport_times = get_setup_and_transport(data) #5

    #goi lai toan bo thong tin
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
        "setup_times": setup_times,
        "transport_times": transport_times,
        "blocked_times": data.get("blocked_times", {})
    }

#Test cac ham con
# for i in range(1,2):
#     file_test = os.path.join("sm", f"sm_0_{i}.json")
#     data = parse_dataset(file_test)
#     results = get_operation_details(data)
#     predecessors, successors = get_precedence(data)
#     processing_times, eligible_machines = get_processing_times(data)
#     setup_times, transport_times = get_setup_and_transport(data)
#     resource_list = data["resources"]
#     types = data["operation_types"]
#     for operation in data["operations"]:
#         print(f"{operation}:")
#         info = results[operation]
#         print(f"operation: {operation} | Job: {info['job']} | Type: {info['type']} | Class: {info['class_name']}")
#         print(f"  <- Cần làm sau (Predecessors): {predecessors[operation]}")
#         print(f"  -> Làm xong sẽ mở khóa (Successors): {successors[operation]}")
#         print(f"  - Các máy thực hiện được: {eligible_machines[operation]}")
#         print(f"  - Chi tiết thời gian: {processing_times[operation]}")
#         print("\n--- KIỂM TRA SETUP & TRANSPORT TIMES ---")
#         r1, r2 = resource_list[0], resource_list[1]
#         t_time = transport_times.get(r1, {}).get(r2, 0)
#         print(f"Thời gian vận chuyển từ {r1} -> {r2}: {t_time} giây")
#         t1, t2, m = types[0], types[1], resource_list[0]
#         s_time = setup_times.get(t1, {}).get(t2, {}).get(m, "Không hỗ trợ/Không đổi")
#         print(f"Thời gian setup trên {m} khi chuyển từ {t1} -> {t2}: {s_time}")
#         print("\n")

#test ham to

file_path = os.path.join("sm", f"sm_0_1.json")
instance = upgraded_parse_dataset(file_path)

# print("\n--- CHI TIẾT OPERATIONS ---")
# for operation in instance["operations"]:
#     info = instance["operation_details"][operation]
#     print(f"[{operation}] | Job: {info['job']} | Type: {info['type']} | Class: {info['class_name']}")
#     print(f"  <- Cần làm sau (Predecessors): {instance['predecessors'][operation]}")
#     print(f"  -> Làm xong sẽ mở khóa (Successors): {instance['successors'][operation]}")
#     print(f"  - Các máy thực hiện được: {instance['eligible_machines'][operation]}")
#     print(f"  - Chi tiết thời gian: {instance['processing_times'][operation]}\n")
#
# print("--- THÔNG TIN SETUP & TRANSPORT MẪU ---")
# r_list = instance["resources"]
# if len(r_list) >= 2:
#     r1, r2 = r_list[0], r_list[1]
#     t_time = instance["transport_times"].get(r1, {}).get(r2, 0)
#     print(f"Thời gian vận chuyển từ {r1} -> {r2}: {t_time} giây")
#
# types = instance["operation_types"]
# if len(types) >= 2 and len(r_list) >= 1:
#     t1, t2, m = types[0], types[1], r_list[0]
#     s_time = instance["setup_times"].get(t1, {}).get(t2, {}).get(m, "Không hỗ trợ/0")
#     print(f"Thời gian setup trên {m} khi chuyển từ {t1} -> {t2}: {s_time}")
# print("=" * 60)

#Ham xu ly ban dau
def pre_processing(instance, UB):
    operations = instance["operations"]
    predecessors = instance["predecessors"]
    successors = instance["successors"]
    proc_times = instance["processing_times"]
    eligible_machines = instance["eligible_machines"]
    details = instance["operation_details"]
    setup_times = instance["setup_times"]
    transport_times = instance["transport_times"]

    def get_p_min_op(op):
        return min(proc_times[op].values()) if proc_times[op] else 0

    def get_p_min_trans(u, v):
        type_u = details[u]["type"]
        type_v = details[v]["type"]
        delays = []
        for k1 in eligible_machines[u]:
            p1 = proc_times[u][k1]
            for k2 in eligible_machines[v]:
                if k1 != k2:
                    tt = transport_times.get(k1, {}).get(k2, 0)
                    delays.append(p1 + tt)
                else:
                    st = setup_times.get(type_u, {}).get(type_v, {}).get(k1, 0)
                    delays.append(p1 + st)
        return min(delays) if delays else get_p_min_op(u)

    in_degree = {op: len(predecessors[op]) for op in operations}
    q = deque([op for op in operations if in_degree[op] == 0])
    topo = []
    while q:
        u = q.popleft()
        topo.append(u)
        for v in successors[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                q.append(v)

    ES = {op: 0 for op in operations}
    for u in topo:
        for v in successors[u]:
            dt = get_p_min_trans(u, v)
            if ES[u] + dt > ES[v]:
                ES[v] = ES[u] + dt

    LS = {op: float('inf') for op in operations}
    for op in operations:
        if not successors[op]:
            LS[op] = UB - get_p_min_op(op)

    for u in reversed(topo):
        for v in successors[u]:
            dt = get_p_min_trans(u, v)
            if LS[v] - dt < LS[u]:
                LS[u] = LS[v] - dt

    domains = {op: range(int(ES[op]), int(LS[op]) + 1) for op in operations}

    return ES, LS, domains

# x_var 4.1
def encode_time_constraints(instance, UB, start_id=1):
    x_var = {}
    s_var = {}
    clauses = []
    cur_id = start_id

    # ID cho x va s
    for op in instance["operations"]:
        for t in range(0, UB + 2):  # xet den UB +1 de tim chan tren
            x_var[(op, t)] = cur_id
            cur_id += 1
        for t in range(0, UB + 1):
            s_var[(op, t)] = cur_id
            cur_id += 1

    ###CNF
    for op in instance["operations"]:
        # bien bat dau sau >= 0 va <= UB
        clauses.append([x_var[(op, 0)]])
        clauses.append([-x_var[(op, UB + 1)]])

        for t in range(0, UB + 1):
            x_t = x_var[(op, t)]
            x_next = x_var[(op, t + 1)]
            s_t = s_var[(op, t)]

            #x_(t+1) -> x_t
            clauses.append([-x_next, x_t])
            # s_t <=> x_t ∧ -x_(t+1) giai thich ca 2 chieu
            clauses.append([-s_t, x_t])
            clauses.append([-s_t, -x_next])
            clauses.append([-x_t, x_next, s_t])
    return clauses, x_var, s_var, cur_id

#Bruh
#Rang buoc EO 4.2
def EO_operation(instance):
    var_map = {}
    clauses = [] #menh de de may sat xu ly
    #gan tung may voi id tang dan
    for op, machine in instance["eligible_machines"].items():
        for m in machine:
            var_map[(op,m)] = len(var_map) + 1
    #clause cho AMO, ALO => EO
    for op, machine in instance["eligible_machines"].items():
        #Id cac mayy thuc hien duoc op nay
        m_id = [var_map[(op, m)] for m in machine]
        clauses.append(m_id) #ALO
        #AMO
        for i in range(len(m_id)):
            for j in range(i+1, len(m_id)):
                clauses.append([-m_id[i], -m_id[j]])
    return clauses, var_map

#Test EO
EO_test= EO_operation(instance)
clause, var_map = EO_test[0], EO_test[1]
print(clause)
print(var_map)

#code rang buoc precedence 4.3
def precedence_constraints(instance, m_var, x_var, s_var, UB):
    clauses = []
    details = instance["operation_details"]
    setup_times = instance["setup_times"]
    transport_times = instance["transport_times"]

    for u in instance["operations"]:
        type_u = details[u]["type"]
        for v in instance["successors"][u]:
            type_v = details[v]["type"]
            for t in range(0, UB + 1):
                if (u, t) not in s_var:
                    continue
                s_ut = s_var[(u, t)]
                for k1 in instance["eligible_machines"][u]:
                    m_u1 = m_var[(u, k1)]
                    p_u1 = instance["processing_times"][u][k1]
                    for k2 in instance["eligible_machines"][v]:
                        m_v2 = m_var[(v, k2)]
                        if k1 != k2:
                            tt = transport_times.get(k1, {}).get(k2, 0)
                            t_target = t + p_u1 + tt
                        else:
                            st = setup_times.get(type_u, {}).get(type_v, {}).get(k1, 0)
                            t_target = t + p_u1 + st

                        if (v, t_target) in x_var:
                            clauses.append([-s_ut, -m_u1, -m_v2, x_var[(v, t_target)]])
                        elif t_target > UB + 1:
                            clauses.append([-s_ut, -m_u1, -m_v2])
    return clauses

# rang buoc setup time va chong chat tren may
def setup_and_non_overlap(instance, m_var, x_var, s_var, y_var, UB):
    clauses = []
    operations = instance["operations"]
    details = instance["operation_details"]
    proc_times = instance["processing_times"]
    setup_times = instance["setup_times"]
    eligible_machines = instance["eligible_machines"]

    reachable = set()
    for op in operations:
        stack = list(instance["successors"][op])
        while stack:
            curr = stack.pop()
            if (op, curr) not in reachable:
                reachable.add((op, curr))
                stack.extend(instance["successors"][curr])

    for idx1 in range(len(operations)):
        u = operations[idx1]
        type_u = details[u]["type"]
        machines_u = set(eligible_machines[u])

        for idx2 in range(idx1 + 1, len(operations)):
            v = operations[idx2]

            if (u, v) in reachable or (v, u) in reachable:
                continue

            common_machines = machines_u.intersection(eligible_machines[v])
            if not common_machines:
                continue

            if (u, v) not in y_var:
                y_var[(u, v)] = len(m_var) + len(s_var) + len(y_var) + 1
            y_uv = y_var[(u, v)]

            type_v = details[v]["type"]

            for k in common_machines:
                m_uk = m_var[(u, k)]
                m_vk = m_var[(v, k)]
                p_uk = proc_times[u][k]
                p_vk = proc_times[v][k]
                st_uv = setup_times.get(type_u, {}).get(type_v, {}).get(k, 0)
                st_vu = setup_times.get(type_v, {}).get(type_u, {}).get(k, 0)

                for t in range(0, UB + 1):
                    if (u, t) in s_var:
                        s_ut = s_var[(u, t)]
                        t_target = t + p_uk + st_uv
                        if (v, t_target) in x_var:
                            clauses.append([-m_uk, -m_vk, -y_uv, -s_ut, x_var[(v, t_target)]])
                        elif t_target > UB + 1:
                            clauses.append([-m_uk, -m_vk, -y_uv, -s_ut])

                for t in range(0, UB + 1):
                    if (v, t) in s_var:
                        s_vt = s_var[(v, t)]
                        t_target = t + p_vk + st_vu
                        if (u, t_target) in x_var:
                            clauses.append([-m_uk, -m_vk, y_uv, -s_vt, x_var[(u, t_target)]])
                        elif t_target > UB + 1:
                            clauses.append([-m_uk, -m_vk, y_uv, -s_vt])

    return clauses

#Xu ly tuyen tinh lien may
def assembly_constraints(instance, m_var, x_var, s_var, y_var, UB):
    clauses = []
    ops = instance["operations"]
    details = instance["operation_details"]
    proc_times = instance["processing_times"]
    setup_times = instance["setup_times"]
    transport_times = instance["transport_times"]
    eligible = instance["eligible_machines"]
    classes = instance.get("operation_classes", {})

    reachable = set()
    for op in ops:
        stack = list(instance["successors"][op])
        while stack:
            curr = stack.pop()
            if (op, curr) not in reachable:
                reachable.add((op, curr))
                stack.extend(instance["successors"][curr])

    job_asm = {}
    for op in ops:
        if classes.get(op, details[op].get("class", 0)) == 1:
            job_asm.setdefault(details[op]["job"], []).append(op)

    for asm in job_asm.values():
        for i in range(len(asm)):
            u = asm[i]
            type_u = details[u]["type"]
            for j in range(i + 1, len(asm)):
                v = asm[j]
                if (u, v) in reachable or (v, u) in reachable:
                    continue

                y_uv = y_var.setdefault((u, v), len(m_var) + len(s_var) + len(y_var) + 1)
                type_v = details[v]["type"]

                for k1 in eligible[u]:
                    m_u1, p_u1 = m_var[(u, k1)], proc_times[u][k1]
                    for k2 in eligible[v]:
                        m_v2, p_v2 = m_var[(v, k2)], proc_times[v][k2]
                        dt_uv = setup_times.get(type_u, {}).get(type_v, {}).get(k1,0) if k1 == k2 else transport_times.get(k1, {}).get(k2, 0)
                        dt_vu = setup_times.get(type_v, {}).get(type_u, {}).get(k1,0) if k1 == k2 else transport_times.get(k2, {}).get(k1, 0)
                        for t in range(UB + 1):
                            if (u, t) in s_var:
                                tgt = t + p_u1 + dt_uv
                                if (v, tgt) in x_var:
                                    clauses.append([-m_u1, -m_v2, -y_uv, -s_var[(u, t)], x_var[(v, tgt)]])
                                elif tgt > UB + 1:
                                    clauses.append([-m_u1, -m_v2, -y_uv, -s_var[(u, t)]])

                            if (v, t) in s_var:
                                tgt = t + p_v2 + dt_vu
                                if (u, tgt) in x_var:
                                    clauses.append([-m_u1, -m_v2, y_uv, -s_var[(v, t)], x_var[(u, tgt)]])
                                elif tgt > UB + 1:
                                    clauses.append([-m_u1, -m_v2, y_uv, -s_var[(v, t)]])

    return clauses

#Tinh UB
def get_ub(instance):
    ops = instance["operations"]
    succs = instance["successors"]
    preds = instance["predecessors"]
    proc = instance["processing_times"]
    eligible = instance["eligible_machines"]
    details = instance["operation_details"]
    setup = instance["setup_times"]

    in_degree = {op: len(preds[op]) for op in ops}
    ready = [op for op in ops if in_degree[op] == 0]

    m_free = {m: 0 for m in instance["resources"]}
    m_last_type = {m: "k0" for m in instance["resources"]}
    op_end = {}
    op_mach = {}

    while ready:
        op = ready.pop(0)
        type_op = details[op]["type"]

        pred_ready_time = max((op_end[p] for p in preds[op]), default=0)

        best_m, best_end = None, float('inf')
        for m in eligible[op]:
            st = setup.get(m_last_type[m], {}).get(type_op, {}).get(m, 0)
            avail = max(m_free[m], pred_ready_time) + st
            end = avail + proc[op][m]
            if end < best_end:
                best_m, best_end = m, end

        op_mach[op] = best_m
        op_end[op] = best_end
        m_free[best_m] = best_end
        m_last_type[best_m] = type_op

        for v in succs[op]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                ready.append(v)

    return max(op_end.values())

#CMAX
def encode_cmax(instance, m_var, x_var, UB):
    clauses = []
    for op in instance["operations"]:
        if len(instance["successors"][op]) == 0:
            for m in instance["eligible_machines"][op]:
                p_ik = instance["processing_times"][op][m]
                t_banned = UB - p_ik + 1
                m_id = m_var[(op, m)]
                if (op, t_banned) in x_var:
                    clauses.append([-m_id, -x_var[(op, t_banned)]])
                elif t_banned <= 0:
                    clauses.append([-m_id])
    return clauses

#main
def main():
    file_path = os.path.join("sm", "sm_0_1.json")
    if not os.path.exists(file_path):
        file_path = "sm_0_1.json"

    print(f"=== BẮT ĐẦU CHẠY THUẬT TOÁN CHO FILE: {file_path} ===")
    instance = upgraded_parse_dataset(file_path)
    ub = get_ub(instance)
    print(f"1. Upper Bound (UB) khởi tạo: {ub}")
    ES, LS, domains = pre_processing(instance, ub)
    print("2. Tiền xử lý hoàn tất (Đã tính ES, LS và Domain Reduction).")
    eo_clauses, m_var = EO_operation(instance)
    time_clauses, x_var, s_var, next_id = encode_time_constraints(instance, ub, start_id=len(m_var) + 1)
    y_var = {}

    c43 = precedence_constraints(instance, m_var, x_var, s_var, ub)
    c44 = setup_and_non_overlap(instance, m_var, x_var, s_var, y_var, ub)
    c45 = assembly_constraints(instance, m_var, x_var, s_var, y_var, ub)
    c46 = encode_cmax(instance, m_var, x_var, ub)

    all_clauses = eo_clauses + time_clauses + c43 + c44 + c45 + c46
    print(f"3. Sinh tổng cộng {len(all_clauses)} mệnh đề CNF.")

    solver = Solver(name='cadical195')
    for clause in all_clauses:
        solver.add_clause(clause)

    start_time = time.perf_counter()
    is_sat = solver.solve()
    exec_time = time.perf_counter() - start_time

    print("\n==================================================")
    if is_sat:
        model = set(solver.get_model())
        print(f"TRẠNG THÁI: TÌM THẤY LỊCH TRÌNH KHẢ THI (SAT)")
        print(f"Thời gian giải SAT Solver: {exec_time:.2f} giây")
        print("--------------------------------------------------")

        cmax_actual = 0
        for op in instance["operations"]:
            assigned_m = next((m for m in instance["eligible_machines"][op] if m_var[(op, m)] in model), None)

            start_t = next((t for t in range(ub + 1) if s_var[(op, t)] in model), None)

            p_time = instance["processing_times"][op].get(assigned_m, 0) if assigned_m else 0
            finish_t = start_t + p_time if start_t is not None else None

            if finish_t:
                cmax_actual = max(cmax_actual, finish_t)

            print(
                f"[{op:20s}] -> Máy: {str(assigned_m):12s} | Start: {str(start_t):3s} | Process: {p_time:2d} | Finish: {str(finish_t):3s}")

        print("--------------------------------------------------")
        print(f"🎯 Makespan (Cmax) đạt được: {cmax_actual}")
    else:
        print("TRẠNG THÁI: VÔ NGHIỆM (UNSAT)")
    print("==================================================")

    solver.delete()


if __name__ == "__main__":
    main()

