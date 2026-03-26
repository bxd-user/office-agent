from app.document.selectors.base import BaseSelector


class ExcelSelector(BaseSelector):
    def select(self, file_path: str):
        raise NotImplementedError("ExcelSelector is not implemented yet.")
