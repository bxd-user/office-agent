from app.document.adapters.word_adapter import WordAdapter


def fill_document(template_path: str, mapping: dict[str, str], output_path: str):
    return WordAdapter().write_kv_pairs_to_template(template_path, mapping, output_path)
