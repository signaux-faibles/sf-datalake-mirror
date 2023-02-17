"""Explain AI predictions using shap package.
"""
from typing import List, Tuple

import numpy as np
import pandas as pd
import pyspark.ml.classification
import shap

import sf_datalake.model
import sf_datalake.transform
import sf_datalake.utils


def explanation_data(
    features_list: List[str],
    model: pyspark.ml.Model,
    train_data: pyspark.sql.DataFrame,
    prediction_data: pyspark.sql.DataFrame,
    n_train_sample: int = 5000,
) -> Tuple[pd.DataFrame, float]:
    """Compute Shapeley coefficients + expected value for predictions.

    Shapeley coefficients represent the contribution to a model output. The computed
    units depend on the explained model. For instance, for logistic regression, and
    gradient-boosted trees, the coefficients computed by shap are in log-odds units.

    Args:
        model: A pyspark model used for prediction.
        train_data: Training dataset (as output by model pipeline).
        prediction_data: Prediction dataset (as output by model pipeline).
        n_train_sample: Number of training set samples used for estimating features
          correlation.

    Returns:
        A tuple containing:
        - A pandas DataFrame containing shap values associated with each feature.
        - The expected failure probability value over the prediction dataset.

    """
    X_prediction = sf_datalake.transform.vector_disassembler(
        df=prediction_data,
        columns=features_list,
        assembled_col="features",
        keep=["siren"],
    ).toPandas()

    if isinstance(model, pyspark.ml.classification.LogisticRegressionModel):
        X_train_sample = (
            sf_datalake.transform.vector_disassembler(
                df=train_data, columns=features_list, assembled_col="features"
            )
            .sample(
                fraction=min(1.0, max(0.0, ((n_train_sample + 1) / train_data.count())))
            )
            .toPandas()
        )

        explainer = shap.LinearExplainer(
            model=(model.coefficients.toArray(), model.intercept),
            nsamples=n_train_sample,
            data=X_train_sample,
            feature_perturbation="correlation_dependent",
        )
        shap_values = explainer.shap_values(X_prediction[features_list].values)

    elif isinstance(
        model,
        (
            pyspark.ml.classification.DecisionTreeClassificationModel,
            pyspark.ml.classification.RandomForestClassificationModel,
            pyspark.ml.classification.GBTClassificationModel,
        ),
    ):
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(
            X_prediction[features_list].values, check_additivity=False
        )
    else:
        raise NotImplementedError(f"{model} models are not supported.")

    # Here tree-based models may output a list of two elements corresponding to the
    # two (complementary) classes. Weirdly enough, this seems to happen only with
    # random forest or decision tree classifiers… Hence the `[1]` item getting.
    if isinstance(
        model,
        (
            pyspark.ml.classification.RandomForestClassificationModel,
            pyspark.ml.classification.DecisionTreeClassificationModel,
        ),
    ):
        shap_values = shap_values[1]
        explainer.expected_value = explainer.expected_value[1]

    sv = pd.DataFrame(
        shap_values,
        index=X_prediction["siren"],
    )
    ev = explainer.expected_value

    sv.columns = features_list
    return sv, ev


def explanation_scores(
    config: dict, shap_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute plot-ready feature contribution.

    This computes individual, as well as aggregated, features contributions. The most
    significant contributions (in favor of a positive prediction) are returned as a
    DataFrame containing concerning feature names and values. The number of concerning
    features to be returned is read from configuration `N_CONCERNING_MICRO` field.

    Contributions are first summed within feature groups:
    - at a "meso" scale: lagged variables and such, for a given feature.
    - at a "group" scale: features that   to the same thematic.

    In case contributions are expressed as log-odds, they are first mapped to the [0, 1]
    range before being returned.

    Args:
        config: The run configuration. It should contain `FEATURE GROUPS`, `MESO_GROUPS`
          and `N_CONCERNING_MICRO` info.
        shap_df: The shap values associated with the features used for machine learning.

    Returns:
        A 2-uple containing:
        - A "macro scores" df, which contains aggregated features contrbutions across a
          feature group.
        - A "concerning scores" df, which contains the most significant individual
          features contributions.

    """
    # Sum "micro" variables that belong to a given group and drop them.
    for group, features in config["MESO_GROUPS"].items():
        shap_df[group] = shap_df[features].sum(axis=1)
        shap_df.drop(features, axis=1, inplace=True)

    # 'Macro' scores per group
    macro_scores = pd.DataFrame([], index=shap_df.index)
    for group, features in config["FEATURE_GROUPS"].items():
        macro_scores.loc[:, f"{group}_macro_score"] = shap_df[features].sum(axis=1)

    # Concerning (highest scoring) features
    n_concerning = config["N_CONCERNING_MICRO"]
    sorter = np.argsort(-shap_df.values, axis=1)[:, :n_concerning]
    concerning_feat = pd.DataFrame(shap_df.columns[sorter], index=shap_df.index)
    concerning_values = pd.DataFrame(
        shap_df.values[np.arange(len(shap_df))[:, np.newaxis], sorter],
        index=shap_df.index,
    )

    concerning_feat.columns = [f"concerning_feat_{n}" for n in range(n_concerning)]
    concerning_values.columns = [f"concerning_val_{n}" for n in range(n_concerning)]
    concerning_scores = concerning_feat.join(concerning_values)
    return macro_scores, concerning_scores