"""Downstream predictors. The same models are used for real-only and real+synthetic runs."""
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from . import data


def make_model(name, seed, numeric=None, categorical=None):
    NUMERIC = numeric or data.NUMERIC
    CATEGORICAL = categorical or data.CATEGORICAL
    if name == "logreg":
        pre = ColumnTransformer([
            ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=5), CATEGORICAL),
        ])
        return make_pipeline(pre, LogisticRegression(C=1.0, max_iter=2000))
    if name == "gbm":
        pre = ColumnTransformer([
            ("num", "passthrough", NUMERIC),
            ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1,
                                   encoded_missing_value=-1), CATEGORICAL),
        ])
        n_cat = len(CATEGORICAL)
        cat_mask = [False] * len(NUMERIC) + [True] * n_cat
        return make_pipeline(pre, HistGradientBoostingClassifier(
            categorical_features=cat_mask, max_iter=300, learning_rate=0.05,
            early_stopping=False, random_state=seed))
    raise ValueError(name)
