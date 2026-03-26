from app.document.adapters.word_adapter import WordAdapter


def validate_document(file_path: str):
    return WordAdapter().validate_replacements(file_path)
