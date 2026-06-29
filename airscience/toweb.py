# -*- coding: gbk -*-
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import mpl_toolkits.mplot3d.art3d as art3d

from calculate_diffuser import calculate_diffuser_by_geometry  

# 设置网页标题和图标
st.set_page_config(page_title="泳池三集一体气流智能设计系统", page_icon="?", layout="wide")

# --- 网页头部 ---
st.title("泳池三集一体系统 - 送风口自动计算与 3D 布局可视化")
st.markdown("输入泳池大厅及水面的几何参数，系统将自动进行暖通负荷校核，并实时渲染双侧对称下送风的三维数字孪生模型。")
st.write("---")

# --- 侧边栏：参数输入面板 ---
st.sidebar.header("几何参数输入面板")

st.sidebar.subheader("1. 泳池大厅（池区）尺寸")
room_length = st.sidebar.number_input("大厅长度 (X: 米)", min_value=1.0, max_value=200.0, value=32.0, step=1.0)
room_width = st.sidebar.number_input("大厅宽度 (Y: 米)", min_value=1.0, max_value=200.0, value=20.0, step=1.0)
room_height = st.sidebar.number_input("大厅高度 (Z: 米)", min_value=1.0, max_value=50.0, value=10.0, step=0.5)

st.sidebar.subheader("2. 泳池水面尺寸")
pool_length = st.sidebar.number_input("泳池长度 (米)", min_value=1.0, max_value=150.0, value=25.0, step=1.0)
pool_width = st.sidebar.number_input("泳池宽度 (米)", min_value=1.0, max_value=100.0, value=12.0, step=1.0)

# 基础数据安全校验
if pool_length >= room_length or pool_width >= room_width:
    st.error("错误：泳池水面尺寸不能大于或等于大厅的尺寸，请重新检查侧边栏输入！")
    st.stop()

# --- 后端核心算法调度 ---
calc_result = calculate_diffuser_by_geometry(room_length, room_width, room_height, pool_length, pool_width)
base_count = calc_result["suggested_diffuser_count"]

# 双侧平分与奇数修正逻辑
if base_count % 2 != 0:
    total_count = base_count + 1
    is_modified = True
else:
    total_count = base_count
    is_modified = False
side_count = total_count // 2

# --- 网页主界面布局：左边看数据，右边看 3D 图 ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("自动化计算结果")
    
    # 用漂亮的指标卡片显示核心数据
    st.metric(label="建议送风口总数", value=f"{total_count} 个", delta="+1 (奇数修正)" if is_modified else None)
    
    st.markdown(f"""
    * **两侧排布**：泳池长边双侧对称排布，每侧 **{side_count}** 个。
    * **风口物理规格**：1.0米 × 0.2米 标准线型条缝风口。
    * **系统计算总风量**：`{calc_result['calculated_total_airflow_cmh']} m?/h`
    * **风量主导因素**：{calc_result['limiting_factor']}
    * **需要风口总长度**：`{calc_result['total_required_length_m']} 米`
    """)
    
    st.info("""
    **暖通工程设计提示**：
    当前采用“下送上回”方案。送风口以 2.5 m/s 的低风速贴墙向上送风，形成对落地玻璃的空气热衬，防止结露；顶部回风口（本图未展示）建议设在 10m 顶部正上方。
    """)

with col2:
    st.subheader("3D 空间布局渲染")
    
    # --- 3D 绘图逻辑 (无缝迁移自你之前的代码) ---
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
    is_x_long = room_length >= room_width
    diffuser_boxes = [] 
    margin = 1.0  
    
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

    # 关键：将 matplotlib 的图表传递给 streamlit 网页组件
    st.pyplot(fig)