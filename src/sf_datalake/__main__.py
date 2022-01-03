"""Main script for statistical prediction of company failure."""

import argparse
import datetime
import logging
import os
import sys
from os import path

# isort: off
sys.path.append(path.join(os.getcwd(), "venv/lib/python3.6/"))
sys.path.append(path.join(os.getcwd(), "venv/lib/python3.6/site-packages/"))
# isort: on

# pylint: disable=C0413

from pyspark.ml import Pipeline

import sf_datalake.io
import sf_datalake.model
import sf_datalake.preprocessor
import sf_datalake.sampler
import sf_datalake.transformer
import sf_datalake.utils


def main(parsed_args: argparse.Namespace):  # pylint: disable=R0914
    """Processes datasets according to configuration to make predictions."""

    # Parse a configuration file and possibly override parameters.
    args = vars(parsed_args)
    config = sf_datalake.utils.get_config(args.pop("config"))
    for param, value in args.items():
        config[param] = value
    _ = config.setdefault(
        "MODEL_OUTPUT_DIR",
        path.join(
            config["OUTPUT_ROOT_DIR"],
            "sorties_modeles",
            datetime.date.today().isoformat(),
        ),
    )

    # Prepare data.
    indics_annuels = sf_datalake.io.load_data(
        {
            "indics_annuels": path.join(
                config["DATA_ROOT_DIR"], "base/indicateurs_annuels.orc"
            ),
        },
        spl_ratio=config["SAMPLE_RATIO"],
    )["indics_annuels"]

    pipeline_preprocessor = Pipeline(
        stages=sf_datalake.preprocessor.generate_stages(config)
    )
    indics_annuels = pipeline_preprocessor.fit(indics_annuels).transform(indics_annuels)

    logging.info(
        "Creating oversampled training set with positive examples ratio %.1f",
        config["POSITIVE_OVERSAMPLING_RATIO"],
    )
    logging.info("Creating train between %s and %s.", *config["TRAIN_DATES"])
    logging.info("Creating test set between %s and %s.", *config["TEST_DATES"])
    logging.info("Creating a prediction set on %s.", config["PREDICTION_DATE"])
    data_train, data_test, data_prediction = sf_datalake.sampler.sample_df(
        indics_annuels, config
    )

    # Build and run Pipeline
    logging.info(
        "Training %s \
        %.3f and %d iterations (maximum).",
        config["MODEL"]["MODEL_NAME"],
        config["MODEL"]["REGULARIZATION_COEFF"],
        config["MODEL"]["MAX_ITER"],
    )  # TODO: Create an array attribute in the config file that lists all the
    # parameters related to the model. Then adjust logging to be more generic.

    stages = []
    stages += sf_datalake.transformer.generate_stages(config)
    stages += sf_datalake.model.generate_stages(config)
    stages += [sf_datalake.transformer.ProbabilityFormatter()]

    pipeline = Pipeline(stages=stages)
    pipeline_model = pipeline.fit(data_train)
    _ = pipeline_model.transform(data_train)
    data_test_transformed = pipeline_model.transform(data_test)
    data_prediction_transformed = pipeline_model.transform(data_prediction)

    model = pipeline_model.stages[-2]

    logging.info(
        "Model weights: %.3f", model.coefficients
    )  # TODO: Find a more generic way, what if model is not parametric
    logging.info(
        "Model intercept: %.3f", model.intercept
    )  # TODO: Find a more generic way, what if model is not parametric

    sf_datalake.io.write_predictions(
        config["MODEL_OUTPUT_DIR"],
        data_test_transformed,
        data_prediction_transformed,
    )
    macro_scores_df, micro_scores_df = sf_datalake.model.explain(
        config, model, data_prediction_transformed
    )
    sf_datalake.io.write_explanations(
        config["MODEL_OUTPUT_DIR"],
        macro_scores_df,
        micro_scores_df,
    )


if __name__ == "__main__":
    _ = sf_datalake.utils.instantiate_spark_session()
    parser = argparse.ArgumentParser(
        description="""
        Run a 'Signaux Faibles' distributed prediction with the chosen set of
        parameters.
        """
    )
    parser.add_argument(
        "--config",
        help="""
        Configuration file name (including '.json' extension). If not provided,
        'base.json' will be used.
        """,
        default="base.json",
    )
    parser.add_argument(
        "--output_directory",
        dest="MODEL_OUTPUT_DIR",
        type=str,
        help="Directory where model predictions and parameters will be saved.",
    )
    parser.add_argument(
        "--sample_ratio",
        dest="SAMPLE_RATIO",
        type=float,
        help="The sample size of the loaded data as a fraction of its complete size.",
    )
    parser.add_argument(
        "--oversampling",
        dest="POSITIVE_OVERSAMPLING_RATIO",
        type=float,
        help="""
        Enforces the ratio of positive observations ("entreprises en défaillance") to be
        the specified ratio.
        """,
    )
    main(parser.parse_args())
