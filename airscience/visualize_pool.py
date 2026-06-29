# -*- coding: gbk -*-
# -*- coding: utf-8 -*-
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import mpl_toolkits.mplot3d.art3d as art3d
from calculate_diffuser import calculate_diffuser_by_geometry
import calculate_diffuser as config  

def draw_3d_pool_system(room_length, room_width, room_height, pool_length, pool_width):
    ## 1. 调用基础算法获取风口基准数量
    calc_result = calculate_diffuser_by_geometry(
        room_length, room_width, room_height, pool_length, pool_width
    )
    base_count = calc_result["suggested_diffuser_count"]
    
    # 双侧平分与奇数修正
    if base_count % 2 != 0:
        total_count = base_count + 1
        print(f"原始计算风口数为奇数 ({base_count})，自动修正为偶数: {total_count} 个")
    else:
        total_count = base_count
        print(f"原始计算风口数为偶数: {total_count} 个")
        
    side_count = total_count // 2
    print(f"通风口将分列泳池长边两侧，每侧布置: {side_count} 个")

    # 风口物理尺寸参数设置 ----
    diffuser_length = config.STANDARD_PIECE_LENGTH  # 单个通风口长度 (m)
    diffuser_height = config.SLOT_AREA_PER_METER/config.STANDARD_PIECE_LENGTH   # 单个通风口宽度 (m)
    # print(f"{diffuser_length=}，{diffuser_height=}")

    # 2. 初始化画布与中文防乱码配置
    plt.rcParams['font.sans-serif'] = ['SimHei']  
    plt.rcParams['axes.unicode_minus'] = False    
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    
    # 3. 几何坐标计算
    room_center_x = room_length / 2.0
    room_center_y = room_width / 2.0
    
    pool_x_min = room_center_x - (pool_length / 2.0)
    pool_x_max = room_center_x + (pool_length / 2.0)
    pool_y_min = room_center_y - (pool_width / 2.0)
    pool_y_max = room_center_y + (pool_width / 2.0)
    
    # 4. 计算两侧风口的几何中心坐标
    # 默认认为 room_length 是长边，风口排布在 Y 轴的两端外墙根（Y=0 侧 和 Y=room_width 侧）
    # 如果 Width 是长边，则转为 X 轴两端
    is_x_long = room_length >= room_width
    
    # 用来存储所有风口矩形的左下角起点坐标，用于后续画矩形
    # 格式: (x, y, width_dim, length_dim, orientation)
    diffuser_boxes = [] 
    margin = (room_length-pool_length)/2  
    
    if is_x_long:
        # 长边在 X 方向，两侧墙基线分别为 y = 0.1 和 y = room_width - 0.1 - diffuser_height
        y_pos = 2.0
        
        if side_count > 1:
            step = (room_length - 2 * margin - diffuser_length) / (side_count - 1)
            for i in range(side_count):
                x_pos = margin + i * step
                diffuser_boxes.append((x_pos, y_pos, diffuser_length, diffuser_height)) # 侧面 1
                #diffuser_boxes_2.append((x_pos, y_pos, diffuser_length, diffuser_height)) # 侧面 2
        else:
            x_pos = room_center_x - (diffuser_length / 2.0)
            diffuser_boxes.append((x_pos, y_pos, diffuser_length, diffuser_height))
            #diffuser_boxes_2.append((x_pos, y_pos, diffuser_length, diffuser_height))
    else:
        # 长边在 Y 方向，两侧墙基线分别为 x = 0.1 和 x = room_length - 0.1 - diffuser_height
        y_pos = 2.0
        
        if side_count > 1:
            step = (room_width - 2 * margin - diffuser_length) / (side_count - 1)
            for i in range(side_count):
                x_pos = margin + i * step
                # 注意这里长宽颠倒，因为是贴着Y轴长边走
                diffuser_boxes.append((x_pos, y_pos, diffuser_height, diffuser_length)) 
                #diffuser_boxes_2.append((x_pos, y_pos, diffuser_height, diffuser_length)) 
        else:
            y_pos = room_center_y - (diffuser_length / 2.0)
            diffuser_boxes.append((x_pos, y_pos, diffuser_height, diffuser_length))
            #diffuser_boxes_2.append((x_pos, y_pos, diffuser_height, diffuser_length))

    # --- 5. 渲染 3D 场景 ---
    
    # A. 绘制大厅整体框架
    ax.plot([0, room_length, room_length, 0, 0], [0, 0, room_width, room_width, 0], [0, 0, 0, 0, 0], 'gray', label='大厅地面')
    ax.plot([0, room_length, room_length, 0, 0], [0, 0, room_width, room_width, 0], [room_height, room_height, room_height, room_height, room_height], 'gray', linestyle='--')
    for x_p, y_p in [(0,0), (room_length, 0), (room_length, room_width), (0, room_width)]:
        ax.plot([x_p, x_p], [y_p, y_p], [0, room_height], 'gray', linestyle=':')

    # B. 绘制居中泳池并填充蓝色
    ax.plot([pool_x_min, pool_x_max, pool_x_max, pool_x_min, pool_x_min], 
            [pool_y_min, pool_y_min, pool_y_max, pool_y_max, pool_y_min], [0, 0, 0, 0, 0], 'b-', linewidth=2)
    pool_patch = Rectangle((pool_x_min, pool_y_min), pool_length, pool_width, color='skyblue', alpha=0.5, label='泳池水面')
    ax.add_patch(pool_patch)
    art3d.pathpatch_2d_to_3d(pool_patch, z=0, zdir="z")

    # C. 绘制具有真实尺寸的红色矩形通风口
    for idx, box in enumerate(diffuser_boxes):
        bx, by, b_w, b_l = box
        # 创建真实的矩形面片
        # 为了在图例中只显示一个标签，我们只给第一个风口加 label
        lbl = f'地面送风口 ({diffuser_length}m × {diffuser_height}m)' if idx == 0 else ""
        diff_patch = Rectangle((bx, by), b_w, b_l, color='red', alpha=0.9, label=lbl)
        ax.add_patch(diff_patch)
        art3d.pathpatch_2d_to_3d(diff_patch, z=0.1, zdir="y") 

    for idx, box in enumerate(diffuser_boxes):
        bx, by, b_w, b_l = box
        # 创建真实的矩形面片
        # 为了在图例中只显示一个标签，我们只给第一个风口加 label
        #lbl = f'地面送风口 ({diffuser_length}m × {diffuser_height}m)' if idx == 0 else ""
        diff_patch = Rectangle((bx, by), b_w, b_l, color='red', alpha=0.9, label=lbl)
        ax.add_patch(diff_patch)
        art3d.pathpatch_2d_to_3d(diff_patch, z=room_width-0.1, zdir="y")

    # --- 6. 界面优化配置 ---
    ax.set_xlabel('长 (X: 米)')
    ax.set_ylabel('宽 (Y: 米)')
    ax.set_zlabel('高 (Z: 米)')
    ax.set_title(f'泳池下送风双侧对称布局 (总数: {total_count} 个)')
    
    ax.set_box_aspect([room_length, room_width, room_height]) 
    ax.set_xlim(0, room_length)
    ax.set_ylim(0, room_width)
    ax.set_zlim(0, room_height + 1)
    
    ax.legend(loc='upper left')
    ax.view_init(elev=30, azim=-55) # 调整到一个极佳的俯视透视视角
    
    print("三维真实尺寸图像生成")
    plt.show()

# --- 测试运行 ---
if __name__ == "__main__":
    # 传入你想要的尺寸参数进行测试
    draw_3d_pool_system(
        room_length=60.0, 
        room_width=60.0, 
        room_height=10.0, 
        pool_length=50.0, 
        pool_width=40.0
    )