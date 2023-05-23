"""Build a dataset by joining DGFiP and Signaux Faibles data.

The join is made along temporal and SIREN variables.

USAGE
    python join_datasets.py --sf <sf_dataset> --dgfip_yearly <DGFiP_yearly_dataset> \
    --output <output_directory>

"""
import argparse
import os
import sys
from os import path

import pyspark.sql.functions as F
from pyspark.sql import Window

# isort: off
sys.path.append(path.join(os.getcwd(), "venv/lib/python3.6/"))
sys.path.append(path.join(os.getcwd(), "venv/lib/python3.6/site-packages/"))
# isort: on

# pylint: disable=C0413
import sf_datalake.transform
from sf_datalake.io import load_data

parser = argparse.ArgumentParser(
    description="Merge DGFiP and Signaux Faibles datasets into a single one."
)
parser.add_argument(
    "--sf",
    dest="sf_data",
    help="Path to the Signaux Faibles dataset.",
)
parser.add_argument(
    "--dgfip_yearly",
    help="Path to the DGFiP yearly dataset.",
)
parser.add_argument(
    "--output",
    dest="output",
    help="Path to the output dataset.",
)

args = parser.parse_args()

# Load datasets
datasets = load_data(
    {
        "sf": args.sf_data,
        "dgfip_yearly": args.dgfip_yearly,
    },
    file_format="orc",
)


# Prepare datasets
siren_normalizer = sf_datalake.transform.IdentifierNormalizer(inputCol="siren")
df_dgfip_yearly = siren_normalizer.transform(datasets["dgfip_yearly"])
df_sf = siren_normalizer.transform(datasets["sf"]).withColumn(
    "periode", F.to_date(F.date_trunc("month", F.col("periode")))
)
df_dgfip_yearly = df_dgfip_yearly.withColumn(
    "null_ratio",
    sum([F.when(F.col(c).isNull(), 1).otherwise(0) for c in df_dgfip_yearly.columns])
    / len(df_dgfip_yearly.columns),
)

# Join datasets and drop (time, SIREN) duplicates with the highest null values ratio
w = Window().partitionBy(["siren", "periode"]).orderBy(F.col("null_ratio").asc())

joined_df = (
    df_sf.join(
        df_dgfip_yearly,
        on=(
            (df_sf.siren == df_dgfip_yearly.siren)
            & (df_sf.periode >= df_dgfip_yearly.date_deb_exercice)
            & (df_sf.periode < df_dgfip_yearly.date_fin_exercice)
        ),
        how="inner",
    )
    .drop(df_dgfip_yearly.siren)
    .withColumn("n_row", F.row_number().over(w))
    .filter(F.col("n_row") == 1)
    .drop("n_row")
)

joined_df.write.format("orc").save(args.output)