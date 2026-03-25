class DocumentError(Exception):
    pass


class UnsupportedDocumentTypeError(DocumentError):
    pass


class DocumentReadError(DocumentError):
    pass


class DocumentWriteError(DocumentError):
    pass


class DocumentVerifyError(DocumentError):
    pass
