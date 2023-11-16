"""Utility functions."""

import datetime as dt
from typing import List

import pyspark.sql
import pyspark.sql.types as T
from pyspark.sql import SparkSession
from pyspark.sql import Window as W
from pyspark.sql import functions as F


def get_spark_session():
    """Creates or gets a SparkSession object."""
    spark = SparkSession.builder.getOrCreate()
    spark.conf.set("spark.shuffle.blockTransferService", "nio")
    spark.conf.set("spark.driver.maxResultSize", "1300M")
    return spark


def numerical_columns(df: pyspark.sql.DataFrame) -> List[str]:
    """Returns a DataFrame's numerical data column names.

    Args:
        df: The input DataFrame.

    Returns:
        A list of column names.

    """
    numerical_types = (
        T.ByteType,
        T.DecimalType,
        T.DoubleType,
        T.FloatType,
        T.IntegerType,
        T.LongType,
        T.ShortType,
    )
    return [
        field.name
        for field in df.schema.fields
        if isinstance(field.dataType, numerical_types)
    ]


def extract_column_names(df: pyspark.sql.DataFrame, assembled_column: str) -> List[str]:
    """Get inner column names from an assembled column.

    Here, "assembled" means: that has been transformed using a VectorAssembler.

    Args:
        df: A DataFrame
        assembled_column: The "assembled" column name.

    Returns:
        A list of column names.

    """
    column_metadata = df.schema[assembled_column].metadata["ml_attr"]
    columns = [None] * column_metadata["num_attrs"]
    for _, variables in column_metadata["attrs"].items():
        for variable_dict in variables:
            columns[variable_dict["idx"]] = variable_dict["name"]
    return columns


def to_date(str_date: str, date_format="%Y-%m-%d") -> dt.date:
    """Convert string date to datetime.date object"""
    return dt.datetime.strptime(str_date, date_format).date()


# pylint: disable=R0913 R0914
def merge_asof(
    df_left: pyspark.sql.DataFrame,
    df_right: pyspark.sql.DataFrame,
    on: str,
    by: str = None,
    tolerance: float = None,
    direction: str = "backward",
) -> pyspark.sql.DataFrame:
    """
    Perform a merge by key distance.
    This is similar to a left-join except that we match
    on nearest key rather than equal keys.
    Both DataFrames must be sorted by the key.

    Note:
        This function performs an asof merge
        on two DataFrames based on a specified column 'on'.
        It supports grouping by additional columns specified in 'by'.
        The 'tolerance' parameter allows for merging
        within a specified difference range.
        The 'direction' parameter determines the direction of the asof merge.

    Args:
        df_left : The left DataFrame to be merged.
        df_right : The right DataFrame to be merged.
        on : The column on which to merge the DataFrames.
        by (optional): The column(s) to group by before merging.
        tolerance (optional): The maximum difference allowed for asof merging in days.
        direction : The direction of asof merging ('backward', 'forward', or 'nearest').

    Returns:
        DataFrame: A DataFrame resulting from the asof merge.

    Example:
        >>> merged_df = merge_asof(
                                df_left,
                                df_right,
                                on='period',
                                by='siren',
                                tolerance=100,
                                direction='backward'
                                )
    """

    def backward(w0, stru1):
        # Implementation of backward merge logic
        return add_diff(F.last(stru1, True).over(w0))

    def forward(w0, stru1):
        # Implementation of forward merge logic
        return add_diff(
            F.first(stru1, True).over(w0.rowsBetween(0, W.unboundedFollowing))
        )

    def nearest(w0, stru1):
        # Implementation of nearest merge logic
        return F.sort_array(F.array(backward(w0, stru1), forward(w0, stru1))).getItem(0)

    def add_diff(col):
        # Add a 'diff' column to the DataFrame
        return F.struct(
            F.abs(F.col(on) - col[on]).alias("diff"), col[on].alias(on), col[c].alias(c)
        )

    # Convert to unix timestamp
    df_left = df_left.withColumn(
        "period", F.unix_timestamp("period", format="yyyy-mm-dd")
    )
    df_right = df_right.withColumn(
        "period", F.unix_timestamp("period", format="yyyy-mm-dd")
    )
    if tolerance:
        if tolerance == 365:
            # 365 is a year for people but the exact number according to unix is 365,24
            tolerance_unix = 31556926
        else:
            tolerance_unix = tolerance * 24 * 60 * 60

    # Handle cases where 'by' is not specified
    df_r = df_right if by else df_right.withColumn("_by", F.lit(1))
    df_l = df_left if by else df_left.withColumn("_by", F.lit(1))
    df_l = df_l.withColumn("_df_l", F.lit(True))
    if by is None:
        by = ["_by"]
    elif isinstance(by, str):
        by = [by]
    else:
        assert all(isinstance(s, str) for s in by), TypeError(
            "All elements of `by` should by strings"
        )

    # Perform a full outer join on specified columns
    join_on = [on] + by
    df = df_l.join(df_r, join_on, "full")

    # Set up the window specification for partitioning and ordering
    w0 = W.partitionBy(*by).orderBy(on)

    # Iterate over columns in df_right for merging
    for c in set(df_right.columns) - set(join_on):
        stru1 = F.when(~F.isnull(c), F.struct(on, c))
        window_functions: dict = {
            "backward": backward(w0, stru1),
            "forward": forward(w0, stru1),
            "nearest": nearest(w0, stru1),
        }
        stru2 = window_functions[direction]

        # Apply tolerance if specified
        if tolerance:
            diff_col = F.abs(F.col(on) - stru2[on]).alias("diff")
            c_col = F.when(diff_col <= tolerance_unix, stru2[c]).otherwise(F.col(c))
            df = df.withColumn(c, c_col)
        else:
            # If no tolerance specified, directly use the result of stru2
            df = df.withColumn(c, stru2[c])

    # Filter to make the merge and drop temporary columns from the result
    df = df.filter("_df_l").drop("_df_l", "_by")

    # Convert unix timestamp to str
    df = df.withColumn(on, F.from_unixtime(df.period, "yyyy-MM-dd HH:mm:ss"))
    df = df.withColumn(on, F.to_date(F.col(on)))

    return df
