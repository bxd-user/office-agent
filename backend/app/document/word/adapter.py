from __future__ import annotations

from app.document.word.analyzer import WordAnalyzer
from app.document.word.filler import WordFiller
from app.document.word.parser import WordParser
from app.document.word.validator import WordValidator
from app.document.word.writer import WordWriter


class WordAdapter:
    def __init__(self):
        self.parser = WordParser()
        self.writer = WordWriter()
        self.analyzer = WordAnalyzer()
        self.filler = WordFiller()
        self.validator = WordValidator()

    def read_text(self, file_path: str):
        return self.parser.read_text(file_path)

    def read_tables(self, file_path: str):
        return self.parser.read_tables(file_path)

    def extract_structure(self, file_path: str):
        return self.parser.extract_structure(file_path)

    def replace_text(self, file_path: str, replacements: dict[str, str], output_path: str):
        return self.writer.replace_text(file_path, replacements, output_path)

    def find_placeholders(self, file_path: str):
        return self.analyzer.find_placeholders(file_path)

    def find_paragraphs_by_keyword(self, file_path: str, keyword: str):
        return self.analyzer.find_paragraphs_by_keyword(file_path, keyword)

    def find_table_by_header(self, file_path: str, headers: list[str]):
        return self.analyzer.find_table_by_header(file_path, headers)

    def write_kv_pairs_to_template(self, file_path: str, mapping: dict[str, str], output_path: str):
        return self.filler.write_kv_pairs_to_template(file_path, mapping, output_path)

    def validate_replacements(self, file_path: str):
        return self.validator.validate_replacements(file_path)