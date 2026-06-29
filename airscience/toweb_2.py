# -*- coding: gbk -*-
import streamlit as st
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import mpl_toolkits.mplot3d.art3d as art3d
import sys
import os

# ==================== 动态将上级目录加入 Python 搜索路径 ====================
# 获取当前文件（toweb_2.py）所在的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 寻找到它的上一级目录（即存放算法核心文件的目录）
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))

# 如果上级目录不在搜索路径中，将其插入到最前面（优先搜索）
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
# ==============================================================================

# ==================== 导入生成式设计模块 ====================
try:
    from pipeline_2D_to_3D import run_pipeline
    from layout_common_def import RectangleSpec as Rect2D
    from config import PipelineConfig, Equipment3DConfig
except ImportError as e:
    st.error(f"错误：找不到排布算法文件！请检查上级目录是否包含算法核心文件。错误信息: {e}")

# 导入基础计算与选型函数 (确保这俩文件跟 toweb_2.py 在一起)
from calculate_diffuser import calculate_diffuser_by_geometry  
from select_model import auto_select_equipment_by_airflow

# 设置网页
st.set_page_config(page_title="泳池三集一体智能选型与设计系统", layout="wide")

# ==================== 数据转换桥梁函数 ====================
def build_layout_config(best_combo):
    """
    将选型结果（由多个设备组成的元组）转换为生成式 2D/3D 算法所需的配置。
    """
    rectangles_2d = []
    equipment_3d_configs = []
    all_in_ports = []
    all_out_ports = []

    # 遍历元组中的每一个设备
    for i, equip in enumerate(best_combo):
        unit_id = f"R{i+1}"
        
        # 1. 2D 矩形规范：直接使用设备自带的长度和宽度
        rect = Rect2D(
            id=unit_id, 
            width=equip["length"], 
            height=equip["width"], 
            rotatable=True, 
            mandatory=True
        )
        rectangles_2d.append(rect)

        # 2. 3D 设备与端口规范：使用设备自带的高度
        in_port_id = f"P{i+1}_in"
        out_port_id = f"P{i+1}_out"
        
        eq_config = Equipment3DConfig(
            rect_id=unit_id,
            height=equip["height"],  # 使用设备实际高度
            ports=[
                {"id": in_port_id, "face": "top", "u": 0.3, "v": 0.5},
                {"id": out_port_id, "face": "top", "u": 0.7, "v": 0.5}
            ]
        )
        equipment_3d_configs.append(eq_config)
        all_in_ports.append(in_port_id)
        all_out_ports.append(out_port_id)

    # 3. 构建连接组 (如果组合中有2台以上，把它们的进风口连一起，出风口连一起)
    connections = [all_in_ports, all_out_ports] if len(best_combo) > 1 else []

    # 4. 生成完整 Pipeline 配置
    pipeline_config = PipelineConfig(
        rectangles=[{"id": r.id, "width": r.width, "height": r.height, "mandatory": r.mandatory} for r in rectangles_2d],
        equipment=equipment_3d_configs,
        connections=connections,
        ga_2d_kwargs={"population_size": 100, "generations": 200, "boundary_area_weight": 0.1}, 
        ga_3d_kwargs={"population_size": 100, "generations": 200}
    )

    return rectangles_2d, pipeline_config


# ==================== 2. 网页前端布局 ====================
st.title("泳池三集一体机智能选型与 3D 布局系统")
st.write("---")

# 侧边栏：参数面板
st.sidebar.header("几何尺寸输入")

st.sidebar.subheader("1. 大厅（池区）建筑尺寸")
room_length = st.sidebar.number_input("大厅长度 (X: 米)", min_value=1.0, max_value=200.0, value=60.0, step=1.0)
room_width = st.sidebar.number_input("大厅宽度 (Y: 米)", min_value=1.0, max_value=200.0, value=60.0, step=1.0)
room_height = st.sidebar.number_input("大厅高度 (Z: 米)", min_value=1.0, max_value=50.0, value=10.0, step=0.5)

st.sidebar.subheader("2. 泳池水面尺寸")
pool_length = st.sidebar.number_input("泳池长度 (米)", min_value=1.0, max_value=150.0, value=50.0, step=1.0)
pool_width = st.sidebar.number_input("泳池宽度 (米)", min_value=1.0, max_value=100.0, value=40.0, step=1.0)

# 数据安全拦截
if pool_length >= room_length or pool_width >= room_width:
    st.error(" 错误：泳池尺寸超过大厅尺寸，请修改参数！")
    st.stop()


# ==================== 3. 核心计算与选型调度 ====================
calc_result = calculate_diffuser_by_geometry(room_length, room_width, room_height, pool_length, pool_width)
total_airflow = calc_result["calculated_total_airflow_cmh"]

best_combo, num_units = auto_select_equipment_by_airflow(total_airflow)


# ==================== 4. 界面主面板显示 ====================
col1, col2 = st.columns([1, 2])

with col1:
    
    st.markdown("#### 最小台数设备匹配")
    if best_combo:
        # 计算组合的总数据
        total_combo_airflow = sum(e['air_flow'] for e in best_combo)
        total_combo_power = sum(e['power'] for e in best_combo)
        model_list_str = "".join([f"- {e['model']}<br>" for e in best_combo])

        sub_c1, sub_c2 = st.columns(2)

        # 1. 选用设备型号：如果设备种类多
        sub_c1.markdown(f"**选用组合方案：**<br><span style='font-size:18px;'>{model_list_str}</span>", unsafe_allow_html=True)
        # 2. 所需台数：best_combo 的长度即为台数
        sub_c2.markdown(f"**总设备台数**<br><span style='font-size:24px; font-weight:bold;'>{len(best_combo)}台</span>", unsafe_allow_html=True)
        # 3. 策略执行提示
        st.markdown(
            f"""
            <div style="background-color: #d4edda; color: #155724; padding: 16px; border-radius: 4px; border-left: 5px solid #28a745; margin-bottom: 20px; margin-top: 20px;">
                策略执行：成功通过多机组合方式（共 <b>{len(best_combo)}台</b>）满足风量需求。
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # 4. 选型核心数据对比
        # 安全余量计算逻辑：(实际总风量 - 目标需求) / 目标需求
        margin = (total_combo_airflow - total_airflow) / total_airflow * 100
        
        st.markdown(f"""
        **选型核心数据对比：**
        * 目标总风量需求：`{round(total_airflow, 0)} m3/h`
        * 组合总额定风量：`{total_combo_airflow} m3/h` 
        * 选型风量安全余量：`{round(margin, 1)}%`
        * 机组运行总电功率估算：`{round(total_combo_power, 1)} kW` 
        """, unsafe_allow_html=True)
        
    else:
        st.error(" 错误：系统所需总风量极大，已超出当前预设设备库的最大承载范围。")

    st.write("---")
    
    # 风口数量统计
    st.markdown("#### 送风口排布统计")
    base_count = calc_result["suggested_diffuser_count"]
    if base_count % 2 != 0:
        total_diffusers = base_count + 1
        st.warning(f"风口总数已进行双侧对称凑整 (由 {base_count} 修正为 {total_diffusers} 个)")
    else:
        total_diffusers = base_count
        st.info(f"风口总数符合双侧完美对称: {total_diffusers} 个")
        
    st.metric(label="每侧长边墙脚风口数", value=f"{total_diffusers // 2} 个")
    st.caption("单段风口设计物理尺寸: 1.0m x 0.2m")

with col2:
    st.subheader("池区通风口3D示意图")
    
    # --- 3D 绘图渲染 ---
    plt.rcParams['font.sans-serif'] = ['SimHei']  
    plt.rcParams['axes.unicode_minus'] = False    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    room_center_x = room_length / 2.0
    room_center_y = room_width / 2.0
    pool_x_min = room_center_x - (pool_length / 2.0)
    pool_x_max = room_center_x + (pool_length / 2.0)
    pool_y_min = room_center_y - (pool_width / 2.0)
    pool_y_max = room_center_y + (pool_width / 2.0)
    
    diffuser_length, diffuser_width = 1.0, 0.2
    side_count = total_diffusers // 2
    is_x_long = room_length >= room_width
    diffuser_boxes = [] 
    margin =  (room_length-pool_length)/2
    
    if is_x_long:
        y_pos = 2
        #y_side2 = room_width - 0.1
        if side_count > 1:
            step = (room_length - 2 * margin - diffuser_length) / (side_count - 1)
            for i in range(side_count):
                x_pos = margin + i * step
                diffuser_boxes.append((x_pos, y_pos, diffuser_length, diffuser_width))
                #diffuser_boxes.append((x_pos, y_pos, diffuser_length, diffuser_width))
        else:
            x_pos = room_center_x - (diffuser_length / 2.0)
            diffuser_boxes.append((x_pos, y_pos, diffuser_length, diffuser_width))
            #diffuser_boxes.append((x_pos, y_side2, diffuser_length, diffuser_width))
    else:
        y_pos = 2
        #x_side2 = room_length - 0.1 - diffuser_width
        if side_count > 1:
            step = (room_width - 2 * margin - diffuser_length) / (side_count - 1)
            for i in range(side_count):
                x_pos = margin + i * step
                diffuser_boxes.append((x_pos, y_pos, diffuser_width, diffuser_length)) 
                #diffuser_boxes.append((x_side2, y_pos, diffuser_width, diffuser_length)) 
        else:
            x_pos = room_center_y - (diffuser_length / 2.0)
            diffuser_boxes.append((x_pos, y_pos, diffuser_width, diffuser_length))
            #diffuser_boxes.append((x_side2, y_pos, diffuser_width, diffuser_length))

    # 绘制空间线条
    ax.plot([0, room_length, room_length, 0, 0], [0, 0, room_width, room_width, 0], [0, 0, 0, 0, 0], 'gray', label='大厅地面')
    ax.plot([0, room_length, room_length, 0, 0], [0, 0, room_width, room_width, 0], [room_height, room_height, room_height, room_height, room_height], 'gray', linestyle='--')
    for x_p, y_p in [(0,0), (room_length, 0), (room_length, room_width), (0, room_width)]:
        ax.plot([x_p, x_p], [y_p, y_p], [0, room_height], 'gray', linestyle=':')

    # 绘制水面
    ax.plot([pool_x_min, pool_x_max, pool_x_max, pool_x_min, pool_x_min], 
            [pool_y_min, pool_y_min, pool_y_max, pool_y_max, pool_y_min], [0, 0, 0, 0, 0], 'b-', linewidth=2)
    pool_patch = Rectangle((pool_x_min, pool_y_min), pool_length, pool_width, color='skyblue', alpha=0.5, label='泳池水面')
    ax.add_patch(pool_patch)
    art3d.pathpatch_2d_to_3d(pool_patch, z=0, zdir="z")

    # 绘制真实尺寸风口矩形
    for idx, box in enumerate(diffuser_boxes):
        bx, by, b_w, b_l = box
        lbl = f'地面送风口 ({diffuser_length}m × {diffuser_width}m)' if idx == 0 else ""
        diff_patch = Rectangle((bx, by), b_w, b_l, color='red', alpha=0.9, label=lbl)
        ax.add_patch(diff_patch)
        art3d.pathpatch_2d_to_3d(diff_patch, z=0.1, zdir="y")

    for idx, box in enumerate(diffuser_boxes):
        bx, by, b_w, b_l = box
        #lbl = f'地面送风口 ({diffuser_length}m × {diffuser_width}m)' if idx == 0 else ""
        diff_patch = Rectangle((bx, by), b_w, b_l, color='red', alpha=0.9, label=lbl)
        ax.add_patch(diff_patch)
        art3d.pathpatch_2d_to_3d(diff_patch, z=room_width-0.1, zdir="y")

    # 视图配置
    ax.set_xlabel('长 (X: 米)')
    ax.set_ylabel('宽 (Y: 米)')
    ax.set_zlabel('高 (Z: 米)')
    ax.set_box_aspect([room_length, room_width, room_height]) 
    ax.set_xlim(0, room_length)
    ax.set_ylim(0, room_width)
    ax.set_zlim(0, room_height + 1)
    ax.legend(loc='upper left')
    ax.view_init(elev=30, azim=-55)

    st.pyplot(fig)


st.divider()

# ==================== 5. 智能机房生成与 3D 排布 (联动核心) ====================
st.subheader("机房生成式排布与正交管线路由")

if best_combo:
    st.write(f"系统将基于已选的 {num_units} 台 设备，自动计算所需最小机房面积，并生成 3D 管线连接方案。")
    
    # 算法选择下拉框
    algo_choice = st.selectbox("选择底层平面排布寻优算法：", ["auto (智能对比选优)", "ga (遗传算法)", "pso (粒子群算法)"])

    if st.button("开始一键生成机房 3D 布局", type="primary"):
        with st.spinner("AI 正在进行空间压缩寻优与正交管线寻路，请稍候（约 3-8 秒）..."):
            
            # 1. 调用数据桥梁构建入参
            rectangles_2d, pipeline_config = build_layout_config(best_combo)
            
            # 2. 调用 pipeline_2D_to_3D
            algo_param = algo_choice.split(" ")[0]
            try:
                # 运行主管道
                result = run_pipeline(
                    rectangles_2d=rectangles_2d,
                    pipeline_config=pipeline_config,
                    algo=algo_param, 
                    skip_plots=False  
                )
                
                st.success("机房生成成功！")
                
                # 3. 提取基本参数并展示
                layout_2d = result["layout_2d"]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("计算最优机房长 (X方向)", f"{layout_2d['boundary_w']:.2f} m")
                m2.metric("计算最优机房宽 (Y方向)", f"{layout_2d['boundary_h']:.2f} m")
                m3.metric("机房纯占地面积", f"{layout_2d['polygon_area']:.2f} m2")
                m4.metric("设备面积利用率", f"{layout_2d['utilization']*100:.1f}%")
                
                st.info(f"寻优细节：本次采用 {layout_2d.get('algo_name', algo_param.upper())} 算法获得最优解，耗时 {layout_2d.get('runtime_sec', 0):.2f} 秒。")

                # 4. 渲染 3D 机房连接图
                if "fig" in result and result["fig"]:
                    st.write("#### 生成式 3D 机房正交管线预览")
                    st.pyplot(result["fig"])
                else:
                    st.warning("提示：管道运行成功，但未返回 3D 图像对象 (fig)。请确认上级目录中 steiner_connect_3D.py 及 pipeline_2D_to_3D.py 已正确返回 fig。")
                    
            except Exception as e:
                st.error(f"机房生成过程中发生错误: {str(e)}")