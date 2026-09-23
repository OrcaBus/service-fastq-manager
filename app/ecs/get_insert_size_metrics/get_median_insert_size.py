#!/usr/bin/env python3

"""
Read the insert-size summary metrics from a Picard CollectInsertSizeMetrics
parquet file (produced by metrics_to_parquet.py) and emit an insert-size
estimate JSON object.

  * Input: path to the parquet file as the first CLI argument.
  * Output: writes
        { "insertSizeEstimate": <median>, "insertSizeStdEstimate": <stddev> }
    as JSON to stdout.

Deriving the estimates from the parquet (rather than re-parsing the Picard text)
means we reuse the single, tested parsing path in metrics_to_parquet.py and
avoid a second, brittle text parser.
"""

# Standard library imports
import json
import os
import sys

# Data processing imports
import pandas as pd

# The Picard InsertSizeMetrics columns we surface as top-level QC estimates
MEDIAN_INSERT_SIZE_COLUMN = 'MEDIAN_INSERT_SIZE'
STANDARD_DEVIATION_COLUMN = 'STANDARD_DEVIATION'


def get_column_value(metrics_df: pd.DataFrame, column: str, parquet_path: str):
    """
    Return the value of `column` from the first row of the Picard metrics parquet.
    """
    if column not in metrics_df.columns:
        raise ValueError(
            f"Could not find column '{column}' in the "
            f"Picard metrics parquet '{parquet_path}'."
        )

    # Picard writes a single summary row per orientation; take the first row.
    value = metrics_df[column].iloc[0]

    # Normalise numpy scalar -> native python number for clean JSON output.
    return value.item()


def get_insert_size_estimates(parquet_path: str) -> dict:
    """
    Read MEDIAN_INSERT_SIZE and STANDARD_DEVIATION from the Picard metrics parquet.
    """
    metrics_df = pd.read_parquet(parquet_path)

    if metrics_df.empty:
        raise ValueError(
            f"Picard metrics parquet '{parquet_path}' contained no data rows."
        )

    return {
        "insertSizeEstimate": get_column_value(
            metrics_df, MEDIAN_INSERT_SIZE_COLUMN, parquet_path
        ),
        "insertSizeStdEstimate": get_column_value(
            metrics_df, STANDARD_DEVIATION_COLUMN, parquet_path
        ),
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(
            "Usage: get_median_insert_size.py <picard_metrics.parquet>",
            file=sys.stderr,
        )
        sys.exit(1)

    estimates = get_insert_size_estimates(sys.argv[1])

    # Serialise fully to a string first, then write + flush in one explicit step.
    # Reading the parquet pulls in the Arrow C++ runtime (via pandas/pyarrow);
    # its resources are torn down at interpreter shutdown. If our stdout is a
    # pipe whose reader (e.g. `aws s3 cp -`) closes early, the implicit flush at
    # shutdown can race with that C++ teardown and the runtime aborts with
    # "terminate called without an active exception" (SIGABRT / exit 134).
    #
    # To avoid that race entirely we flush explicitly here, swallow a broken
    # pipe as a clean exit, and then hard-exit with os._exit so the Arrow C++
    # atexit destructors never run against a closed stdout.
    payload = json.dumps(estimates)

    try:
        sys.stdout.write(payload)
        sys.stdout.flush()
    except BrokenPipeError:
        # Reader went away before we finished writing; nothing more to do.
        os._exit(0)

    # Skip normal interpreter shutdown (and the Arrow C++ atexit teardown) to
    # avoid the SIGABRT race described above. stdout is already flushed.
    os._exit(0)
