# -*- coding: gbk -*-
import math


SLOT_AREA_PER_METER = 0.3  # 每米条缝风口的有效出风面积 (m2/m)
STANDARD_PIECE_LENGTH = 1 # 拟定单段风口标准长度 (m)
def calculate_diffuser_by_geometry(room_length: float, room_width: float, room_height: float, 
                                   pool_length: float, pool_width: float) -> dict:
    """
    根据大厅的长宽高、以及泳池水面的长宽，自动计算所需地面送风口数量。
    """
    # --- 1. 计算派生几何参数 ---
    room_area = room_length * room_width    # 大厅建筑面积 (㎡)
    room_volume = room_area * room_height   # 大厅体积 (m?)
    pool_area = pool_length * pool_width    # 泳池水面面积 (㎡)
    
    # --- 2. 硬编码工程默认值 ---
    ACH_DEFAULT = 4          # 10米高空间推荐的换气次数 (次/小时)
    UNIT_EVAP_RATE = 0.22      # 标准工况下单位水面蒸发率 (kg/(m2·h))
    DELTA_D = 3.0              # 三集一体机进出含湿量差 (g/kg)
    AIR_DENSITY = 1.2          # 标准空气密度 (kg/m3)
    DESIGN_VELOCITY = 2.5      # 风口设计出风速 (m/s)
    
    # 风口物理规格限制（标准双槽条缝风口）

    
    # --- 3. 核心风量计算逻辑 ---
    
    # 轨道一：基于水面蒸发量（除湿需求）计算风量
    total_evaporation = pool_area * UNIT_EVAP_RATE  # 总散湿量 kg/h
    air_flow_by_dehumidify = total_evaporation / (AIR_DENSITY * DELTA_D * 0.001)
    
    # 轨道二：基于大厅整体体积和换气次数校核风量
    air_flow_by_ach = room_volume * ACH_DEFAULT
    
    # 取两者最大值作为系统总送风量
    total_supply_air_flow = max(air_flow_by_dehumidify, air_flow_by_ach)
    
    # --- 4. 计算风口数量 ---
    
    # 计算风口需要的总有效出风面积
    total_effective_area = total_supply_air_flow / (3600 * DESIGN_VELOCITY)
    
    # 计算需要风口的总长度
    total_required_length = total_effective_area / SLOT_AREA_PER_METER
    
    # 计算单个标准长度风口的有效面积
    single_diffuser_area = SLOT_AREA_PER_METER * STANDARD_PIECE_LENGTH
    
    # 向上取整得到最终风口个数
    diffuser_count = math.ceil(total_effective_area / single_diffuser_area)
    
    # --- 5. 组装结果输出 ---
    return {
        "room_area_m2": round(room_area, 2),
        "room_volume_m3": round(room_volume, 2),
        "pool_area_m2": round(pool_area, 2),
        "calculated_total_airflow_cmh": round(total_supply_air_flow, 2),
        "limiting_factor": "大空间换气次数限制 (Volume Ventilation)" if air_flow_by_ach > air_flow_by_dehumidify else "除湿负荷限制 (Dehumidification)",
        "total_required_length_m": round(total_required_length, 2),
        "suggested_diffuser_count": diffuser_count,
        "single_diffuser_spec": f"{STANDARD_PIECE_LENGTH}米 标准线型条缝风口"
    }

# --- 测试运行 ---
if __name__ == "__main__":
    # 示例输入：
    # 大厅：长 30米，宽 20米，高 10米
    # 泳池：长 25米，宽 12米
    r_len, r_wid, r_hei = 60.0, 60.0, 10.0
    p_len, p_wid = 50.0, 40.0
    
    result = calculate_diffuser_by_geometry(
        room_length=r_len, room_width=r_wid, room_height=r_hei,
        pool_length=p_len, pool_width=p_wid
    )
    
    print("====== 泳池送风口自动计算结果 ======")
    print(f"输入大厅尺寸: 长 {r_len}m * 宽 {r_wid}m * 高 {r_hei}m (面积: {result['room_area_m2']} ㎡)")
    print(f"输入水面尺寸: 长 {p_len}m * 宽 {p_wid}m (水面面积: {result['pool_area_m2']} ㎡)")
    print("-" * 40)
    print(f"系统计算总送风量: {result['calculated_total_airflow_cmh']} ㎡/h")
    print(f"风量主导因素: {result['limiting_factor']}")
    print(f"需要风口总长度: {result['total_required_length_m']} 米")
    print(f" 最终输出【送风口个数】: {result['suggested_diffuser_count']} 个 ({result['single_diffuser_spec']})")