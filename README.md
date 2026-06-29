# 泳池三集一体智能设计系统

## 项目简介

本项目是一套完整的暖通设备生成式设计系统。它底层应用了运筹学与启发式算法（GA/PSO），深度结合了暖通工程的实际业务逻辑（三集一体选型、风量计算、防结露气流组织），最终落脚于 3D 可视化与自动化管线路由。系统能够实现从几何参数输入、物理风量计算、设备自动选型到机房自动化排布与 3D 渲染的全链路闭环设计。

## 核心文件与系统架构说明

系统架构层次分明，由以下 17 个核心文件组成，分为 5 大主要模块：

### 一、 几何引擎与配置管理

* **`layout_geometry_def.py`**：纯粹的底层几何数学库。提供分离轴定理（SAT）多边形碰撞检测、点在多边形内判定、线段相交、角度捕捉（10° 整数倍）等底层算法。
* **`layout_common_def.py`**：数据结构定义中心。利用 Python 的 dataclass 定义了遗传算法的基因 (`Gene`)、矩形规格 (`RectangleSpec`)、障碍物 (`SquareObstacle`) 和已放置设备 (`PlacedRect`) 等核心实体。
* **`config.py` & `example_pipeline_config.json`**：全局参数与设置管理。允许工程师通过 JSON 灵活调整设备的输入参数（长宽高、端口坐标）和算法调优权重（如边界面积惩罚权重）。

### 二、 2D 生成式排布引擎 (Generative Layout)

* **指定边界排布：`GA_layout.py` 与 `PSO_layout.py`**
  - **作用：** 在**已知的固大多边形边界**内（如特定的机房形状），自动寻找设备的最优排布位置。目标是最大化面积利用率，同时避免设备碰撞、避开障碍物，并强偏好水平/竖直的轴对齐摆放（通过角度惩罚实现）。
  - **用法：** 传入指定的 Polygon 坐标、设备清单和障碍物，分别通过遗传算法（GA）或粒子群算法（PSO）输出每个设备的最优 $(X, Y)$ 坐标和旋转角度。
* **自动边界排布：`auto_boundary_GA.py` 与 `auto_boundary_PSO.py`**
  - **作用：** 更高阶的排布寻优。在不知道具体机房大小的情况下，算法除了优化设备的相对位置，还将**包围盒的尺寸（边界的宽和高）作为变量**纳入优化维度，以求得出所需面积最小的机房尺寸。
  - **用法：** 直接传入设备清单，算法输出最优排布的同时，顺带生成一个极其紧凑的外包矩形边界，常用于项目前期的空间预估。

### 三、 3D 正交管线路由引擎

* **`steiner_connect_3D.py`**
  - **作用：** 解决三维空间下的**带避障正交斯坦纳树连接**问题。它将 2D 排布结果推挤成带有高度的 3D 长方体 (Cuboid)，并在指定的设备端口之间生成必须沿 X/Y/Z 轴对齐（曼哈顿距离）的管线路径，同时严禁管线穿过设备本身。
  - **用法：** 接收 3D 长方体信息、端口坐标 (`u, v` 映射面) 和连接分组，使用带碰撞惩罚的 GA 算法寻找最优 Steiner 点位置，并使用 `matplotlib` 进行 3D 渲染，支持前端的正交/透视投影切换和视角交互。

### 四、 流程编排与测试

* **`pipeline_2D_to_3D.py`**

  - **作用：** 全链路主控程序（Orchestrator）。它像一条流水线，先跑 2D 自动边界排布得到平面坐标 $\rightarrow$ 结合配置赋予设备高度和端口 $\rightarrow$ 丢给 3D 算法生成连接管线 $\rightarrow$ 输出最终的整体设计和 3D 可视化图。

  - **用法：** 核心工作流入口。通过终端执行 `python pipeline_2D_to_3D.py --config xxx.json` 即可一键完成从清单到 3D MEP 管线的全套生成。

  - ```
    #自动调用
    python pipeline_2D_to_3D.py --config example_pipeline_config.json
    python pipeline_2D_to_3D.py --config example_pipeline_config.json --algo auto
    #手动调用GA或PSO
    python pipeline_2D_to_3D.py --config example_pipeline_config.json --algo pso
    python pipeline_2D_to_3D.py --config example_pipeline_config.json --algo pso
    ```

    
* **`test_layout.py` & `auto_boundary_test.py`**

  - **作用：** 算法基准测试（Benchmark）工具。内置了从简单（少量矩形无障碍）到困难（大量矩形复杂多边形+多障碍物）的标准化测试集，横向对比 GA 和 PSO 算法。
  - **用法：** 运行后自动生成多组测试，对比 GA 和 PSO 在运行时间、空间利用率、边界面积等指标上的优劣，并输出详细的 JSON 报告和 `.txt` 对比表格，用于算法选型和调参。

### 五、 暖通业务逻辑与前端 WebUI
* **` calculate_diffuser.py` **：后端核心计算大脑。根据大厅和泳池尺寸，通过“除湿需求”与“空间换气次数”双轨制校验并取最大值，计算总送排风量及防结露风口数量。
* **`select_model.py`**：智能选型模块。采用“分步逼近与反向复核算法”，并利用 `itertools.combinations_with_replacement` 在设备库中挑选出所需物理空间最小、最匹配风量需求的多型号组合方案。
* **`visualize_pool.py`**：Matplotlib 3D 渲染模块。利用 `Rectangle` 绘制真实尺寸的地板风口面片，并通过 `art3d.pathpatch_2d_to_3d` 映射至 3D 平面中。
* **`toweb_2.py`**： Web 主入口。它不仅包含 `app.py` 与 `visualize_pool.py` 的前端逻辑，还吸收了原计划中的数据桥梁功能，实现了用户输入 -> 风量计算 -> 设备多组合寻优 -> 算法赛马机房生成 -> 3D 渲染的全自动联动闭环。

##  快速启动

```bash
streamlit run airscience/toweb_2.py
```