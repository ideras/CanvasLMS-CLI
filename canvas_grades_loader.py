"""
This module provides the CanvasGradesLoader class for loading and validating student grades
from a CSV file, as well as handling associated Markdown and PDF evaluation files. It supports
file existence checks, column validation, and conversion of Markdown files to PDF format using
the MarkdownToPDFConverter utility.
Classes:
    CanvasGradesLoader: Loads grades from a CSV file, validates data, checks for associated
    files, and converts Markdown comments to PDF files.
Dependencies:
    - os
    - typing.List
    - pathlib.Path
    - pandas
    - markdown_converter.MarkdownToPDFConverter
"""
import os
from typing import List, Final, Optional
from pathlib import Path
import pandas as pd
from markdown_converter import MarkdownToPDFConverter

class CanvasGradesLoader:
    """
    CanvasGradesLoader is responsible for loading grades from a CSV file into memory and applying data validations.
    Validations include checking if the file exists and converting Markdown content to PDF format.
    """
    def __init__(self, filepath: str, root_dir: Optional[str]):
        self.filepath = filepath

        self.root_dir: str = root_dir if root_dir else str(Path(filepath).resolve().parent)

        self.valid_columns: Final[List[str]] = [
            "canvas_id", "student_id", "grade", "comment", "comments", 
            "md_exam_file1", "pdf_exam_file1", "md_exam_file2",
            "pdf_exam_file2", "md_eval_file", "pdf_eval_file"
        ]

        self._md_file_columns: Final[List[str]] = [
            "md_exam_file1", "md_exam_file2", "md_eval_file"
        ]

        self._pdf_file_columns: Final[List[str]] = [
            "pdf_exam_file1", "pdf_exam_file2", "pdf_eval_file"
        ]

        self._data_frame = None
        self._load_file()
        self._check_files_exists()
        self._convert_markdown_files()

    @property
    def data_frame(self) -> pd.DataFrame | None:
        return self._data_frame
    
    @property
    def md_file_columns(self) -> List[str]:
        return self._md_file_columns
    
    @property
    def pdf_file_columns(self) -> List[str]:
        return self._pdf_file_columns

    def _load_file(self) -> None:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"CSV file not found: {self.filepath}")

        try:
            self._data_frame = pd.read_csv(self.filepath)

            rename_map = {
                "canvas_id": "student_id",
                "comments": "comment",
            }

            self._data_frame.rename(columns=rename_map, inplace=True)

            invalid = [c for c in self._data_frame.columns if c not in self.valid_columns]
            if invalid:
                raise ValueError(f"Invalid column(s) in CSV file: {', '.join(invalid)}")

            self._data_frame = self._data_frame.dropna(subset=['student_id', 'grade'])
            self._data_frame['student_id'] = self._data_frame['student_id'].astype(str).str.strip()
            self._data_frame['grade'] = pd.to_numeric(self._data_frame['grade'], errors='coerce')
            self._data_frame = self._data_frame.dropna(subset=['grade'])

        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {e}") from e

    def _check_files_exists(self) -> None:
        file_columns = self._pdf_file_columns + self._md_file_columns

        if not any(column in self._data_frame.columns for column in file_columns):
            return

        for index, row in self._data_frame.iterrows():
            for column_name in file_columns:
                file_ext = '.md' if column_name.startswith('md_') else '.pdf'
                file_type = 'markdown' if column_name.startswith('md_') else 'PDF'
                filepath = str(row.get(column_name, '')).strip()

                if not filepath:
                    continue

                filepath_obj = Path(filepath)

                if not filepath_obj.is_absolute():
                    filepath_obj = Path(self.root_dir) / filepath_obj
                    filepath = str(filepath_obj)
                    self._data_frame.at[index, column_name] = filepath

                if os.path.exists(filepath):
                    if not filepath.lower().endswith(file_ext):
                        raise ValueError(f"Invalid {file_type} file: {filepath}")
                else:
                    raise FileNotFoundError(f"{file_type.capitalize()} file: '{filepath}' doesn't exists")

    def _convert_markdown_files(self) -> None:
        has_md_file_columns = False

        for column_name in self._md_file_columns:
            if column_name in self._data_frame.columns:
                has_md_file_columns = True

        if not has_md_file_columns:
            return

        md_converter = MarkdownToPDFConverter()

        for index, row in self._data_frame.iterrows():
            for column_name in self._md_file_columns:
                if column_name in self._data_frame.columns:
                    md_sfilepath = str(row.get('md_eval_file', '')).strip()

                    if not md_sfilepath:
                        continue

                    md_filepath = Path(md_sfilepath)
                    pdf_filepath = md_filepath.with_suffix(".pdf")

                    converted_pdf = md_converter.convert_file(str(md_filepath), str(pdf_filepath))

                    if not converted_pdf:
                        raise RuntimeError(f"Cannot convert file '{md_sfilepath}'")
                    pdf_column_name = column_name.replace("md_", "pdf_")

                    self._data_frame.at[index, pdf_column_name] = str(pdf_filepath)