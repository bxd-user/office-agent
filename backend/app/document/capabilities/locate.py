from app.document.adapters.word_adapter import WordAdapter


def locate_targets(file_path: str, keyword: str):
    return WordAdapter().find_paragraphs_by_keyword(file_path, keyword)
