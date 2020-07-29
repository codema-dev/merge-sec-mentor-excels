from collections import defaultdict
from typing import Dict, List

import icontract
import numpy as np
import pandas as pd
import prefect
from prefect import task


@icontract.ensure(
    lambda result: np.nan not in result.columns, "Empty value in columns..."
)
def _replace_header_with_row(df: pd.DataFrame, header_row: int) -> pd.DataFrame:

    # Convert Excel row number into equiv pandas row number
    # (i.e. zero indexed and skip one row for header)
    header_row -= 2
    new_first_row = header_row + 1

    df.columns = df.iloc[header_row]
    df = df.iloc[new_first_row:].reset_index(drop=True)
    df.columns.name = ""

    import ipdb

    ipdb.set_trace()
    return df


def _rename_columns_to_unique_names(df: pd.DataFrame) -> pd.DataFrame:

    renamer = defaultdict()

    for col in df.columns[df.columns.duplicated(keep=False)].tolist():
        if col not in renamer:
            renamer[col] = [col + "_0"]
        else:
            renamer[col].append(col + "_" + str(len(renamer[col])))

    return df.rename(
        columns=lambda column_name: renamer[column_name].pop(0)
        if column_name in renamer
        else column_name
    )


def _fillna_to_zero_in_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:

    numeric_columns = df.convert_dtypes().select_dtypes(np.number)
    df.loc[:, numeric_columns.columns] = numeric_columns.fillna(0)
    return df


@task
def transform_sheet(
    excel_sheets_raw: List[pd.DataFrame], header_row: int,
) -> pd.DataFrame:

    excel_sheets_clean = [
        df.pipe(_replace_header_with_row, header_row) for df in excel_sheets_raw
    ]

    return (
        pd.concat(excel_sheets_clean)
        .reset_index(drop=True)
        .replace(["?", " "], np.nan)
        .pipe(_rename_columns_to_unique_names)
        .dropna()
        .pipe(_fillna_to_zero_in_numeric_columns)
    )

