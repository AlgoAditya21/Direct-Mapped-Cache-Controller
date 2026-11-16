#!/usr/bin/env python3
"""VCD -> waveform PNG renderer for the cache demo.

Parses cache.vcd, extracts the signals that tell the miss -> refill -> hit
story over the first few CPU accesses, and draws a clean, readable digital
waveform. No deps beyond matplotlib.
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

VCD = sys.argv[1] if len(sys.argv) > 1 else "cache.vcd"
OUT = sys.argv[2] if len(sys.argv) > 2 else "docs/waveform.png"

# id -> (name, width). ids found from the VCD header.
SIGS = {
    "0": ("clk", 1),
    "2": ("cpu_req", 1),
    "1": ("cpu_addr", 32),
    ")": ("cpu_ready", 1),
    "(": ("hit_flag", 1),
    "$": ("mem_req", 1),
    "%": ("mem_ready", 1),
    "L": ("state", 2),
    "#": ("stat_accesses", 32),
    '"': ("stat_hits", 32),
    "!": ("stat_misses", 32),
}

# Signals we actually draw, top to bottom. clk dropped (too dense, no story).
# stat_hits/stat_misses dropped (stat_accesses alone marks the access count).
ORDER = [
    "cpu_req", "cpu_addr", "state",
    "mem_req", "mem_ready",
    "cpu_ready", "hit_flag",
    "stat_accesses",
]

# Friendly row labels.
LABEL = {
    "cpu_req": "cpu_req",
    "cpu_addr": "cpu_addr",
    "state": "state",
    "mem_req": "mem_req",
    "mem_ready": "mem_ready",
    "cpu_ready": "cpu_ready",
    "hit_flag": "hit_flag",
    "stat_accesses": "accesses",
}

STATE_NAME = {0: "IDLE", 1: "COMPARE", 2: "ALLOC", 3: "DONE"}

PS_PER_NS = 1000.0
BLUE = "#1f77b4"
GREEN = "#2e7d32"
MISS_SHADE = "#fdecea"   # light red
HIT_SHADE = "#e8f5e9"    # light green


def parse(path):
    """Return {name: [(time, value), ...]} with value as int."""
    changes = {sid: [] for sid in SIGS}
    t = 0
    with open(path) as f:
        in_dumps = False
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("$"):
                if line.startswith("$enddefinitions"):
                    in_dumps = True
                continue
            if line[0] == "#":
                t = int(line[1:])
                continue
            if not in_dumps:
                continue
            c = line[0]
            if c in "01":                      # scalar: <val><id>
                sid = line[1:]
                if sid in SIGS:
                    changes[sid].append((t, int(c)))
            elif c in "bB":                    # vector: b<bits> <id>
                bits, sid = line[1:].split()
                if sid in SIGS:
                    val = int(bits, 2) if set(bits) <= {"0", "1"} else 0
                    changes[sid].append((t, val))
    return {SIGS[sid][0]: ev for sid, ev in changes.items()}


def value_at(events, t):
    v = 0
    for (et, ev) in events:
        if et <= t:
            v = ev
        else:
            break
    return v


def segments(events, t0, t1):
    """Return list of (start, end, value) spans within [t0, t1]."""
    spans = []
    cur = value_at(events, t0)
    seg_start = t0
    for (et, ev) in events:
        if et <= t0:
            continue
        if et >= t1:
            break
        if ev != cur:
            spans.append((seg_start, et, cur))
            cur = ev
            seg_start = et
    spans.append((seg_start, t1, cur))
    return spans


def fmt_val(name, val):
    if name == "state":
        return STATE_NAME.get(val, str(val))
    if name == "cpu_addr":
        return f"0x{val:X}"
    return str(val)


def draw_scalar(ax, events, t0, t1, y, h):
    lo = y + 0.18 * h
    hi = y + 0.82 * h
    xs, ys = [], []
    prev = None
    for (s, e, v) in segments(events, t0, t1):
        lvl = hi if v else lo
        if prev is not None and prev != lvl:
            xs.append(s); ys.append(prev)   # vertical edge
        xs.append(s); ys.append(lvl)
        xs.append(e); ys.append(lvl)
        prev = lvl
    ax.plot(xs, ys, color=BLUE, linewidth=1.8, solid_joinstyle="miter")


def draw_bus(ax, events, name, t0, t1, y, h, span_ns):
    lo = y + 0.2 * h
    hi = y + 0.8 * h
    mid = y + 0.5 * h
    bevel = min(span_ns, (t1 - t0) * 0.004)
    for (s, e, v) in segments(events, t0, t1):
        if e - s < 1:
            continue
        # hexagon-ish box
        ax.plot([s + bevel, e - bevel], [hi, hi], color=GREEN, linewidth=1.6)
        ax.plot([s + bevel, e - bevel], [lo, lo], color=GREEN, linewidth=1.6)
        ax.plot([s, s + bevel], [mid, hi], color=GREEN, linewidth=1.6)
        ax.plot([s, s + bevel], [mid, lo], color=GREEN, linewidth=1.6)
        ax.plot([e - bevel, e], [hi, mid], color=GREEN, linewidth=1.6)
        ax.plot([e - bevel, e], [lo, mid], color=GREEN, linewidth=1.6)
        txt = fmt_val(name, v)
        # Skip labels on segments too narrow to hold the text without
        # spilling into neighbours. ~1.05 ns per char at this font size.
        if (e - s) < len(txt) * 1.05 + 1.0:
            continue
        t = ax.text((s + e) / 2, mid, txt, ha="center", va="center",
                    fontsize=10, family="monospace", weight="bold",
                    color="#1b5e20")
        t.set_clip_on(True)


def main():
    data = parse(VCD)

    # Window: first access through the 5th, converted to ns.
    acc = data["stat_accesses"]
    t_start_ps = 0
    t_end_ps = None
    for (t, v) in acc:
        if v == 1 and t_start_ps == 0:
            t_start_ps = max(0, t - 3000)
        if v == 5:
            t_end_ps = t + 2000
            break
    if t_end_ps is None:
        t_end_ps = t_start_ps + 60000

    t0 = t_start_ps / PS_PER_NS
    t1 = t_end_ps / PS_PER_NS
    span_ns = (t1 - t0)

    # Convert all event times to ns.
    data = {k: [(et / PS_PER_NS, v) for (et, v) in ev] for k, ev in data.items()}

    fig, ax = plt.subplots(figsize=(14, 7.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    row_h = 1.0
    gap = 0.55
    y = 0
    yticks, ylabels = [], []

    rows = list(reversed(ORDER))
    for name in rows:
        ev = data[name]
        width = next(w for _, (n, w) in SIGS.items() if n == name)
        yticks.append(y + row_h / 2)
        ylabels.append(LABEL[name])
        if width == 1:
            draw_scalar(ax, ev, t0, t1, y, row_h)
        else:
            draw_bus(ax, ev, name, t0, t1, y, row_h, span_ns)
        y += row_h + gap

    top = y - gap + 0.2

    # Shade the first access (MISS) and the next (first HIT) using cpu_ready.
    ready_spans = [s for s in segments(data["cpu_ready"], t0, t1) if s[2] == 1]
    hit_ev = data["hit_flag"]
    first_done = ready_spans[0][0] if ready_spans else None

    # Access boundaries: each access spans from one cpu_req rise region.
    # Shade region 1 (miss) up to first cpu_ready, region 2 (hit) after.
    if first_done is not None:
        ax.add_patch(Rectangle((t0, -0.15), first_done - t0, top + 0.15,
                     facecolor=MISS_SHADE, edgecolor="none", zorder=0))
        ax.text(t0 + (first_done - t0) / 2, top - 0.05, "ACCESS 1  —  MISS",
                ha="center", va="top", fontsize=11, weight="bold",
                color="#b71c1c")
        # hit region: from first_done to the 2nd cpu_ready (or end)
        hit_end = ready_spans[1][0] if len(ready_spans) > 1 else t1
        ax.add_patch(Rectangle((first_done, -0.15), hit_end - first_done,
                     top + 0.15, facecolor=HIT_SHADE, edgecolor="none",
                     zorder=0))
        ax.text(first_done + (hit_end - first_done) / 2, top - 0.05,
                "ACCESS 2  —  HIT", ha="center", va="top", fontsize=11,
                weight="bold", color="#1b5e20")

    ax.set_xlim(t0, t1)
    ax.set_ylim(-0.25, top + 0.35)
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=12, family="monospace", weight="bold")
    ax.set_xlabel("time (ns)", fontsize=12)
    ax.tick_params(axis="x", labelsize=10)
    ax.set_title("Direct-Mapped Cache: first CPU accesses  (cold miss, refill, then hit)",
                 fontsize=15, weight="bold", pad=14)
    ax.grid(axis="x", color="#e0e0e0", linewidth=0.6, zorder=0)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="y", length=0)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(f"wrote {OUT}  window=[{t0:.0f},{t1:.0f}] ns")


if __name__ == "__main__":
    main()
