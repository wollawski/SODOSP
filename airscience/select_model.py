# -*- coding: gbk -*-
import math
from itertools import combinations_with_replacement

# -*- coding: gbk -*-
EQUIPMENT_DATABASE = [
    {"model": "SXYCK-30",  "air_flow": 6000,  "power": 15.0,  "length": 4.0, "width": 1.2, "height": 1.5},
    {"model": "SXYCK-50",  "air_flow": 12000, "power": 28.0,  "length": 4.0, "width": 1.3, "height": 1.5},
    {"model": "SXYCK-80",  "air_flow": 18000, "power": 48.0,  "length": 5.3, "width": 2.0, "height": 1.9},
    {"model": "SXYCK-120", "air_flow": 25000, "power": 65.0, "length": 6.4, "width": 2.3, "height": 2.2},
    {"model": "SXYCK-165", "air_flow": 34000, "power": 89.0, "length": 6.4, "width": 2.3, "height": 2.2},
    {"model": "SXYCK-200", "air_flow": 43000, "power": 108.0, "length": 7.4, "width": 2.3, "height": 2.5},
    {"model": "SXYCK-250", "air_flow": 52000, "power": 134.5, "length": 7.4, "width": 2.4, "height": 2.5},
    {"model": "SXYCK-300", "air_flow": 60000, "power": 167.0, "length": 8.0, "width": 2.8, "height": 2.8},
]
def auto_select_equipment_by_airflow(target_airflow_sum):
    """
    根据目标总风量，自动匹配多型号设备组合，并强制预留 10% 安全余量。
    """
    # 设定安全余量为 10%
    SAFETY_MARGIN = 1.10
    buffered_target = target_airflow_sum * SAFETY_MARGIN
    
    if target_airflow_sum <= 0:
        return [], 0

    # 获取数据库中单台设备能达到的最大风量
    max_single_airflow = max(e["air_flow"] for e in EQUIPMENT_DATABASE)
    
    # 基于预留余量后的风量需求，重新计算所需的最小设备总数
    num_units = math.ceil(buffered_target / max_single_airflow)
    num_units = max(1, num_units)  # 至少需要 1 台
    
    best_combo = None
    min_diff = float('inf')
    best_power = float('inf')

    # 在所有可能的 N 台设备组合中寻找
    # 允许不同型号混合，且允许重复（即允许选两台同样的型号）
    for combo in combinations_with_replacement(EQUIPMENT_DATABASE, num_units):
        total_airflow = sum(e["air_flow"] for e in combo)
        
        # 必须满足 10% 余量后的总风量
        if total_airflow >= buffered_target:
            diff = total_airflow - buffered_target
            total_power = sum(e["power"] for e in combo)
            
            # 寻找差值最小的组合；若差值一致，则对比总功耗，优先选功耗小的
            if diff < min_diff or (abs(diff - min_diff) < 1e-6 and total_power < best_power):
                min_diff = diff
                best_power = total_power
                best_combo = combo

    # 结果排序：按风量从大到小排列，方便前端展示
    if best_combo:
        best_combo = sorted(list(best_combo), key=lambda x: x["air_flow"], reverse=True)
        
    return best_combo, num_units