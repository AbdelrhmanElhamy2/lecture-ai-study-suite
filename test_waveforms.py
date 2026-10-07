import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from models import DiagramDefinition, DiagramElement

def render_rectifier_waveforms(diagram: DiagramDefinition, output_path: Path) -> Path:
    """
    Renders synchronized electrical engineering waveforms for half-wave rectifier:
    1. Input AC Voltage v_s(wt)
    2. Output Load Voltage v_o(wt)
    3. Diode Voltage v_d(wt)
    """
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8.5, 5.8), sharex=True, dpi=250)
    
    # 2 full AC cycles: 0 to 4*pi
    wt = np.linspace(0, 4 * np.pi, 1000)
    Vm = 1.0
    vs = Vm * np.sin(wt)
    vo = np.where(vs > 0, vs, 0.0)
    vd = np.where(vs < 0, vs, 0.0)
    
    # Theme colors
    COLOR_VS = "#2563EB" # Royal Blue
    COLOR_VO = "#0D9488" # Teal
    COLOR_VD = "#DC2626" # Crimson
    COLOR_GRID = "#E2E8F0"
    
    # Subplot 1: Input Supply Voltage v_s
    ax1.plot(wt, vs, color=COLOR_VS, lw=2.2, label=r"$v_s(\omega t) = V_m \sin(\omega t)$")
    ax1.axhline(0, color="#64748B", lw=0.9, ls="--")
    ax1.set_ylabel(r"$v_s(\omega t)$", fontsize=10, weight="bold", color=COLOR_VS)
    ax1.set_ylim(-1.3, 1.4)
    ax1.set_yticks([-1.0, 0, 1.0])
    ax1.set_yticklabels([r"$-V_m$", "0", r"$+V_m$"], fontsize=8.5)
    ax1.grid(True, ls=":", color=COLOR_GRID, alpha=0.8)
    ax1.legend(loc="lower left", fontsize=8.0, framealpha=0.92)
    ax1.set_title(f"Figure: {diagram.title}", fontsize=11, weight="bold", color="#0F172A", pad=10)
    
    # Interval highlights on Subplot 1
    ax1.text(np.pi/2, 1.15, "Diode ON", ha="center", fontsize=8, color="#0D9488", weight="bold")
    ax1.text(3*np.pi/2, 1.15, "Diode OFF", ha="center", fontsize=8, color="#DC2626", weight="bold")
    ax1.text(5*np.pi/2, 1.15, "Diode ON", ha="center", fontsize=8, color="#0D9488", weight="bold")
    ax1.text(7*np.pi/2, 1.15, "Diode OFF", ha="center", fontsize=8, color="#DC2626", weight="bold")
    
    # Subplot 2: Output Voltage v_o
    ax2.plot(wt, vo, color=COLOR_VO, lw=2.2, label=r"$v_o(\omega t)$ (Load Voltage)")
    ax2.fill_between(wt, 0, vo, color=COLOR_VO, alpha=0.15)
    # Average DC level line
    ax2.axhline(Vm / np.pi, color="#D97706", lw=1.2, ls="--", label=r"$V_{dc} = \frac{V_m}{\pi} \approx 0.318 V_m$")
    ax2.axhline(0, color="#64748B", lw=0.9, ls="--")
    ax2.set_ylabel(r"$v_o(\omega t)$", fontsize=10, weight="bold", color=COLOR_VO)
    ax2.set_ylim(-0.4, 1.4)
    ax2.set_yticks([0, Vm/np.pi, 1.0])
    ax2.set_yticklabels(["0", r"$V_{dc}$", r"$+V_m$"], fontsize=8.5)
    ax2.grid(True, ls=":", color=COLOR_GRID, alpha=0.8)
    ax2.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
    
    # Subplot 3: Diode Voltage v_d
    ax3.plot(wt, vd, color=COLOR_VD, lw=2.2, label=r"$v_d(\omega t)$ (Diode Voltage)")
    ax3.fill_between(wt, vd, 0, color=COLOR_VD, alpha=0.15)
    ax3.axhline(0, color="#64748B", lw=0.9, ls="--")
    ax3.set_ylabel(r"$v_d(\omega t)$", fontsize=10, weight="bold", color=COLOR_VD)
    ax3.set_ylim(-1.4, 0.5)
    ax3.set_yticks([-1.0, 0])
    ax3.set_yticklabels([r"$-V_m$ (PIV)", "0"], fontsize=8.5)
    ax3.grid(True, ls=":", color=COLOR_GRID, alpha=0.8)
    ax3.legend(loc="lower right", fontsize=8.5, framealpha=0.9)
    
    # X-axis formatting: wt in terms of pi
    x_ticks = [0, np.pi, 2*np.pi, 3*np.pi, 4*np.pi]
    x_labels = ["0", r"$\pi$", r"$2\pi$", r"$3\pi$", r"$4\pi$"]
    ax3.set_xticks(x_ticks)
    ax3.set_xticklabels(x_labels, fontsize=9.5, weight="bold")
    ax3.set_xlabel(r"Angle $\omega t$ (radians)", fontsize=10, weight="bold", color="#0F172A")
    
    # Draw vertical alignment dashed markers across all 3 subplots
    for t_val in x_ticks:
        for ax in [ax1, ax2, ax3]:
            ax.axvline(t_val, color="#94A3B8", lw=0.8, ls=":")
            
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", dpi=250)
    plt.close(fig)
    print(f"Generated waveform plot at: {output_path}")
    return output_path

diag = DiagramDefinition(
    diagram_id="diag_halfwave_waveforms",
    title="Synchronized Waveforms for Half-Wave Rectifier with Resistive Load",
    diagram_type="WAVEFORM",
    elements=[],
    caption="Synchronized waveforms showing input AC, rectified load voltage, and diode reverse blocking voltage."
)

render_rectifier_waveforms(diag, Path("test_rectifier_waveforms.png"))
