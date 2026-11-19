"""
STEP 4 - Predict which bookings will cancel, and turn the model into a business policy.

Design choices (each one is an interview talking point):
  * ONLY information known at booking time is used. Excluded as leakage:
      reservation_status / reservation_status_date  (they ARE the outcome)
      assigned_room_type, booking_changes            (happen after booking)
      required_car_parking_spaces                    (0% of bookings with parking cancel ->
                                                      almost certainly recorded at check-in)
  * TIME-BASED split: train on arrivals before Mar-2017, test on Mar-Aug 2017.
    A random split would let the model "see the future" and overstate accuracy.
  * Two models: logistic regression (interpretable baseline) vs gradient boosting.
  * Metrics: ROC-AUC, PR-AUC, Brier score, plus results on No-Deposit bookings only,
    because that is where a deposit policy could actually change anything.
  * Permutation importance on raw features (works for any model).

Outputs: data/processed/model_scores.csv, model_deciles.csv, model_importance.csv, model_metrics.csv
         outputs/figures/07-09_*.png

Run:  python python/s04_cancellation_model.py
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score, roc_curve
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import config as C
from plot_style import plt, pct, save, PRIMARY, ACCENT, NEGATIVE, NEUTRAL

NUMERIC = ["lead_time", "stays_in_weekend_nights", "stays_in_week_nights", "adults", "children",
           "babies", "is_repeated_guest", "previous_cancellations", "previous_bookings_not_canceled",
           "days_in_waiting_list", "adr", "total_of_special_requests", "arrival_month_num",
           "arrival_date_week_number"]
CATEGORICAL = ["hotel", "meal", "market_segment", "distribution_channel", "deposit_type",
               "customer_type", "reserved_room_type", "country_group", "has_agent"]
LEAKAGE_EXCLUDED = ["reservation_status", "reservation_status_date", "assigned_room_type",
                    "booking_changes", "required_car_parking_spaces"]


def prepare(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    top = d["country"].value_counts().head(15).index
    d["country_group"] = np.where(d["country"].isin(top), d["country"], "Other")
    d["has_agent"] = np.where(d["agent"] > 0, "Yes", "No")
    return d


def make_models():
    onehot = OneHotEncoder(handle_unknown="ignore", min_frequency=20, sparse_output=False)
    logit = Pipeline([
        ("prep", ColumnTransformer([("num", StandardScaler(), NUMERIC), ("cat", onehot, CATEGORICAL)])),
        ("clf", LogisticRegression(max_iter=3000, C=1.0)),
    ])
    gbm = Pipeline([
        ("prep", ColumnTransformer([("num", "passthrough", NUMERIC),
                                    ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20,
                                                          sparse_output=False), CATEGORICAL)])),
        ("clf", HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31,
                                               l2_regularization=1.0, random_state=C.RANDOM_STATE)),
    ])
    return {"Logistic regression": logit, "Gradient boosting": gbm}


def run() -> dict:
    C.ensure_dirs()
    d = prepare(pd.read_csv(C.PROCESSED_DIR / "fact_bookings.csv"))
    train = d[d["arrival_date"] < C.MODEL_TEST_START]
    test = d[d["arrival_date"] >= C.MODEL_TEST_START]
    X_cols = NUMERIC + CATEGORICAL
    print(f"Train: {len(train):,} bookings (arrivals < {C.MODEL_TEST_START}); test: {len(test):,}")

    metrics, scores, m = [], {}, {}
    nd_mask = (test["deposit_type"] == "No Deposit").to_numpy()
    for name, model in make_models().items():
        model.fit(train[X_cols], train["is_canceled"])
        p = model.predict_proba(test[X_cols])[:, 1]
        scores[name] = p
        y = test["is_canceled"].to_numpy()
        metrics.append({
            "model": name,
            "roc_auc": round(roc_auc_score(y, p), 3),
            "pr_auc": round(average_precision_score(y, p), 3),
            "brier": round(brier_score_loss(y, p), 3),
            "accuracy_at_50pct": round(float(((p >= 0.5) == y).mean()), 3),
            "roc_auc_no_deposit": round(roc_auc_score(y[nd_mask], p[nd_mask]), 3),
            "test_cancel_rate": round(float(y.mean()), 3),
        })
        print(f"  {name:20s} AUC {metrics[-1]['roc_auc']}  PR-AUC {metrics[-1]['pr_auc']}  "
              f"AUC(no deposit) {metrics[-1]['roc_auc_no_deposit']}")
    met = pd.DataFrame(metrics)
    met.to_csv(C.PROCESSED_DIR / "model_metrics.csv", index=False, lineterminator="\n")
    best = met.sort_values("roc_auc_no_deposit", ascending=False).iloc[0]["model"]
    p_best = scores[best]

    # ---- ROC curves ------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    for (name, p), colr in zip(scores.items(), [NEUTRAL, PRIMARY]):
        fpr, tpr, _ = roc_curve(test["is_canceled"], p)
        ax.plot(fpr, tpr, color=colr, label=f"{name} (AUC {roc_auc_score(test['is_canceled'], p):.3f})")
    ax.plot([0, 1], [0, 1], ls="--", color="#CBD5E1")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.legend(loc="lower right")
    ax.set_title("ROC on unseen months (Mar-Aug 2017)")
    save(fig, C.FIGURE_DIR / "07_roc_curves.png")

    # ---- Risk deciles on No-Deposit test bookings ------------------------ #
    t = test.assign(risk_score=p_best)
    ndt = t[t["deposit_type"] == "No Deposit"].copy()
    ndt["risk_decile"] = pd.qcut(ndt["risk_score"].rank(method="first", ascending=False), 10,
                                 labels=range(1, 11)).astype(int)  # 1 = highest risk
    dec = ndt.groupby("risk_decile").agg(
        bookings=("booking_id", "size"), avg_predicted=("risk_score", "mean"),
        actual_cancel_rate=("is_canceled", "mean"), cancellations=("is_canceled", "sum"),
        lost_revenue=("lost_revenue", "sum"), booking_value=("booking_value", "sum"),
        avg_adr=("adr", "mean"), realized_revenue=("realized_revenue", "sum")).reset_index()
    dec["share_of_cancellations"] = dec["cancellations"] / dec["cancellations"].sum()
    dec["cum_share_of_cancellations"] = dec["share_of_cancellations"].cumsum()
    # first-night value of each decile's cancelled bookings (what a 1-night deposit would have secured)
    first_night = ndt[ndt["is_canceled"] == 1].groupby("risk_decile")["adr"].sum()
    dec["first_night_value_of_cancellations"] = dec["risk_decile"].map(first_night).fillna(0)
    dec = dec.round(4)
    dec.to_csv(C.PROCESSED_DIR / "model_deciles.csv", index=False, lineterminator="\n")

    fig, ax = plt.subplots(figsize=(9, 4.3))
    bars = ax.bar(dec["risk_decile"].astype(str), 100 * dec["actual_cancel_rate"],
                  color=[NEGATIVE] + [NEUTRAL] * 9)
    ax.bar_label(bars, fmt="%.0f%%")
    ax.axhline(100 * ndt["is_canceled"].mean(), color=PRIMARY, ls="--", label="Average")
    pct(ax)
    ax.legend()
    ax.set_xlabel("Risk decile (1 = the 10% of bookings the model scores riskiest)")
    ax.set_title("Actual cancellation rate by predicted-risk decile (No-Deposit bookings, unseen months)")
    save(fig, C.FIGURE_DIR / "08_risk_deciles.png")

    # ---- Permutation importance ------------------------------------------ #
    best_model = make_models()[best]
    best_model.fit(train[X_cols], train["is_canceled"])
    sample = test.sample(min(6000, len(test)), random_state=C.RANDOM_STATE)
    pi = permutation_importance(best_model, sample[X_cols], sample["is_canceled"], scoring="roc_auc",
                                n_repeats=4, random_state=C.RANDOM_STATE, n_jobs=1)
    imp = (pd.DataFrame({"feature": X_cols, "auc_drop": pi.importances_mean, "std": pi.importances_std})
           .sort_values("auc_drop", ascending=False).round(4))
    imp.to_csv(C.PROCESSED_DIR / "model_importance.csv", index=False, lineterminator="\n")
    top = imp.head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(top["feature"], top["auc_drop"], xerr=top["std"], color=PRIMARY)
    ax.set_xlabel("Drop in ROC-AUC when the feature is shuffled")
    ax.set_title(f"What drives cancellation risk ({best})")
    save(fig, C.FIGURE_DIR / "09_feature_importance.png")

    # ---- Scores table for Power BI ----------------------------------------- #
    out = t[["booking_id", "risk_score"]].copy()
    out["risk_score"] = out["risk_score"].round(4)
    out = out.merge(ndt[["booking_id", "risk_decile"]], on="booking_id", how="left")
    out["risk_decile"] = out["risk_decile"].astype("Int64")
    out["risk_band"] = pd.cut(out["risk_score"], [-0.01, 0.3, 0.6, 1.01], labels=["Low", "Medium", "High"]).astype(str)
    out.to_csv(C.PROCESSED_DIR / "model_scores.csv", index=False, lineterminator="\n")

    # ---- Policy: 1-night deposit for the riskiest 10% of No-Deposit bookings ---- #
    d1 = dec.iloc[0]
    walkaway = 0.05  # assumption: 5% of the guests asked for a deposit who would have stayed book elsewhere
    protected = float(d1["first_night_value_of_cancellations"])
    friction = walkaway * float(d1["realized_revenue"])
    m.update({
        "model_best": best,
        "model_train_rows": len(train), "model_test_rows": len(test),
        **{f"{'logit' if k.startswith('Log') else 'gbm'}_{c}": v
           for k, row in met.set_index("model").iterrows() for c, v in row.items()},
        "top_decile_cancel_pct": round(100 * float(d1["actual_cancel_rate"]), 1),
        "nodeposit_avg_cancel_pct": round(100 * float(ndt["is_canceled"].mean()), 1),
        "top_decile_share_of_cancellations_pct": round(100 * float(d1["share_of_cancellations"]), 1),
        "top2_deciles_share_of_cancellations_pct": round(100 * float(dec.iloc[1]["cum_share_of_cancellations"]), 1),
        "policy_protected_first_night": round(protected, 0),
        "policy_friction_cost": round(friction, 0),
        "policy_net": round(protected - friction, 0),
        "policy_walkaway_assumption_pct": walkaway * 100,
        "top_features": list(imp["feature"].head(5)),
    })
    return m


if __name__ == "__main__":
    for k, v in run().items():
        print(f"{k:42s} {v}")
