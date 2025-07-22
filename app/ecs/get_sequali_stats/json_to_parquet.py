#!/usr/bin/env python3

# Standard library imports
from copy import copy
import json
import sys
from os import environ

# Data processing imports
import pyarrow as pa
from pandas import DataFrame
from pyarrow import Table
import pyarrow.parquet as pq
import pandas as pd


# Handling functions
def get_inputs_from_stdin():
    return json.load(sys.stdin)


def update_percentiles(row_iter_: pd.Series) -> pd.Series:
    row_iter = copy(row_iter_)
    for key in ['percentiles', 'front_percentiles', 'end_percentiles']:
        row_iter[key] = list(map(
            lambda percentile_list: {
                percentile_list[0]: percentile_list[1]
            },
            row_iter[key]
        ))

    return row_iter


def update_adapter_content(row_iter_: pd.Series) -> pd.Series:
    row_iter = copy(row_iter_)
    row_iter['adapters_read1'] = list(map(
        lambda adapter_read: {
            adapter_read[0]: adapter_read[1]
        },
        row_iter['adapters_read1']
    ))

    if 'adapters_read2' in row_iter:
        row_iter['adapters_read2'] = list(map(
            lambda adapter_read: {
                adapter_read[0]: adapter_read[1]
            },
            row_iter['adapters_read2']
        ))

    return row_iter


def update_tile_content(row_iter_: pd.Series) -> pd.Series:
    row_iter = copy(row_iter_)
    row_iter['normalized_per_tile_averages'] = list(map(
        lambda percentile_list: {
            percentile_list[0]: percentile_list[1]
        },
        row_iter['normalized_per_tile_averages']
    ))

    return row_iter


def json_to_pyarrow(json_data) -> Table:
    """
    Convert Sequali JSON data to a PyArrow Table.
    'per_tile_quality', 'per_tile_quality_read2'
    """
    # Convert the JSON data to a Pandas DataFrame
    # We wrap in a list to ensure it's treated as a single record
    sequali_df: DataFrame = pd.DataFrame([json_data])

    # Sequali JSON data contains some odd structures for some of the fields.
    # For per_position_mean_quality_and_spread / per_position_mean_quality_and_spread_read2,
    # We need to convert the percentiles from a list of lists where each sublist contains
    # 2 elements, 'name' and list of values to a list of dictionaries where the name is the key
    sequali_df['per_position_mean_quality_and_spread'] = sequali_df['per_position_mean_quality_and_spread'].apply(
        lambda row_iter_: update_percentiles(row_iter_)
    )
    if 'per_position_mean_quality_and_spread_read2' in sequali_df.columns:
        sequali_df['per_position_mean_quality_and_spread_read2'] = sequali_df['per_position_mean_quality_and_spread_read2'].apply(
            lambda row_iter_: update_percentiles(row_iter_)
        )

    # Likewise for adapter_content_from_overlap, the adapter_read1 and adapter_read2 fields
    # Are actually a list of lists when they should be a list of dictionaries
    sequali_df['adapter_content_from_overlap'] = sequali_df['adapter_content_from_overlap'].apply(
        lambda row_iter_: update_adapter_content(row_iter_)
    )

    # Likewise for the per_tile_quality and per_tile_quality_read2 fields
    # The normalized_per_tile_averages is a list of lists when it should be a list of dictionaries
    sequali_df['per_tile_quality'] = sequali_df['per_tile_quality'].apply(
        lambda row_iter_: update_tile_content(row_iter_)
    )

    if 'per_tile_quality_read2' in sequali_df.columns:
        sequali_df['per_tile_quality_read2'] = sequali_df['per_tile_quality_read2'].apply(
            lambda row_iter_: update_tile_content(row_iter_)
        )

    # Add the fastq id from the environment to the metadata
    sequali_df['meta']['fastqId'] = environ['FASTQ_ID']

    # Drop nanopore metrics
    if 'nanopore_metrics' in sequali_df.columns:
        sequali_df.drop(columns=['nanopore_metrics'], inplace=True)

    # Convert the Pandas DataFrame to a PyArrow Table
    return pa.Table.from_pandas(sequali_df)


if __name__ == '__main__':
    # Import JSON data from stdin
    json_data = get_inputs_from_stdin()

    # Convert the JSON data to a PyArrow Table
    sequali_table = json_to_pyarrow(json_data)

    # Write the PyArrow Table to stdout
    pq.write_table(sequali_table, sys.stdout.buffer)
