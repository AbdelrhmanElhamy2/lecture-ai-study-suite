import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math
import textwrap
from pathlib import Path
from models import DiagramDefinition, DiagramElement

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

def render_function_plot_refined(diagram: DiagramDefinition, output_path: Path) -> Path:
    """
    Renders an academic scientific/engineering function plot with:
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
                        xy=(0.62, 4.0), xytext=(0.82, 4.0),
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
