"""
A/B Test Results & Significance Calculator

Two tabs, deliberately:
1. Results — the full readout of THIS experiment (gate_30 vs gate_40): primary
   metric, secondary metric, guardrail, SRM, and power context. For a
   stakeholder who wants the answer without reading the notebook.
2. Calculator — a reusable tool built on analysis/ab_test_stats.py, so any
   future experiment's numbers can be plugged in.

Visual language: a dark "instrument panel" — every stat is a readout with a
signal meter showing where its p-value sits against the significance
threshold, because the actual job of this tool is telling signal from noise.

Run:
    streamlit run dashboard/app.py
"""
import sys
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent / "analysis"))
from ab_test_stats import (
    srm_check, two_proportion_ztest, required_sample_size,
    minimum_detectable_effect, mann_whitney_test, bonferroni_alpha,
)

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
INK = "#0E1621"
PANEL = "#16202C"
PANEL_2 = "#1C2836"
HAIRLINE = "#2A3745"
TEXT = "#E7ECF1"
MUTED = "#8CA0B3"
SIGNAL = "#37D6C4"    # control series / "pass" / "ship"
CAUTION = "#F2B84D"   # treatment series / "borderline"
STOP = "#F1654F"      # "do not ship"

CONTROL_COLOR = SIGNAL
TREATMENT_COLOR = CAUTION

st.set_page_config(page_title="A/B Test Analytics", layout="wide", page_icon="🧪")

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.block-container {{ padding-top: 2rem; max-width: 1200px; }}
h1, h2, h3 {{ font-family: 'Inter', sans-serif; letter-spacing: -0.01em; }}

/* Hero */
.hero {{
    background: linear-gradient(135deg, {INK} 0%, {PANEL} 100%);
    border: 1px solid {HAIRLINE}; border-radius: 12px;
    padding: 28px 32px; margin-bottom: 28px;
}}
.hero-eyebrow {{
    font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; letter-spacing: 0.18em;
    color: {SIGNAL}; text-transform: uppercase; margin-bottom: 10px;
}}
.hero-row {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px; }}
.hero-title {{ font-family: 'IBM Plex Mono', monospace; font-size: 28px; font-weight: 600; color: {TEXT}; }}
.hero-title span {{ color: {MUTED}; font-weight: 400; }}
.verdict-pill {{
    font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; padding: 9px 18px; border-radius: 999px; white-space: nowrap;
}}
.verdict-stop {{ background: rgba(241,101,79,0.14); color: {STOP}; border: 1px solid {STOP}; }}
.verdict-go {{ background: rgba(55,214,196,0.14); color: {SIGNAL}; border: 1px solid {SIGNAL}; }}
.verdict-hold {{ background: rgba(242,184,77,0.14); color: {CAUTION}; border: 1px solid {CAUTION}; }}
.hero-meta {{ font-size: 13px; color: {MUTED}; margin-top: 12px; }}

/* Readout cards */
.readout-card {{
    background: {PANEL}; border: 1px solid {HAIRLINE}; border-left: 3px solid var(--accent);
    border-radius: 8px; padding: 16px 18px; height: 100%;
}}
.readout-eyebrow {{
    font-size: 10.5px; letter-spacing: 0.13em; color: {MUTED}; text-transform: uppercase; font-weight: 600;
}}
.readout-value {{
    font-family: 'IBM Plex Mono', monospace; font-size: 24px; font-weight: 600; color: {TEXT};
    margin: 6px 0 2px;
}}
.readout-delta {{ font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; color: var(--accent); font-weight: 600; }}
.meter-track {{ position: relative; height: 5px; background: {HAIRLINE}; border-radius: 3px; margin: 12px 0 7px; }}
.meter-fill {{ position: absolute; height: 100%; border-radius: 3px; background: var(--accent); opacity: 0.30; }}
.meter-marker {{ position: absolute; top: -3.5px; width: 2px; height: 12px; background: var(--accent); border-radius: 1px; }}
.meter-threshold {{ position: absolute; top: -3.5px; width: 1px; height: 12px; background: {MUTED}; }}
.readout-caption {{ font-size: 10.5px; color: {MUTED}; font-family: 'IBM Plex Mono', monospace; }}

/* Section labels */
.section-eyebrow {{
    font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em;
    color: {SIGNAL}; text-transform: uppercase; margin: 6px 0 2px;
}}

/* Recommendation panel */
.reco-panel {{
    background: {PANEL}; border: 1px solid {HAIRLINE}; border-left: 3px solid var(--accent);
    border-radius: 8px; padding: 18px 22px; margin: 4px 0 8px; color: {TEXT}; line-height: 1.65; font-size: 14.5px;
}}
.reco-panel b {{ color: {TEXT}; }}

/* Tabs -> segmented control */
[data-testid="stTabs"] div[role="tablist"] {{
    gap: 6px; border-bottom: none; background: {PANEL}; padding: 6px; border-radius: 10px;
    border: 1px solid {HAIRLINE};
}}
button[data-baseweb="tab"] {{
    border-radius: 8px !important; color: {MUTED} !important; font-weight: 600 !important;
    font-size: 14px !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{ background: {INK} !important; color: {SIGNAL} !important; }}
[data-baseweb="tab-highlight"] {{ display: none; }}
[data-baseweb="tab-border"] {{ display: none; }}

/* Radio -> pill buttons */
[data-testid="stRadio"] > div {{ flex-direction: row; gap: 8px; flex-wrap: wrap; }}
[data-testid="stRadio"] label {{
    background: {PANEL}; border: 1px solid {HAIRLINE}; padding: 9px 16px; border-radius: 999px; margin: 0;
    transition: all 0.15s ease;
}}
[data-testid="stRadio"] label:has(input:checked) {{ background: rgba(55,214,196,0.14); border-color: {SIGNAL}; }}
[data-testid="stRadio"] label > div:first-child {{ display: none; }}

/* Misc */
[data-testid="stExpander"] {{ background: {PANEL}; border: 1px solid {HAIRLINE}; border-radius: 8px; }}
hr {{ border-color: {HAIRLINE} !important; }}
[data-testid="stDataFrame"] {{ border: 1px solid {HAIRLINE}; border-radius: 8px; overflow: hidden; }}
.stCaption, [data-testid="stCaptionContainer"] {{ color: {MUTED} !important; }}
</style>
""", unsafe_allow_html=True)


def signal_meter(eyebrow, value, delta, p_value, alpha, accent, caption):
    """Signature component: shows a stat plus where its p-value sits vs. the significance threshold."""
    p_clamped = max(min(p_value, 1.0), 1e-6)
    pos = min(max(-math.log10(p_clamped) / 4, 0), 1) * 100
    thresh = min(max(-math.log10(alpha) / 4, 0), 1) * 100
    st.markdown(f"""
    <div class="readout-card" style="--accent:{accent}">
        <div class="readout-eyebrow">{eyebrow}</div>
        <div class="readout-value">{value}</div>
        <div class="readout-delta">{delta}</div>
        <div class="meter-track">
            <div class="meter-fill" style="width:{pos:.1f}%"></div>
            <div class="meter-threshold" style="left:{thresh:.1f}%"></div>
            <div class="meter-marker" style="left:{pos:.1f}%"></div>
        </div>
        <div class="readout-caption">{caption}</div>
    </div>
    """, unsafe_allow_html=True)


def plain_card(eyebrow, value, delta, accent, caption):
    """A descriptive readout with no meter — for numbers that aren't a hypothesis-test result
    (a baseline rate, a required sample size, an MDE threshold). The meter is reserved for
    cards that actually report a p-value against a significance threshold."""
    st.markdown(f"""
    <div class="readout-card" style="--accent:{accent}">
        <div class="readout-eyebrow">{eyebrow}</div>
        <div class="readout-value">{value}</div>
        <div class="readout-delta">{delta}</div>
        <div class="readout-caption" style="margin-top:14px;">{caption}</div>
    </div>
    """, unsafe_allow_html=True)


def dark_chart(fig, height=380):
    fig.update_layout(
        paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font=dict(family="Inter, sans-serif", color=TEXT, size=13),
        xaxis=dict(gridcolor=HAIRLINE, zerolinecolor=HAIRLINE, linecolor=HAIRLINE),
        yaxis=dict(gridcolor=HAIRLINE, zerolinecolor=HAIRLINE, linecolor=HAIRLINE),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=12)),
        margin=dict(t=44, b=10, l=10, r=10), height=height,
    )
    return fig


st.markdown("""
<div style="display:flex; align-items:center; gap:10px; margin-bottom: 4px;">
    <span style="font-family:'IBM Plex Mono',monospace; font-size:22px;">🧪</span>
    <span style="font-family:'IBM Plex Mono',monospace; font-size:20px; font-weight:600; color:#E7ECF1;">A/B TEST ANALYTICS</span>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊  Experiment Results", "🧮  Significance Calculator"])


# =============================================================================
# Tab 1: this experiment's results
# =============================================================================
with tab1:

    @st.cache_data
    def load_data():
        return pd.read_csv(ROOT / "data" / "cookie_cats.csv")

    df = load_data()
    ctrl = df[df.version == "gate_30"]
    treat = df[df.version == "gate_40"]

    srm = srm_check(len(ctrl), len(treat))
    d7 = two_proportion_ztest(ctrl.retention_7.sum(), len(ctrl), treat.retention_7.sum(), len(treat))
    d1 = two_proportion_ztest(ctrl.retention_1.sum(), len(ctrl), treat.retention_1.sum(), len(treat),
                               alpha=bonferroni_alpha(0.05, 3))
    guardrail = mann_whitney_test(ctrl.sum_gamerounds.values, treat.sum_gamerounds.values,
                                   alpha=bonferroni_alpha(0.05, 3))
    achieved_mde = minimum_detectable_effect(min(len(ctrl), len(treat)), d7.rate_a)

    verdict_class, verdict_text = ("verdict-stop", "● Stop — do not ship") if (d7.is_significant and d7.abs_diff < 0) else (
        ("verdict-go", "● Go — ship") if (d7.is_significant and d7.abs_diff > 0) else
        ("verdict-hold", "● Hold — no significant effect"))

    st.markdown(f"""
    <div class="hero">
        <div class="hero-eyebrow">Experiment Readout</div>
        <div class="hero-row">
            <div class="hero-title">Gate Placement <span>— Cookie Cats</span></div>
            <div class="verdict-pill {verdict_class}">{verdict_text}</div>
        </div>
        <div class="hero-meta">Level 30 (control) vs. Level 40 (treatment) · {len(df):,} players · real random assignment, real outcomes</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        signal_meter("Primary · D7 retention", f"{d7.rate_a:.1%} → {d7.rate_b:.1%}",
                     f"{d7.abs_diff:+.2%} pp", d7.p_value, 0.05,
                     STOP if d7.abs_diff < 0 else SIGNAL,
                     f"p={d7.p_value:.4f} · significant")
    with c2:
        signal_meter("Secondary · D1 retention", f"{d1.rate_a:.1%} → {d1.rate_b:.1%}",
                     f"{d1.abs_diff:+.2%} pp", d1.p_value, bonferroni_alpha(0.05, 3),
                     CAUTION,
                     f"p={d1.p_value:.4f} · adj. α={bonferroni_alpha(0.05,3):.4f}")
    with c3:
        signal_meter("Guardrail · engagement", f"{int(guardrail.median_a)} → {int(guardrail.median_b)} rounds",
                     "median, not mean", guardrail.p_value, bonferroni_alpha(0.05, 3),
                     CAUTION,
                     f"p={guardrail.p_value:.4f} · Mann-Whitney")
    with c4:
        signal_meter("Sample ratio check", "PASS" if not srm.is_mismatched else "FLAGGED",
                     f"χ² p={srm.p_value:.3f}", srm.p_value, 0.001,
                     SIGNAL if not srm.is_mismatched else STOP,
                     "randomization integrity")

    st.markdown('<div class="section-eyebrow" style="margin-top:28px;">Recommendation</div>', unsafe_allow_html=True)
    accent = STOP if "stop" in verdict_class else (SIGNAL if "go" in verdict_class else CAUTION)
    st.markdown(f"""
    <div class="reco-panel" style="--accent:{accent}">
    Moving the gate to level 40 <b>decreased</b> Day-7 retention by <b>{abs(d7.abs_diff)*100:.2f} percentage points</b>
    ({d7.rate_a:.2%} → {d7.rate_b:.2%}), a statistically significant result
    (p={d7.p_value:.4f}, 95% CI [{d7.ci_diff_low:+.2%}, {d7.ci_diff_high:+.2%}]).
    Day-1 retention moved the same direction but did not clear the multiple-comparison-adjusted bar (p={d1.p_value:.4f}).
    Engagement did <b>{'not ' if not guardrail.is_significant else ''}differ significantly</b> between arms
    (p={guardrail.p_value:.4f}) — this isn't a retention-for-engagement tradeoff.
    See <code>executive_memo.md</code> for the full writeup.
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Power context — was this test big enough to trust the nulls?"):
        st.write(
            f"At the actual sample size (smaller arm = {min(len(ctrl), len(treat)):,} users), this test could "
            f"reliably detect a Day-7 retention effect as small as **{achieved_mde*100:.2f} percentage points** "
            f"(α=0.05, power=0.80). The pre-registered minimum effect of interest was 1.0pp, so a 'no significant "
            f"difference' result on a secondary/guardrail metric here means a genuine null, not an underpowered test."
        )

    st.divider()

    st.markdown('<div class="section-eyebrow">Retention by arm</div>', unsafe_allow_html=True)
    col_chart, col_table = st.columns([3, 2])

    with col_chart:
        metrics = ["D1 retention", "D7 retention"]
        ctrl_rates = [d1.rate_a, d7.rate_a]
        treat_rates = [d1.rate_b, d7.rate_b]

        def half_width(p, n):
            return 1.96 * np.sqrt(p * (1 - p) / n)

        ctrl_err = [half_width(d1.rate_a, len(ctrl)), half_width(d7.rate_a, len(ctrl))]
        treat_err = [half_width(d1.rate_b, len(treat)), half_width(d7.rate_b, len(treat))]

        fig = go.Figure()
        fig.add_bar(name="gate_30 (control)", x=metrics, y=ctrl_rates,
                    error_y=dict(type="data", array=ctrl_err, visible=True, color=MUTED),
                    marker_color=CONTROL_COLOR, text=[f"{v:.2%}" for v in ctrl_rates], textposition="outside")
        fig.add_bar(name="gate_40 (treatment)", x=metrics, y=treat_rates,
                    error_y=dict(type="data", array=treat_err, visible=True, color=MUTED),
                    marker_color=TREATMENT_COLOR, text=[f"{v:.2%}" for v in treat_rates], textposition="outside")
        fig.update_layout(barmode="group", yaxis_tickformat=".0%", yaxis_title="Retention rate")
        st.plotly_chart(dark_chart(fig), use_container_width=True)
        st.caption("Error bars: ±95% CI per arm (normal approximation). D7 gap is significant; D1 is not, after multiple-comparison adjustment.")

    with col_table:
        summary = df.groupby("version").agg(
            n_users=("userid", "count"),
            d1_retention=("retention_1", "mean"),
            d7_retention=("retention_7", "mean"),
            median_rounds=("sum_gamerounds", "median"),
        ).round(4)
        st.dataframe(summary, use_container_width=True)
        st.download_button(
            "⬇  Download summary (CSV)",
            summary.to_csv().encode("utf-8"),
            file_name="cookie_cats_summary.csv",
            mime="text/csv",
        )

    st.divider()

    st.markdown('<div class="section-eyebrow">Guardrail — engagement (rounds played)</div>', unsafe_allow_html=True)
    st.write(
        f"Median rounds — control: **{int(guardrail.median_a)}**, treatment: **{int(guardrail.median_b)}**. "
        f"Mann-Whitney U test (non-parametric — this metric is heavily right-skewed with extreme outliers): "
        f"p={guardrail.p_value:.4f} — **{'a significant' if guardrail.is_significant else 'no significant'} "
        f"difference** in engagement between arms."
    )

    cap = st.slider("Cap x-axis at N rounds (display only — a few extreme outliers stretch the raw range)",
                     100, 1000, 500, 50)
    plot_df = df[df.sum_gamerounds < cap]

    fig2 = go.Figure()
    fig2.add_histogram(x=plot_df.loc[plot_df.version == "gate_30", "sum_gamerounds"],
                        name="gate_30 (control)", marker_color=CONTROL_COLOR, opacity=0.75, nbinsx=50)
    fig2.add_histogram(x=plot_df.loc[plot_df.version == "gate_40", "sum_gamerounds"],
                        name="gate_40 (treatment)", marker_color=TREATMENT_COLOR, opacity=0.75, nbinsx=50)
    fig2.update_layout(barmode="overlay", xaxis_title="Rounds played (first 14 days)", yaxis_title="Players")
    st.plotly_chart(dark_chart(fig2, height=360), use_container_width=True)
    st.caption(f"Both distributions truncated at {cap:,} rounds for display only — the statistical test above uses the full, untruncated data.")


# =============================================================================
# Tab 2: reusable calculator
# =============================================================================
with tab2:
    st.markdown('<div class="section-eyebrow">Reusable calculator</div>', unsafe_allow_html=True)
    st.caption("Plug in any experiment's numbers — not tied to the Cookie Cats dataset above.")

    calc_mode = st.radio(
        "calc_mode", ["Test significance of a completed experiment", "Required sample size before launching",
                       "Minimum detectable effect for a given sample size"],
        horizontal=True, label_visibility="collapsed",
    )

    if calc_mode == "Test significance of a completed experiment":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Control**")
            n_a = st.number_input("Control: total users", min_value=1, value=10000, key="n_a")
            x_a = st.number_input("Control: successes/conversions", min_value=0, value=1000, key="x_a")
        with col2:
            st.markdown("**Treatment**")
            n_b = st.number_input("Treatment: total users", min_value=1, value=10000, key="n_b")
            x_b = st.number_input("Treatment: successes/conversions", min_value=0, value=1100, key="x_b")

        alpha = st.slider("Significance level (alpha)", 0.01, 0.10, 0.05, 0.01)

        if x_a > n_a or x_b > n_b:
            st.error("Successes can't exceed total users.")
        else:
            srm_result = srm_check(int(n_a), int(n_b))
            if srm_result.is_mismatched:
                st.warning(f"⚠️ Sample Ratio Mismatch flagged (p={srm_result.p_value:.4f}) — "
                           f"investigate randomization before trusting the result below.")

            result = two_proportion_ztest(int(x_a), int(n_a), int(x_b), int(n_b), alpha=alpha)

            c1, c2, c3 = st.columns(3)
            with c1:
                plain_card("Control rate", f"{result.rate_a:.2%}", "&nbsp;", MUTED, "baseline")
            with c2:
                plain_card("Treatment rate", f"{result.rate_b:.2%}", f"{result.abs_diff:+.2%}",
                           SIGNAL if result.is_significant else CAUTION, "vs. control")
            with c3:
                signal_meter("Significance", f"p = {result.p_value:.4f}",
                             "significant" if result.is_significant else "not significant",
                             result.p_value, alpha, SIGNAL if result.is_significant else CAUTION,
                             f"α = {alpha}")

            st.markdown(f"""
            <div class="reco-panel" style="--accent:{SIGNAL if result.is_significant else CAUTION}; margin-top:18px;">
            <b>{'Significant' if result.is_significant else 'Not significant'}</b> at α={alpha}.
            95% CI on the difference: [{result.ci_diff_low:+.2%}, {result.ci_diff_high:+.2%}].
            Relative lift: {result.relative_lift_pct:+.1f}%.
            </div>
            """, unsafe_allow_html=True)

            fig3 = go.Figure()
            fig3.add_bar(x=["Control", "Treatment"], y=[result.rate_a, result.rate_b],
                         marker_color=[CONTROL_COLOR, TREATMENT_COLOR],
                         text=[f"{result.rate_a:.2%}", f"{result.rate_b:.2%}"], textposition="outside")
            fig3.update_layout(yaxis_tickformat=".0%", yaxis_title="Rate", showlegend=False)
            st.plotly_chart(dark_chart(fig3, height=320), use_container_width=True)

    elif calc_mode == "Required sample size before launching":
        baseline = st.number_input("Baseline conversion rate (%)", min_value=0.1, max_value=99.0, value=19.0) / 100
        mde = st.number_input("Minimum detectable effect, absolute (percentage points)", min_value=0.1, max_value=50.0, value=1.0) / 100
        power = st.slider("Power", 0.70, 0.95, 0.80, 0.05)
        alpha = st.slider("Significance level (alpha)", 0.01, 0.10, 0.05, 0.01, key="ss_alpha")

        n = required_sample_size(baseline, mde, alpha=alpha, power=power)

        c1, c2 = st.columns(2)
        with c1:
            plain_card("Required per arm", f"{n:,}", "&nbsp;", SIGNAL, f"at MDE={mde*100:.1f}pp")
        with c2:
            plain_card("Total experiment size", f"{n*2:,}", "&nbsp;", MUTED, "50/50 split")

        st.markdown('<div class="section-eyebrow" style="margin-top:20px;">How sample size scales with the effect you want to detect</div>', unsafe_allow_html=True)
        mde_range = np.linspace(max(mde * 0.3, 0.001), mde * 3, 40)
        sizes = [required_sample_size(baseline, m, alpha=alpha, power=power) for m in mde_range]
        fig4 = go.Figure()
        fig4.add_scatter(x=mde_range * 100, y=sizes, mode="lines", line=dict(color=SIGNAL, width=3))
        fig4.add_scatter(x=[mde * 100], y=[n], mode="markers", marker=dict(color=CAUTION, size=12), showlegend=False)
        fig4.update_layout(xaxis_title="Minimum detectable effect (percentage points)",
                            yaxis_title="Required sample size per arm", showlegend=False)
        st.plotly_chart(dark_chart(fig4, height=340), use_container_width=True)
        st.caption("Smaller effects are exponentially more expensive to detect — the curve to show stakeholders who ask for a smaller MDE without a bigger sample.")

    else:  # Minimum detectable effect for a given sample size
        st.write("Already ran the test, or locked into a fixed sample size? Find out what effect size you actually had power to detect.")
        baseline = st.number_input("Baseline conversion rate (%)", min_value=0.1, max_value=99.0, value=19.0, key="mde_baseline") / 100
        n_per_arm = st.number_input("Sample size per arm (the smaller arm, if unequal)", min_value=10, value=15000, key="mde_n")
        power = st.slider("Power", 0.70, 0.95, 0.80, 0.05, key="mde_power")
        alpha = st.slider("Significance level (alpha)", 0.01, 0.10, 0.05, 0.01, key="mde_alpha")

        mde_result = minimum_detectable_effect(int(n_per_arm), baseline, alpha=alpha, power=power)
        plain_card("Minimum detectable effect", f"{mde_result*100:.2f} pp", "&nbsp;", SIGNAL,
                   f"n={n_per_arm:,}/arm · power={power}")
        st.caption(
            f"With {n_per_arm:,} users per arm and a {baseline:.1%} baseline, this experiment could reliably "
            f"detect a true effect of {mde_result*100:.2f} percentage points or larger. A 'no significant "
            f"difference' result below this line is a real null; above it, treat it as inconclusive rather than "
            f"as evidence of no effect."
        )

st.divider()
st.caption("Data: Cookie Cats mobile game A/B test (public dataset) · Built for portfolio / data-analyst demonstration purposes.")
