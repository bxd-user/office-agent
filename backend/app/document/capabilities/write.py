from app.document.adapters.word_adapter import WordAdapter


def write_document(file_path: str, replacements: dict[str, str], output_path: str):
    return WordAdapter().replace_text(file_path, replacements, output_path)
