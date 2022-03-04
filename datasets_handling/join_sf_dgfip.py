"""Build a dataset by joining DGFiP and Signaux Faibles data.

The join is made along temporal and SIRET variables.

USAGE
    python join_sf_dgfip.py --sf <sf_dataset> --dgfip <DGFiP_dataset> \
    --output <output_directory>

"""
import argparse
from os import path

import pyspark.sql.functions as F

from sf_datalake.io import load_data
from sf_datalake.transform import stringify_and_pad_siren

parser = argparse.ArgumentParser(
    description="Merge DGFiP and Signaux Faibles datasets into a single one."
)
parser.add_argument(
    "--sf",
    destination="sf_data",
    help="Path to the Signaux Faibles dataset.",
)
parser.add_argument(
    "--dgfip",
    destination="dgfip_data",
    help="Path to the dgfip dataset.",
)
parser.add_argument(
    "--output",
    destination="output",
    help="Path to the output dataset.",
)
parser.add_argument(
    "--diff",
    destination="bilan_periode_diff",
    help="""Difference between 'arrete_bilan_diane' and 'periode' that will be
    used to complete missing diane accounting year end date (used as a join key).
    """,
    type=int,
    default=392,
)

args = parser.parse_args()
# data_paths = {
#     "sf": args.sf_data,
#     "yearly": path.join(args.dgfip_dir, ""),
#     "monthly": path.join(args.dgfip_dir, ""),
# }

## Load datasets

datasets = load_data({"sf": args.sf_data, "dgfip": args.dgfip_data}, file_format="orc")

## Join datasets

df_dgfip = datasets["dgfip"].withColumnRenamed("siren", "siren_dgfip")
df_sf = stringify_and_pad_siren(datasets["sf"]).withColumn(
    "approx_date_fin_exercice",
    F.coalesce(
        F.col("arrete_bilan_diane"),
        F.last_day(F.date_add(F.col("periode"), args.diff)),
    ),
)

df_joined = df_sf.join(
    df_dgfip,
    on=[
        F.year(df_sf.approx_date_fin_exercice) == F.year(df_dgfip.date_fin_exercice),
        df_sf.siren == df_dgfip.siren,
    ],
    how="full_outer",
)

df_joined.write.format("orc").save(path.join(args.output))
