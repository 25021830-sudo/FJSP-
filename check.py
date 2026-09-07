import json
from pathlib import Path

def check_nonzero_blocked_times(root_dir: str = "."):
    root_path = Path(root_dir)
    json_files = list(root_path.rglob("*.json"))
    
    non_zero_instances = []
    total_checked = 0
    
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            blocked_times = data.get("blocked_times", {})
            total_checked += 1
            
            # Kiểm tra xem có resource nào có blocked_time != 0 không
            for res, b_time in blocked_times.items():
                if b_time != 0:
                    non_zero_instances.append((file_path.name, res, b_time))
        except Exception as e:
            print(f"Lỗi khi đọc file {file_path}: {e}")

    print(f"--- KẾT QUẢ KIỂM TRA ---")
    print(f"Tổng số file JSON đã duyệt: {total_checked}")
    if non_zero_instances:
        print(f"Tìm thấy {len(non_zero_instances)} instance có blocked_times != 0:")
        for name, res, b_time in non_zero_instances:
            print(f" - File: {name} | Machine: {res} | Blocked time: {b_time}")
    else:
        print("Không có instance nào có blocked_times khác 0 (tất cả đều = 0).")

# Chạy kiểm tra
check_nonzero_blocked_times(".")