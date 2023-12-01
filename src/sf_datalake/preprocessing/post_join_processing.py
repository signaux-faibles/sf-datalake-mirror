"""Carry out some pre-processing over the "sf" dataset.

1) Adds new columns to dataset by:
- computing averages, lags, etc. of existing variables.
- computing new features derived from existing ones.
2) Aggregates data at the SIREN level.

An output dataset will be stored as split orc files under the chosen output directory.

USAGE
    python sf_preprocessing.py <input_directory> <output_directory> \
-t [time_computations_config_filename] -a [aggregation_config_filename]

"""
import os
import sys
from os import path
from typing import Dict, List

from pyspark.ml import PipelineModel, Transformer

# isort: off
sys.path.append(path.join(os.getcwd(), "venv/lib/python3.6/"))
sys.path.append(path.join(os.getcwd(), "venv/lib/python3.6/site-packages/"))
# isort: on

# pylint: disable=C0413
import sf_datalake.io
import sf_datalake.transform

####################
# Loading datasets #
####################

parser = sf_datalake.io.data_path_parser()
parser.description = "Build a dataset with aggregated SIREN-level data and new time \
averaged/lagged variables."

parser.add_argument("-c", "--configuration", help="Configuration file.", required=True)
parser.add_argument(
    "--output_format", default="orc", help="Output dataset file format."
)


args = parser.parse_args()
configuration = sf_datalake.configuration.ConfigurationHelper(args.configuration)
input_ds = sf_datalake.io.load_data(
    {"input": args.input}, file_format="csv", sep=",", infer_schema=False
)["input"]

# Set every column name to lower case (if not already).
df = input_ds.toDF(*(col.lower() for col in input_ds.columns))

#################
# Create target #
#################

# pylint: disable=E1136
building_steps = [
    sf_datalake.transform.TargetVariable(
        inputCol=configuration.learning.target["judgment_date_col"],
        outputCol=configuration.learning.target["class_col"],
        n_months=configuration.learning.target["n_months"],
    ),
]

##########################
# Missing Value Handling #
##########################

if not configuration.preprocessing.drop_missing_values:
    raise NotImplementedError(
        " VectorAssembler in spark < 2.4.0 doesn't handle including missing values."
    )

missing_values_handling_steps = []
if configuration.preprocessing.fill_default_values:
    missing_values_handling_steps.append(
        sf_datalake.transform.MissingValuesHandler(
            inputCols=list(configuration.preprocessing.fill_default_values),
            value=configuration.preprocessing.fill_default_values,
        ),
    )
if configuration.preprocessing.fill_imputation_strategy:
    imputation_strategy_features: Dict[str, List[str]] = {}
    for (
        feature,
        strategy,
    ) in configuration.preprocessing.fill_imputation_strategy.items():
        imputation_strategy_features.setdefault(strategy, []).append(feature)

    missing_values_handling_steps.extend(
        sf_datalake.transform.MissingValuesHandler(
            inputCols=features,
            strategy=strategy,
        )
        for strategy, features in imputation_strategy_features.items()
    )


#####################
# Time Computations #
#####################

# pylint: disable=unsubscriptable-object
lag_features = []
diff_features = []
time_computations: List[Transformer] = []
for feature, n_months in configuration.preprocessing.time_aggregation["lag"].items():
    time_computations.append(
        sf_datalake.transform.LagOperator(inputCol=feature, n_months=n_months)
    )
    lag_features.append(f"{feature}_lag{n_months}m")
for feature, n_months in configuration.preprocessing.time_aggregation["diff"].items():
    time_computations.append(
        sf_datalake.transform.DiffOperator(inputCol=feature, n_months=n_months)
    )
    diff_features.append(f"{feature}_diff{n_months}m")
for feature, n_months in configuration.preprocessing.time_aggregation["mean"].items():
    time_computations.append(
        sf_datalake.transform.MovingAverage(inputCol=feature, n_months=n_months)
    )

# Fill Missing values created by lag computation

lag_filling_strategy = "bfill"  # Maybe to add into configuration files

time_computations.extend(
    sf_datalake.transform.MissingValuesHandler(
        inputCols=features,
        strategy=lag_filling_strategy,
    )
    for features in (lag_features + diff_features)
)


output_ds = PipelineModel(
    stages=building_steps + missing_values_handling_steps + time_computations
).transform(df)


sf_datalake.io.write_data(output_ds, args.output, args.output_format)
