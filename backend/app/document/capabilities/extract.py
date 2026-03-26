from app.document.adapters.word_adapter import WordAdapter


def extract_content(file_path: str):
    return WordAdapter().extract_structure(file_path)
