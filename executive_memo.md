# Experiment Readout: Progress Gate Placement (Level 30 → Level 40)

**To:** Product & Game Design
**From:** Data Analytics
**Re:** Should we move the first progress gate from level 30 to level 40?

## Recommendation: Do not move the gate to level 40.

## Why

We tested moving the gate on 90,189 real players, split ~50/50 between the
current placement (level 30) and the proposed placement (level 40).

- **Day-7 retention dropped by 0.82 percentage points** (19.02% → 18.20%) in
  the level-40 group. This is statistically significant (p = 0.0016) and holds
  up after excluding outlier accounts.
- Day-1 retention moved the same direction but wasn't statistically significant
  on its own — the effect is a genuine longer-horizon retention story, not
  noise in an early metric.
- Engagement (rounds played) did **not** differ significantly between groups —
  so this isn't a "retention loss offset by engagement gain" tradeoff. It's a
  clean loss.

## The counterintuitive part (worth flagging to design)

The working theory going in was that a later gate would keep players in the
core loop longer before any friction, and would therefore help retention. The
data says the opposite. Our read: by level 40, players have invested
meaningfully more time before hitting the first real friction point, and the
eventual stop may feel more costly or discouraging than an earlier, lower-stakes
pause at level 30. We can't prove that mechanism from this data alone — it's a
hypothesis for design to weigh, not a fact this test establishes.

## Caveats (so this isn't oversold)

- **Practical vs. statistical significance:** the pre-registered minimum
  effect we cared about was 1.0 percentage point; the observed effect (0.82pp)
  is real but slightly under that bar. This is a genuine effect, not a huge one.
- **Minor sample ratio imbalance:** control/treatment split was 44,700 /
  45,489 (~0.9% off 50/50). This passes the standard SRM threshold used by
  experimentation platforms (p < 0.001) but the raw p-value (0.0086) is close
  enough to be worth a note to the team owning randomization — treat this
  result with slightly less certainty than a perfectly balanced test would
  warrant, not as invalidated.
- This test only measures the gate's effect in isolation. It doesn't tell us
  whether a different mechanism at level 40 (e.g. a softer gate, or a reward
  instead of a wait) would produce a different result.

## Bottom line

Keep the gate at level 30. The data doesn't support the "later gate helps
retention" hypothesis, and the observed effect runs the other way with no
offsetting engagement benefit.
