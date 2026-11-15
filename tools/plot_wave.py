#!/usr/bin/env python3
"""Minimal VCD -> waveform PNG renderer for the cache demo.

No external deps beyond matplotlib. Parses cache.vcd, extracts a handful of
signals over a chosen time window (the first few CPU accesses, which show a
miss -> refill -> hit sequence), and draws a GTKWave-style digital waveform.
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
# display order (top to bottom)
ORDER = ["clk", "cpu_req", "cpu_addr", "state", "mem_req", "mem_ready",
         "cpu_ready", "hit_flag", "stat_accesses", "stat_hits", "stat_misses"]
STATE_NAME = {0: "IDLE", 1: "COMPARE", 2: "ALLOC", 3: "DONE"}


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


def main():
    data = parse(VCD)

    # Window: find the time of the 3rd access completing, so we capture
    # miss -> refill -> hit. Use stat_accesses reaching ~5.
    acc = data["stat_accesses"]
    t_start = 0
    t_end = None
    for (t, v) in acc:
        if v == 1 and t_start == 0:
            t_start = max(0, t - 2000)
        if v == 5:
            t_end = t + 3000
            break
    if t_end is None:
        t_end = t_start + 60000

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor("white")

    row_h = 1.0
    gap = 0.6
    y = 0
    yticks, ylabels = [], []

    # build a dense time grid for stepping
    grid = list(range(t_start, t_end, 50))

    for name in reversed(ORDER):
        ev = data[name]
        width = next(w for _, (n, w) in SIGS.items() if n == name)
        yc = y + row_h / 2
        yticks.append(yc)
        ylabels.append(name)

        if width == 1:
            xs, ys = [], []
            for gt in grid:
                v = value_at(ev, gt)
                xs.append(gt)
                ys.append(y + (0.15 + 0.7 * v) * row_h)
            ax.step(xs, ys, where="post", color="#1f77b4", linewidth=1.4)
        else:
            # multi-bit: draw a bus with value labels at each change
            # find transitions within window
            last = None
            seg_start = t_start
            for gt in grid + [t_end]:
                v = value_at(ev, gt)
                if last is None:
                    last = v
                    seg_start = gt
                elif v != last:
                    _bus_segment(ax, seg_start, gt, y, row_h, name, last)
                    last = v
                    seg_start = gt
            _bus_segment(ax, seg_start, t_end, y, row_h, name, last)

        y += row_h + gap

    ax.set_xlim(t_start, t_end)
    ax.set_ylim(-0.3, y)
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=10, family="monospace")
    ax.set_xlabel("time (ps)", fontsize=10)
    ax.set_title("Direct-Mapped Cache - first accesses "
                 "(miss → refill → hit)", fontsize=13, weight="bold")
    ax.grid(axis="x", color="#dddddd", linewidth=0.5)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    import os
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT, dpi=130)
    print(f"wrote {OUT}  window=[{t_start},{t_end}] ps")


def _bus_segment(ax, x0, x1, y, row_h, name, val):
    if x1 - x0 < 1:
        return
    lo = y + 0.2 * row_h
    hi = y + 0.8 * row_h
    ax.plot([x0, x1], [lo, lo], color="#2ca02c", linewidth=1.2)
    ax.plot([x0, x1], [hi, hi], color="#2ca02c", linewidth=1.2)
    if name == "state":
        txt = STATE_NAME.get(val, str(val))
    elif name in ("cpu_addr",):
        txt = f"0x{val:X}"
    else:
        txt = str(val)
    ax.text((x0 + x1) / 2, y + 0.5 * row_h, txt, ha="center", va="center",
            fontsize=8, family="monospace")


if __name__ == "__main__":
    main()
