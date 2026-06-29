# 泳池三集一体智能设计系统

## 项目简介

本项目是一套完整的暖通设备生成式设计系统。它底层应用了运筹学与启发式算法（GA/PSO），深度结合了暖通工程的实际业务逻辑（三集一体选型、风量计算、防结露气流组织），最终落脚于 3D 可视化与自动化管线路由。系统能够实现从几何参数输入、物理风量计算、设备自动选型到机房自动化排布与 3D 渲染的全链路闭环设计。

## 核心文件与系统架构说明

系统架构层次分明，由以下 17 个核心文件组成，分为 5 大主要模块：

### 一、 核心底座：几何引擎与配置管理
这是整个系统的基石，负责处理最底层的数学运算、空间干涉检查和数据初始化。
* **`layout_geometry_def.py`**：纯粹的底层几何数学库。提供分离轴定理（SAT）多边形碰撞检测、点在多边形内判定、线段相交、角度捕捉（10° 整数倍）等底层算法。
* **`layout_common_def.py`**：数据结构定义中心。利用 Python 的 dataclass 定义了遗传算法的基因 (`Gene`)、矩形规格 (`RectangleSpec`)、障碍物 (`SquareObstacle`) 和已放置设备 (`PlacedRect`) 等核心实体。
* **`config.py` & `example_pipeline_config.json`**：全局参数与设置管理。允许工程师通过 JSON 灵活调整设备的输入参数（长宽高、端口坐标）和算法调优权重（如边界面积惩罚权重）。

### 二、 2D 生成式排布引擎 (Generative Layout)
这一层解决了二维装箱（Bin Packing）优化问题，即设备在有限空间内如何摆放最紧凑。
* **`GA_layout.py` & `PSO_layout.py`**：指定边界排布算法。在已知的固大多边形边界内，通过遗传算法 (GA) 或粒子群算法 (PSO) 自动寻找设备的最优排布位置，最大化面积利用率并避免碰撞。
* **`auto_boundary_GA.py` & `auto_boundary_PSO.py`**：自动边界排布算法。在不知道机房大小的情况下，将包围盒的尺寸作为变量纳入优化维度，以求得出所需面积最小的最优机房尺寸。内含 `_decode` 和 `_is_rect_valid` 函数用于空间合法性校验。

### 三、 3D 正交管线路由引擎
* **`steiner_connect_3D.py`**：解决三维空间下的带避障正交斯坦纳树连接问题。将二维平面的设备“升维”成带有高度的 3D 长方体，并精确计算风口坐标（Ports），生成沿 X/Y/Z 轴对齐的管线路径。同时提供 3D 渲染，支持 Top/Front/Side 视角以及 Orthographic（正交）/ Perspective（透视）投影模式切换。

### 四、 流程编排与基准测试
* **`pipeline_2D_to_3D.py`**：全链路主控程序（Orchestrator）。串联 2D 自动排布与 3D 管线连接生成工作流。支持 `--algo auto` 模式，实现 GA 与 PSO 算法的后台赛马机制，自动择优输出。
* **`test_layout.py` & `auto_boundary_test.py`**：算法基准测试工具，利用标准化测试集横向对比 GA 和 PSO 在运行时间、空间利用率和边界面积上的表现。

### 五、 暖通业务逻辑与前端 WebUI
* **` calculate_diffuser.py` **：后端核心计算大脑。根据大厅和泳池尺寸，通过“除湿需求”与“空间换气次数”双轨制校验并取最大值，计算总送排风量及防结露风口数量。
* **`select_model.py`**：智能选型模块。采用“分步逼近与反向复核算法”，并利用 `itertools.combinations_with_replacement` 在设备库中挑选出所需物理空间最小、最匹配风量需求的多型号组合方案。
* **`visualize_pool.py`**：Matplotlib 3D 渲染模块。利用 `Rectangle` 绘制真实尺寸的地板风口面片，并通过 `art3d.pathpatch_2d_to_3d` 映射至 3D 平面中。
* **`toweb_2.py`**： Web 主入口。它不仅包含 `app.py` 与 `visualize_pool.py` 的前端逻辑，还吸收了原计划中的数据桥梁功能，实现了用户输入 -> 风量计算 -> 设备多组合寻优 -> 算法赛马机房生成 -> 3D 渲染的全自动联动闭环。

##  快速启动

**1. 命令行自动化流水线**

```bash
streamlit run airscience/toweb_2.py