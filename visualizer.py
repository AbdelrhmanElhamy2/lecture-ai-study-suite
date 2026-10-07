import os
import re
import math
import textwrap
import logging
from pathlib import Path
from typing import List, Optional
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from models import DiagramDefinition, DiagramElement
from config import ASSETS_DIR

logger = logging.getLogger(__name__)

# Universal Academic Color Palette
PRIMARY_COLOR = "#1E40AF"     # Royal Blue
SECONDARY_COLOR = "#0D9488"   # Teal
ACCENT_COLOR = "#D97706"      # Warm Amber
PURPLE_COLOR = "#7C3AED"      # Deep Purple
BG_CARD = "#F8FAFC"           # Soft Slate
TEXT_DARK = "#0F172A"         # Slate 900
TEXT_MUTED = "#475569"        # Slate 600
BORDER_COLOR = "#CBD5E1"      # Slate 300

BOX_PALETTE = ["#2563EB", "#0D9488", "#7C3AED", "#D97706", "#DB2777", "#059669", "#4F46E5"]

def wrap_text(text: str, width: int = 18) -> str:
    """Wrap text to keep diagram boxes compact and readable."""
    if not text:
        return ""
    return "\n".join(textwrap.wrap(text, width=width))

def render_flowchart(diagram: DiagramDefinition, output_path: Path) -> Path:
    """Renders a sleek horizontal or vertical flowchart sequence without text collisions."""
    elements = diagram.elements
    n = max(len(elements), 1)
    
    # Decide horizontal vs vertical layout
    is_vertical = n > 4
    
    if is_vertical:
        card_labels = [wrap_text(e.label, width=38) for e in elements]
        card_descs = [wrap_text(e.description or "", width=50) for e in elements]
        
        box_w = 7.8
        box_x = 0.6
        step_dy = 2.0
        fig_w, fig_h = 8.6, max(4.5, n * step_dy + 0.6)
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
        ax.set_xlim(0, 9.0)
        ax.set_ylim(-0.4, n * step_dy)
        
        box_h = 1.45
        
        for i, elem in enumerate(elements):
            y_pos = (n - 1 - i) * step_dy
            color = BOX_PALETTE[i % len(BOX_PALETTE)]
            
            # Card background
            card = patches.FancyBboxPatch(
                (box_x, y_pos), box_w, box_h,
                boxstyle="round,pad=0.12,rounding_size=0.22",
                linewidth=1.8, edgecolor=color, facecolor=BG_CARD
            )
            ax.add_patch(card)
            
            # Step badge
            badge = patches.FancyBboxPatch(
                (box_x + 0.25, y_pos + box_h - 0.62), 1.05, 0.45,
                boxstyle="round,pad=0.08,rounding_size=0.15",
                linewidth=0, facecolor=color
            )
            ax.add_patch(badge)
            ax.text(box_x + 0.77, y_pos + box_h - 0.40, f"#{i+1}", color="white",
                    weight="bold", fontsize=10.0, ha="center", va="center")
            
            # Label
            curr_label = card_labels[i]
            ax.text(box_x + 1.5, y_pos + box_h - 0.25, curr_label, color=TEXT_DARK,
                    weight="bold", fontsize=11.0, ha="left", va="top")
            
            # Subtitle/Description placed safely below label
            curr_desc = card_descs[i]
            if curr_desc:
                n_lbl = len(curr_label.split("\n"))
                desc_top_y = y_pos + box_h - 0.25 - (n_lbl * 0.32) - 0.08
                ax.text(box_x + 1.5, desc_top_y, curr_desc, color=TEXT_MUTED,
                        fontsize=9.0, ha="left", va="top")
                
            # Connecting Arrow
            if i < n - 1:
                next_y = (n - 2 - i) * step_dy + box_h
                ax.annotate(
                    "", xy=(4.5, next_y), xytext=(4.5, y_pos),
                    arrowprops=dict(arrowstyle="-|>", color="#64748B", lw=2.2, mutation_scale=16)
                )
    else:
        # Horizontal layout: measure text requirements across all elements
        card_labels = [wrap_text(e.label, width=18) for e in elements]
        card_descs = [wrap_text(e.description or "", width=25) for e in elements]
        
        max_label_lines = max(len(lbl.split("\n")) for lbl in card_labels)
        max_desc_lines = max(len(desc.split("\n")) for desc in card_descs)
        
        header_h = 0.50
        gap_under_header = 0.18
        label_line_h = 0.25
        gap_under_label = 0.18
        desc_line_h = 0.18
        bottom_pad = 0.25
        
        needed_card_h = (
            header_h + gap_under_header +
            (max_label_lines * label_line_h) +
            gap_under_label +
            (max_desc_lines * desc_line_h) +
            bottom_pad
        )
        box_h = max(3.0, needed_card_h)
        box_w = 2.6
        gap_between_boxes = 0.70
        
        fig_w = max(8.5, n * (box_w + gap_between_boxes) + 0.8)
        fig_h = max(4.4, box_h + 1.2)
        
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
        total_width = n * box_w + (n - 1) * gap_between_boxes
        ax.set_xlim(0, total_width + 1.0)
        ax.set_ylim(0, fig_h)
        
        start_x = 0.5
        y_pos = (fig_h - box_h) / 2.0 - 0.2
        
        for i, elem in enumerate(elements):
            x_pos = start_x + i * (box_w + gap_between_boxes)
            color = BOX_PALETTE[i % len(BOX_PALETTE)]
            
            # Card background
            card = patches.FancyBboxPatch(
                (x_pos, y_pos), box_w, box_h,
                boxstyle="round,pad=0.10,rounding_size=0.22",
                linewidth=1.8, edgecolor=color, facecolor=BG_CARD
            )
            ax.add_patch(card)
            
            # Step header bar at top of card
            header_bar = patches.FancyBboxPatch(
                (x_pos, y_pos + box_h - header_h), box_w, header_h,
                boxstyle="round,pad=0.04,rounding_size=0.18",
                linewidth=0, facecolor=color
            )
            ax.add_patch(header_bar)
            ax.text(
                x_pos + box_w / 2, y_pos + box_h - (header_h / 2),
                f"Step {i+1}", color="white", weight="bold", fontsize=10,
                ha="center", va="center"
            )
            
            # Label (Step Title)
            curr_label = card_labels[i]
            label_top_y = y_pos + box_h - header_h - gap_under_header
            ax.text(
                x_pos + box_w / 2, label_top_y,
                curr_label, color=TEXT_DARK, weight="bold", fontsize=9.5,
                ha="center", va="top"
            )
            
            # Subtle separator line between title and description
            n_lbl_lines = len(curr_label.split("\n"))
            sep_y = label_top_y - (n_lbl_lines * label_line_h) - 0.08
            ax.plot(
                [x_pos + 0.35, x_pos + box_w - 0.35], [sep_y, sep_y],
                color="#E2E8F0", linewidth=0.8
            )
            
            # Subtitle / Description text placed safely below separator
            curr_desc = card_descs[i]
            if curr_desc:
                desc_top_y = sep_y - 0.10
                ax.text(
                    x_pos + box_w / 2, desc_top_y,
                    curr_desc, color=TEXT_MUTED, fontsize=8.0,
                    ha="center", va="top"
                )
                
            # Connecting Arrow
            if i < n - 1:
                arrow_start_x = x_pos + box_w + 0.05
                arrow_end_x = arrow_start_x + gap_between_boxes - 0.10
                arrow_y = y_pos + (box_h / 2)
                ax.annotate(
                    "", xy=(arrow_end_x, arrow_y), xytext=(arrow_start_x, arrow_y),
                    arrowprops=dict(
                        arrowstyle="-|>", color="#64748B", lw=2.2,
                        mutation_scale=16
                    )
                )

    ax.set_title(diagram.title, fontsize=13, weight="bold", color=TEXT_DARK, pad=14)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return output_path

def render_comparison_bar(diagram: DiagramDefinition, output_path: Path) -> Path:
    """Renders a comparison bar chart for quantitative benchmarks or metric comparisons."""
    elements = diagram.elements
    labels = [wrap_text(e.label, 16) for e in elements]
    values = [e.value if e.value is not None else (i + 1) * 20 for i, e in enumerate(elements)]
    
    fig, ax = plt.subplots(figsize=(7.5, max(3.5, len(labels) * 0.8)), dpi=150)
    colors = [BOX_PALETTE[i % len(BOX_PALETTE)] for i in range(len(labels))]
    
    bars = ax.barh(labels, values, color=colors, height=0.55, edgecolor="none", zorder=3)
    
    ax.grid(axis="x", linestyle="--", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BORDER_COLOR)
    ax.spines["bottom"].set_color(BORDER_COLOR)
    
    # Value labels on top of bars
    for bar in bars:
        w = bar.get_width()
        ax.text(w + (max(values)*0.02), bar.get_y() + bar.get_height()/2,
                f"{w:.1f}" if isinstance(w, float) else f"{w}",
                va="center", ha="left", fontsize=9, color=TEXT_DARK, weight="bold")
        
    ax.set_title(diagram.title, fontsize=12, weight="bold", color=TEXT_DARK, pad=14)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return output_path

def render_process_cycle(diagram: DiagramDefinition, output_path: Path) -> Path:
    """Renders a circular cyclic process diagram for lifecycles, states, and reciprocal processes."""
    elements = diagram.elements
    n = len(elements)
    if n <= 1:
        return render_flowchart(diagram, output_path)
    
    if n == 2:
        # Two-state reciprocal cycle
        fig, ax = plt.subplots(figsize=(7.5, 4.4), dpi=150)
        ax.set_xlim(-4.0, 4.0)
        ax.set_ylim(-2.4, 2.4)
        ax.axis("off")
        
        x1, y1 = -2.0, 0.0
        x2, y2 = 2.0, 0.0
        
        # Card 1 (Left)
        c1 = patches.FancyBboxPatch((x1 - 1.25, y1 - 0.7), 2.5, 1.4,
                                   boxstyle="round,pad=0.1,rounding_size=0.2",
                                   linewidth=1.8, edgecolor=PRIMARY_COLOR, facecolor=BG_CARD)
        ax.add_patch(c1)
        ax.text(x1, y1 + 0.15, wrap_text(elements[0].label, 16), color=TEXT_DARK, weight="bold",
                fontsize=9.5, ha="center", va="center")
        if elements[0].description:
            ax.text(x1, y1 - 0.35, wrap_text(elements[0].description, 20), color=TEXT_MUTED,
                    fontsize=8.0, ha="center", va="center")
                    
        # Card 2 (Right)
        c2 = patches.FancyBboxPatch((x2 - 1.25, y2 - 0.7), 2.5, 1.4,
                                   boxstyle="round,pad=0.1,rounding_size=0.2",
                                   linewidth=1.8, edgecolor=SECONDARY_COLOR, facecolor=BG_CARD)
        ax.add_patch(c2)
        ax.text(x2, y2 + 0.15, wrap_text(elements[1].label, 16), color=TEXT_DARK, weight="bold",
                fontsize=9.5, ha="center", va="center")
        if elements[1].description:
            ax.text(x2, y2 - 0.35, wrap_text(elements[1].description, 20), color=TEXT_MUTED,
                    fontsize=8.0, ha="center", va="center")
                    
        # Top forward curved arrow (1 -> 2)
        ax.annotate("", xy=(x2 - 0.4, y2 + 0.75), xytext=(x1 + 0.4, y1 + 0.75),
                    arrowprops=dict(arrowstyle="-|>", color=PRIMARY_COLOR, lw=2.2,
                                   connectionstyle="arc3,rad=-0.3", mutation_scale=15))
        ax.text(0, 1.35, "Phase Transition", ha="center", va="center", fontsize=8.5, weight="bold", color=PRIMARY_COLOR)
        
        # Bottom return curved arrow (2 -> 1)
        ax.annotate("", xy=(x1 + 0.4, y1 - 0.75), xytext=(x2 - 0.4, y2 - 0.75),
                    arrowprops=dict(arrowstyle="-|>", color=SECONDARY_COLOR, lw=2.2,
                                   connectionstyle="arc3,rad=-0.3", mutation_scale=15))
        ax.text(0, -1.35, "Cyclic Return", ha="center", va="center", fontsize=8.5, weight="bold", color=SECONDARY_COLOR)
        
        # Center badge
        center_circle = plt.Circle((0, 0), 0.65, color="#EFF6FF", ec=PRIMARY_COLOR, lw=1.5)
        ax.add_patch(center_circle)
        ax.text(0, 0, "CYCLE", color=PRIMARY_COLOR, weight="bold", fontsize=9.5, ha="center", va="center")
        
        ax.set_title(diagram.title, fontsize=12, weight="bold", color=TEXT_DARK, pad=12)
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches="tight", dpi=150)
        plt.close(fig)
        return output_path
    
    # n >= 3 nodes in circle
    fig, ax = plt.subplots(figsize=(6.5, 6.0), dpi=150)
    ax.set_xlim(-3.5, 3.5)
    ax.set_ylim(-3.5, 3.5)
    
    radius = 2.0
    
    for i, elem in enumerate(elements):
        angle = 2 * math.pi * i / n
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        color = BOX_PALETTE[i % len(BOX_PALETTE)]
        
        # Circle / rounded box
        card = patches.FancyBboxPatch(
            (x - 0.75, y - 0.45), 1.5, 0.9,
            boxstyle="round,pad=0.1,rounding_size=0.2",
            linewidth=1.5, edgecolor=color, facecolor=BG_CARD
        )
        ax.add_patch(card)
        
        lbl = wrap_text(elem.label, 12)
        ax.text(x, y, lbl, color=TEXT_DARK, weight="bold",
                fontsize=8.5, ha="center", va="center")
        
        # Curved connecting arrow to next node
        next_angle = 2 * math.pi * ((i + 1) % n) / n
        ax.annotate(
            "",
            xy=(radius * math.cos(next_angle - 0.22), radius * math.sin(next_angle - 0.22)),
            xytext=(radius * math.cos(angle + 0.22), radius * math.sin(angle + 0.22)),
            arrowprops=dict(
                arrowstyle="-|>", color=TEXT_MUTED, lw=1.8,
                connectionstyle="arc3,rad=-0.25", mutation_scale=12
            )
        )
        
    # Center badge
    center_circle = plt.Circle((0, 0), 0.7, color="#EFF6FF", ec=PRIMARY_COLOR, lw=1.5)
    ax.add_patch(center_circle)
    ax.text(0, 0, "CYCLE", color=PRIMARY_COLOR, weight="bold", fontsize=10, ha="center", va="center")

    ax.set_title(diagram.title, fontsize=12, weight="bold", color=TEXT_DARK, pad=10)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return output_path

def validate_and_normalize_diagram(diagram: DiagramDefinition) -> DiagramDefinition:
    """
    Validates diagram element count against numeric references in its title.
    If the title mentions a specific count (e.g., 'The Three Pillars of Power Electronics'),
    verifies the element count matches. If mismatched, logs a warning and reconciles elements
    (e.g., removing redundant self-referential central concepts like 'Power Electronics'
    from the outer pillars, ensuring exactly 'Power', 'Electronics', 'Control').
    """
    title_lower = diagram.title.lower()
    elements = list(diagram.elements)

    # 1. Specific check for 'Three Pillars' / 'The Three Pillars of Power Electronics'
    if "three pillars" in title_lower or "3 pillars" in title_lower:
        expected = 3
        if "power electronic" in title_lower:
            filtered = [
                e for e in elements
                if e.label.strip().lower() not in ["power electronics", "the three pillars", "power electronic system"]
            ]
            if len(elements) != expected:
                logger.warning(
                    f"Diagram title '{diagram.title}' specifies {expected} pillars, but received {len(elements)} elements. "
                    "Reconciling to exactly three pillars: Power, Electronics, Control."
                )
            if len(filtered) == 3:
                for elem in filtered:
                    lbl_lower = elem.label.lower()
                    if "power" in lbl_lower:
                        elem.label = "Power"
                    elif "electronic" in lbl_lower:
                        elem.label = "Electronics"
                    elif "control" in lbl_lower:
                        elem.label = "Control"
                elements = filtered
            elif len(elements) != 3:
                elements = [
                    DiagramElement(label="Power", description="Power Systems: Generation, transmission, and grid networks"),
                    DiagramElement(label="Electronics", description="Solid-State Electronics: Semiconductor devices and circuits"),
                    DiagramElement(label="Control", description="Control Theory: Feedback loops, stability, and PWM regulation")
                ]
            diagram.elements = elements
            return diagram

    # 2. General word/digit count validation
    num_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }
    match = re.search(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|[1-9]|10)\s+([a-z]+)', title_lower)
    if match:
        word = match.group(1)
        expected = int(word) if word.isdigit() else num_map.get(word, 0)
        noun = match.group(2)
        if expected > 0 and noun in ["pillars", "stages", "steps", "conditions", "components", "principles", "phases", "rules", "layers"]:
            if len(elements) != expected:
                logger.warning(
                    f"Diagram '{diagram.title}' count mismatch: title specifies {expected} {noun}, "
                    f"but received {len(elements)} elements."
                )
                if len(elements) > expected:
                    filtered = [e for e in elements if e.label.strip().lower() not in title_lower]
                    if len(filtered) == expected:
                        diagram.elements = filtered

    return diagram


def render_concept_map(diagram: DiagramDefinition, output_path: Path) -> Path:
    """Renders a central hub-and-spoke concept map or taxonomic classification tree with guaranteed zero text collisions."""
    diagram = validate_and_normalize_diagram(diagram)
    elements = diagram.elements
    n = max(len(elements), 1)
    
    # Generous canvas dimensions
    fig, ax = plt.subplots(figsize=(10.2, 6.4), dpi=150)
    ax.set_xlim(-6.2, 6.2)
    ax.set_ylim(-4.0, 4.0)
    ax.axis("off")
    
    # Central Hub
    hub_w, hub_h = 3.2, 1.55
    hub_card = patches.FancyBboxPatch(
        (-hub_w/2, -hub_h/2), hub_w, hub_h,
        boxstyle="round,pad=0.1,rounding_size=0.25",
        linewidth=2.4, edgecolor=PRIMARY_COLOR, facecolor="#EFF6FF", zorder=2
    )
    ax.add_patch(hub_card)
    
    hub_title = wrap_text(diagram.title, 22)
    n_hub_lines = len(hub_title.split("\n"))
    hub_title_y = 0.25 if n_hub_lines <= 2 else 0.32
    ax.text(0, hub_title_y, hub_title, color=PRIMARY_COLOR, weight="bold",
            fontsize=10.0, ha="center", va="center", zorder=3)
    
    # Core Concept badge inside hub
    badge_w, badge_h = 1.3, 0.32
    hub_badge = patches.FancyBboxPatch(
        (-badge_w/2, -0.55), badge_w, badge_h,
        boxstyle="round,pad=0.04,rounding_size=0.12",
        linewidth=0, facecolor="#DBEAFE", zorder=3
    )
    ax.add_patch(hub_badge)
    ax.text(0, -0.39, "Core Concept", color="#1D4ED8", fontsize=7.8, weight="bold", ha="center", va="center", zorder=4)
    
    # Outer Nodes in ellipse with expanded radius
    rx, ry = 4.3, 2.7
    nw, nh = 2.6, 1.45
    
    for i, elem in enumerate(elements):
        angle = 2 * math.pi * i / n
        x = rx * math.cos(angle)
        y = ry * math.sin(angle)
        color = BOX_PALETTE[i % len(BOX_PALETTE)]
        
        # Line from hub edge to node edge
        ax.plot([0, x * 0.70], [0, y * 0.70], color="#94A3B8", lw=1.6, ls="--", zorder=1)
        
        # Node Card
        node_card = patches.FancyBboxPatch(
            (x - nw/2, y - nh/2), nw, nh,
            boxstyle="round,pad=0.08,rounding_size=0.20",
            linewidth=1.8, edgecolor=color, facecolor=BG_CARD, zorder=3
        )
        ax.add_patch(node_card)
        
        # Top-down text placement inside node card to mathematically prevent overlap
        wrapped_label = wrap_text(elem.label, 17)
        n_lbl = len(wrapped_label.split("\n"))
        label_top_y = y + nh/2 - 0.22
        ax.text(x, label_top_y, wrapped_label, color=TEXT_DARK, weight="bold",
                fontsize=8.8, ha="center", va="top", zorder=4)
        
        if elem.description:
            wrapped_desc = wrap_text(elem.description, 23)
            # Position separator and description strictly below the label lines
            sep_y = label_top_y - (n_lbl * 0.22) - 0.05
            ax.plot([x - nw/2 + 0.35, x + nw/2 - 0.35], [sep_y, sep_y], color="#E2E8F0", lw=0.8, zorder=3)
            desc_top_y = sep_y - 0.08
            ax.text(x, desc_top_y, wrapped_desc, color=TEXT_MUTED,
                    fontsize=7.2, ha="center", va="top", zorder=4)
                    
    ax.set_title(diagram.title, fontsize=12.5, weight="bold", color=TEXT_DARK, pad=14)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return output_path


def render_timeline(diagram: DiagramDefinition, output_path: Path) -> Path:
    """Renders a chronological timeline with alternating milestones along a central axis with collision-free card typography."""
    elements = diagram.elements
    n = max(len(elements), 1)
    
    fig_w = max(8.5, n * 2.3 + 1.2)
    fig, ax = plt.subplots(figsize=(fig_w, 4.8), dpi=150)
    ax.set_xlim(0, n * 2.3 + 0.8)
    ax.set_ylim(-2.8, 2.8)
    ax.axis("off")
    
    # Central Timeline Axis
    axis_y = 0.0
    ax.plot([0.5, n * 2.3 + 0.3], [axis_y, axis_y], color="#94A3B8", lw=3.0, zorder=1)
    ax.annotate("", xy=(n * 2.3 + 0.5, axis_y), xytext=(n * 2.3 + 0.1, axis_y),
                arrowprops=dict(arrowstyle="-|>", color="#94A3B8", lw=3.0, mutation_scale=18))
    
    for i, elem in enumerate(elements):
        x = 1.1 + i * 2.3
        is_top = (i % 2 == 0)
        color = BOX_PALETTE[i % len(BOX_PALETTE)]
        
        # Milestone dot
        dot = plt.Circle((x, axis_y), 0.16, color=color, ec="white", lw=2.0, zorder=4)
        ax.add_patch(dot)
        
        # Stem connecting dot to card
        stem_y = 0.95 if is_top else -0.95
        ax.plot([x, x], [axis_y, stem_y], color=color, lw=1.8, ls=":", zorder=2)
        
        # Card with generous dimensions
        cw, ch = 2.1, 1.35
        cy = stem_y if is_top else stem_y - ch
        card = patches.FancyBboxPatch(
            (x - cw/2, cy), cw, ch,
            boxstyle="round,pad=0.08,rounding_size=0.18",
            linewidth=1.6, edgecolor=color, facecolor=BG_CARD, zorder=3
        )
        ax.add_patch(card)
        
        badge_y = cy + ch - 0.20
        ax.text(x, badge_y, f"Stage {i+1}", color=color, weight="bold", fontsize=8.0, ha="center", va="center", zorder=4)
        
        wrapped_label = wrap_text(elem.label, 15)
        n_lbl = len(wrapped_label.split("\n"))
        label_top_y = cy + ch - 0.40
        ax.text(x, label_top_y, wrapped_label, color=TEXT_DARK, weight="bold", fontsize=8.5, ha="center", va="top", zorder=4)
        
        if elem.description:
            sep_y = label_top_y - (n_lbl * 0.21) - 0.04
            desc_top_y = sep_y - 0.05
            ax.text(x, desc_top_y, wrap_text(elem.description, 18), color=TEXT_MUTED, fontsize=7.0, ha="center", va="top", zorder=4)
            
    ax.set_title(diagram.title, fontsize=12.5, weight="bold", color=TEXT_DARK, pad=14)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return output_path


def render_system_block_diagram(diagram: DiagramDefinition, output_path: Path) -> Path:
    """
    Renders a universal 2-tier multi-component or closed-loop system architecture diagram
    with spacious margins, collision-free arrow badges, and strictly top-down card typography.
    Forward / Primary Tier: Component 1 -> Component 2 -> Component 3
    Secondary / Feedback Tier: Component 6 <- Component 5 <- Component 4
    """
    elements = diagram.elements
    title_upper = diagram.title.upper()
    is_power_domain = "POWER" in title_upper and ("CONVERTER" in title_upper or "RECTIFIER" in title_upper or "INVERTER" in title_upper or "ELECTRONIC" in title_upper or "SYSTEM" in title_upper)
    
    if is_power_domain:
        default_labels = [
            "Power Source",
            "Power Converter",
            "Electrical Load",
            "Feedback Sensors",
            "Controller Unit",
            "Gate Driver",
        ]
        default_descs = [
            "Primary Source / Utility",
            "Core Processing Unit",
            "Output / Destination",
            "Monitoring / Transducers",
            "Decision / Controller",
            "Actuator / Driver",
        ]
    else:
        default_labels = [
            "Primary Source",
            "Core Processing Unit",
            "Output / Destination",
            "Monitoring / Transducers",
            "Decision / Controller",
            "Actuator / Driver",
        ]
        default_descs = [
            "Primary Source",
            "Core Processing Unit",
            "Output / Destination",
            "Monitoring / Transducers",
            "Decision / Controller",
            "Actuator / Driver",
        ]

    # Process elements: fall back to node's description if label is empty, never emit generic Component N
    labels = []
    descs = []
    for e in elements:
        lbl = (e.label or "").strip()
        dsc = (e.description or "").strip()
        if not lbl and dsc:
            lbl = dsc
            dsc = ""
        labels.append(lbl)
        descs.append(dsc)
        
    while len(labels) < 6:
        slot = len(labels)
        labels.append(default_labels[slot])
        descs.append(default_descs[slot])

    for idx in range(6):
        if not labels[idx] or re.match(r"^Component\s*\d+$", labels[idx], re.IGNORECASE):
            labels[idx] = descs[idx] if descs[idx] else default_labels[idx]
        if not descs[idx] and idx < len(default_descs):
            descs[idx] = default_descs[idx]

    labels = [wrap_text(lbl, 16) for lbl in labels]
    descs = [wrap_text(dsc, 22) for dsc in descs]
    
    # Context-aware arrow labels
    if is_power_domain:
        fwd1_lbl = "Input Power"
        fwd2_lbl = "Processed Power"
        down_lbl = "Measurement"
        feed1_lbl = "Feedback Signals"
        feed2_lbl = "PWM Commands"
        up_lbl = "Gate Switching\nPulses"
        ref_lbl = "Reference Input ($V_{ref}, I_{ref}$)"
    else:
        fwd1_lbl = "Input / Request"
        fwd2_lbl = "Processed Flow"
        down_lbl = "State / Output"
        feed1_lbl = "Metrics / Signals"
        feed2_lbl = "Control / Logic"
        up_lbl = "Feedback / Update\nLoop"
        ref_lbl = "Target / Policy"

    fig, ax = plt.subplots(figsize=(11.0, 6.4), dpi=150)
    ax.set_xlim(0, 11.6)
    ax.set_ylim(-0.5, 6.2)
    ax.axis("off")
    
    COLOR1 = "#1E40AF"     # Royal Blue
    COLOR2 = "#0D9488"     # Teal
    COLOR3 = "#7C3AED"     # Purple
    COLOR4 = "#D97706"     # Amber
    COLOR5 = "#2563EB"     # Blue
    COLOR6 = "#DC2626"     # Crimson
    
    bw, bh = 2.45, 1.45
    by_top = 3.8
    by_bot = 0.9
    bx1 = 0.5
    bx2 = 4.55
    bx3 = 8.6
    
    # Helper to draw box text strictly top-down
    def draw_box_content(bx, by, label_str, desc_str, lbl_color=TEXT_DARK):
        top_y = by + bh - 0.24
        lbl_lines = label_str.split("\n")
        n_lbl = len(lbl_lines)
        ax.text(bx + bw/2, top_y, label_str, ha="center", va="top",
                fontsize=9.5, weight="bold", color=lbl_color, zorder=4)
        if desc_str:
            sep_y = top_y - (n_lbl * 0.23) - 0.05
            desc_top_y = sep_y - 0.06
            ax.text(bx + bw/2, desc_top_y, desc_str, ha="center", va="top",
                    fontsize=7.6, color=TEXT_MUTED, zorder=4)

    # Box 1
    c1 = patches.FancyBboxPatch((bx1, by_top), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                linewidth=2.0, edgecolor=COLOR1, facecolor=BG_CARD, zorder=2)
    ax.add_patch(c1)
    draw_box_content(bx1, by_top, labels[0], descs[0])
            
    # Box 2
    c2 = patches.FancyBboxPatch((bx2, by_top), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                linewidth=2.4, edgecolor=COLOR2, facecolor="#F0FDFA", zorder=2)
    ax.add_patch(c2)
    draw_box_content(bx2, by_top, labels[1], descs[1], lbl_color="#0F766E")
            
    # Box 3
    c3 = patches.FancyBboxPatch((bx3, by_top), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                linewidth=2.0, edgecolor=COLOR3, facecolor=BG_CARD, zorder=2)
    ax.add_patch(c3)
    draw_box_content(bx3, by_top, labels[2], descs[2])
            
    # Primary Forward Arrows with collision-free badges
    mid_fwd1 = (bx1 + bw + bx2) / 2
    ax.annotate("", xy=(bx2, by_top + bh/2), xytext=(bx1 + bw, by_top + bh/2),
                arrowprops=dict(arrowstyle="-|>", color=COLOR1, lw=3.0, mutation_scale=18), zorder=3)
    ax.text(mid_fwd1, by_top + bh/2 + 0.28, fwd1_lbl, ha="center", va="bottom",
            fontsize=8.0, weight="bold", color=COLOR1, zorder=4,
            bbox=dict(boxstyle="round,pad=0.20", facecolor="white", edgecolor="#CBD5E1", lw=0.8, alpha=0.95))
    
    mid_fwd2 = (bx2 + bw + bx3) / 2
    ax.annotate("", xy=(bx3, by_top + bh/2), xytext=(bx2 + bw, by_top + bh/2),
                arrowprops=dict(arrowstyle="-|>", color=COLOR1, lw=3.0, mutation_scale=18), zorder=3)
    ax.text(mid_fwd2, by_top + bh/2 + 0.28, fwd2_lbl, ha="center", va="bottom",
            fontsize=8.0, weight="bold", color=COLOR1, zorder=4,
            bbox=dict(boxstyle="round,pad=0.20", facecolor="white", edgecolor="#CBD5E1", lw=0.8, alpha=0.95))
    
    # Bottom Row: Secondary / Feedback Loop (y = 0.9 to 2.35)
    # Box 4 (under Box 3)
    bx4, by4 = bx3, by_bot
    c4 = patches.FancyBboxPatch((bx4, by4), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                linewidth=1.8, edgecolor=COLOR4, facecolor=BG_CARD, zorder=2)
    ax.add_patch(c4)
    draw_box_content(bx4, by4, labels[3], descs[3])
            
    # Box 5 (under Box 2)
    bx5, by5 = bx2, by_bot
    c5 = patches.FancyBboxPatch((bx5, by5), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                linewidth=1.8, edgecolor=COLOR5, facecolor=BG_CARD, zorder=2)
    ax.add_patch(c5)
    draw_box_content(bx5, by5, labels[4], descs[4])
            
    # Box 6 (under Box 1)
    bx6, by6 = bx1, by_bot
    c6 = patches.FancyBboxPatch((bx6, by6), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                linewidth=1.8, edgecolor=COLOR6, facecolor=BG_CARD, zorder=2)
    ax.add_patch(c6)
    draw_box_content(bx6, by6, labels[5], descs[5])
            
    # Down arrow from Box 3 to Box 4
    ax.annotate("", xy=(bx3 + bw/2, by_bot + bh), xytext=(bx3 + bw/2, by_top),
                arrowprops=dict(arrowstyle="-|>", color=COLOR4, lw=2.2, ls="--", mutation_scale=15), zorder=3)
    ax.text(bx3 + bw/2 + 0.22, (by_top + by_bot + bh)/2, down_lbl, ha="left", va="center",
            fontsize=7.5, color=COLOR4, weight="bold", zorder=4,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#FDBA74", lw=0.8, alpha=0.95))
    
    # Left arrow from Box 4 to Box 5
    mid_feed1 = (bx4 + bx5 + bw) / 2
    ax.annotate("", xy=(bx5 + bw, by_bot + bh/2), xytext=(bx4, by_bot + bh/2),
                arrowprops=dict(arrowstyle="-|>", color=COLOR5, lw=2.2, ls="--", mutation_scale=15), zorder=3)
    ax.text(mid_feed1, by_bot + bh/2 + 0.25, feed1_lbl, ha="center", va="bottom",
            fontsize=7.5, color=COLOR5, weight="bold", zorder=4,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#93C5FD", lw=0.8, alpha=0.95))
    
    # Left arrow from Box 5 to Box 6
    mid_feed2 = (bx5 + bx6 + bw) / 2
    ax.annotate("", xy=(bx6 + bw, by_bot + bh/2), xytext=(bx5, by_bot + bh/2),
                arrowprops=dict(arrowstyle="-|>", color=COLOR6, lw=2.2, ls="--", mutation_scale=15), zorder=3)
    ax.text(mid_feed2, by_bot + bh/2 + 0.25, feed2_lbl, ha="center", va="bottom",
            fontsize=7.5, color=COLOR6, weight="bold", zorder=4,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#FCA5A5", lw=0.8, alpha=0.95))
    
    # Up arrow from Box 6 to Box 2
    ax.annotate("", xy=(bx2, by_top + bh*0.25), xytext=(bx6 + bw * 0.75, by_bot + bh),
                arrowprops=dict(arrowstyle="-|>", color=COLOR6, lw=2.4,
                                connectionstyle="arc3,rad=-0.12", mutation_scale=16), zorder=3)
    
    # Feedback loop label badge positioned cleanly above Box 6
    arc_label_x = bx6 + bw/2
    arc_label_y = by_bot + bh + 0.38
    ax.text(arc_label_x, arc_label_y, up_lbl, ha="center", va="center",
            fontsize=7.6, color="#B91C1C", weight="bold", zorder=5,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#FEF2F2", edgecolor="#FCA5A5", lw=1.2, alpha=0.98))
            
    # Reference input into Box 5
    ax.annotate("", xy=(bx5 + bw/2, by_bot), xytext=(bx5 + bw/2, 0.08),
                arrowprops=dict(arrowstyle="-|>", color="#059669", lw=2.0, mutation_scale=15), zorder=3)
    ax.text(bx5 + bw/2, -0.06, ref_lbl, ha="center", va="top",
            fontsize=8.0, color="#059669", weight="bold", zorder=4,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#6EE7B7", lw=0.8, alpha=0.95))
    
    ax.set_title(diagram.title, fontsize=12.5, weight="bold", color=TEXT_DARK, pad=14)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return output_path


def render_function_plot(diagram: DiagramDefinition, output_path: Path) -> Path:
    """
    Renders an academic scientific/mathematical/engineering function plot with:
    1. Highly accurate domain physics curves (Relaxation Oscillators, Clippers, Diode IV, ECG, AP, Bode, etc.)
    2. Numbered markers on the curve matching operational phases
    3. A dedicated lower card panel for detailed multi-sentence explanations (Guaranteed ZERO collisions)
    """
    elements = diagram.elements
    n_elem = len(elements)
    has_cards = n_elem > 0
    
    title_upper = diagram.title.upper()
    diag_id_upper = diagram.diagram_id.upper()
    
    # Canvas sizing: 2-tier layout if cards present, single plot otherwise
    if has_cards:
        fig = plt.figure(figsize=(9.4, 6.2), dpi=150)
        gs = fig.add_gridspec(2, 1, height_ratios=[3.3, 1.7], hspace=0.34)
        ax = fig.add_subplot(gs[0])
        ax_cards = fig.add_subplot(gs[1])
        ax_cards.axis("off")
    else:
        fig, ax = plt.subplots(figsize=(9.2, 4.6), dpi=150)
        ax_cards = None

    markers = []  # List of tuples: (x, y, label, color, offset_x, offset_y)
    
    # -------------------------------------------------------------
    # 1. Relaxation Oscillator / Sawtooth / Shockley / UJT / 555
    # -------------------------------------------------------------
    if any(k in title_upper or k in diag_id_upper for k in ["RELAXATION", "SAWTOOTH", "SHOCKLEY", "OSCILLATOR", "RAMP", "UJT", "ASTABLE"]):
        Vs = 1.20     # Supply asymptote
        Vbo = 0.85    # Breakover threshold
        Vv = 0.15     # Valley / holding voltage
        tau_ch = 3.0  # Charging time constant
        # Exact analytic charging duration to reach Vbo precisely
        t_ch = tau_ch * np.log((Vs - Vv) / (Vs - Vbo))  # ~ 3.296
        t_dis = 0.35  # Rapid discharge duration
        T_period = t_ch + t_dis  # ~ 3.646
        
        t = np.linspace(0, 2.7 * T_period, 1000)
        
        def sawtooth_calc(t_val):
            phase = t_val % T_period
            if phase <= t_ch:
                return Vs - (Vs - Vv) * np.exp(-phase / tau_ch)
            else:
                dt = phase - t_ch
                return Vv + (Vbo - Vv) * np.exp(-dt / 0.075)
                
        vc = np.array([sawtooth_calc(ti) for ti in t])
        ax.plot(t, vc, color="#2563EB", lw=2.4, label=r"Capacitor Voltage $v_C(t)$", zorder=4)
        
        # Threshold lines
        ax.axhline(Vs, color="#94A3B8", ls=":", lw=1.2, label=r"DC Supply Asymptote $V_S$ ($1.2 V_{BO}$)")
        ax.axhline(Vbo, color="#DC2626", ls="--", lw=1.3, label=r"Shockley Breakover Voltage $V_{BO}$")
        ax.axhline(Vv, color="#0D9488", ls="--", lw=1.3, label=r"Holding / Valley Voltage $V_V$")
        
        # Shaded conduction zones
        ax.axvspan(0, t_ch, color="#EFF6FF", alpha=0.55, label="RC Charging Interval ($T_{ch}$)")
        ax.axvspan(t_ch, T_period, color="#FEF2F2", alpha=0.65, label="Rapid Diode Discharge ($T_{dis}$)")
        ax.axvspan(T_period, T_period + t_ch, color="#EFF6FF", alpha=0.55)
        ax.axvspan(T_period + t_ch, 2 * T_period, color="#FEF2F2", alpha=0.65)
        
        ax.set_ylim(0.0, 1.35)
        ax.set_xlim(0, 2.7 * T_period)
        ax.set_xlabel("Time ($t / RC$ normalized)", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Capacitor Voltage $v_C(t)$ (Normalized)", fontsize=9.5, weight="bold", color="#0F172A")
        
        # Physical markers on the first cycle
        markers = [
            (t_ch * 0.5, sawtooth_calc(t_ch * 0.5), "1", "#2563EB", 0, 18),
            (t_ch, Vbo, "2", "#DC2626", -16, 14),
            (t_ch + 0.12, 0.45, "3", "#7C3AED", 18, 5),
            (T_period, Vv, "4", "#0D9488", 14, -18)
        ]

    # -------------------------------------------------------------
    # 2. Clipper / Limiter / Clamper / Double Zener
    # -------------------------------------------------------------
    elif any(k in title_upper or k in diag_id_upper for k in ["CLIPPER", "LIMITER", "CLAMPER", "ZENER CLIPPER", "DOUBLE ZENER", "CLIPPING"]):
        wt = np.linspace(0, 4 * np.pi, 1000)
        Vm = 1.0
        Vclip = 0.55
        vi = Vm * np.sin(wt)
        vo = np.clip(vi, -Vclip, Vclip)
        
        ax.plot(wt, vi, color="#94A3B8", ls="--", lw=1.5, label=r"Input Sinusoid $v_i(\omega t) = V_m\sin(\omega t)$")
        ax.plot(wt, vo, color="#0D9488", lw=2.4, label=r"Clipped Output $v_o(\omega t)$", zorder=4)
        ax.fill_between(wt, 0, vo, color="#0D9488", alpha=0.12)
        
        ax.axhline(Vclip, color="#DC2626", ls="--", lw=1.2, label=r"$+V_{clip} = +(V_{Z2} + 0.7\mathrm{V})$")
        ax.axhline(-Vclip, color="#D97706", ls="--", lw=1.2, label=r"$-V_{clip} = -(V_{Z1} + 0.7\mathrm{V})$")
        ax.axhline(0, color="#64748B", ls=":", lw=0.8)
        
        ax.set_ylim(-1.3, 1.3)
        ax.set_xlim(0, 4 * np.pi)
        ax.set_xticks([0, np.pi, 2*np.pi, 3*np.pi, 4*np.pi])
        ax.set_xticklabels(["0", r"$\pi$", r"$2\pi$", r"$3\pi$", r"$4\pi$"], fontsize=9, weight="bold")
        ax.set_xlabel(r"Phase Angle $\omega t$ (radians)", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Voltage (V)", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (0.55, np.sin(0.55), "1", "#2563EB", 0, 16),
            (np.pi / 2, Vclip, "2", "#DC2626", 0, 16),
            (np.pi, 0.0, "3", "#7C3AED", 12, 14),
            (3 * np.pi / 2, -Vclip, "4", "#D97706", 0, -20)
        ]

    # -------------------------------------------------------------
    # 3. Diode I-V Characteristics & Temperature Shift
    # -------------------------------------------------------------
    elif any(k in title_upper or k in diag_id_upper for k in ["I-V", "IV ", "IV_", "CHARACTERISTIC", "DIODE MODEL", "TEMPERATURE SHIFT", "THERMAL SHIFT"]):
        v_fwd = np.linspace(0, 0.95, 400)
        i_fwd_25 = 0.0005 * (np.exp(v_fwd / 0.095) - 1.0)
        i_fwd_75 = 0.0015 * (np.exp((v_fwd + 0.10) / 0.095) - 1.0)
        
        v_rev = np.linspace(-4.5, 0, 400)
        i_rev_25 = -0.01 - 8.0 * np.maximum(0, (-v_rev - 3.5) / 0.5)**2
        i_rev_75 = -0.04 - 8.0 * np.maximum(0, (-v_rev - 3.4) / 0.5)**2
        
        v_all = np.concatenate([v_rev, v_fwd])
        i_25 = np.concatenate([i_rev_25, i_fwd_25])
        i_75 = np.concatenate([i_rev_75, i_fwd_75])
        
        is_temp = "TEMP" in title_upper or "TEMPERATURE" in title_upper
        
        ax.plot(v_all, i_25, color="#2563EB", lw=2.3, label="Room Temperature $T_1 = 25^{\\circ}\\mathrm{C}$", zorder=4)
        if is_temp:
            ax.plot(v_all, i_75, color="#D97706", ls="--", lw=2.0, label="Elevated Temp $T_2 = 75^{\\circ}\\mathrm{C}$ (Left Shift)", zorder=4)
            ax.annotate(r"$\Delta V = -2\,\mathrm{mV}/^{\circ}\mathrm{C}$",
                        xy=(0.60, 3.8), xytext=(0.42, 5.0),
                        arrowprops=dict(arrowstyle="->", color="#DC2626", lw=1.6),
                        fontsize=8.5, weight="bold", color="#DC2626", va="center")
        
        ax.axhline(0, color="#64748B", lw=0.9, ls="-")
        ax.axvline(0, color="#64748B", lw=0.9, ls="-")
        ax.axvline(0.70, color="#94A3B8", ls=":", lw=1.0, label=r"Knee Potential $V_\gamma \approx 0.7\mathrm{V}$")
        ax.axvline(-3.5, color="#DC2626", ls=":", lw=1.0, label=r"Zener Breakdown $V_Z \approx -3.5\mathrm{V}$")
        
        ax.set_xlim(-4.5, 1.0)
        ax.set_ylim(-7.5, 9.5)
        ax.set_xlabel("Diode Voltage $V_D$ (V)", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Diode Current $I_D$ (mA)", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (0.82, 6.0, "1", "#2563EB", -18, 10),
            (0.70, 0.8, "2", "#0D9488", 12, 14),
            (-1.5, -0.05, "3", "#7C3AED", 0, 16),
            (-3.7, -4.5, "4", "#DC2626", 18, 0)
        ]

    # -------------------------------------------------------------
    # 4. Action Potential (Neurobiology / Electrophysiology)
    # -------------------------------------------------------------
    elif any(k in title_upper or k in diag_id_upper for k in ["ACTION POTENTIAL", "NEURON", "DEPOLARIZATION", "HODGKIN", "NERNST", "NERVE"]):
        t = np.linspace(0, 6.0, 600)
        Vm = np.zeros_like(t)
        for i, ti in enumerate(t):
            if ti < 1.0:
                Vm[i] = -70.0
            elif ti < 1.4:
                Vm[i] = -70.0 + (ti - 1.0) * 37.5
            elif ti < 2.0:
                Vm[i] = -55.0 + 90.0 * np.sin((ti - 1.4) / 0.6 * (np.pi / 2))
            elif ti < 3.2:
                Vm[i] = +35.0 - 115.0 * ((ti - 2.0) / 1.2)**1.2
            elif ti < 4.2:
                Vm[i] = -80.0 + 10.0 * (ti - 3.2)
            else:
                Vm[i] = -70.0
                
        ax.plot(t, Vm, color="#2563EB", lw=2.4, label="Membrane Potential $V_m(t)$", zorder=4)
        ax.axhline(+35, color="#DC2626", ls="--", lw=1.1, label=r"Overshoot Peak ($+35\,\mathrm{mV}$)")
        ax.axhline(-55, color="#D97706", ls="--", lw=1.1, label=r"Threshold Potential ($-55\,\mathrm{mV}$)")
        ax.axhline(-70, color="#64748B", ls=":", lw=1.1, label=r"Resting Potential ($-70\,\mathrm{mV}$)")
        ax.axhline(-80, color="#7C3AED", ls=":", lw=1.0, label=r"Hyperpolarization ($-80\,\mathrm{mV}$)")
        
        ax.set_ylim(-92, 50)
        ax.set_xlim(0, 6.0)
        ax.set_xlabel("Time (milliseconds)", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Membrane Potential $V_m$ (mV)", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (0.6, -70.0, "1", "#64748B", 0, 16),
            (1.8, 15.0, "2", "#DC2626", -16, 12),
            (2.6, -20.0, "3", "#0D9488", 16, 10),
            (3.6, -78.0, "4", "#7C3AED", 0, -18)
        ]

    # -------------------------------------------------------------
    # 5. Physiological ECG (Cardiac Waveform)
    # -------------------------------------------------------------
    elif any(k in title_upper or k in diag_id_upper for k in ["ECG", "EKG", "CARDIAC", "HEART", "P-QRS-T", "WIGGERS"]):
        t = np.linspace(0, 1.2, 800)
        ecg = np.zeros_like(t)
        ecg += 0.22 * np.exp(-((t - 0.22) / 0.045)**2)
        ecg -= 0.15 * np.exp(-((t - 0.38) / 0.015)**2)
        ecg += 1.20 * np.exp(-((t - 0.42) / 0.025)**2)
        ecg -= 0.32 * np.exp(-((t - 0.46) / 0.020)**2)
        ecg += 0.38 * np.exp(-((t - 0.72) / 0.080)**2)
        
        ax.plot(t, ecg, color="#DC2626", lw=2.3, label="Lead II ECG Signal", zorder=4)
        ax.axhline(0, color="#64748B", ls=":", lw=0.9)
        
        ax.set_ylim(-0.5, 1.45)
        ax.set_xlim(0, 1.2)
        ax.set_xlabel("Time (seconds)", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Amplitude (mV)", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (0.22, 0.22, "1", "#2563EB", 0, 16),
            (0.42, 1.20, "2", "#DC2626", 0, 14),
            (0.55, 0.00, "3", "#0D9488", 12, 14),
            (0.72, 0.38, "4", "#7C3AED", 0, 16)
        ]

    # -------------------------------------------------------------
    # 6. Filter Frequency Response / Bode Magnitude
    # -------------------------------------------------------------
    elif any(k in title_upper or k in diag_id_upper for k in ["FREQUENCY RESPONSE", "BODE", "FILTER", "CUTOFF", "LOWPASS", "LOW-PASS", "HIGHPASS", "HIGH-PASS", "BANDPASS"]):
        f = np.linspace(0.01, 3.5, 500)
        H = 1.0 / np.sqrt(1.0 + f**6)
        
        ax.plot(f, H, color="#2563EB", lw=2.4, label=r"Normalized Gain $|H(f)| = \frac{1}{\sqrt{1 + (f/f_c)^{2n}}}$", zorder=4)
        ax.axhline(1.0 / np.sqrt(2), color="#DC2626", ls="--", lw=1.2, label=r"$-3\,\mathrm{dB}$ Cutoff Threshold ($0.707$)")
        ax.axvline(1.0, color="#D97706", ls="--", lw=1.2, label=r"Cutoff Frequency $f_c$")
        
        ax.axvspan(0.0, 1.0, color="#EFF6FF", alpha=0.5, label="Passband ($f < f_c$)")
        ax.axvspan(1.0, 3.5, color="#F8FAFC", alpha=0.7, label="Stopband / Attenuation")
        
        ax.set_ylim(0, 1.15)
        ax.set_xlim(0, 3.5)
        ax.set_xlabel("Normalized Frequency ($f / f_c$)", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Normalized Magnitude $|H(f)|$", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (0.4, 0.99, "1", "#2563EB", 0, 16),
            (1.0, 1.0/np.sqrt(2), "2", "#DC2626", 14, 14),
            (1.4, 0.35, "3", "#D97706", 16, 12),
            (2.4, 0.05, "4", "#7C3AED", 0, 16)
        ]

    # -------------------------------------------------------------
    # 7. Step Response / First-Order RC/RL Charging
    # -------------------------------------------------------------
    elif any(k in title_upper or k in diag_id_upper for k in ["STEP RESPONSE", "TRANSIENT", "CHARGING", "FIRST ORDER", "FIRST-ORDER", "TIME CONSTANT"]):
        t = np.linspace(0, 5.0, 500)
        y = 1.0 - np.exp(-t)
        
        ax.plot(t, y, color="#2563EB", lw=2.4, label=r"Transient Response $v(t) = V_0(1 - e^{-t/\tau})$", zorder=4)
        ax.axhline(1.0, color="#64748B", ls="--", lw=1.2, label=r"Steady-State Asymptote $V_0$ ($100\%$)")
        ax.axhline(0.632, color="#0D9488", ls=":", lw=1.1, label=r"$1\tau$ Threshold ($63.2\%$)")
        ax.axhline(0.950, color="#D97706", ls=":", lw=1.1, label=r"$3\tau$ Threshold ($95.0\%$)")
        
        ax.set_ylim(0, 1.18)
        ax.set_xlim(0, 5.0)
        ax.set_xlabel(r"Time Normalized to Time Constant ($t / \tau$)", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Normalized Response", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (1.0, 1.0 - np.exp(-1.0), "1", "#0D9488", 12, 14),
            (2.0, 1.0 - np.exp(-2.0), "2", "#2563EB", 12, 14),
            (3.0, 1.0 - np.exp(-3.0), "3", "#D97706", 12, 12),
            (4.8, 1.0 - np.exp(-4.8), "4", "#7C3AED", -14, 14)
        ]

    # -------------------------------------------------------------
    # 8. Exponential Decay / Discharge / Cooling / Half-Life
    # -------------------------------------------------------------
    elif any(k in title_upper or k in diag_id_upper for k in ["DECAY", "EXPONENTIAL", "DISCHARGE", "COOLING", "HALF-LIFE"]):
        t = np.linspace(0, 5.0, 500)
        y = np.exp(-t)
        
        ax.plot(t, y, color="#2563EB", lw=2.4, label=r"Exponential Decay $y(t) = y_0 e^{-t/\tau}$", zorder=4)
        t_half = np.log(2)
        ax.axvline(t_half, color="#DC2626", ls="--", lw=1.1, label=r"Half-Life $t_{1/2} \approx 0.693\tau$")
        ax.axhline(0.50, color="#DC2626", ls=":", lw=1.0)
        ax.axvline(1.0, color="#0D9488", ls="--", lw=1.1, label=r"Time Constant $\tau$ ($36.8\%$)")
        
        ax.set_ylim(0, 1.15)
        ax.set_xlim(0, 5.0)
        ax.set_xlabel(r"Time ($t / \tau$)", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Normalized Amplitude", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (0.2, np.exp(-0.2), "1", "#2563EB", 14, 12),
            (t_half, 0.50, "2", "#DC2626", 14, 14),
            (1.0, np.exp(-1.0), "3", "#0D9488", 14, 14),
            (3.0, np.exp(-3.0), "4", "#7C3AED", 14, 14)
        ]

    # -------------------------------------------------------------
    # 9. Sigmoid / Logistic / Enzyme Kinetics
    # -------------------------------------------------------------
    elif any(k in title_upper or k in diag_id_upper for k in ["SIGMOID", "LOGISTIC", "GROWTH", "SATURATION", "ENZYME", "MICHAELIS", "HILL"]):
        s = np.linspace(0, 10.0, 500)
        Vmax = 1.0
        Km = 2.0
        v = (Vmax * s) / (Km + s)
        
        ax.plot(s, v, color="#0D9488", lw=2.4, label=r"Reaction Velocity $v = \frac{V_{max}[S]}{K_m + [S]}$", zorder=4)
        ax.axhline(Vmax, color="#94A3B8", ls="--", lw=1.2, label=r"Asymptotic Velocity $V_{max}$")
        ax.axhline(0.5 * Vmax, color="#DC2626", ls=":", lw=1.1, label=r"Half-Maximal Rate $0.5 V_{max}$")
        ax.axvline(Km, color="#DC2626", ls="--", lw=1.1, label=r"Michaelis Constant $K_m = 2.0$")
        
        ax.set_ylim(0, 1.15)
        ax.set_xlim(0, 10.0)
        ax.set_xlabel("Substrate Concentration $[S]$", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Reaction Rate $v$", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (0.8, (Vmax * 0.8)/(Km + 0.8), "1", "#2563EB", 14, 12),
            (Km, 0.5 * Vmax, "2", "#DC2626", 14, 14),
            (5.0, (Vmax * 5.0)/(Km + 5.0), "3", "#D97706", 14, 12),
            (9.0, (Vmax * 9.0)/(Km + 9.0), "4", "#7C3AED", -14, 12)
        ]

    # -------------------------------------------------------------
    # 10. Economic Supply & Demand / Equilibrium
    # -------------------------------------------------------------
    elif any(k in title_upper or k in diag_id_upper for k in ["EQUILIBRIUM", "SUPPLY", "DEMAND", "MARKET"]):
        q = np.linspace(1, 10, 500)
        demand = 11 - q
        supply = 1 + q
        ax.plot(q, demand, color="#DC2626", lw=2.2, label="Demand Curve ($D$)", zorder=4)
        ax.plot(q, supply, color="#2563EB", lw=2.2, label="Supply Curve ($S$)", zorder=4)
        
        eq_q, eq_p = 5.0, 6.0
        ax.plot(eq_q, eq_p, "o", color="#059669", markersize=8, zorder=6)
        ax.axvline(eq_q, color="#64748B", ls=":", lw=1.0)
        ax.axhline(eq_p, color="#64748B", ls=":", lw=1.0)
        
        ax.set_xlim(0, 11)
        ax.set_ylim(0, 12)
        ax.set_xlabel("Quantity ($Q$)", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Price ($P$)", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (2.5, 8.5, "1", "#DC2626", 14, 12),
            (eq_q, eq_p, "2", "#059669", 14, 14),
            (7.5, 8.5, "3", "#2563EB", 14, 12),
            (7.5, 3.5, "4", "#D97706", 14, -14)
        ]

    # -------------------------------------------------------------
    # 11. Damped Oscillation / Underdamped Dynamic Response
    # -------------------------------------------------------------
    elif any(k in title_upper or k in diag_id_upper for k in ["DAMPED", "HARMONIC", "VIBRATION", "UNDERDAMPED"]):
        t = np.linspace(0, 4 * np.pi, 600)
        y = np.exp(-0.25 * t) * np.cos(t)
        ax.plot(t, y, color="#2563EB", lw=2.2, label=r"Dynamic Response $f(t) = e^{-\zeta\omega_n t}\cos(\omega_d t)$", zorder=4)
        ax.plot(t, np.exp(-0.25 * t), "--", color="#94A3B8", lw=1.1, label="Decay Envelope")
        ax.plot(t, -np.exp(-0.25 * t), "--", color="#94A3B8", lw=1.1)
        ax.axhline(0, color="#64748B", lw=0.8, ls=":")
        
        ax.set_xlabel("Time / Phase ($t$)", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Amplitude / Response", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (0.0, 1.0, "1", "#2563EB", 14, 10),
            (np.pi, -np.exp(-0.25*np.pi), "2", "#DC2626", 14, -14),
            (2 * np.pi, np.exp(-0.5*np.pi), "3", "#0D9488", 14, 12),
            (3 * np.pi, -np.exp(-0.75*np.pi), "4", "#7C3AED", 14, -12)
        ]

    # -------------------------------------------------------------
    # 12. Fallback: Clean Harmonic Waveform
    # -------------------------------------------------------------
    else:
        t = np.linspace(0, 4 * np.pi, 600)
        y = np.sin(t) + 0.3 * np.sin(3 * t)
        ax.plot(t, y, color="#2563EB", lw=2.2, label="Signal Waveform", zorder=4)
        ax.axhline(0, color="#64748B", lw=0.8, ls=":")
        ax.set_xlabel("Phase / Time", fontsize=9.5, weight="bold", color="#0F172A")
        ax.set_ylabel("Magnitude", fontsize=9.5, weight="bold", color="#0F172A")
        
        markers = [
            (np.pi/2, 0.7, "1", "#2563EB", 0, 16),
            (np.pi, 0.0, "2", "#0D9488", 12, 14),
            (3*np.pi/2, -0.7, "3", "#DC2626", 0, -18),
            (2*np.pi, 0.0, "4", "#7C3AED", 12, 14)
        ]

    # Common styling for the plot canvas
    ax.grid(True, linestyle=":", color="#E2E8F0", alpha=0.85)
    ax.legend(loc="upper right", fontsize=8.2, framealpha=0.95, edgecolor=BORDER_COLOR)
    ax.set_title(f"Figure: {diagram.title}", fontsize=11.5, weight="bold", color=TEXT_DARK, pad=10)

    # -------------------------------------------------------------
    # Numbered Badges on Curve (Linked to cards below)
    # -------------------------------------------------------------
    for idx, m in enumerate(markers[:n_elem]):
        mx, my, badge_num, mcolor, ox, oy = m
        ax.plot(mx, my, "o", color=mcolor, markersize=7, zorder=6)
        ax.annotate(
            f"#{badge_num}",
            xy=(mx, my),
            xytext=(ox, oy),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="-|>", color=mcolor, lw=1.2),
            bbox=dict(boxstyle="circle,pad=0.22", facecolor=mcolor, edgecolor="white", lw=1.2),
            fontsize=7.5, color="white", weight="bold", ha="center", va="center",
            zorder=7
        )

    # -------------------------------------------------------------
    # Lower Structured Cards Panel (GUARANTEED ZERO OVERLAP & FULL HEADROOM)
    # -------------------------------------------------------------
    if has_cards and ax_cards is not None:
        ax_cards.set_xlim(0, 9.4)
        ax_cards.set_ylim(-0.10, 2.05)
        
        display_count = min(n_elem, 4)
        left_margin = 0.35
        right_margin = 0.35
        total_w = 9.4 - left_margin - right_margin
        gap = 0.22 if display_count > 1 else 0.0
        card_w = (total_w - (display_count - 1) * gap) / display_count
        card_h = 1.82
        card_y = 0.04
        
        for i in range(display_count):
            elem = elements[i]
            color = BOX_PALETTE[i % len(BOX_PALETTE)]
            card_x = left_margin + i * (card_w + gap)
            
            # Card background
            card = patches.FancyBboxPatch(
                (card_x, card_y), card_w, card_h,
                boxstyle="round,pad=0.02,rounding_size=0.12",
                linewidth=1.6, edgecolor=color, facecolor=BG_CARD
            )
            ax_cards.add_patch(card)
            
            # Header Badge (#1, #2, etc.)
            badge_h = 0.24
            badge_w = 0.65
            badge_x = card_x + (card_w - badge_w) / 2
            badge_y = card_y + card_h - badge_h - 0.06
            badge = patches.FancyBboxPatch(
                (badge_x, badge_y), badge_w, badge_h,
                boxstyle="round,pad=0.02,rounding_size=0.08",
                linewidth=0, facecolor=color
            )
            ax_cards.add_patch(badge)
            ax_cards.text(card_x + card_w / 2, badge_y + badge_h / 2,
                          f"#{i+1}", color="white", weight="bold",
                          fontsize=7.8, ha="center", va="center")
            
            # Label (Card Title)
            title_width = max(14, int(card_w * 8.5))
            wrapped_title = wrap_text(elem.label, title_width)
            title_lines = len(wrapped_title.split("\n"))
            title_top_y = badge_y - 0.07
            ax_cards.text(card_x + card_w / 2, title_top_y,
                          wrapped_title, color=TEXT_DARK, weight="bold",
                          fontsize=7.8, ha="center", va="top")
            
            # Separator line
            sep_y = title_top_y - (title_lines * 0.15) - 0.04
            ax_cards.plot([card_x + 0.15, card_x + card_w - 0.15], [sep_y, sep_y],
                          color="#E2E8F0", lw=0.7)
            
            # Description text (safely bounded with generous font sizing)
            if elem.description:
                desc_width = max(16, int(card_w * 12.0))
                wrapped_desc = wrap_text(elem.description, desc_width)
                ax_cards.text(card_x + card_w / 2, sep_y - 0.06,
                              wrapped_desc, color=TEXT_MUTED,
                              fontsize=6.8, ha="center", va="top", linespacing=1.15)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return output_path

def render_rectifier_waveforms(diagram: DiagramDefinition, output_path: Path) -> Path:
    """
    Renders synchronized electrical engineering waveforms for half-wave or full-wave bridge rectifier:
    1. Input AC Voltage v_s(wt)
    2. Output Load Voltage v_o(wt)
    3. Diode Voltage v_d(wt)
    """
    title_upper = diagram.title.upper()
    diag_id_upper = diagram.diagram_id.upper()
    is_full_wave = any(k in title_upper or k in diag_id_upper for k in ["FULL", "BRIDGE", "FULL_WAVE", "FULL-WAVE"])

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8.8, 6.0), sharex=True, dpi=150)
    
    # 2 full AC cycles: 0 to 4*pi
    wt = np.linspace(0, 4 * np.pi, 1000)
    Vm = 1.0
    vs = Vm * np.sin(wt)
    
    COLOR_VS = "#2563EB"  # Royal Blue
    COLOR_VO = "#0D9488"  # Teal
    COLOR_VD = "#DC2626"  # Crimson
    COLOR_GRID = "#E2E8F0"

    if is_full_wave:
        vo = np.abs(vs)
        vd = np.where(vs > 0, -vs, 0.0)  # Reverse voltage across non-conducting pair
        vdc_val = 2 * Vm / np.pi
        vdc_label = r"$V_{dc} = \frac{2V_m}{\pi} \approx 0.637 V_m$"
        c_lbl_pos = "Diodes D1, D2 ON"
        c_lbl_neg = "Diodes D3, D4 ON"
        c_lbl_pos_color = "#0D9488"
        c_lbl_neg_color = "#7C3AED"
        vd_label = r"$v_{D3,D4}(\omega t)$ (Idle Diode Reverse Voltage)"
    else:
        vo = np.where(vs > 0, vs, 0.0)
        vd = np.where(vs < 0, vs, 0.0)
        vdc_val = Vm / np.pi
        vdc_label = r"$V_{dc} = \frac{V_m}{\pi} \approx 0.318 V_m$"
        c_lbl_pos = "Diode ON"
        c_lbl_neg = "Diode OFF"
        c_lbl_pos_color = "#0D9488"
        c_lbl_neg_color = "#DC2626"
        vd_label = r"$v_d(\omega t)$ (Diode Reverse Voltage)"
    
    # Subplot 1: Input Supply Voltage v_s
    ax1.plot(wt, vs, color=COLOR_VS, lw=2.2, label=r"$v_s(\omega t) = V_m \sin(\omega t)$")
    ax1.axhline(0, color="#64748B", lw=0.9, ls="--")
    ax1.set_ylabel(r"$v_s(\omega t)$", fontsize=10, weight="bold", color=COLOR_VS)
    ax1.set_ylim(-1.3, 1.55)
    ax1.set_yticks([-1.0, 0, 1.0])
    ax1.set_yticklabels([r"$-V_m$", "0", r"$+V_m$"], fontsize=8.5)
    ax1.grid(True, ls=":", color=COLOR_GRID, alpha=0.8)
    ax1.legend(loc="lower left", fontsize=8.0, framealpha=0.92)
    ax1.set_title(f"Figure: {diagram.title}", fontsize=11, weight="bold", color="#0F172A", pad=10)
    
    # Conduction Interval highlights (safely positioned at top without legend collision)
    ax1.text(np.pi/2, 1.25, c_lbl_pos, ha="center", fontsize=8, color=c_lbl_pos_color, weight="bold")
    ax1.text(3*np.pi/2, 1.25, c_lbl_neg, ha="center", fontsize=8, color=c_lbl_neg_color, weight="bold")
    ax1.text(5*np.pi/2, 1.25, c_lbl_pos, ha="center", fontsize=8, color=c_lbl_pos_color, weight="bold")
    ax1.text(7*np.pi/2, 1.25, c_lbl_neg, ha="center", fontsize=8, color=c_lbl_neg_color, weight="bold")
    
    # Subplot 2: Output Voltage v_o
    ax2.plot(wt, vo, color=COLOR_VO, lw=2.2, label=r"$v_o(\omega t)$ (Load Voltage)")
    ax2.fill_between(wt, 0, vo, color=COLOR_VO, alpha=0.15)
    ax2.axhline(vdc_val, color="#D97706", lw=1.2, ls="--", label=vdc_label)
    ax2.axhline(0, color="#64748B", lw=0.9, ls="--")
    ax2.set_ylabel(r"$v_o(\omega t)$", fontsize=10, weight="bold", color=COLOR_VO)
    ax2.set_ylim(-0.3, 1.4)
    ax2.set_yticks([0, vdc_val, 1.0])
    ax2.set_yticklabels(["0", r"$V_{dc}$", r"$+V_m$"], fontsize=8.5)
    ax2.grid(True, ls=":", color=COLOR_GRID, alpha=0.8)
    ax2.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
    
    # Subplot 3: Diode Voltage v_d
    ax3.plot(wt, vd, color=COLOR_VD, lw=2.2, label=vd_label)
    ax3.fill_between(wt, vd, 0, color=COLOR_VD, alpha=0.15)
    ax3.axhline(0, color="#64748B", lw=0.9, ls="--")
    ax3.set_ylabel(r"$v_d(\omega t)$", fontsize=10, weight="bold", color=COLOR_VD)
    ax3.set_ylim(-1.4, 0.5)
    ax3.set_yticks([-1.0, 0])
    ax3.set_yticklabels([r"$-V_m$ (PIV)", "0"], fontsize=8.5)
    ax3.grid(True, ls=":", color=COLOR_GRID, alpha=0.8)
    ax3.legend(loc="lower right", fontsize=8.5, framealpha=0.9)
    
    x_ticks = [0, np.pi, 2*np.pi, 3*np.pi, 4*np.pi]
    x_labels = ["0", r"$\pi$", r"$2\pi$", r"$3\pi$", r"$4\pi$"]
    ax3.set_xticks(x_ticks)
    ax3.set_xticklabels(x_labels, fontsize=9.5, weight="bold")
    ax3.set_xlabel(r"Angle $\omega t$ (radians)", fontsize=10, weight="bold", color="#0F172A")
    
    for t_val in x_ticks:
        for ax in [ax1, ax2, ax3]:
            ax.axvline(t_val, color="#94A3B8", lw=0.8, ls=":")
            
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return output_path

def generate_diagram(diagram: DiagramDefinition, output_dir: Optional[Path] = None) -> Path:
    """Universal academic diagram dispatcher supporting all disciplines."""
    diagram = validate_and_normalize_diagram(diagram)
    target_dir = output_dir or ASSETS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    clean_id = "".join(c for c in diagram.diagram_id if c.isalnum() or c in ("_", "-"))
    output_path = target_dir / f"diagram_{clean_id}.png"
    
    dtype = diagram.diagram_type.upper()
    title_upper = diagram.title.upper()
    diag_id_upper = diagram.diagram_id.upper()
    
    # 1. Specialized rectifier waveforms (only when specifically dealing with rectifier waveforms/voltages)
    is_rectifier_waveform = (
        ("RECTIFIER" in dtype or "RECTIFIER" in title_upper or "RECTIFIER" in diag_id_upper) and
        any(k in dtype or k in title_upper or k in diag_id_upper for k in ["WAVEFORM", "SIGNAL", "VOLTAGE", "CURVE", "SUITE"]) and
        not any(k in title_upper for k in ["CONDUCTION PATH", "PATHWAY", "FLOWCHART", "STEP"])
    )
    if is_rectifier_waveform:
        return render_rectifier_waveforms(diagram, output_path)
        
    # 2. Chronological Timelines (History, clinical stages, project phases)
    if "TIMELINE" in dtype or "TIMELINE" in title_upper or "CHRONOLOG" in title_upper:
        return render_timeline(diagram, output_path)
        
    # 3. Concept Maps & Taxonomies (Biology, Law, Classification trees)
    if "CONCEPT" in dtype or "TAXONOMY" in title_upper or "HIERARCHY" in title_upper:
        return render_concept_map(diagram, output_path)
        
    # 4. Multi-Component System Block Diagrams & Closed Loops (CS, Engineering, Biology cascades)
    if any(k in dtype for k in ["BLOCK_DIAGRAM", "CLOSED_LOOP", "ARCHITECTURE", "SYSTEM_BLOCK"]) or \
       (("SYSTEM" in title_upper or "ARCHITECTURE" in title_upper) and len(diagram.elements) >= 4 and not any(k in title_upper for k in ["WAVEFORM", "OSCILLATOR", "CLIPPER"])):
        return render_system_block_diagram(diagram, output_path)
        
    # 5. Scientific Curves & Function Plots (Waveforms, Oscillators, Clippers, Diode IV, ECG, AP, Bode, etc.)
    if any(k in dtype for k in ["WAVEFORM", "SIGNAL", "FUNCTION", "PLOT", "CURVE"]) or \
       any(k in title_upper for k in ["WAVEFORM", "SIGNAL", "OSCILLATOR", "CLIPPER", "SAWTOOTH", "RESPONSE CURVE", "EQUILIBRIUM", "DECAY", "ACTION POTENTIAL", "BODE"]):
        return render_function_plot(diagram, output_path)
        
    # 6. Circular Cycles & Lifecycles
    if "CYCLE" in dtype or "LIFECYCLE" in title_upper:
        return render_process_cycle(diagram, output_path)
        
    # 7. Comparison Bar Charts
    if "BAR" in dtype or "COMPARISON" in dtype or "BENCHMARK" in title_upper:
        return render_comparison_bar(diagram, output_path)
        
    # 8. Default: Sequential Flowchart / Process Pipeline
    return render_flowchart(diagram, output_path)

def render_formula_image(latex_expr: str, output_path: Path) -> Optional[Path]:
    """
    Renders a LaTeX math expression into a high-resolution, transparent-background PNG.
    Falls back gracefully if LaTeX syntax has unsupported tokens.
    """
    try:
        clean_latex = latex_expr.strip()
        if not clean_latex:
            return None
            
        # Repair unescaped JSON LaTeX tokens
        clean_latex = clean_latex.replace('\x09ext', r'\text').replace('\x09imes', r'\times')
        clean_latex = clean_latex.replace('\x09heta', r'\theta').replace('\x09hickapprox', r'\approx')
        clean_latex = clean_latex.replace('\x09o', r'\to').replace('\x09au', r'\tau')
        clean_latex = clean_latex.replace('\x0c', 'f').replace('\x08', 'b')

        clean_latex = re.sub(r'(?<!\\)frac\{', r'\\frac{', clean_latex)
        clean_latex = re.sub(r'(?<!\\)text\{', r'\\text{', clean_latex)
        clean_latex = re.sub(r'(?<!\\)sqrt\{', r'\\sqrt{', clean_latex)
        clean_latex = re.sub(r'hickapprox', r'\\approx', clean_latex)
        clean_latex = clean_latex.replace(r'\thickapprox', r'\approx')
        
        # Repair degree notations for matplotlib mathtext
        clean_latex = re.sub(r'\^\{\\?circ\}\s*([cCfFkK])', r'^{\\circ}\1', clean_latex)
        clean_latex = re.sub(r'\^\\?circ\s*([cCfFkK])', r'^{\\circ}\1', clean_latex)
        clean_latex = re.sub(r'\\degree', r'^{\\circ}', clean_latex)
        
        if not clean_latex.startswith("$"):
            clean_latex = f"${clean_latex}$"
            
        fig = plt.figure(figsize=(7.0, 1.2), dpi=300)
        fig.patch.set_alpha(0.0)
        
        fig.text(
            0.5, 0.5, clean_latex,
            fontsize=16, ha='center', va='center',
            color='#0F172A'
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, bbox_inches='tight', transparent=True, pad_inches=0.1)
        plt.close(fig)
        return output_path
    except Exception:
        plt.close('all')
        return None
