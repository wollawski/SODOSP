"""
auto_boundary_GA.py �? 遗传算法二维矩形排布（自动生成矩形边界）�?

�? GA_layout.py 的核心区别：
  - 无需指定边界多边形，算法自动优化矩形边界 (W, H)
  - 适应度函数增加边界面积最小化目标
  - 边界尺寸作为染色体级基因参与进化
"""
from __future__ import annotations
import argparse
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from config import AlgorithmConfig
from layout_common_def import (
    Point,
    EPS,
    VALID_ANGLES_DEG,
    Gene,
    RectangleSpec,
    SquareObstacle,
    PlacedRect,
    clamp,
    wrap_angle,
    convex_overlap_strict,
    rect_inside_polygon,
    axis_alignment_deviation,
)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class Chromosome:
    boundary_w: float
    boundary_h: float
    genes: List[Gene]

    @staticmethod
    def polygon_from_boundary(w: float, h: float) -> List[Point]:
        return [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]


# ---------------------------------------------------------------------------
# 几何工具函数
# ---------------------------------------------------------------------------
# 遗传算法求解�? �? 自动边界�?
# ---------------------------------------------------------------------------
class AutoBoundaryGAPacker:
    """遗传算法矩形排布，自动优化矩形边界尺寸�?

    输入只需矩形规格和障碍物，边界由算法自动寻优�?
    适应�? = 面积奖励 + 数量奖励 - 碰撞惩罚 - 角度惩罚 - 边界面积惩罚
    """

    def __init__(
        self,
        obstacles: Sequence[SquareObstacle],
        rectangles: Sequence[RectangleSpec],
        population_size: int = 240,
        generations: int = 420,
        crossover_rate: float = 0.85,
        mutation_rate: float = 0.16,
        elite_count: int = 6,
        tournament_size: int = 3,
        angle_preference_weight: float = 50.0,
        boundary_area_weight: float = 0.5,
        random_seed: int | None = 20,
    ) -> None:
        self.obstacles = list(obstacles)
        self.rectangles = list(rectangles)

        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elite_count = elite_count
        self.tournament_size = tournament_size
        self.angle_preference_weight = angle_preference_weight
        self.boundary_area_weight = boundary_area_weight

        self.rng = random.Random(random_seed)

        # 根据矩形总面积估算边界尺寸的合理范围
        total_rect_area = sum(spec.width * spec.height for spec in self.rectangles)
        estimated_side = math.sqrt(total_rect_area * 1.5)

        max_rect_dim = 0.0
        for spec in self.rectangles:
            max_rect_dim = max(max_rect_dim, spec.width, spec.height)

        self.min_w = max(estimated_side * 0.3, max_rect_dim * 0.8)
        self.max_w = estimated_side * 3.0
        self.min_h = max(estimated_side * 0.3, max_rect_dim * 0.8)
        self.max_h = estimated_side * 3.0

        self._init_boundary_w = estimated_side * 1.2
        self._init_boundary_h = estimated_side * 1.2

        self._obstacle_polys = [o.as_polygon() for o in self.obstacles]

    @staticmethod
    def _polygon_area(polygon: Sequence[Point]) -> float:
        area = 0.0
        n = len(polygon)
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            area += x1 * y2 - x2 * y1
        return abs(area) / 2.0

    def _random_gene(self, spec: RectangleSpec) -> Gene:
        angle = 0.0
        if spec.rotatable:
            r = self.rng.random()
            if r < 0.9:
                angle = self.rng.choice([0.0, 0.5, 1.0, 1.5]) * math.pi
            else:
                deg = self.rng.choice(VALID_ANGLES_DEG)
                angle = math.radians(deg)

        return Gene(
            cx=self.rng.uniform(0.0, self._init_boundary_w),
            cy=self.rng.uniform(0.0, self._init_boundary_h),
            angle=angle,
            active=True if spec.mandatory else (self.rng.random() < 0.9),
        )

    def _init_population(self) -> List[Chromosome]:
        pop: List[Chromosome] = []
        for _ in range(self.population_size):
            bw = self.rng.uniform(self.min_w, self.max_w)
            bh = self.rng.uniform(self.min_h, self.max_h)
            genes = [self._random_gene(spec) for spec in self.rectangles]
            pop.append(Chromosome(boundary_w=bw, boundary_h=bh, genes=genes))
        return pop

    def _decode(
        self, chromosome: Chromosome
    ) -> Tuple[List[PlacedRect], List[Point]]:
        polygon = Chromosome.polygon_from_boundary(
            chromosome.boundary_w, chromosome.boundary_h
        )
        out: List[PlacedRect] = []
        for spec, gene in zip(self.rectangles, chromosome.genes):
            active = spec.mandatory or gene.active
            if not active:
                continue
            angle = wrap_angle(gene.angle if spec.rotatable else 0.0)
            out.append(
                PlacedRect(
                    id=spec.id,
                    cx=clamp(gene.cx, 0.0, chromosome.boundary_w),
                    cy=clamp(gene.cy, 0.0, chromosome.boundary_h),
                    width=spec.width,
                    height=spec.height,
                    angle=angle,
                    mandatory=spec.mandatory,
                )
            )
        return out, polygon

    def _is_rect_valid(
        self, rect: PlacedRect, already_kept: Sequence[PlacedRect], polygon: Sequence[Point]
    ) -> bool:
        
        # 1. 墙体净距限制 (1m)
        # polygon 是四个点: [(0,0), (W,0), (W,H), (0,H)]
        W = polygon[2][0]
        H = polygon[2][1]
        
        # 构建一个向内收缩 1m 的虚拟安全边界
        shrunk_polygon = [
            (1.0, 1.0), 
            (W - 1.0, 1.0), 
            (W - 1.0, H - 1.0), 
            (1.0, H - 1.0)
        ]
        # 使用内缩后的边界来判断：如果超出了安全区，说明离墙太近了，判违规！
        if not rect_inside_polygon(rect, shrunk_polygon):
            return False
        # 2. 设备间距限制 (1.2m)
        # 将当前准备放进去的设备，长宽各放大 1.2m（相当于四周各弹出 0.6m 的气囊）
        inflated_rect = PlacedRect(
            id=rect.id, cx=rect.cx, cy=rect.cy,
            width=rect.width + 1.2, height=rect.height + 1.2,  # 长宽增加 1.2
            angle=rect.angle, mandatory=rect.mandatory
        )
        rp_inflated = inflated_rect.corners() # 提取气囊边界点

        # 检查是否撞到承重柱/障碍物（这里保持原实体大小进行检测，如果你希望柱子也要有 1m 间距，就把 rect.corners() 换成 rp_inflated）
        rp_original = rect.corners()
        for op in self._obstacle_polys:
            if convex_overlap_strict(rp_original, op):
                return False

        # 遍历检查之前已经放好的设备
        for other in already_kept:
            # 把已经放好的设备，同样长宽各放大 1.2m（四周各弹出 0.6m 的气囊）
            inflated_other = PlacedRect(
                id=other.id, cx=other.cx, cy=other.cy,
                width=other.width + 1.2, height=other.height + 1.2, # 长宽增加 1.2
                angle=other.angle, mandatory=other.mandatory
            )
            # 如果两个气囊发生了重叠，说明真实铁皮之间的距离小于了 1.2m，判违规！
            if convex_overlap_strict(rp_inflated, inflated_other.corners()):
                return False
                
        return True

    def _fitness(self, chrom: Chromosome) -> float:
        placed, polygon = self._decode(chrom)
        area_reward = sum(r.area for r in placed)
        count_reward = 8.0 * len(placed)
        penalty = 0.0

        # 获取当前机房的宽和高
        W = chrom.boundary_w
        H = chrom.boundary_h

        # 1. 防止机房太小导致崩溃的底线保护
        if W <= 2.0 or H <= 2.0:
            penalty += 10000.0  # 扣一万分！
        else:
            # 2. 构建内缩 1m 的墙体安全边界
            shrunk_polygon = [
                (1.0, 1.0),
                (W - 1.0, 1.0),
                (W - 1.0, H - 1.0),
                (1.0, H - 1.0)
            ]
            
            for rect in placed:
                # 越界检测：如果超出了安全边界（即靠墙小于 1m），给予重罚
                if not rect_inside_polygon(rect, shrunk_polygon):
                    penalty += 520.0 + 6.0 * rect.area
                
                # 柱子等固定障碍物检测（保持原尺寸）
                rp_orig = rect.corners()
                for op in self._obstacle_polys:
                    if convex_overlap_strict(rp_orig, op):
                        penalty += 760.0
                
                # 角度惩罚
                penalty += self.angle_preference_weight * axis_alignment_deviation(rect.angle)

            # 3. 设备间 1.2m 净距检测
            # 提前构造放大 1.2m 的虚拟气囊，极大提升计算速度
            inflated_list = []
            for rect in placed:
                inflated_list.append(PlacedRect(
                    id=rect.id, cx=rect.cx, cy=rect.cy,
                    width=rect.width + 1.2, height=rect.height + 1.2,
                    angle=rect.angle, mandatory=rect.mandatory
                ).corners())

            # 气囊两两碰撞检测
            for i in range(len(inflated_list)):
                for j in range(i + 1, len(inflated_list)):
                    if convex_overlap_strict(inflated_list[i], inflated_list[j]):
                        penalty += 900.0  # 气囊碰撞即代表净距小于 1.2m，重罚！

        # ── 边界面积最小化惩罚 ──
        boundary_area = W * H
        boundary_penalty = self.boundary_area_weight * boundary_area
        penalty += boundary_penalty

        return area_reward + count_reward - penalty

    def _tournament_select(
        self, population: Sequence[Chromosome], fitnesses: Sequence[float]
    ) -> Chromosome:
        idxs = [self.rng.randrange(len(population)) for _ in range(self.tournament_size)]
        best_idx = max(idxs, key=lambda i: fitnesses[i])
        best = population[best_idx]
        copied_genes = [Gene(g.cx, g.cy, g.angle, g.active) for g in best.genes]
        return Chromosome(boundary_w=best.boundary_w, boundary_h=best.boundary_h, genes=copied_genes)

    def _crossover(
        self, p1: Chromosome, p2: Chromosome
    ) -> Tuple[Chromosome, Chromosome]:
        if self.rng.random() > self.crossover_rate:
            g1 = [Gene(g.cx, g.cy, g.angle, g.active) for g in p1.genes]
            g2 = [Gene(g.cx, g.cy, g.angle, g.active) for g in p2.genes]
            return (
                Chromosome(boundary_w=p1.boundary_w, boundary_h=p1.boundary_h, genes=g1),
                Chromosome(boundary_w=p2.boundary_w, boundary_h=p2.boundary_h, genes=g2),
            )

        # 交叉边界尺寸
        if self.rng.random() < 0.5:
            bw1, bw2 = p1.boundary_w, p2.boundary_w
        else:
            bw1, bw2 = p2.boundary_w, p1.boundary_w
        if self.rng.random() < 0.5:
            bh1, bh2 = p1.boundary_h, p2.boundary_h
        else:
            bh1, bh2 = p2.boundary_h, p1.boundary_h

        # 交叉矩形基因
        c1_genes: List[Gene] = []
        c2_genes: List[Gene] = []
        for g1, g2 in zip(p1.genes, p2.genes):
            if self.rng.random() < 0.5:
                c1_genes.append(Gene(g1.cx, g1.cy, g1.angle, g1.active))
                c2_genes.append(Gene(g2.cx, g2.cy, g2.angle, g2.active))
            else:
                c1_genes.append(Gene(g2.cx, g2.cy, g2.angle, g2.active))
                c2_genes.append(Gene(g1.cx, g1.cy, g1.angle, g1.active))

        return (
            Chromosome(boundary_w=bw1, boundary_h=bh1, genes=c1_genes),
            Chromosome(boundary_w=bw2, boundary_h=bh2, genes=c2_genes),
        )

    def _mutate(self, chromosome: Chromosome) -> Chromosome:
        # 边界尺寸变异
        bw = chromosome.boundary_w
        bh = chromosome.boundary_h
        if self.rng.random() < self.mutation_rate:
            span_w = (self.max_w - self.min_w) * 0.10
            bw = clamp(bw + self.rng.gauss(0.0, span_w), self.min_w, self.max_w)
        if self.rng.random() < self.mutation_rate:
            span_h = (self.max_h - self.min_h) * 0.10
            bh = clamp(bh + self.rng.gauss(0.0, span_h), self.min_h, self.max_h)

        # 矩形基因变异
        mutated_genes: List[Gene] = []
        for gene, spec in zip(chromosome.genes, self.rectangles):
            cx, cy, angle, active = gene.cx, gene.cy, gene.angle, gene.active

            if self.rng.random() < self.mutation_rate:
                span_x = bw * 0.10
                span_y = bh * 0.10
                cx = clamp(cx + self.rng.gauss(0.0, span_x), 0.0, bw)
                cy = clamp(cy + self.rng.gauss(0.0, span_y), 0.0, bh)

            if spec.rotatable and (self.rng.random() < self.mutation_rate):
                angle_deg = math.degrees(angle)
                step = self.rng.choice([-20, -10, 10, 20])
                angle_deg += step
                angle_deg = round(angle_deg / 10.0) * 10.0
                angle = math.radians(angle_deg)
                if self.rng.random() < 0.55:
                    axis_deg = round(angle_deg / 90.0) * 90.0
                    angle_deg = axis_deg + self.rng.choice([-10, 0, 10])
                    angle_deg = round(angle_deg / 10.0) * 10.0
                    angle = math.radians(angle_deg)
                angle = wrap_angle(angle)
            elif not spec.rotatable:
                angle = 0.0

            if (not spec.mandatory) and (self.rng.random() < self.mutation_rate * 0.6):
                active = not active

            mutated_genes.append(Gene(cx=cx, cy=cy, angle=angle, active=active))

        return Chromosome(boundary_w=bw, boundary_h=bh, genes=mutated_genes)

    def _repair_feasible_layout(
        self, chromosome: Chromosome
    ) -> Tuple[List[PlacedRect], List[str], List[Point]]:
        polygon = Chromosome.polygon_from_boundary(
            chromosome.boundary_w, chromosome.boundary_h
        )
        decoded, _ = self._decode(chromosome)
        mandatory = [r for r in decoded if r.mandatory]
        optional = [r for r in decoded if not r.mandatory]

        kept: List[PlacedRect] = []
        dropped_mandatory: List[str] = []

        for rect in mandatory:
            if self._is_rect_valid(rect, kept, polygon):
                kept.append(rect)
            else:
                dropped_mandatory.append(rect.id)

        optional_sorted = sorted(
            optional,
            key=lambda r: (r.area - 0.5 * axis_alignment_deviation(r.angle) * r.area),
            reverse=True,
        )
        for rect in optional_sorted:
            if self._is_rect_valid(rect, kept, polygon):
                kept.append(rect)

        return kept, dropped_mandatory, polygon

    def solve(self) -> Dict[str, object]:
        population = self._init_population()
        best: Chromosome = population[0]
        best_fitness = -math.inf
        fitness_history: List[float] = []

        for _ in range(self.generations):
            fitnesses = [self._fitness(ch) for ch in population]
            idx = max(range(len(population)), key=lambda i: fitnesses[i])
            if fitnesses[idx] > best_fitness:
                best_fitness = fitnesses[idx]
                best = Chromosome(
                    boundary_w=population[idx].boundary_w,
                    boundary_h=population[idx].boundary_h,
                    genes=[Gene(g.cx, g.cy, g.angle, g.active) for g in population[idx].genes],
                )
            fitness_history.append(best_fitness)

            ranked = sorted(
                range(len(population)), key=lambda i: fitnesses[i], reverse=True
            )
            next_pop: List[Chromosome] = [
                Chromosome(
                    boundary_w=population[i].boundary_w,
                    boundary_h=population[i].boundary_h,
                    genes=[Gene(g.cx, g.cy, g.angle, g.active) for g in population[i].genes],
                )
                for i in ranked[: self.elite_count]
            ]

            while len(next_pop) < self.population_size:
                p1 = self._tournament_select(population, fitnesses)
                p2 = self._tournament_select(population, fitnesses)
                c1, c2 = self._crossover(p1, p2)
                c1 = self._mutate(c1)
                c2 = self._mutate(c2)
                next_pop.append(c1)
                if len(next_pop) < self.population_size:
                    next_pop.append(c2)

            population = next_pop

        final_layout, dropped_mandatory, final_polygon = self._repair_feasible_layout(best)
        used_area = sum(r.area for r in final_layout)
        poly_area = best.boundary_w * best.boundary_h
        utilization = used_area / poly_area if poly_area > EPS else 0.0

        return {
            "best_fitness": best_fitness,
            "boundary_w": best.boundary_w,
            "boundary_h": best.boundary_h,
            "polygon": final_polygon,
            "polygon_area": poly_area,
            "placed_area": used_area,
            "utilization": utilization,
            "placed_rectangles": final_layout,
            "dropped_mandatory": dropped_mandatory,
            "fitness_history": fitness_history,
        }


# ---------------------------------------------------------------------------
# 可视�? & SVG 导出
# ---------------------------------------------------------------------------
def visualize_layout(
    polygon: Sequence[Point],
    obstacles: Sequence[SquareObstacle],
    placed_rectangles: Sequence[PlacedRect],
    fitness_history: Sequence[float] | None = None,
    save_path: str | None = None,
    show: bool = True,
) -> None:
    try:
        from matplotlib import patches
        import matplotlib.pyplot as plt
    except ImportError:
        target = save_path or "layout_result.svg"
        if not target.lower().endswith(".svg"):
            target = f"{target}.svg"
        save_layout_svg(polygon, obstacles, placed_rectangles, target)
        print("matplotlib is not installed, fallback to SVG export.")
        print(f"figure_saved       : {target}")
        return

    if fitness_history:
        fig, (ax_layout, ax_fit) = plt.subplots(1, 2, figsize=(14, 6))
    else:
        fig, ax_layout = plt.subplots(1, 1, figsize=(8, 6))
        ax_fit = None

    ax_layout.add_patch(
        patches.Polygon(
            polygon, closed=True, fill=True,
            facecolor="#EEF7ED", edgecolor="#2D6A4F", linewidth=2.0,
        )
    )

    for obs in obstacles:
        ax_layout.add_patch(
            patches.Polygon(
                obs.as_polygon(), closed=True,
                facecolor="#6C757D", edgecolor="#212529",
                linewidth=1.5, hatch="//", alpha=0.85,
            )
        )

    cmap = plt.colormaps.get_cmap("tab20")
    for i, rect in enumerate(placed_rectangles):
        pts = rect.corners()
        color = cmap(i % 20)
        ax_layout.add_patch(
            patches.Polygon(
                pts, closed=True,
                facecolor=color, edgecolor="black",
                linewidth=1.2, alpha=0.66,
            )
        )
        angle_deg = math.degrees(rect.angle)
        ax_layout.text(
            rect.cx, rect.cy,
            f"{rect.id}\n{angle_deg:.0f}°",
            ha="center", va="center",
            fontsize=8, color="black", weight="bold",
        )

    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    ax_layout.set_xlim(min(xs) - 2, max(xs) + 2)
    ax_layout.set_ylim(min(ys) - 2, max(ys) + 2)
    ax_layout.set_aspect("equal", adjustable="box")
    ax_layout.set_title("Rectangle Layout �? GA Auto-Boundary (Angles: multiples of 10°)")
    ax_layout.set_xlabel("X")
    ax_layout.set_ylabel("Y")
    ax_layout.grid(True, alpha=0.2)

    if ax_fit is not None and fitness_history:
        ax_fit.plot(
            range(1, len(fitness_history) + 1),
            fitness_history, color="#1D3557", lw=2.0,
        )
        ax_fit.set_title("GA Best Fitness Over Generations")
        ax_fit.set_xlabel("Generation")
        ax_fit.set_ylabel("Best Fitness")
        ax_fit.grid(True, alpha=0.25)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=180, bbox_inches="tight")
        print(f"figure_saved       : {save_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def save_layout_svg(
    polygon: Sequence[Point],
    obstacles: Sequence[SquareObstacle],
    placed_rectangles: Sequence[PlacedRect],
    output_path: str,
) -> None:
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    canvas_w = 1000.0
    canvas_h = 700.0
    margin = 40.0
    dx = max(max_x - min_x, 1e-6)
    dy = max(max_y - min_y, 1e-6)
    scale = min((canvas_w - 2 * margin) / dx, (canvas_h - 2 * margin) / dy)

    def to_svg_point(p: Point) -> Tuple[float, float]:
        sx = margin + (p[0] - min_x) * scale
        sy = canvas_h - (margin + (p[1] - min_y) * scale)
        return sx, sy

    def poly_to_points(poly: Sequence[Point]) -> str:
        return " ".join(
            f"{x:.2f},{y:.2f}" for x, y in (to_svg_point(p) for p in poly)
        )

    colors = [
        "#A8DADC", "#F4A261", "#2A9D8F", "#E76F51", "#8AB17D",
        "#F6BD60", "#90CAF9", "#BDB2FF", "#FFD6A5", "#84A59D",
    ]

    lines: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(canvas_w)}" '
        f'height="{int(canvas_h)}" viewBox="0 0 {int(canvas_w)} {int(canvas_h)}">',
        '<rect width="100%" height="100%" fill="#FAFAFA"/>',
        f'<polygon points="{poly_to_points(polygon)}" '
        f'fill="#EEF7ED" stroke="#2D6A4F" stroke-width="2"/>',
    ]
    for obs in obstacles:
        lines.append(
            f'<polygon points="{poly_to_points(obs.as_polygon())}" '
            f'fill="#6C757D" stroke="#212529" stroke-width="1.5"/>'
        )
    for i, rect in enumerate(placed_rectangles):
        c = colors[i % len(colors)]
        rect_pts = rect.corners()
        lines.append(
            f'<polygon points="{poly_to_points(rect_pts)}" '
            f'fill="{c}" fill-opacity="0.72" stroke="#111" stroke-width="1.2"/>'
        )
        tx, ty = to_svg_point((rect.cx, rect.cy))
        angle_deg = math.degrees(rect.angle)
        lines.append(
            f'<text x="{tx:.2f}" y="{ty:.2f}" font-size="12" '
            f'text-anchor="middle" dominant-baseline="central" '
            f'fill="#111" font-weight="700">{rect.id} {angle_deg:.0f}°</text>'
        )
    lines.append("</svg>")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# demo & CLI
# ---------------------------------------------------------------------------
def demo(
    visualize: bool = True,
    save_path: str | None = None,
    show_plot: bool = True,
    solver_config: AlgorithmConfig | None = None,
) -> None:
    obstacles = [
        #SquareObstacle(x=9.0, y=8.0, size=4.0),
        #SquareObstacle(x=23.0, y=12.0, size=5.0),
        #SquareObstacle(x=30.0, y=20.0, size=3.0),
    ]

    rectangles = [
        RectangleSpec("R1", 8, 2.8, rotatable=True, mandatory=True),
        RectangleSpec("R2", 8, 2.8, rotatable=True, mandatory=True),
        RectangleSpec("R3", 7.4, 2.3, rotatable=True, mandatory=True),
    ]

    solver_config = solver_config or AlgorithmConfig()
    solver = AutoBoundaryGAPacker(
        obstacles=obstacles,
        rectangles=rectangles,
        **solver_config.to_kwargs(),
    )
    result = solver.solve()

    print("=== GA Auto-Boundary Rectangle Layout Result ===")
    print(f"best_fitness        : {result['best_fitness']:.3f}")
    print(f"boundary (W × H)    : {result['boundary_w']:.2f} × {result['boundary_h']:.2f}")
    print(f"boundary_area       : {result['polygon_area']:.3f}")
    print(f"placed_area         : {result['placed_area']:.3f}")
    print(f"utilization         : {result['utilization'] * 100:.2f}%")
    if result["dropped_mandatory"]:
        print(f"dropped_mandatory   : {result['dropped_mandatory']}")

    print("placed_rectangles:")
    for r in result["placed_rectangles"]:
        print(
            f"  {r.id}: cx={r.cx:.2f}, cy={r.cy:.2f}, "
            f"w={r.width:.2f}, h={r.height:.2f}, angle_deg={math.degrees(r.angle):.1f}"
        )

    if visualize:
        visualize_layout(
            polygon=result["polygon"],
            obstacles=obstacles,
            placed_rectangles=result["placed_rectangles"],
            fitness_history=result.get("fitness_history"),
            save_path=save_path,
            show=show_plot,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GA rectangle layout with auto-generated rectangular boundary."
    )
    parser.add_argument("--no-vis", action="store_true", help="Disable plotting.")
    parser.add_argument("--save-fig", type=str, default=None, help="Save figure to path.")
    parser.add_argument("--config", type=str, default=None,
                        help="JSON config file for GA algorithm parameters.")
    parser.add_argument("--no-show", action="store_true", help="Do not open plot window.")
    args = parser.parse_args()

    solver_config = AlgorithmConfig.from_json(args.config) if args.config else AlgorithmConfig()

    demo(
        visualize=not args.no_vis,
        save_path=args.save_fig,
        show_plot=not args.no_show,
        solver_config=solver_config,
    )
