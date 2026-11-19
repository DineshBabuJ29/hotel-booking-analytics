"""Shared chart style so every figure in /outputs/figures looks consistent."""
import matplotlib
matplotlib.use("Agg")  # render to files, no window needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

PRIMARY = "#0F766E"   # teal - main series (Coastal theme)
ACCENT = "#F59E0B"    # amber - comparison
NEGATIVE = "#E11D48"  # rose - bad outcome
NEUTRAL = "#A8A29E"   # warm grey - context

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 13, "axes.titlelocation": "left",
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 10,
})


def money(ax, axis="y", sym="€"):
    """Format an axis as {sym} thousands / millions."""
    def fmt(x, _):
        if abs(x) >= 1e6:
            return f"{sym}{x / 1e6:.1f}M"
        if abs(x) >= 1e3:
            return f"{sym}{x / 1e3:.0f}K"
        return f"{sym}{x:.0f}"
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(mticker.FuncFormatter(fmt))


def pct(ax, axis="y"):
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(mticker.PercentFormatter(decimals=0))


def save(fig, path):
    fig.savefig(path)
    plt.close(fig)
    print(f"  saved {path.name}")
