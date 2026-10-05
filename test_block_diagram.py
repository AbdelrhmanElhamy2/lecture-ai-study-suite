import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from models import DiagramDefinition, DiagramElement

def test_system_block_diagram():
    diag = DiagramDefinition(
        diagram_id="diag_system_block_diagram",
        title="Block Diagram of a Complete Power Electronic System",
        diagram_type="FLOWCHART",
        elements=[
            DiagramElement(label="Power Source (AC/DC)", description="Utility grid, battery, or renewable source"),
            DiagramElement(label="Power Converter", description="Solid-state semiconductor switches"),
            DiagramElement(label="Electrical Load", description="Motor drive, battery bank, or grid load"),
            DiagramElement(label="Sensors & Feedback", description="Voltage, current, and speed transducers"),
            DiagramElement(label="Controller & DSP", description="Compares reference and generates PWM control"),
            DiagramElement(label="Gate Driver Stage", description="Signal isolation and gate charge amplification")
        ],
        caption="Forward high-power flow path and closed-loop feedback regulation loop."
    )
    
    fig, ax = plt.subplots(figsize=(9.2, 5.2), dpi=250)
    ax.set_xlim(0, 10.0)
    ax.set_ylim(0, 6.0)
    ax.axis("off")
    
    # Palette
    POWER_COLOR = "#1E40AF"     # Deep Blue
    CONV_COLOR = "#0D9488"      # Teal
    LOAD_COLOR = "#7C3AED"      # Purple
    SENSE_COLOR = "#D97706"     # Amber
    CTRL_COLOR = "#2563EB"      # Blue
    GATE_COLOR = "#DC2626"      # Crimson
    BG_BOX = "#F8FAFC"
    TEXT_DARK = "#0F172A"
    TEXT_MUTED = "#475569"
    
    # Top Row: Forward Power Flow (y = 3.6 to 5.0)
    # Box 1: Power Source
    bx1, by1, bw, bh = 0.6, 3.6, 2.5, 1.4
    card1 = patches.FancyBboxPatch((bx1, by1), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                   linewidth=2.0, edgecolor=POWER_COLOR, facecolor=BG_BOX)
    ax.add_patch(card1)
    ax.text(bx1 + bw/2, by1 + bh - 0.35, "Power Source\n(AC / DC)", ha="center", va="center",
            fontsize=10.5, weight="bold", color=TEXT_DARK)
    ax.text(bx1 + bw/2, by1 + 0.35, "Grid, Battery, Solar", ha="center", va="center",
            fontsize=8.5, color=TEXT_MUTED)
            
    # Box 2: Power Converter
    bx2, by2 = 3.75, 3.6
    card2 = patches.FancyBboxPatch((bx2, by2), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                   linewidth=2.4, edgecolor=CONV_COLOR, facecolor="#F0FDFA")
    ax.add_patch(card2)
    ax.text(bx2 + bw/2, by2 + bh - 0.35, "Power Converter\n(Semiconductor Stage)", ha="center", va="center",
            fontsize=10.5, weight="bold", color="#0F766E")
    ax.text(bx2 + bw/2, by2 + 0.35, "Switches (Diodes, IGBTs)", ha="center", va="center",
            fontsize=8.5, color=TEXT_MUTED)
            
    # Box 3: Load
    bx3, by3 = 6.9, 3.6
    card3 = patches.FancyBboxPatch((bx3, by3), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                   linewidth=2.0, edgecolor=LOAD_COLOR, facecolor=BG_BOX)
    ax.add_patch(card3)
    ax.text(bx3 + bw/2, by3 + bh - 0.35, "Electrical Load\n(Application)", ha="center", va="center",
            fontsize=10.5, weight="bold", color=TEXT_DARK)
    ax.text(bx3 + bw/2, by3 + 0.35, "Motor, Grid, Actuator", ha="center", va="center",
            fontsize=8.5, color=TEXT_MUTED)
            
    # Power Flow Arrows (Thick Blue)
    ax.annotate("", xy=(bx2, by1 + bh/2), xytext=(bx1 + bw, by1 + bh/2),
                arrowprops=dict(arrowstyle="-|>", color=POWER_COLOR, lw=3.0, mutation_scale=18))
    ax.text((bx1 + bw + bx2)/2, by1 + bh/2 + 0.22, "Input Power", ha="center", fontsize=8.0, weight="bold", color=POWER_COLOR)
    
    ax.annotate("", xy=(bx3, by2 + bh/2), xytext=(bx2 + bw, by2 + bh/2),
                arrowprops=dict(arrowstyle="-|>", color=POWER_COLOR, lw=3.0, mutation_scale=18))
    ax.text((bx2 + bw + bx3)/2, by2 + bh/2 + 0.22, "Processed Power", ha="center", fontsize=8.0, weight="bold", color=POWER_COLOR)
    
    # Bottom Row: Feedback Control Loop (y = 0.8 to 2.2)
    # Box 4: Sensors (directly below Load)
    bx4, by4 = 6.9, 0.8
    card4 = patches.FancyBboxPatch((bx4, by4), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                   linewidth=1.8, edgecolor=SENSE_COLOR, facecolor=BG_BOX)
    ax.add_patch(card4)
    ax.text(bx4 + bw/2, by4 + bh - 0.35, "Sensors & Measurement", ha="center", va="center",
            fontsize=10.0, weight="bold", color=TEXT_DARK)
    ax.text(bx4 + bw/2, by4 + 0.35, "Voltage & Current Transducers", ha="center", va="center",
            fontsize=8.0, color=TEXT_MUTED)
            
    # Box 5: Controller & Reference
    bx5, by5 = 3.75, 0.8
    card5 = patches.FancyBboxPatch((bx5, by5), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                   linewidth=1.8, edgecolor=CTRL_COLOR, facecolor=BG_BOX)
    ax.add_patch(card5)
    ax.text(bx5 + bw/2, by5 + bh - 0.35, "Controller & Reference", ha="center", va="center",
            fontsize=10.0, weight="bold", color=TEXT_DARK)
    ax.text(bx5 + bw/2, by5 + 0.35, "PID / Feedback Algorithm", ha="center", va="center",
            fontsize=8.0, color=TEXT_MUTED)
            
    # Box 6: Gate Driver Stage
    bx6, by6 = 0.6, 0.8
    card6 = patches.FancyBboxPatch((bx6, by6), bw, bh, boxstyle="round,pad=0.08,rounding_size=0.18",
                                   linewidth=1.8, edgecolor=GATE_COLOR, facecolor=BG_BOX)
    ax.add_patch(card6)
    ax.text(bx6 + bw/2, by6 + bh - 0.35, "Gate Drive Circuit", ha="center", va="center",
            fontsize=10.0, weight="bold", color=TEXT_DARK)
    ax.text(bx6 + bw/2, by6 + 0.35, "Isolation & Gate Pulses", ha="center", va="center",
            fontsize=8.0, color=TEXT_MUTED)
            
    # Feedback Arrows (Dashed / Colored)
    # Down arrow from Load to Sensors
    ax.annotate("", xy=(bx4 + bw/2, by4 + bh), xytext=(bx3 + bw/2, by3),
                arrowprops=dict(arrowstyle="-|>", color=SENSE_COLOR, lw=2.0, ls="--", mutation_scale=15))
    ax.text(bx4 + bw/2 + 0.15, (by3 + by4 + bh)/2, "Measurement", ha="left", va="center", fontsize=7.5, color=SENSE_COLOR, weight="bold")
    
    # Left arrow from Sensors to Controller
    ax.annotate("", xy=(bx5 + bw, by5 + bh/2), xytext=(bx4, by4 + bh/2),
                arrowprops=dict(arrowstyle="-|>", color=CTRL_COLOR, lw=2.0, ls="--", mutation_scale=15))
    ax.text((bx4 + bx5 + bw)/2, by5 + bh/2 + 0.2, "Feedback Signals", ha="center", fontsize=7.5, color=CTRL_COLOR, weight="bold")
    
    # Left arrow from Controller to Gate Driver
    ax.annotate("", xy=(bx6 + bw, by6 + bh/2), xytext=(bx5, by5 + bh/2),
                arrowprops=dict(arrowstyle="-|>", color=GATE_COLOR, lw=2.0, ls="--", mutation_scale=15))
    ax.text((bx5 + bx6 + bw)/2, by6 + bh/2 + 0.2, "Control / PWM", ha="center", fontsize=7.5, color=GATE_COLOR, weight="bold")
    
    # Up arrow from Gate Driver to Power Converter
    ax.annotate("", xy=(bx2 + 0.5, by2), xytext=(bx6 + bw/2, by6 + bh),
                arrowprops=dict(arrowstyle="-|>", color=GATE_COLOR, lw=2.2,
                                connectionstyle="arc3,rad=-0.15", mutation_scale=16))
    ax.text(bx6 + bw/2 + 0.8, (by2 + by6 + bh)/2, "Gate Switching\nCommands", ha="center", va="center",
            fontsize=7.5, color=GATE_COLOR, weight="bold")
            
    # Reference input into Controller
    ax.annotate("", xy=(bx5 + bw/2, by5), xytext=(bx5 + bw/2, 0.2),
                arrowprops=dict(arrowstyle="-|>", color="#059669", lw=1.8, mutation_scale=14))
    ax.text(bx5 + bw/2, 0.1, "Reference Input ($V_{ref}, I_{ref}$)", ha="center", va="top", fontsize=8.0, color="#059669", weight="bold")
    
    ax.set_title(diag.title, fontsize=12.5, weight="bold", color=TEXT_DARK, pad=12)
    plt.tight_layout()
    out = Path("test_system_block_diagram.png")
    plt.savefig(out, bbox_inches="tight", dpi=250)
    plt.close(fig)
    print(f"Rendered test diagram: {out}")

test_system_block_diagram()
