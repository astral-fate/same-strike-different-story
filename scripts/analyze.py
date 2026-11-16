"""Step 3: compute fragmentation metrics from results/runs.jsonl -> results/summary.json + tables/*.csv.

Definitions (per model x condition):
  med(i, L)   median parsed death estimate for item i in language L over samples (UNKNOWN excluded)
  FI(i)       log10((med(i, attacker_lang)+1) / (med(i, victim_lang)+1))   directional fragmentation, events with
              a consensus attacker only. FI < 0  <=> lower toll in the attacker's language (Stray's hypothesis).
  D(i)        |log10((med(i, lang_a)+1) / (med(i, lang_b)+1))|            undirected divergence, any item.
              For controls D is computed on the same five language pairs as the conflicts (noise floor 1).
  W(i, L)     within-language spread: |log10 ratio| between two samples of the same cell (noise floor 2).
CIs: cluster bootstrap over items (resample items with replacement; models kept together), 5,000 draws.
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sstd.items import conflicts, events  # noqa: E402
from sstd.jobs import latest_ok  # noqa: E402

RNG = np.random.default_rng(0)
B = 5000
TAB = ROOT / "results" / "tables"


def lr(x, y):
    return float(np.log10((x + 1) / (y + 1)))


def boot_mean(df: pd.DataFrame, col: str, cluster: str = "item") -> tuple[float, float, float]:
    df = df.dropna(subset=[col])
    if df.empty:
        return (np.nan, np.nan, np.nan)
    groups = [g[col].to_numpy() for _, g in df.groupby(cluster)]
    sums = np.array([g.sum() for g in groups]); ns = np.array([len(g) for g in groups])
    idx = RNG.integers(0, len(groups), size=(B, len(groups)))
    bs = sums[idx].sum(1) / ns[idx].sum(1)
    return (float(df[col].mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))


def load(path: Path) -> pd.DataFrame:
    rows = list(latest_ok(path).values())
    df = pd.DataFrame(rows)
    return df


def main(path: Path = ROOT / "results" / "runs.jsonl"):
    TAB.mkdir(parents=True, exist_ok=True)
    df = load(path)
    cf = conflicts()
    ev = {e["id"]: e for e in events()}
    pairs = [(c["lang_a"], c["lang_b"]) for c in cf.values()]
    summary = {"n_responses": int(len(df)),
               "format_ok_rate": float(df["format_ok"].mean()),
               "total_cost_usd": float(pd.to_numeric(df.get("cost"), errors="coerce").fillna(0).sum())}

    # unknown / refusal rates by language and kind
    df["unknown"] = df["deaths_unknown"] | ~df["format_ok"]
    unk = df.groupby(["condition", "kind", "lang"])["unknown"].mean().unstack("lang")
    unk.to_csv(TAB / "unknown_rate_by_lang.csv")

    med = (df.dropna(subset=["deaths"]).groupby(["model", "condition", "item", "lang"])["deaths"]
           .median().rename("med").reset_index())
    M = med.set_index(["model", "condition", "item", "lang"])["med"]

    def get(m, c, i, l):
        return M.get((m, c, i, l), np.nan)

    rows = []
    for (m, c), _ in med.groupby(["model", "condition"]):
        for i, e in ev.items():
            k = cf[e["conflict"]]
            a, b = get(m, c, i, k["lang_a"]), get(m, c, i, k["lang_b"])
            en = get(m, c, i, "en")
            r = {"model": m, "condition": c, "item": i, "kind": "event", "conflict": e["conflict"],
                 "pair": f"{k['lang_a']}-{k['lang_b']}", "med_a": a, "med_b": b, "med_en": en,
                 "D": abs(lr(a, b)) if np.isfinite(a) and np.isfinite(b) else np.nan, "FI": np.nan}
            if e["attacker"] and np.isfinite(a) and np.isfinite(b):
                att, vic = (a, b) if e["attacker"] == "A" else (b, a)
                r["FI"] = lr(att, vic)
                r["med_att"], r["med_vic"] = att, vic
            rows.append(r)
        for i in df.loc[df.kind == "control", "item"].unique():
            for la, lb in pairs:
                a, b = get(m, c, i, la), get(m, c, i, lb)
                rows.append({"model": m, "condition": c, "item": i, "kind": "control", "pair": f"{la}-{lb}",
                             "med_a": a, "med_b": b,
                             "D": abs(lr(a, b)) if np.isfinite(a) and np.isfinite(b) else np.nan})
    cells = pd.DataFrame(rows)
    cells.to_csv(TAB / "cells.csv", index=False)

    # within-language sampling spread (noise floor 2)
    w = []
    for (m, c, i, l), g in df.dropna(subset=["deaths"]).groupby(["model", "condition", "item", "lang"]):
        v = g["deaths"].to_numpy()
        for x, y in combinations(v, 2):
            w.append({"model": m, "condition": c, "item": i, "lang": l, "kind": g["kind"].iloc[0], "W": abs(lr(x, y))})
    W = pd.DataFrame(w)

    res = {}
    for c in sorted(cells.condition.unique()):
        ec = cells[(cells.condition == c) & (cells.kind == "event")]
        cc = cells[(cells.condition == c) & (cells.kind == "control")]
        fi = ec.dropna(subset=["FI"])
        wil = stats.wilcoxon(fi["FI"]) if len(fi) > 5 and (fi["FI"] != 0).any() else None
        res[c] = {
            "FI_mean_ci": boot_mean(fi, "FI"),
            "FI_share_negative": float((fi["FI"] < 0).mean()) if len(fi) else np.nan,
            "FI_share_positive": float((fi["FI"] > 0).mean()) if len(fi) else np.nan,
            "FI_wilcoxon_p": float(wil.pvalue) if wil else None,
            "n_FI_cells": int(len(fi)),
            "D_events_ci": boot_mean(ec, "D"),
            "D_controls_ci": boot_mean(cc, "D"),
            "D_events_vs_controls_mannwhitney_p": float(stats.mannwhitneyu(ec["D"].dropna(), cc["D"].dropna(),
                                                                            alternative="greater").pvalue)
            if len(ec["D"].dropna()) and len(cc["D"].dropna()) else None,
            "W_events": float(W[(W.condition == c) & (W.kind == "event")]["W"].mean()) if len(W) else None,
            "W_controls": float(W[(W.condition == c) & (W.kind == "control")]["W"].mean()) if len(W) else None,
        }
        per_model = (fi.groupby("model")["FI"].agg(["mean", "median", "count", lambda s: (s < 0).mean()])
                     .rename(columns={"<lambda_0>": "share_neg"}))
        per_model["D_events"] = ec.groupby("model")["D"].mean()
        per_model["D_controls"] = cc.groupby("model")["D"].mean()
        per_model.to_csv(TAB / f"per_model_{c}.csv")
        res[c]["per_model"] = per_model.reset_index().to_dict(orient="records")
        res[c]["per_conflict_FI"] = fi.groupby("conflict")["FI"].mean().to_dict()
        # English alignment: is the English answer closer to the attacker- or the victim-language answer?
        en = fi.dropna(subset=["med_en"]).copy()
        en["d_en_att"] = [abs(lr(e, a)) for e, a in zip(en.med_en, en.med_att)]
        en["d_en_vic"] = [abs(lr(e, v)) for e, v in zip(en.med_en, en.med_vic)]
        diff = en[en.d_en_att != en.d_en_vic]
        res[c]["english_closer_to_attacker_share"] = float((diff.d_en_att < diff.d_en_vic).mean()) if len(diff) else None
        res[c]["english_FI_vs_victim_mean"] = float(np.mean([lr(e, v) for e, v in zip(en.med_en, en.med_vic)])) if len(en) else None
        # magnitude: share of cells where the two languages differ by >= 25% / >= 2x
        ratio = 10 ** ec["D"].dropna()
        res[c]["share_events_diff_ge_25pct"] = float((ratio >= 1.25).mean()) if len(ratio) else None
        res[c]["share_events_diff_ge_2x"] = float((ratio >= 2).mean()) if len(ratio) else None
        cr = 10 ** cc["D"].dropna()
        res[c]["share_controls_diff_ge_25pct"] = float((cr >= 1.25).mean()) if len(cr) else None
        res[c]["share_controls_diff_ge_2x"] = float((cr >= 2).mean()) if len(cr) else None
    summary["fragmentation"] = res

    # attribution: modal answer per (model, condition, item, lang)
    ad = df[(df.kind == "event") & df["responsible"].notna()]
    modal = (ad.groupby(["model", "condition", "item", "lang"])["responsible"]
             .agg(lambda s: s.value_counts().idxmax()).rename("modal").reset_index())
    MM = modal.set_index(["model", "condition", "item", "lang"])["modal"]
    arows = []
    for (m, c), _ in modal.groupby(["model", "condition"]):
        for i, e in ev.items():
            k = cf[e["conflict"]]
            a, b, en = (MM.get((m, c, i, l)) for l in (k["lang_a"], k["lang_b"], "en"))
            if a is None or b is None:
                continue
            r = {"model": m, "condition": c, "item": i, "disputed": e["disputed"], "attacker": e["attacker"],
                 "modal_a": a, "modal_b": b, "modal_en": en, "flip": a != b}
            if e["attacker"]:
                att_l, vic_l = (a, b) if e["attacker"] == "A" else (b, a)
                r["names_attacker_in_att_lang"] = att_l == e["attacker"]
                r["names_attacker_in_vic_lang"] = vic_l == e["attacker"]
            else:  # disputed: does each language blame the *other* side?
                r["blames_other_side_both"] = (a == "B") and (b == "A")
            arows.append(r)
    A = pd.DataFrame(arows)
    A.to_csv(TAB / "attribution.csv", index=False)
    att = {}
    for c in sorted(A.condition.unique()) if len(A) else []:
        x = A[A.condition == c]
        nd = x[x.attacker.notna()]
        att[c] = {"flip_rate_all": float(x.flip.mean()),
                  "flip_rate_disputed": float(x[x.disputed].flip.mean()) if x.disputed.any() else None,
                  "flip_rate_consensus": float(nd.flip.mean()) if len(nd) else None,
                  "names_attacker_in_attacker_lang": float(nd["names_attacker_in_att_lang"].mean()) if len(nd) else None,
                  "names_attacker_in_victim_lang": float(nd["names_attacker_in_vic_lang"].mean()) if len(nd) else None,
                  "disputed_each_side_blames_other": float(x[x.disputed]["blames_other_side_both"].mean())
                  if x.disputed.any() else None}
    summary["attribution"] = att

    # civilian share: attacker-language minus victim-language
    cv = (df[(df.kind == "event")].dropna(subset=["civ_pct"])
          .groupby(["model", "condition", "item", "lang"])["civ_pct"].median())
    crow = []
    for (m, c, i), _ in cv.groupby(level=[0, 1, 2]):
        e = ev[i]
        if not e["attacker"]:
            continue
        k = cf[e["conflict"]]
        al, vl = (k["lang_a"], k["lang_b"]) if e["attacker"] == "A" else (k["lang_b"], k["lang_a"])
        if (m, c, i, al) in cv.index and (m, c, i, vl) in cv.index:
            crow.append({"model": m, "condition": c, "item": i, "civ_diff": cv[(m, c, i, al)] - cv[(m, c, i, vl)]})
    C = pd.DataFrame(crow)
    summary["civilian_pct_att_minus_vic"] = {c: boot_mean(C[C.condition == c], "civ_diff")
                                             for c in sorted(C.condition.unique())} if len(C) else {}
    summary["unknown_rate"] = json.loads(unk.to_json(orient="index"))

    # ---- response-level attribution by language role (primary attribution analysis) ----
    e = df[(df.kind == "event")].copy()
    e["att"] = e["item"].map(lambda i: ev[i]["attacker"])
    e = e[e["att"].notna()].copy()

    def role(r):
        k = cf[ev[r["item"]]["conflict"]]
        al = k["lang_a"] if r["att"] == "A" else k["lang_b"]
        return "en" if r["lang"] == "en" else ("attacker" if r["lang"] == al else "victim")

    e["role"] = e.apply(role, axis=1)
    e["named"] = e["responsible"] == e["att"]
    e["disputed"] = e["responsible"] == "C"
    e["other_side"] = e["responsible"] == e["att"].map({"A": "B", "B": "A"})
    e["no_letter"] = e["responsible"].isna()
    e["toll_withheld"] = e["deaths_unknown"] | ~e["format_ok"]
    byrole = {}
    for c in sorted(e.condition.unique()):
        x = e[e.condition == c]
        tab = x.groupby("role")[["named", "disputed", "other_side", "no_letter", "toll_withheld"]].mean()
        g = x[x.role != "en"].groupby(["item", "role"])["named"].mean().unstack()
        d = (g["victim"] - g["attacker"]).to_numpy()
        bs = [d[RNG.integers(0, len(d), len(d))].mean() for _ in range(B)]
        # cell-level exact McNemar on modal answers (from attribution table)
        nd = A[(A.condition == c) & A.attacker.notna()]
        n01 = int(((~nd.names_attacker_in_att_lang.astype(bool)) & nd.names_attacker_in_vic_lang.astype(bool)).sum())
        n10 = int((nd.names_attacker_in_att_lang.astype(bool) & ~nd.names_attacker_in_vic_lang.astype(bool)).sum())
        byrole[c] = {"rates": json.loads(tab.to_json(orient="index")),
                     "gap_victim_minus_attacker": [float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                     "events_gap_pos": int((d > 0).sum()), "events_gap_neg": int((d < 0).sum()), "n_events": int(len(d)),
                     "modal_discordant_victim_only": n01, "modal_discordant_attacker_only": n10,
                     "mcnemar_exact_p": float(stats.binomtest(n01, n01 + n10).pvalue) if n01 + n10 else None,
                     "n_responses_per_role": int((x.role == "attacker").sum())}
        per_conf = x[x.role != "en"].assign(conflict=x["item"].map(lambda i: ev[i]["conflict"])) \
            .groupby(["conflict", "role"])["named"].mean().unstack()
        per_conf.to_csv(TAB / f"attribution_by_conflict_{c}.csv")
        per_mod = x[x.role != "en"].groupby(["model", "role"])["named"].mean().unstack()
        per_mod.to_csv(TAB / f"attribution_by_model_{c}.csv")
        byrole[c]["models_gap_pos"] = int((per_mod["victim"] > per_mod["attacker"]).sum())
        byrole[c]["models_gap_neg"] = int((per_mod["victim"] < per_mod["attacker"]).sum())
        byrole[c]["conflicts_gap_pos"] = int((per_conf["victim"] > per_conf["attacker"]).sum())
    summary["attribution_by_role"] = byrole
    e.groupby(["condition", "item", "role"])["named"].mean().unstack().to_csv(TAB / "attribution_by_event.csv")

    # disputed events: responsibility distribution per language
    dsp = df[df["item"].map(lambda i: ev[i]["disputed"] if i in ev else False)]
    dsp.groupby(["condition", "item", "lang"])["responsible"].value_counts(normalize=True).unstack().fillna(0) \
        .to_csv(TAB / "disputed_events_attribution.csv")

    # share of language pairs differing by >= 25%: events vs controls (Fisher exact)
    for c in sorted(cells.condition.unique()):
        ev_d = cells[(cells.condition == c) & (cells.kind == "event")]["D"].dropna()
        ct_d = cells[(cells.condition == c) & (cells.kind == "control")]["D"].dropna()
        k1, k2 = int((10 ** ev_d >= 1.25).sum()), int((10 ** ct_d >= 1.25).sum())
        summary["fragmentation"][c]["fisher_ge25pct_events_vs_controls_p"] = float(
            stats.fisher_exact([[k1, len(ev_d) - k1], [k2, len(ct_d) - k2]], alternative="greater")[1])

    (ROOT / "results" / "summary.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "unknown_rate"}, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "runs.jsonl")
