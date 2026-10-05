import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math
import textwrap
from pathlib import Path
from models import DiagramDefinition, DiagramElement

# Color Palette
PRIMARY_COLOR = "#1E40AF"     # Royal Blue
SECONDARY_COLOR = "#0D9488"   # Teal
ACCENT_COLOR = "#D97706"      # Warm Amber
PURPLE_COLOR = "#7C3AED"      # Purple
BG_CARD = "#F8FAFC"           # Soft Slate
TEXT_DARK = "#0F172A"         # Slate 900
TEXT_MUTED = "#475569"        # Slate 600
BORDER_COLOR = "#CBD5E1"      # Slate 300
BOX_PALETTE = ["#2563EB", "#0D9488", "#7C3AED", "#D97706", "#DB2777", "#059669", "#4F46E5"]

def wrap_text(text: str, width: int = 18) -> str:
    if not text:
        return ""
    return "\n".join(textwrap.wrap(text, width=width))

def render_concept_map(diagram: DiagramDefinition, output_path: Path) -> Path:
    """Renders a central hub-and-spoke concept map or taxonomy tree."""
    elements = diagram.elements
    n = max(len(elements), 1)
    
    fig, ax = plt.subplots(figsize=(8.8, 5.2), dpi=250)
    ax.set_xlim(-4.8, 4.8)
    ax.set_ylim(-3.2, 3.2)
    ax.axis("off")
    
    # Central Hub
    hub_w, hub_h = 2.4, 1.2
    hub_card = patches.FancyBboxPatch(
        (-hub_w/2, -hub_h/2), hub_w, hub_h,
        boxstyle="round,pad=0.1,rounding_size=0.25",
        linewidth=2.2, edgecolor=PRIMARY_COLOR, facecolor="#EFF6FF"
    )
    ax.add_patch(hub_card)
    ax.text(0, 0.1, wrap_text(diagram.title, 16), color=PRIMARY_COLOR, weight="bold",
            fontsize=10.0, ha="center", va="center")
    ax.text(0, -0.35, "Core Concept", color="#3B82F6", fontsize=7.5, weight="semibold", ha="center", va="center")
    
    # Outer Nodes in ellipse
    rx, ry = 3.3, 2.1
    for i, elem in enumerate(elements):
        angle = 2 * math.pi * i / n
        x = rx * math.cos(angle)
        y = ry * math.sin(angle)
        color = BOX_PALETTE[i % len(BOX_PALETTE)]
        
        # Line from hub to node
        ax.plot([0, x * 0.78], [0, y * 0.78], color="#CBD5E1", lw=1.5, ls="--", zorder=1)
        
        # Node Card
        nw, nh = 1.9, 0.95
        node_card = patches.FancyBboxPatch(
            (x - nw/2, y - nh/2), nw, nh,
            boxstyle="round,pad=0.08,rounding_size=0.18",
            linewidth=1.8, edgecolor=color, facecolor=BG_CARD, zorder=3
        )
        ax.add_patch(node_card)
        ax.text(x, y + 0.1, wrap_text(elem.label, 14), color=TEXT_DARK, weight="bold",
                fontsize=8.5, ha="center", va="center", zorder=4)
        if elem.description:
            ax.text(x, y - 0.25, wrap_text(elem.description, 16), color=TEXT_MUTED,
                    fontsize=7.0, ha="center", va="center", zorder=4)
                    
    ax.set_title(diagram.title, fontsize=12, weight="bold", color=TEXT_DARK, pad=12)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", dpi=250)
    plt.close(fig)
    return output_path

def render_timeline(diagram: DiagramDefinition, output_path: Path) -> Path:
    """Renders a chronological timeline with alternating milestones along a central axis."""
    elements = diagram.elements
    n = max(len(elements), 1)
    
    fig_w = max(8.5, n * 2.2 + 1.0)
    fig, ax = plt.subplots(figsize=(fig_w, 4.6), dpi=250)
    ax.set_xlim(0, n * 2.2 + 0.8)
    ax.set_ylim(-2.6, 2.6)
    ax.axis("off")
    
    # Central Timeline Axis
    axis_y = 0.0
    ax.plot([0.5, n * 2.2 + 0.3], [axis_y, axis_y], color="#94A3B8", lw=3.0, zorder=1)
    # Right arrow cap
    ax.annotate("", xy=(n * 2.2 + 0.5, axis_y), xytext=(n * 2.2 + 0.1, axis_y),
                arrowprops=dict(arrowstyle="-|>", color="#94A3B8", lw=3.0, mutation_scale=18))
    
    for i, elem in enumerate(elements):
        x = 1.0 + i * 2.2
        is_top = (i % 2 == 0)
        color = BOX_PALETTE[i % len(BOX_PALETTE)]
        
        # Milestone dot on timeline axis
        dot = plt.Circle((x, axis_y), 0.16, color=color, ec="white", lw=2.0, zorder=4)
        ax.add_patch(dot)
        
        # Stem connecting dot to card
        stem_y = 1.0 if is_top else -1.0
        ax.plot([x, x], [axis_y, stem_y], color=color, lw=1.8, ls=":", zorder=2)
        
        # Card
        cw, ch = 1.9, 1.1
        cy = stem_y if is_top else stem_y - ch
        card = patches.FancyBboxPatch(
            (x - cw/2, cy), cw, ch,
            boxstyle="round,pad=0.08,rounding_size=0.18",
            linewidth=1.6, edgecolor=color, facecolor=BG_CARD, zorder=3
        )
        ax.add_patch(card)
        
        # Card badge & text
        badge_y = cy + ch - 0.22
        ax.text(x, badge_y, f"Stage {i+1}", color=color, weight="bold", fontsize=8.0, ha="center", va="center")
        ax.text(x, cy + ch/2 - 0.05, wrap_text(elem.label, 14), color=TEXT_DARK, weight="bold", fontsize=8.5, ha="center", va="center")
        if elem.description:
            ax.text(x, cy + 0.20, wrap_text(elem.description, 16), color=TEXT_MUTED, fontsize=7.0, ha="center", va="center")
            
    ax.set_title(diagram.title, fontsize=12, weight="bold", color=TEXT_DARK, pad=12)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", dpi=250)
    plt.close(fig)
    return output_path

# Quick test
diag1 = DiagramDefinition(
    diagram_id="test_concept",
    title="Taxonomy of Machine Learning Paradigms",
    diagram_type="CONCEPT_MAP",
    elements=[
        DiagramElement(label="Supervised Learning", description="Labeled training datasets"),
        DiagramElement(label="Unsupervised Learning", description="Clustering & pattern discovery"),
        DiagramElement(label="Reinforcement Learning", description="Reward-driven policy optimization"),
        DiagramElement(label="Self-Supervised Learning", description="Pretext tasks & representation")
    ],
    caption="Major algorithmic paradigms in modern artificial intelligence."
)
render_concept_map(diag1, Path("test_concept_out.png"))

diag2 = DiagramDefinition(
    diagram_id="test_timeline",
    title="Stages of Clinical Drug Development",
    diagram_type="TIMELINE",
    elements=[
        DiagramElement(label="Preclinical Research", description="In vitro & animal safety"),
        DiagramElement(label="Phase I Trial", description="Healthy safety & dosing"),
        DiagramElement(label="Phase II Trial", description="Patient efficacy & side effects"),
        DiagramElement(label="Phase III Trial", description="Large-scale multicenter testing"),
        DiagramElement(label="FDA Approval", description="Regulatory review & marketing")
    ],
    caption="Sequential timeline of pharmaceutical translation and verification."
)
render_timeline(diag2, Path("test_timeline_out.png"))
print("Generated universal test diagrams successfully.")
