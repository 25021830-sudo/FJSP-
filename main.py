import json
import os

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
        # bien >= 0 va ko >= UB + 1
        clauses.append([x_var[(op, 0)]])
        clauses.append([-x_var[(op, UB + 1)]])

        for t in range(0, UB + 1):
            x_t = x_var[(op, t)]
            x_next = x_var[(op, t + 1)]
            s_t = s_var[(op, t)]

            #x_(t+1) -> x_t
            clauses.append([-x_next, x_t])

            # s_t <=> x_t ∧ -x_(t+1)
            clauses.append([-s_t, x_t])
            clauses.append([-s_t, -x_next])
            clauses.append([-x_t, x_next, s_t])
    return clauses, x_var, s_var, cur_id

## UB va CMax 4.5
def UB_and_Cmax(instance, m_var, x_var, buffer_per_op=10):
    total_processing_time = 0
    for time in instance["processing_times"].values():
        total_processing_time += max(time.values())
    UB = total_processing_time + len(instance["operations"]) * buffer_per_op
    Cmax_clause = []
    for op in instance["operations"]:
        if len(instance["successors"][op]) == 0: # xet nguyen cong cuoi cung khong co thang lien truoc
            for m in instance["eligible_machines"][op]:
                processing_ik = instance["processing_times"][op][m]
                t_banned = UB - processing_ik + 1 #thoi gian bi cam bat dau
                machine_id = m_var[(op,m)]
                if (op, t_banned) in x_var:
                    x_id = x_var[op, t_banned]
                    Cmax_clause.append([-machine_id, -x_id])
                elif t_banned <= 0:
                    Cmax_clause.append([-machine_id])
    return UB, Cmax_clause

# Test UB và cmax
# 1. Lay m_var tu ham EO
eo_clauses, m_var = EO_operation(instance)

# 2. Tinh UB truoc de sinh bang bien x_var
tong_p = sum(max(t.values()) for t in instance["processing_times"].values())
buffer = 10
ub_est = tong_p + len(instance["operations"]) * buffer

# 3. Sinh bien thoi gian x_var va s_var theo UB
start_id = len(m_var) + 1
time_clauses, x_var, s_var, next_id = encode_time_constraints(instance, ub_est, start_id)

# 4. Goi ham kiem tra UB_and_Cmax
UB, cmax_clauses = UB_and_Cmax(instance, m_var, x_var, buffer_per_op=buffer)

# 5. In ket qua ra man hinh
print("=" * 50)
print("KET QUA TEST UB VA CMAX:")
print("Gia tri UB:", UB)
print("Tong so menh de Cmax:", len(cmax_clauses))

# In thu 5 menh de Cmax dau tien
print("\n5 menh de Cmax mau:")
for c in cmax_clauses[:5]:
    print(c)
#


