#!/usr/bin/env python3

"""
Convert a Picard CollectInsertSizeMetrics text metrics file into a parquet file.

Mirrors the I/O convention of get_sequali_stats/json_to_parquet.py:
  * read the metrics text from stdin
  * write the parquet output to stdout (binary buffer)
  * pull the fastq id from the FASTQ_ID environment variable and attach it to
    the metadata so each fastq pair has a distinct record.

Picard CollectInsertSizeMetrics text output looks like:

    ## htsjdk.samtools.metrics.StringHeader
    # picard.analysis.CollectInsertSizeMetrics ...
    ## htsjdk.samtools.metrics.StringHeader
    # Started on: ...

    ## METRICS CLASS	picard.analysis.InsertSizeMetrics
    MEDIAN_INSERT_SIZE	MODE_INSERT_SIZE	...	PAIR_ORIENTATION	...
    309	309	...	FR	...

    ## HISTOGRAM	java.lang.Integer
    insert_size	All_Reads.fr_count
    1	2
    ...

We parse the `## METRICS CLASS` section (a tab-delimited header row followed by
one or more data rows) into a dataframe and write it out as parquet. The
`## HISTOGRAM` section and all comment (`#`) / blank lines are ignored.
"""

# Standard library imports
import sys
from io import StringIO
from os import environ

# Data processing imports
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from pandas import DataFrame
from pyarrow import Table

# Section markers used by Picard metrics files
METRICS_CLASS_MARKER = '## METRICS CLASS'
SECTION_MARKER = '##'


def get_input_from_stdin() -> str:
    """Read the raw Picard metrics text from stdin."""
    return sys.stdin.read()


def extract_metrics_class_lines(metrics_text: str) -> list:
    """
    Extract the tab-delimited lines of the `## METRICS CLASS` table.

    Returns the header line plus data rows (as a list of strings), stopping at
    the next `##` section marker (e.g. `## HISTOGRAM`) or end of file. Blank
    lines and comment lines (starting with `#`) inside the section are skipped.
    """
    lines = metrics_text.splitlines()

    in_metrics_class = False
    table_lines = []

    for line in lines:
        stripped = line.strip()

        if not in_metrics_class:
            # Look for the start of the METRICS CLASS section
            if stripped.startswith(METRICS_CLASS_MARKER):
                in_metrics_class = True
            continue

        # We are inside the METRICS CLASS section.
        # A new section marker (## ...) ends the table.
        if stripped.startswith(SECTION_MARKER):
            break

        # Skip blank lines and any remaining comment lines robustly
        if stripped == '' or stripped.startswith('#'):
            continue

        table_lines.append(line)

    return table_lines


def metrics_to_dataframe(metrics_text: str) -> DataFrame:
    """
    Parse the Picard `## METRICS CLASS` table into a pandas DataFrame.
    """
    table_lines = extract_metrics_class_lines(metrics_text)

    if len(table_lines) < 2:
        raise ValueError(
            "Could not find a Picard '## METRICS CLASS' table with a header "
            "row and at least one data row in the provided metrics text."
        )

    # The first line is the header, subsequent lines are data rows.
    metrics_df: DataFrame = pd.read_csv(
        StringIO('\n'.join(table_lines)),
        sep='\t',
    )

    return metrics_df


def metrics_to_pyarrow(metrics_text: str) -> Table:
    """
    Convert Picard CollectInsertSizeMetrics text to a PyArrow Table.
    """
    metrics_df = metrics_to_dataframe(metrics_text)

    # Attach the fastq id from the environment so each record is uniquely
    # identifiable, mirroring the sequali json_to_parquet metadata handling.
    if 'FASTQ_ID' in environ:
        metrics_df['fastqId'] = environ['FASTQ_ID']

    return pa.Table.from_pandas(metrics_df)


if __name__ == '__main__':
    # Read the Picard metrics text from stdin
    metrics_text = get_input_from_stdin()

    # Convert the metrics text to a PyArrow Table
    metrics_table = metrics_to_pyarrow(metrics_text)

    # Write the PyArrow Table to stdout
    pq.write_table(metrics_table, sys.stdout.buffer)
