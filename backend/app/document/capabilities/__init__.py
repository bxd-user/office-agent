from app.document.capabilities.compare import compare_document
from app.document.capabilities.extract import extract_content
from app.document.capabilities.fill import fill_document
from app.document.capabilities.locate import locate_targets
from app.document.capabilities.read import read_document
from app.document.capabilities.validate import validate_document
from app.document.capabilities.write import write_document

__all__ = [
    "read_document",
    "extract_content",
    "locate_targets",
    "fill_document",
    "compare_document",
    "validate_document",
    "write_document",
]
