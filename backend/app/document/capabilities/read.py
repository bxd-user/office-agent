from app.document.adapters.word_adapter import WordAdapter


def read_document(file_path: str):
    return WordAdapter().extract_structure(file_path)
