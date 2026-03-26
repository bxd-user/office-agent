from app.document.word.comparator import WordComparator


def compare_document(file_a: str, file_b: str):
    return WordComparator().compare(file_a, file_b)
