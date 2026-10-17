import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


def _lerp_color(c1, c2, t: float):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(len(c1)))


def render_engineering_icon(canvas_size: int = 2048) -> Image.Image:
    """
    Renders a high-resolution, anti-aliased Universal Engineering Study Suite icon
    matching the app's dark slate / precision blueprint aesthetic (#0b1322 / #2563eb / #60a5fa / #f8fafc).
    """
    s = canvas_size
    pad = int(s * 0.025)
    radius = int(s * 0.22)

    # 1. Create vertical gradient background for the squircle
    bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    top_col = (11, 19, 34, 255)      # #0b1322
    mid_col = (16, 28, 51, 255)      # #101c33
    bot_col = (12, 21, 38, 255)      # #0c1526

    grad = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad_px = grad.load()
    for y in range(s):
        t = y / max(1, s - 1)
        if t < 0.55:
            col = _lerp_color(top_col, mid_col, t / 0.55)
        else:
            col = _lerp_color(mid_col, bot_col, (t - 0.55) / 0.45)
        for x in range(s):
            grad_px[x, y] = col

    # Radial glow in center (subtle blueprint cobalt glow)
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    cx, cy = s // 2, int(s * 0.44)
    max_r = int(s * 0.44)
    for r in range(max_r, 0, -8):
        alpha = int(60 * (1.0 - (r / max_r) ** 1.6))
        glow_draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(37, 99, 235, alpha))
    grad = Image.alpha_composite(grad, glow)

    # 2. Engineering blueprint grid inside the canvas
    grid_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grid_layer)
    minor_step = int(s * 0.055)

    for idx, pos in enumerate(range(pad, s - pad, minor_step)):
        is_major = (idx % 3 == 0)
        line_col = (59, 130, 246, 36 if is_major else 16)
        width = max(2, int(s * (0.0018 if is_major else 0.001)))
        gdraw.line([(pos, pad), (pos, s - pad)], fill=line_col, width=width)
        gdraw.line([(pad, pos), (s - pad, pos)], fill=line_col, width=width)

    # Corner CAD registration crosshairs (+)
    cross_offset = int(s * 0.145)
    cross_arm = int(s * 0.018)
    cross_w = max(3, int(s * 0.0024))
    cross_col = (96, 165, 250, 105)
    for px in (cross_offset, s - cross_offset):
        for py in (cross_offset, s - cross_offset):
            gdraw.line([(px - cross_arm, py), (px + cross_arm, py)], fill=cross_col, width=cross_w)
            gdraw.line([(px, py - cross_arm), (px, py + cross_arm)], fill=cross_col, width=cross_w)

    grad = Image.alpha_composite(grad, grid_layer)

    # Mask to rounded squircle
    mask = Image.new("L", (s, s), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((pad, pad, s - pad, s - pad), radius=radius, fill=255)
    bg.paste(grad, (0, 0), mask)

    # 3. Squircle double-border (outer slate-blue frame + inner subtle highlight)
    frame_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(frame_layer)
    outer_w = int(s * 0.018)
    inner_inset = pad + int(s * 0.026)
    fdraw.rounded_rectangle(
        (pad, pad, s - pad, s - pad),
        radius=radius,
        outline=(37, 99, 235, 240),
        width=outer_w,
    )
    fdraw.rounded_rectangle(
        (inner_inset, inner_inset, s - inner_inset, s - inner_inset),
        radius=radius - int(s * 0.022),
        outline=(148, 163, 184, 60),
        width=max(2, int(s * 0.003)),
    )
    bg = Image.alpha_composite(bg, frame_layer)

    # 4. Technical Gear & Circuit Traces
    emblem = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    edraw = ImageDraw.Draw(emblem)

    gear_cx, gear_cy = s // 2, int(s * 0.435)
    outer_gear_r = int(s * 0.268)
    inner_gear_r = int(s * 0.230)

    # Draw circuit trace leads & nodes first so they tuck cleanly under the gear body
    trace_y_top = gear_cy - int(s * 0.062)
    trace_y_bot = gear_cy + int(s * 0.062)
    trace_w = int(s * 0.011)
    trace_col = (56, 189, 248, 225)
    node_r = int(s * 0.021)

    # Left circuit traces
    l_x1 = gear_cx - inner_gear_r + int(s * 0.01)
    l_x2 = int(s * 0.125)
    edraw.line([(l_x1, trace_y_top), (l_x2 + int(s * 0.04), trace_y_top), (l_x2, trace_y_top - int(s * 0.04))], fill=trace_col, width=trace_w)
    edraw.line([(l_x1, trace_y_bot), (l_x2 + int(s * 0.04), trace_y_bot), (l_x2, trace_y_bot + int(s * 0.04))], fill=trace_col, width=trace_w)
    for nx, ny in [(l_x2, trace_y_top - int(s * 0.04)), (l_x2, trace_y_bot + int(s * 0.04))]:
        edraw.ellipse((nx - node_r, ny - node_r, nx + node_r, ny + node_r), fill=(11, 19, 34, 255), outline=(56, 189, 248, 255), width=int(s * 0.008))

    # Right circuit traces
    r_x1 = gear_cx + inner_gear_r - int(s * 0.01)
    r_x2 = s - int(s * 0.125)
    edraw.line([(r_x1, trace_y_top), (r_x2 - int(s * 0.04), trace_y_top), (r_x2, trace_y_top - int(s * 0.04))], fill=trace_col, width=trace_w)
    edraw.line([(r_x1, trace_y_bot), (r_x2 - int(s * 0.04), trace_y_bot), (r_x2, trace_y_bot + int(s * 0.04))], fill=trace_col, width=trace_w)
    for nx, ny in [(r_x2, trace_y_top - int(s * 0.04)), (r_x2, trace_y_bot + int(s * 0.04))]:
        edraw.ellipse((nx - node_r, ny - node_r, nx + node_r, ny + node_r), fill=(11, 19, 34, 255), outline=(56, 189, 248, 255), width=int(s * 0.008))

    # 12-tooth precision machine gear
    num_teeth = 12
    gear_pts = []
    for i in range(num_teeth * 4):
        angle = (i * math.pi * 2) / (num_teeth * 4) - math.pi / 2
        phase = i % 4
        r = outer_gear_r if phase in (1, 2) else inner_gear_r
        if phase == 1:
            angle -= 0.018
        elif phase == 2:
            angle += 0.018
        gear_pts.append((gear_cx + r * math.cos(angle), gear_cy + r * math.sin(angle)))

    edraw.polygon(gear_pts, fill=(15, 31, 58, 240), outline=(59, 130, 246, 195), width=int(s * 0.007))

    # Inner precision protractor / degree ring
    ring_r = int(s * 0.195)
    edraw.ellipse(
        (gear_cx - ring_r, gear_cy - ring_r, gear_cx + ring_r, gear_cy + ring_r),
        fill=(11, 20, 38, 250),
        outline=(96, 165, 250, 210),
        width=int(s * 0.0075),
    )

    # Degree tick marks around the inner ring
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        t_len = int(s * (0.020 if deg % 45 == 0 else 0.011))
        r1 = ring_r - int(s * 0.006)
        r2 = r1 - t_len
        w = int(s * (0.0045 if deg % 45 == 0 else 0.0025))
        col = (147, 197, 253, 190 if deg % 45 == 0 else 105)
        edraw.line(
            [
                (gear_cx + r1 * math.cos(rad), gear_cy + r1 * math.sin(rad)),
                (gear_cx + r2 * math.cos(rad), gear_cy + r2 * math.sin(rad)),
            ],
            fill=col,
            width=w,
        )

    # 6. Continuous Harmonic Sine / Carrier Wave across the inner ring
    wave_pts = []
    wave_left = gear_cx - int(ring_r * 0.82)
    wave_right = gear_cx + int(ring_r * 0.82)
    wave_amp = int(s * 0.052)
    steps = 120
    for i in range(steps + 1):
        u = i / steps
        wx = wave_left + (wave_right - wave_left) * u
        env = math.sin(u * math.pi) ** 0.75
        wy = gear_cy + int(s * 0.012) - wave_amp * env * math.sin((u - 0.5) * 2.5 * math.pi)
        wave_pts.append((wx, wy))
    edraw.line(wave_pts, fill=(56, 189, 248, 240), width=int(s * 0.013), joint="curve")

    # 7. Precision Drafting Compass / Caliper A-Frame (Hero Foreground Symbol)
    apex_x, apex_y = gear_cx, int(s * 0.240)
    leg_len = int(s * 0.350)
    spread_angle = math.radians(24)

    left_tip_x = apex_x - int(leg_len * math.sin(spread_angle))
    left_tip_y = apex_y + int(leg_len * math.cos(spread_angle))
    right_tip_x = apex_x + int(leg_len * math.sin(spread_angle))
    right_tip_y = apex_y + int(leg_len * math.cos(spread_angle))

    # Drop shadow behind compass
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sh_off = int(s * 0.012)
    sdraw.line([(apex_x, apex_y + sh_off), (left_tip_x, left_tip_y + sh_off)], fill=(0, 0, 0, 150), width=int(s * 0.032))
    sdraw.line([(apex_x, apex_y + sh_off), (right_tip_x, right_tip_y + sh_off)], fill=(0, 0, 0, 150), width=int(s * 0.032))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=int(s * 0.012)))
    emblem = Image.alpha_composite(emblem, shadow)
    edraw = ImageDraw.Draw(emblem)

    # Horizontal crossbar of the drafting compass
    bar_y = apex_y + int(leg_len * 0.54)
    bar_half_w = int(s * 0.115)
    edraw.line(
        [(apex_x - bar_half_w, bar_y), (apex_x + bar_half_w, bar_y)],
        fill=(147, 197, 253, 255),
        width=int(s * 0.016),
    )
    # Center adjustment wheel on crossbar
    wheel_w = int(s * 0.018)
    wheel_h = int(s * 0.028)
    edraw.rounded_rectangle(
        (apex_x - wheel_w, bar_y - wheel_h, apex_x + wheel_w, bar_y + wheel_h),
        radius=int(s * 0.006),
        fill=(37, 99, 235, 255),
        outline=(248, 250, 252, 255),
        width=int(s * 0.005),
    )

    # Left & Right compass legs (crisp white/ice-slate metallic vectors)
    leg_w = int(s * 0.028)
    edraw.line([(apex_x, apex_y), (left_tip_x, left_tip_y)], fill=(248, 250, 252, 255), width=leg_w)
    edraw.line([(apex_x, apex_y), (right_tip_x, right_tip_y)], fill=(226, 232, 240, 255), width=leg_w)

    # Compass needle tips
    for tx, ty in [(left_tip_x, left_tip_y), (right_tip_x, right_tip_y)]:
        r_tip = int(s * 0.014)
        edraw.ellipse((tx - r_tip, ty - r_tip, tx + r_tip, ty + r_tip), fill=(96, 165, 250, 255))

    # Compass top handle & hinge head
    handle_h = int(s * 0.044)
    handle_w = int(s * 0.014)
    edraw.rounded_rectangle(
        (apex_x - handle_w, apex_y - handle_h - int(s * 0.02), apex_x + handle_w, apex_y),
        radius=int(s * 0.007),
        fill=(248, 250, 252, 255),
    )
    hinge_r = int(s * 0.035)
    edraw.ellipse(
        (apex_x - hinge_r, apex_y - hinge_r, apex_x + hinge_r, apex_y + hinge_r),
        fill=(37, 99, 235, 255),
        outline=(248, 250, 252, 255),
        width=int(s * 0.010),
    )
    inner_dot_r = int(s * 0.011)
    edraw.ellipse(
        (apex_x - inner_dot_r, apex_y - inner_dot_r, apex_x + inner_dot_r, apex_y + inner_dot_r),
        fill=(248, 250, 252, 255),
    )

    # 8. Open Technical Study Guide / Engineering Folio at Base (clean separation below gear)
    book_cy = int(s * 0.785)
    book_w = int(s * 0.265)
    book_h = int(s * 0.095)
    spine_dip = int(s * 0.032)

    left_page = [
        (gear_cx, book_cy - book_h // 2 + spine_dip),
        (gear_cx - book_w, book_cy - book_h // 2 - int(s * 0.015)),
        (gear_cx - book_w, book_cy + book_h // 2 - int(s * 0.015)),
        (gear_cx, book_cy + book_h // 2 + spine_dip),
    ]
    right_page = [
        (gear_cx, book_cy - book_h // 2 + spine_dip),
        (gear_cx + book_w, book_cy - book_h // 2 - int(s * 0.015)),
        (gear_cx + book_w, book_cy + book_h // 2 - int(s * 0.015)),
        (gear_cx, book_cy + book_h // 2 + spine_dip),
    ]

    edraw.polygon(left_page, fill=(30, 58, 138, 245), outline=(248, 250, 252, 255), width=int(s * 0.009))
    edraw.polygon(right_page, fill=(29, 78, 216, 245), outline=(248, 250, 252, 255), width=int(s * 0.009))

    # Page rule lines inside the open study guide
    for row_idx in (-1, 1):
        ly_offset = int(row_idx * s * 0.018)
        edraw.line(
            [
                (gear_cx - int(book_w * 0.78), book_cy + ly_offset - int(s * 0.005)),
                (gear_cx - int(book_w * 0.20), book_cy + ly_offset + int(s * 0.012)),
            ],
            fill=(147, 197, 253, 215),
            width=int(s * 0.0065),
        )
        edraw.line(
            [
                (gear_cx + int(book_w * 0.20), book_cy + ly_offset + int(s * 0.012)),
                (gear_cx + int(book_w * 0.78), book_cy + ly_offset - int(s * 0.005)),
            ],
            fill=(191, 219, 254, 215),
            width=int(s * 0.0065),
        )

    # Center spine highlight
    edraw.line(
        [(gear_cx, book_cy - book_h // 2 + spine_dip), (gear_cx, book_cy + book_h // 2 + spine_dip)],
        fill=(248, 250, 252, 255),
        width=int(s * 0.010),
    )

    bg = Image.alpha_composite(bg, emblem)
    return bg


def build_clean_icon():
    base_dir = Path(__file__).parent.resolve()
    static_dir = base_dir / "static"
    static_dir.mkdir(exist_ok=True)

    png_out = static_dir / "app_icon.png"
    master_out = static_dir / "engineering_icon_master.png"
    ico_out_1 = base_dir / "biomedical_icon.ico"
    ico_out_2 = base_dir / "app_icon.ico"

    print("Rendering high-resolution Universal Engineering Study Suite icon (2048x2048 -> 512x512)...")
    hi_res = render_engineering_icon(2048)

    # Save 1024x1024 master PNG
    master_img = hi_res.resize((1024, 1024), Image.Resampling.LANCZOS)
    master_img.save(master_out, format="PNG")

    # Save 512x512 web/UI PNG
    final_png = hi_res.resize((512, 512), Image.Resampling.LANCZOS)
    final_png.save(png_out, format="PNG")
    print(f"Saved PNG icon: {png_out}")

    # Save multi-resolution Windows .ico files
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    final_png.save(ico_out_1, format="ICO", sizes=icon_sizes)
    final_png.save(ico_out_2, format="ICO", sizes=icon_sizes)
    print(f"Saved ICO icons: {ico_out_1}, {ico_out_2}")


if __name__ == "__main__":
    build_clean_icon()
