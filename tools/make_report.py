"""
tools/make_report.py
====================
Builds report/Worm_Garden_3D_Report.pdf (8 pages, English) with reportlab.

All figures come from screenshots/ ; the texture contact sheet is assembled
here from assets/.
Run:  python tools\\make_report.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Frame, Image as RLImage,
                                PageTemplate, Paragraph, Spacer, Table,
                                TableStyle, KeepTogether, PageBreak)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "screenshots")
ASSETS = os.path.join(ROOT, "assets")
OUT_DIR = os.path.join(ROOT, "report")
os.makedirs(OUT_DIR, exist_ok=True)

TITLE = "Worm's Garden Adventure 3D"
SUB = ("From a 2D maze game to a hand-written 3D software rasteriser<br/>"
       "GEIAL31L-B2a - Computer Graphics course project")


# --------------------------------------------------------------------- tex ---
def texture_sheet(path=None):
    """Contact sheet of the nine procedural textures."""
    names = ["grass", "stone", "water", "checker", "apple",
             "gold", "worm", "feather", "wood"]
    cell, pad = 128, 18
    cols = 3
    rows = (len(names) + cols - 1) // cols
    W = cols * (cell + pad) + pad
    H = rows * (cell + pad + 16) + pad
    sheet = Image.new("RGB", (W, H), (248, 248, 246))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(names):
        img = Image.open(os.path.join(ASSETS, n + ".png")).convert("RGB")
        img = img.resize((cell, cell), Image.NEAREST)
        x = pad + (i % cols) * (cell + pad)
        y = pad + (i // cols) * (cell + pad + 16)
        sheet.paste(img, (x, y))
        d.rectangle([x - 1, y - 1, x + cell, y + cell], outline=(180, 180, 180))
        d.text((x + 2, y + cell + 3), n, fill=(40, 40, 40))
    out = path or os.path.join(SHOTS, "fig12_textures.png")
    sheet.save(out)
    return out


# --------------------------------------------------------------------- pdf ---
def build():
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica",
                          fontSize=9.6, leading=13.2, alignment=TA_JUSTIFY,
                          spaceAfter=5)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                        fontSize=14, leading=17, spaceBefore=10, spaceAfter=5,
                        textColor=colors.HexColor("#1f3b52"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                        fontSize=10.8, leading=13, spaceBefore=7, spaceAfter=3,
                        textColor=colors.HexColor("#2b5d7d"))
    small = ParagraphStyle("small", parent=body, fontSize=8.2, leading=10.4,
                           textColor=colors.HexColor("#444444"), alignment=TA_CENTER,
                           spaceBefore=2, spaceAfter=8)
    code = ParagraphStyle("code", parent=body, fontName="Courier", fontSize=8.0,
                          leading=10.5, backColor=colors.HexColor("#f2f2f2"),
                          borderPadding=4, spaceBefore=2, spaceAfter=6,
                          alignment=TA_JUSTIFY)

    def P(t, s=body):
        return Paragraph(t, s)

    def _path(name):
        if os.path.isabs(name):
            return name
        for base in (SHOTS, ROOT):
            p = os.path.join(base, name)
            if os.path.exists(p):
                return p
        raise FileNotFoundError(name)

    def IMG(name, width_cm=15.5, caption=""):
        path = _path(name)
        img = Image.open(path)
        w, h = img.size
        W = width_cm * cm
        return [RLImage(path, width=W, height=W * h / w),
                P(caption, small) if caption else Spacer(0, 0)]

    def IMG2(name_a, name_b, caption, width_cm=7.6):
        """Two figures side by side (each width_cm wide)."""
        cells = []
        for name in (name_a, name_b):
            path = _path(name)
            img = Image.open(path)
            w, h = img.size
            W = width_cm * cm
            cells.append(RLImage(path, width=W, height=W * h / w))
        table = Table([cells], colWidths=[width_cm * cm + 4, width_cm * cm + 4])
        table.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                   ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return [table, P(caption, small)]

    story = []

    # ---------------------------------------------------------- title page ---
    story.append(Spacer(0, 1.6 * cm))
    story.append(Paragraph(TITLE, ParagraphStyle(
        "t", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24,
        leading=28, textColor=colors.HexColor("#1f3b52"))))
    story.append(Spacer(0, 0.15 * cm))
    story.append(Paragraph(SUB, ParagraphStyle(
        "s", parent=body, fontSize=11, leading=15, alignment=TA_CENTER,
        textColor=colors.HexColor("#556677"))))
    story.append(Spacer(0, 0.9 * cm))
    story.append(Paragraph(
        "<b>Xuefan Zhang (P51W1R)</b><br/>University of Miskolc<br/>"
        "19 November 2026", ParagraphStyle(
            "a", parent=body, alignment=TA_CENTER, fontSize=10, leading=15)))
    story.append(Spacer(0, 0.6 * cm))

    story.append(P(
        "<b>Abstract.</b> This report describes the conversion of a small 2D maze game "
        "(<i>Worm's Garden Adventure</i>, delivered as a single Pygame script) into a "
        "3D game drawn by a renderer written from scratch with NumPy. No 3D library "
        "is used: every vertex is transformed by hand-built 4x4 matrices, clipped "
        "against the near plane, projected, rasterised with barycentric coordinates "
        "into a float z-buffer, textured with perspective-correct UV interpolation "
        "and shaded with a single directional light. Pygame keeps its original role "
        "of window, input and text, and Pillow only generates the texture bitmaps. "
        "The report explains the mathematics, walks through the pipeline stage by "
        "stage, documents four Part B extensions (distance fog, bilinear filtering, "
        "frustum-culled wall chunks and switchable render resolutions) and reports "
        "honest frame-time measurements together with an explanation of why the "
        "renderer is limited to roughly 7 frames per second at 480x300."))

    story.append(Spacer(0, 0.5 * cm))

    checklist = [
        ["Part A requirement", "Where it is implemented"],
        ["Vector maths, 4x4 matrices", "math3d.py (about 20 functions, 19 unit tests)"],
        ["View matrix & world->camera", "math3d.camera_basis / world_to_camera"],
        ["Perspective + orthographic projection", "math3d.project_* / camera.py (key P)"],
        ["Triangle rasteriser, z-buffer", "raster.Renderer._raster"],
        ["Back-face culling, near-plane clip", "raster.draw_mesh / clip_triangle_near"],
        ["Lighting, texture mapping", "raster._raster, textures.py"],
        ["3D models, game logic, HUD", "mesh.py, game.py, scene.py, hud.py"],
        ["Part B: fog, bilinear, culling, resolutions",
         "scene.py (G), raster.py (T), frustum.py, config.py (F5)"],
    ]
    t = Table(checklist, colWidths=[6.6 * cm, 9.3 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.6),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe8ef")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9fb4c4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ------------------------------------------------------------ section 1 ---
    story.append(P("1. Introduction and goal", h1))
    story.append(P(
        "The starting point was a complete 2D game: a depth-first maze, a worm "
        "controlled with W/A/S/D, water holes, patrolling birds, four apples and a "
        "finish flag, all drawn with Pygame rectangles and circles into a "
        "1280x800 window at 50 pixels per cell. The task was not to write a new "
        "game but to keep that game and replace its <i>presentation layer</i> with "
        "a 3D one. The handbook is explicit: Pygame may keep the window, the input "
        "handling and the HUD, but every 3D pixel must be produced by our own "
        "maths. PyOpenGL, moderngl, Panda3D, Ursina, PyBullet and every other 3D "
        "engine are forbidden."))
    story.append(P(
        "The conversion therefore touched three layers only:"))
    story.append(Table([
        ["Layer", "2D version", "3D version"],
        ["World model", "integer cell (col, row)",
         "floating point world position (x, y, z), 1 cell = 1 world unit"],
        ["Walls", "pygame.draw.rect per cell edge",
         "box meshes merged into wall runs, then into 4x4-cell chunks"],
        ["Drawing", "draw.circle / draw.rect on a Surface",
         "transform -> cull -> clip -> project -> rasterise -> shade"],
        ["Camera", "implicit, top-down, fixed",
         "explicit eye + basis, orbit, zoom, three presets, two projections"],
    ], colWidths=[2.6 * cm, 5.4 * cm, 8.3 * cm], style=TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.4),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe8ef")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9fb4c4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])))
    story.append(Spacer(0, 0.3 * cm))
    story.append(P(
        "The game rules were kept bit-for-bit where possible: the same DFS backtracker "
        "with the same neighbour rules, the same start cell (column 0, middle row) and "
        "finish cell (last column, middle row), the same apple scoring (3 x 50 for the "
        "silver apples and 100 for the golden one), the same enemy count "
        "(<font face='Courier'>min(2 + level, 8)</font>) and the same rule that the flag "
        "only opens after four apples. What changed is that a cell now has a centre in "
        "world space, walls have thickness 0.16 and height 0.75, the worm is a sphere "
        "of radius 0.22 and every distance that was measured in pixels is now measured "
        "in world units (0.34 units instead of 17 pixels for the flag trigger, for "
        "example)."))

    story.append(P("2. From 2D coordinates to a 3D world", h1))
    story.append(P(
        "The world uses a right-handed coordinate system with <b>X = east</b> (the "
        "column axis), <b>Y = up</b> and <b>Z = south</b> (the row axis). A cell "
        "<font face='Courier'>(col, row)</font> therefore has its centre at "
        "<font face='Courier'>(col + 0.5, h, row + 0.5)</font>, and the four movement "
        "directions map to the vectors W = (0,0,-1), S = (0,0,+1), A = (-1,0,0) and "
        "D = (+1,0,0). Keeping the mapping this literal meant that the maze generator, "
        "the neighbour search and the enemy path-finding could be copied from the 2D "
        "script without changing a single rule."))
    story.append(P(
        "Walls needed more care. In 2D a wall is a one-pixel line; in 3D it is a solid "
        "box that the worm can collide with. The generator stores wall flags per cell "
        "edge, so adjacent flags are merged into <i>wall runs</i> first (a corridor "
        "wall becomes one long box instead of eight short ones), and each run becomes "
        "both a mesh and an axis-aligned collider "
        "<font face='Courier'>(x0, x1, z0, z1)</font>. Collision is a circle-versus-box "
        "test in the X/Z plane: the closest point of the box to the worm centre is "
        "computed and compared with the squared radius. Jumping is a one-dimensional "
        "Euler integration on Y only (gravity 10 u/s², initial speed 3.2 u/s), which is "
        "enough to hop over a 0.16-thick wall run."))

    # ------------------------------------------------------------ section 3 ---
    story.append(P("3. The mathematics", h1))
    story.append(P(
        "All of the maths lives in <font face='Courier'>math3d.py</font> and is written "
        "with NumPy arrays of shape (3,) and (4,4). Column vectors are used, so a "
        "matrix multiplies on the left of a point and composition reads right to left: "
        "in <font face='Courier'>T @ Ry @ S</font> the point is scaled first, then "
        "rotated, then translated.", body))

    story.append(P("3.1 Camera basis and the view matrix", h2))
    story.append(P(
        "A camera is fully described by an eye point and an orthonormal basis "
        "(right, up, forward). The basis is built from the direction "
        "<font face='Courier'>forward = normalize(target - eye)</font>. One subtlety "
        "caused a mirrored image in an early build: the first version computed "
        "<font face='Courier'>right = cross(up, forward)</font>, which flips the "
        "horizontal axis. The correct right-handed construction for a camera that looks "
        "down +Z with +Y up is <font face='Courier'>right = cross(forward, up)</font> "
        "and <font face='Courier'>up = cross(right, forward)</font>, because then "
        "<font face='Courier'>right</font> equals world +X when the camera looks towards "
        "-Z. A unit test asserts exactly this, so the mirror bug cannot come back.", body))
    story.append(P(
        "World-to-camera is then a change of basis followed by a translation: "
        "<font face='Courier'>p_cam = (dot(right, p - eye), dot(up, p - eye), "
        "dot(forward, p - eye))</font>. Written as a 4x4 matrix this is the usual view "
        "matrix with the three basis vectors as rows and "
        "<font face='Courier'>-R^T t</font> in the last column; "
        "<font face='Courier'>first_cube.py</font> prints both matrices so the "
        "construction can be checked by hand.", body))
    story.append(KeepTogether(IMG("first_cube.png", 8.4,
        "Figure 1 - Milestone demo: a chessboard-textured cube, transformed by the "
        "hand-built model matrix T @ Ry @ Rx @ S, floating above a tiled floor.")))

    story.append(P("3.2 Perspective and orthographic projection", h2))
    story.append(P(
        "Perspective projection uses a focal length in pixels derived from the "
        "vertical field of view: <font face='Courier'>f = (height / 2) / "
        "tan(fov_y / 2)</font>, which gives 285.6 px for a 400-pixel-tall image at "
        "70 degrees - and exactly 200 px at 90 degrees, which is the value one of the "
        "unit tests pins down. A point in camera space projects to "
        "<font face='Courier'>sx = w/2 + f * x / z</font>, "
        "<font face='Courier'>sy = h/2 - f * y / z</font>; points with z <= 0 are "
        "behind the camera and are rejected. Because the division is by z, five "
        "roughly parallel lines converge to one vanishing point, which is what makes "
        "corridors look deep.", body))
    story.append(P(
        "The orthographic mode keeps the same camera position and orientation but "
        "replaces the division by a fixed scale "
        "<font face='Courier'>f / z_target</font>, so parallel edges stay parallel "
        "and the walls keep their true proportions. Pressing P switches between the "
        "two modes live; figures 2 and 3 show the same camera in both. Orthographic "
        "is useful to check the maze geometry, perspective is better for playing.", body))
    story.append(KeepTogether(IMG2("fig01_perspective.png", "fig02_orthographic.png",
        "Figures 2 and 3 - the identical elevated camera with perspective (left) and "
        "orthographic (right) projection. Perspective converges the corridors, the "
        "orthographic view keeps cell size uniform and is the better geometry check.")))
    story.append(Spacer(0, 0.3 * cm))

    # ------------------------------------------------------------ section 4 ---
    story.append(P("4. The rendering pipeline", h1))
    story.append(P(
        "One frame goes through six stages. Except for the innermost per-pixel loop "
        "the stages are vectorised over whole triangles with NumPy, which is what "
        "keeps a pure-Python renderer usable at all.", body))
    story.append(Table([
        ["Stage", "What happens", "Key code"],
        ["1 Transform", "model -> world (4x4), then world -> camera (basis)", "draw_mesh"],
        ["2 Cull", "back-face test on dot(normal, eye - centroid); frustum AABB test per chunk", "draw_mesh, frustum.py"],
        ["3 Clip", "Sutherland-Hodgman against the near plane, result is a fan", "clip_triangle_near"],
        ["4 Project", "perspective divide, screen-space bounding box", "_emit"],
        ["5 Rasterise", "barycentric inside test, z-buffer per pixel, perspective-correct UV", "_raster"],
        ["6 Shade", "texture sample, ambient + diffuse, linear fog, write colour", "_raster"],
    ], colWidths=[2.5 * cm, 10.0 * cm, 3.8 * cm], style=TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.2),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe8ef")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9fb4c4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])))
    story.append(Spacer(0, 0.25 * cm))
    story.append(P(
        "<b>Culling.</b> Back-face culling removes roughly half of the twelve triangles "
        "of a box. Because a wall seen from a shallow angle shows both its top face and "
        "one side, it halves the triangle count without visual loss. The chunk cull is "
        "coarser but more valuable: the maze is cut into 24 chunk meshes of 4x4 cells, "
        "each with an axis-aligned bounding box, and a chunk is skipped when its AABB is "
        "outside any of the six frustum planes. The AABB test uses the plane normal and "
        "the box's <i>max</i> support point; an early version used the min point and "
        "wrongly culled every box that straddled a plane, which is why a whole wall run "
        "disappeared for several debugging sessions.", body))
    story.append(P(
        "<b>Rasterisation.</b> For each triangle the screen-space bounding box is "
        "clipped to the framebuffer, a mesh-grid of pixel centres is built with "
        "<font face='Courier'>np.meshgrid</font>, and the barycentric weights "
        "(w0, w1, w2) are evaluated for every pixel at once. A pixel is inside when "
        "all three weights are non-negative. Depth is interpolated linearly in screen "
        "space (equivalent to 1/z in camera space), which is what the z-buffer compares. "
        "The texture coordinates are interpolated <i>after</i> dividing by depth and "
        "<i>before</i> dividing back, which is the cheap standard fix for affine UV "
        "distortion on large floor triangles.", body))
    story.append(P(
        "<b>Why the image looks the way it does.</b> Flat shading (one normal per "
        "triangle) is a deliberate choice: it keeps the rasteriser to one lighting "
        "evaluation per triangle and gives the low-poly garden its slightly papery look. "
        "A near plane of 0.1 units keeps the interpolated UVs finite when a wall passes "
        "the camera.", body))
    story.append(KeepTogether(IMG2("fig03_wireframe.png", "fig05_depth.png",
        "Figures 4 and 5 - debug views of the follow camera. Left: F1 wireframe, every "
        "rasterised triangle edge drawn over the shaded frame (300 triangles). Right: "
        "F3 depth buffer, near = bright; the sky is left at infinity.")))
    story.append(KeepTogether(IMG("fig04_normals.png", 8.2,
        "Figure 6 - F2 normal visualisation. Faces aiming up light the green channel, "
        "faces aiming east the red one and faces aiming south the blue one, which makes "
        "a wrongly wound triangle immediately visible.")))

    # ------------------------------------------------------------ section 5 ---
    story.append(PageBreak())
    story.append(P("5. Textures and lighting", h1))
    story.append(P(
        "Nine textures are generated procedurally with Pillow at start-up and written "
        "to <font face='Courier'>assets/</font> so that the report and the game share "
        "the same bitmaps: grass (noise + speckles), stone bricks (offset courses with "
        "highlight and shadow lines), water (concentric ripples), a chessboard, two "
        "apple skins (red and gold), a segmented worm skin, feather and wood. Each is "
        "128x128 RGB and is sampled by nearest neighbour by default, bilinearly when "
        "the user presses T.", body))
    story.append(KeepTogether(IMG(texture_sheet(), 9.6,
        "Figure 7 - The nine procedural textures. Stone was brightened after a first "
        "play-test: with only ambient light on a south-facing wall the original bitmap "
        "turned almost black.")))
    story.append(P(
        "Lighting is a single directional term: "
        "<font face='Courier'>I = 0.34 + 0.66 * max(0, dot(n, L))</font> with the "
        "normalised light direction L = (0.42, 0.86, 0.28) pointing from the surface "
        "towards the light. The 0.34 ambient floor guarantees that no face is pure "
        "black, which matters because the whole garden is lit by one lamp. The colour "
        "written to the framebuffer is "
        "<font face='Courier'>texture(u, v) * tint * I</font>, and fog is blended on "
        "top of that. F2 replaces the colour with the normal encoded as RGB, which is "
        "the quickest way to see whether a triangle is facing the wrong way.", body))

    # ------------------------------------------------------------ section 6 ---
    story.append(P("6. Part B extensions", h1))
    story.append(P(
        "Four extensions were implemented; three are graphical and one is practical.", body))
    story.append(P("6.1 Distance fog (key G)", h2))
    story.append(P(
        "Each pixel blends towards the fog colour with "
        "<font face='Courier'>f = clamp((depth - start) / (end - start), 0, 1)</font>. "
        "Rather than fixing the distances in world units, both are derived from the "
        "current camera distance (<font face='Courier'>start = 0.28 d</font>, "
        "<font face='Courier'>end = 1.7 d</font>), so the effect keeps the same "
        "relative strength when the player zooms. Fog serves two purposes: it hides the "
        "hard outer edge of a finite maze, and it is a depth cue that helps reading "
        "which corridor is nearer. It can be toggled at any time, which makes the "
        "comparison in figures 8 and 9 honest.", body))
    story.append(KeepTogether(IMG2("fig06_fog_off.png", "fig07_fog_on.png",
        "Figures 8 and 9 - the same frame with distance fog disabled (left) and enabled "
        "(right). The toggle is the G key, so the only difference between the two images "
        "is the fog blend in the pixel shader.")))

    story.append(P("6.2 Bilinear texture filtering (key T)", h2))
    story.append(P(
        "Nearest-neighbour sampling makes a floor shrink into a shimmering mess at a "
        "grazing angle, because one texel can cover dozens of pixels. Bilinear sampling "
        "takes the four texels around the sample point and weights them by the "
        "fractional part of the coordinates. In the renderer this is four NumPy gathers "
        "plus three lerps, evaluated for the whole triangle at once, so the cost is a "
        "few percent of a frame. Figure 10 and 11 show the same grazing-angle slab of "
        "stone, first with nearest and then with bilinear sampling.", body))
    story.append(KeepTogether(IMG2("fig08_nearest.png", "fig09_bilinear.png",
        "Figures 10 and 11 - the same grazing-angle slab of stone with nearest-neighbour "
        "(left) and bilinear (right) sampling. Brick edges are hard and stair-stepped on "
        "the left, soft and continuous on the right.")))

    story.append(P("6.3 Frustum-culled wall chunks, resolution presets, particles", h2))
    story.append(P(
        "The maze is generated as one mesh, but for rendering it is split into 4x4-cell "
        "chunks. Each chunk carries its own AABB, and <font face='Courier'>frustum.py</font> "
        "tests it against the six planes of the view frustum. In the follow camera the "
        "HUD reports 8 of 24 chunks drawn, i.e. two thirds of the wall geometry never "
        "reaches the rasteriser. The same idea is reused for the four resolution "
        "presets (F5): the scene is rendered into a small offscreen buffer and "
        "letterboxed up to the 1280x800 window, which keeps the aspect ratio "
        "independent of the window shape. Finally, a small particle system spawns "
        "sparkles when an apple is collected and a firework at the flag; each particle "
        "is a point with a world position and a size that is attenuated by 1/z.", body))
    story.append(KeepTogether(IMG("fig10_gameplay.png", 9.2,
        "Figure 12 - Gameplay after eight scripted steps. The worm is the orange chain "
        "of spheres, apples float and bob, and the blue water hole is lethal.")))

    # ------------------------------------------------------------ section 7 ---
    story.append(P("7. Performance measurements", h1))
    story.append(P(
        "The numbers below come from <font face='Courier'>tools/perf_bench.py</font>, "
        "which renders twelve frames per configuration after one warm-up frame and "
        "reports the mean. The measurements were taken on the laptop used for "
        "development (Windows 11, Python 3.13.18, NumPy 2.5.5) with no other load."))
    story.append(Table([
        ["Resolution", "Camera", "ms / frame", "FPS", "Triangles"],
        ["480x300 FAST", "elevated", "141", "7.1", "989"],
        ["480x300 FAST", "follow", "163", "6.2", "306"],
        ["640x400 BALANCED", "elevated", "205", "4.9", "1059"],
        ["640x400 BALANCED", "follow", "237", "4.2", "313"],
        ["896x560 HIGH", "elevated", "244", "4.1", "1145"],
        ["896x560 HIGH", "follow", "402", "2.5", "317"],
        ["1280x800 NATIVE", "elevated", "301", "3.3", "1199"],
        ["1280x800 NATIVE", "follow", "819", "1.2", "322"],
    ], colWidths=[4.2 * cm, 2.6 * cm, 2.6 * cm, 2.2 * cm, 2.6 * cm],
        style=TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.6),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe8ef")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9fb4c4")),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ])))
    story.append(Spacer(0, 0.25 * cm))
    story.append(P(
        "The interesting result is that the follow camera, which draws only about 300 "
        "triangles, is often <i>slower</i> than the elevated camera with 1100. The "
        "reason is fill rate: in the follow view a few large wall and floor triangles "
        "cover most of the screen, while the elevated view is made of many small ones. "
        "Triangles, then, are not the cost driver in the near view - pixels are.", body))
    story.append(P(
        "Profiling the inner loop showed where the time goes. Each triangle costs a "
        "roughly constant 0.10-0.15 ms no matter how many pixels it covers, because the "
        "per-triangle path performs about forty NumPy calls on small arrays: "
        "subtracting the eye, projecting three vertices, choosing the fan, building "
        "meshgrids, evaluating three barycentric planes, gathering texels, and so on. "
        "At 300 triangles that is around 45 ms of pure overhead, and at 1100 triangles "
        "it is 150 ms. Fill rate then adds roughly 0.2-0.6 ms per thousand pixels.", body))
    story.append(P(
        "Four optimisations were tried and measured. Casting the mesh arrays to float32 "
        "and removing a modulo from the texture sampler gained about 10 %. Caching unit "
        "spheres and boxes and only translating them per frame saved a few milliseconds. "
        "Sorting chunks front-to-back gained nothing, because early z-rejection is "
        "already cheap. Subdividing large triangles adaptively never triggered: the "
        "largest triangle never exceeded 2x the screen, so the code path stays dormant. "
        "The honest conclusion is that the remaining cost is Python-level per-triangle "
        "overhead, and that removing it would require batching many triangles into one "
        "vectorised pass or moving the inner loop out of Python entirely.", body))
    story.append(P(
        "Because of this the game defaults to the FAST 480x300 preset (about 7 fps) and "
        "lets the player raise the resolution with F5 when demonstrating the renderer "
        "rather than playing. Gameplay uses a capped time step, so the simulation stays "
        "stable even when the frame rate drops.", body))

    # ------------------------------------------------------------ section 8 ---
    story.append(P("8. Testing and verification", h1))
    story.append(P(
        "Nineteen unit tests run with <font face='Courier'>python -m unittest "
        "discover -s tests</font> and cover the parts that are easy to get subtly wrong:"))
    story.append(Table([
        ["Test group", "What is asserted"],
        ["Vectors", "cross product is orthogonal to both inputs; normalisation length"],
        ["Matrices", "+90 deg about +Y maps +X to -Z; composition order; direction ignores translation"],
        ["Camera basis", "orthonormal; screen right equals world +X when looking to -Z (no mirroring); round trip"],
        ["Projection", "a point on the axis lands in the screen centre; behind-camera returns None; focal = 200 at 90 deg for h = 400"],
        ["Near clipping", "a crossing triangle is split into two with all z >= near; an inside triangle is returned unchanged"],
        ["Maze", "deterministic for a seed; a perfect maze has cols*rows-1 openings; every cell reachable; circle/box collision"],
        ["Rasteriser", "the nearer of two overlapping quads wins the z-buffer test"],
    ], colWidths=[3.4 * cm, 12.9 * cm], style=TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.2),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe8ef")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9fb4c4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ])))
    story.append(Spacer(0, 0.2 * cm))
    story.append(P(
        "Visual verification used the three debug views instead of assertions: F1 for "
        "the triangle structure, F2 for normals (a wrongly wound face shows up "
        "immediately as the wrong colour), F3 for the depth buffer. Two bugs in this "
        "project were found exactly this way: the missing wall run (a frustum test that "
        "culled boxes straddling a plane) and the mirrored image (the reversed cross "
        "product in the camera basis). Both now have a regression test.", body))

    # ------------------------------------------------------------ section 9 ---
    story.append(P("9. Limitations and conclusion", h1))
    story.append(P(
        "The renderer has no shadows, no transparency, no mip-mapping and only one "
        "directional light. Large floor triangles are handled by splitting the floor "
        "into a grid and by correcting the UV interpolation rather than by clipping "
        "polygons against the screen edge. The frame rate is the main weakness and is "
        "discussed honestly above."))
    story.append(P(
        "What the project does demonstrate is that the whole of a real-time 3D "
        "pipeline - model and view matrices, projection, clipping, back-face culling, "
        "frustum culling, barycentric rasterisation, a depth buffer, perspective-correct "
        "texturing, directional shading and fog - fits into about 1,500 lines of "
        "readable Python once the mathematics is understood, and that every stage can "
        "be switched on and off to see what it contributes. The 2D game survives "
        "unchanged underneath, which was the actual point of the assignment: only the "
        "presentation layer was replaced."))

    story.append(Spacer(0, 0.4 * cm))
    story.append(P("<b>Appendix A - files and commands</b>", h2))
    story.append(P(
        "<font face='Courier'>python main.py</font> &nbsp; play &nbsp;|&nbsp; "
        "<font face='Courier'>python first_cube.py</font> &nbsp; milestone demo &nbsp;|&nbsp; "
        "<font face='Courier'>python -m unittest discover -s tests -v</font> &nbsp; tests &nbsp;|&nbsp; "
        "<font face='Courier'>python tools\\make_figures.py</font> &nbsp; figures &nbsp;|&nbsp; "
        "<font face='Courier'>python tools\\perf_bench.py</font> &nbsp; benchmark", code))

    doc = BaseDocTemplate(os.path.join(OUT_DIR, "Worm_Garden_3D_Report.pdf"),
                          pagesize=A4,
                          leftMargin=2.0 * cm, rightMargin=2.0 * cm,
                          topMargin=1.7 * cm, bottomMargin=1.7 * cm,
                          title="Worm's Garden Adventure 3D - report",
                          author="Xuefan Zhang (P51W1R)")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="n")

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#8899aa"))
        canvas.drawString(doc.leftMargin, 1.0 * cm,
                          "Worm's Garden Adventure 3D - GEIAL31L-B2a")
        canvas.drawRightString(A4[0] - doc.rightMargin, 1.0 * cm,
                               "page %d" % doc_.page)
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=footer)])
    doc.build(story)
    print("report written to", os.path.join(OUT_DIR, "Worm_Garden_3D_Report.pdf"))


if __name__ == "__main__":
    build()
