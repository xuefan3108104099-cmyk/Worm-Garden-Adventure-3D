# 任务对照与讲解 · Task Guide (English + 中文 + 拼音)

> 课程：GEIAL31L-B2a Computer Graphics Programming
> 作业：Worm's Garden Adventure 3D
> 作者：Xuefan Zhang (P51W1R)
> 本文档把评分表的每一条要求，对应到「代码位置 / 截图 / 英文说明 / 中文＋拼音讲解」。

---

## 0. 一句话总览 / One-paragraph summary

**English.** The 2D Pygame game was kept, and its *presentation layer* was replaced
by a software 3D renderer written with NumPy only: matrices, projection, clipping,
z-buffer rasterisation, texturing, lighting and fog are all hand-written.
Pygame keeps the window, input and HUD; Pillow only makes textures and PNGs.

**中文.** 保留了原来的 2D 游戏逻辑，只把「显示层」换成自己写的 NumPy 3D 软件渲染器：
矩阵变换、投影、裁剪、z-buffer 光栅化、贴图、光照、雾，全部自己算。
Pygame 只负责窗口、按键和 HUD 文字；Pillow 只负责生成贴图和存 PNG。

**拼音要点 / Pinyin key terms**

| 英文 | 拼音 | 中文 |
|------|------|------|
| renderer | rǎn dē rě rùi / 渲染器 xiǎn rǎn qì | 渲染器 |
| rasterisation | lā sī tè ruì zéi shén / 光栅化 guāng shān huà | 光栅化 |
| z-buffer | zēi bā fěi / 深度缓冲 shēn dù huǎn chōng | 深度缓冲 |
| barycentric | bā rùi sēn tè rí kè / 重心坐标 zhòng xīn zuò biāo | 重心坐标 |
| perspective | pè sī pèi kè tì fū / 透视 tòu shì | 透视投影 |
| orthographic | ò sī ruò gé rā fěi kè / 正交 zhèng jiāo | 正交投影 |
| frustum culling | fǔ lā sī tè mǔ kā lìng / 视锥剔除 shì zhuī tī chú | 视锥剔除 |
| bilinear | bāi lì nǐ è / 双线性 shuāng xiàn xìng | 双线性过滤 |
| fog | fā gé / 雾 wù | 距离雾 |

---

## 1. Part A ① 世界与数据转换 / World & data conversion（10 分）

**Code:** `maze.py`（`cell_center_3d`, `collect_wall_runs`, `runs_to_boxes`,
`circle_hits_xz`）、`config.py`（全部尺寸常量）、`game.py`（`build_level`）
**Screenshot:** `screenshots/fig01_perspective.png`, `fig02_orthographic.png`

**English.** The maze generator is reused unchanged (same DFS backtracker, same
start cell = column 0 middle row, same finish cell = last column middle row).
A cell `(col,row)` now has a centre at `(col+0.5, 0, row+0.5)` world units;
1 cell = 1 unit. Wall flags are merged into *wall runs* and each run becomes a box
mesh **and** an axis-aligned collider `(x0,x1,z0,z1)`, so drawing and physics agree.

**中文.** 迷宫生成器原封不动复用（同样的深度优先回溯、同样的起点格和终点格）。
每个格子在世界坐标里的中心是 `(col+0.5, 0, row+0.5)`，1 格 = 1 个世界单位。
墙的标记先合并成「墙段」，每段同时生成一个盒子模型和一矩形的碰撞盒，保证「看到的墙」和「撞到的墙」一致。

*Pinyin:* mílù (迷宫 maze)、zuòbiāo (坐标 coordinate)、pèngzhuàng hé (碰撞盒 collider).

---

## 2. Part A ② 几何与 4×4 变换 / Geometry & transforms（12 分）

**Code:** `mesh.py`（`box` / `sphere` / `quad` / `tiled_floor` / `merge_meshes` /
`transform_mesh` / `translated`）、`math3d.py`（`translation` / `rotation_x|y|z` /
`scale` / `@` 乘法）、`first_cube.py`
**Screenshot:** `first_cube.png`（里程碑立方体）, `fig10_gameplay.png`

**English.** Every model is a triangle soup: positions, normals, UVs. The model
matrix is `T @ Ry @ Rx @ S` (column vectors, so the rightmost matrix applies first),
and `first_cube.py` prints the resulting 4×4 matrices so the numbers can be checked
by hand. A unit test asserts that `+90°` about `+Y` maps `+X` to `−Z`.

**中文.** 所有模型都是三角面片（顶点、法线、UV）。模型矩阵写成 `T @ Ry @ Rx @ S`，
因为是列向量左乘，最右边的矩阵最先作用。`first_cube.py` 会把两个 4×4 矩阵打印出来，
可以手算核对。单元测试断言：绕 +Y 转 +90° 会把 +X 变到 −Z（右手坐标系）。

*Pinyin:* jǔzhèn (矩阵 matrix)、xuánzhuǎn (旋转 rotation)、píngyí (平移 translation)、suōfàng (缩放 scale).

---

## 3. Part A ③ 相机与两种投影 / Camera & both projections（12 分）

**Code:** `camera.py`（三个预设 1/2/3、Q/E 轨道、滚轮缩放、`fit_distance` 二分）、
`math3d.py`（`camera_basis` / `world_to_camera` / `project_perspective` /
`project_orthographic`）
**Screenshot:** `fig01` vs `fig02`（同机位 透视/正交 对比）

**English.** The basis is built as `right = cross(forward, up)`, `up = cross(right,
forward)`; the first version used `cross(up, forward)` and the whole image came out
**mirrored**, so a regression test now pins the correct handedness.
Perspective: `f = (h/2)/tan(fov/2)`, `sx = w/2 + f·x/z`, `sy = h/2 − f·y/z`.
Orthographic keeps the direction but replaces the divide with a constant scale, so
parallel edges stay parallel. `P` switches live.

**中文.** 相机基向量换成 `right = cross(forward, up)`；早期版本写成 `cross(up, forward)`，
结果整幅画面**左右镜像**，现在用单元测试锁死正确的右手关系。
透视投影：焦距由视场角算出，然后除以 z；正交投影不除 z，用固定比例，所以平行线保持平行。
按 `P` 可以随时切换。

*Pinyin:* xiàngjī jī (相机基 camera basis)、jìngxiàng (镜像 mirror)、zhèngjiāo (正交 orthographic)、tòushì (透视 perspective).

---

## 4. Part A ④ 可见性与光栅化 / Visibility & rasterisation（12 分）

**Code:** `raster.py`（`draw_mesh` 背面剔除 → `clip_triangle_near` 近平面裁剪 →
`_emit` 投影 → `_raster` 重心坐标 + z-buffer）、`frustum.py`（六平面 AABB 剔除）、
`tests/test_math3d.py`
**Screenshot:** `fig03_wireframe.png`（F1 线框）, `fig05_depth.png`（F3 深度）

**English.** Back-face culling uses `dot(n, eye−centroid) > 0`. A triangle crossing
the near plane is split by Sutherland–Hodgman into a fan (3→4 vertices→2 triangles),
so no vertex ever has `z ≤ 0` at the divide. Inside-test: compute three barycentric
weights for the whole bounding box at once, keep pixels where all three are ≥ 0.
Depth is interpolated linearly in screen space (equal to 1/z), and the nearest wins.

**中文.** 背面剔除用「法线 · (眼睛−重心) > 0」。跨过近平面的三角形用 Sutherland–Hodgman
切多边形，3 个顶点变 4 个顶点再拆成 2 个三角形，保证除法时 z 永远 > 0。
覆盖测试一次算出整个包围盒的三个重心坐标，三个都 ≥ 0 的像素才算在三角形内。
深度按屏幕空间线性插值（等价于 1/z），小的赢（近的遮挡远的）。

*Pinyin:* bèimiàn tīchú (背面剔除 back-face culling)、jìn píngmiàn (近平面 near plane)、shēndù huǎnchōng (深度缓冲 z-buffer)、zhòngxīn zuòbiāo (重心坐标 barycentric).

---

## 5. Part A ⑤ 光照与贴图 / Lighting & texture mapping（10 分）

**Code:** `textures.py`（9 张 Pillow 程序化贴图 + `sample_nearest` / `sample_bilinear`）、
`raster.py`（逐三角形 flat shading、透视校正 UV）
**Screenshot:** `fig12_textures.png`（贴图拼图）, `fig04_normals.png`（F2 法线）

**English.** `I = 0.34 + 0.66·max(0, n·L)`, `L = normalize(0.42, 0.86, 0.28)`.
Ambient 0.34 guarantees no face is pure black. UVs are interpolated *after* dividing
by depth and *before* multiplying back (perspective-correct interpolation), which is
why the floor tiles do not swim.

**中文.** 亮度 = 环境光 0.34 + 漫反射 0.66 × max(0, 法线·光方向)。环境光保证没有纯黑面。
UV 先除以深度插值、再乘回深度，这是透视校正，所以地面格子不会「游动/扭曲」。

*Pinyin:* guāngzhào (光照 lighting)、mànfǎnshè (漫反射 diffuse)、huánjìngguāng (环境光 ambient)、tòushì jiàozhèng (透视校正 perspective-correct).

---

## 6. Part A ⑥ 3D 玩法与动画 / 3D gameplay & animation（10 分）

**Code:** `game.py`（分轴滑动碰撞、跳跃欧拉积分、水/鸟/苹果/终点判定、关卡升级）、
`particles.py`、`scene.py`
**Screenshot:** `fig13_bird.png`（鸟 + 水坑 + 蠕虫）, `fig11_hud.png`（整窗 HUD）

**English.** Collision is resolved per axis (try X, then Z) so the worm slides along
walls instead of sticking. Jump: `y` integrated with gravity 10 and initial speed 3.2.
Water kills, a bird bump sends you back to the start, 4 apples open the flag, and
each level rebuilds a new maze with one more bird.

**中文.** 碰撞分轴处理（先试 X 再试 Z），撞墙时会贴着墙滑而不是卡死。
跳跃只对 y 做积分（重力 10、初速 3.2）。踩到水坑就重来；被鸟撞到回起点；
集齐 4 个苹果才能通关；每过一关重新生成迷宫并多一只鸟。

*Pinyin:* pèngzhuàng (碰撞 collision)、fēnzhóu (分轴 per-axis)、tiàoyuè (跳跃 jump)、guòguān (过关 level up).

---

## 7. Part A ⑦ 测试、代码与文档 / Tests, code & documentation（4 分）

**Code:** `tests/test_math3d.py`（19 个 unittest）、`tools/perf_bench.py`、
`README.md`、`report/Worm_Garden_3D_Report.pdf`（8 页英文报告）

**English.** `python -m unittest discover -s tests` → 19 tests OK. The report is 8
pages with equations, figures, a performance table and the limitations.

**中文.** 19 个单元测试全部通过；报告 8 页，含公式、图、性能表和局限性讨论。

*Pinyin:* dānyuán cèshì (单元测试 unit test)、xìngnéng (性能 performance)、bàogào (报告 report).

---

## 8. Part B ① 图形扩展：距离雾 / Graphics extension: distance fog（15 分）

**Code:** `scene.py`（`fog_start/end` 由相机距离推导）、`raster.py`（逐像素混合）、`G` 键
**Screenshot:** `fig06_fog_off.png` ↔ `fig07_fog_on.png`（同机位 before/after）

**English.** `f = clamp((depth−start)/(end−start), 0, 1)`, colour mixed towards
`FOG_COLOR`. `start = 0.28 d`, `end = 1.7 d` so the strength is zoom-independent.
Two benefits: it hides the hard edge of a finite maze and it is a depth cue.

**中文.** 每个像素按深度线性混合到雾色。起点终点都跟相机距离成比例，所以缩放时强度不变。
好处有两个：遮住有限迷宫的硬边，以及提供“远近”的深度线索。

*Pinyin:* wù (fog)、shēndù xiànsuǒ (深度线索 depth cue).

---

## 9. Part B ② 第二扩展：双线性过滤 / Second feature: bilinear filtering（10 分）

**Code:** `textures.sample_bilinear`、`raster._raster`、`T` 键
**Screenshot:** `fig08_nearest.png` ↔ `fig09_bilinear.png`（同场景 before/after）

**English.** Four taps weighted by the fractional texel coordinates (three lerps),
evaluated for the whole triangle at once. Nearest sampling at a grazing angle turns
the floor into a shimmering staircase; bilinear removes the stepping.

**中文.** 取最近的 4 个纹素，按小数部分加权（3 次插值），整块三角形一次算完。
最近邻采样在掠射角下会让地面「闪烁 + 阶梯状」，双线性把阶梯抹平。

*Pinyin:* shuāngxiànxìng (双线性 bilinear)、wùsù (纹素 texel)、lüèshè jiǎo (掠射角 grazing angle).

---

## 10. Part B ③ 附加：视锥剔除 + 分辨率档位 + 粒子 / Extras

**Code:** `frustum.py`、`game.py`（4×4 格分块）、`config.RESOLUTION_PRESETS`、`particles.py`

**English.** 24 wall chunks, each AABB-tested against 6 planes → typically 8 of 24 are
drawn in the follow view (two thirds of the geometry never reaches the rasteriser).
`F5` cycles 480×300 → 1280×800 with letterboxed up-scaling. Particles sparkle on
pickup and explode at the flag.

**中文.** 迷宫墙切成 24 块，每块用包围盒对 6 个平面做剔除，跟随视角下通常只画 8 块
（三分之二的几何根本不会进入光栅化）。按 `F5` 在 4 档分辨率之间切换并等比放大。
粒子在吃苹果时闪光、通关时放烟花。

*Pinyin:* shìzhuī tīchú (视锥剔除 frustum culling)、bāowéihé (包围盒 AABB)、lìzǐ (粒子 particle).

---

## 11. 性能结论（报告第 7 节）/ Performance conclusion

| 分辨率 | 相机 | 毫秒/帧 | FPS |
|---|---|---|---|
| 480×300 (FAST) | elevated | 141 | 7.1 |
| 480×300 (FAST) | follow | 163 | 6.2 |
| 640×400 | elevated | 205 | 4.9 |
| 896×560 | elevated | 244 | 4.1 |
| 1280×800 | follow | 819 | 1.2 |

**English.** The cost is dominated by ~40 NumPy calls **per triangle** (fixed Python
overhead), not by fill rate — which is why the follow camera (300 triangles) is often
slower than the elevated one (1100). Default preset is FAST on purpose.

**中文.** 瓶颈是「每个三角形大约 40 次 NumPy 调用」的固定开销，不是填充率；
所以只画 300 个三角形的跟随视角反而可能比重画 1100 个的俯视更慢。
默认用 FAST 档是故意的，并如实写在报告里。

*Pinyin:* píngjǐng (瓶颈 bottleneck)、kāixiāo (开销 overhead)、fēngěng (帧率 frame rate).

---

## 12. 交付清单 / Deliverables checklist

| 手册要求 | 文件 |
|---|---|
| 全部源码 | 根目录 `*.py`（13 个模块） |
| README（安装/运行/按键/版本） | `README.md` |
| 6–10 页技术报告 | `report/Worm_Garden_3D_Report.pdf`（8 页） |
| 2–4 分钟录屏 | `screenshots/demo.mp4` |
| 截图文件夹 | `screenshots/`（fig01–fig13 + first_cube + HUD） |
| 测试文件夹 | `tests/test_math3d.py`（19 个测试） |
| 外部代码/素材声明 | `README.md` 第 8 节：无第三方 3D 库，贴图全部自己生成 |
