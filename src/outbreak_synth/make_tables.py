"""Table 1 for the paper (paper/table_data.tex): one row per outbreak, from the library summaries and the replays.
Usage: PYTHONPATH=src python -m outbreak_synth.make_tables"""
import json
from pathlib import Path

import pandas as pd

from .analyse_os2 import final_paths


def main():
    s = pd.read_csv("results/library_frozen_summary.csv").set_index("outbreak")
    rows = []
    for run, part in [("exp08d_os_replay_known", "Development"), ("exp18b_os_replay_frozen", "Frozen test")]:
        outs = json.loads(Path("results", f"{run}.json").read_text())["outbreaks"]
        paths = final_paths(run, E=20, m=10, s=0.99)
        for f in sorted(outs, key=lambda x: (x.split("_")[-1], x)):
            g = paths[f][1]
            rows.append((part, f, outs[f]["info"]["day0"], outs[f]["info"]["test_n"], outs[f]["info"]["test_deaths"], g))
    name = lambda f: f.replace("othervirus", "Other virus").replace("flu", "Influenza").replace("covid", "COVID-19").replace("_", " ")
    lines = [r"\begin{table}[t]", r"\centering\scriptsize",
             r"\caption{Outbreaks. Patients: hospitalised with a recorded outcome. Missing: share of the 16 yes/no fields "
             r"not collected or not filled in. Day 0: start of the replay. Test: patients admitted on days 91--182 "
             r"(July 2020 for COVID-19 2020). Green: GreenLight's green-light day ($-$: none by day 90). H1N1 2009 is used only as "
             r"an earlier outbreak to borrow from.}\label{tab:data}",
             r"\resizebox{\linewidth}{!}{%", r"\begin{tabular}{llrrrrlrrr}", r"\toprule",
             r"Set & Outbreak & Patients & Died (\%) & Median age & Missing (\%) & Day 0 & Test patients & Test deaths & Green \\",
             r"\midrule"]
    last = None
    for part, f, d0, tn, td, g in rows:
        if last and part != last:
            lines.append(r"\midrule")
        r = s.loc[f]
        lines.append(f"{part if part != last else ''} & {name(f)} & {int(r.patients):,} & {100 * r.death_rate:.1f} & {r.median_age:.0f} & "
                     f"{100 * r.fields_missing_share:.0f} & {d0} & {tn:,} & {td:,} & {g if g is not None else '$-$'} \\\\")
        last = part
    r = s.loc["h1n1_2009"]
    lines += [r"\midrule", f"Source only & H1N1 2009 & {int(r.patients):,} & {100 * r.death_rate:.1f} & {r.median_age:.0f} & "
              f"{100 * r.fields_missing_share:.0f} & -- & -- & -- & -- \\\\", r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
    Path("paper/table_data.tex").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
