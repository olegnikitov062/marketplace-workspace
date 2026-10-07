"""Fixed failure categories for the isolated runner; never format exceptions."""
from unittest import TextTestResult

SQL_CATEGORIES = {
    '55P03': 'LOCK_UNAVAILABLE', '57014': 'QUERY_CANCELLED',
    '40001': 'SERIALIZATION', '40P01': 'DEADLOCK', '42501': 'PERMISSION',
    '23514': 'CHECK_CONSTRAINT', '23503': 'FOREIGN_KEY', '23505': 'UNIQUE',
}
CATEGORIES = frozenset((*SQL_CATEGORIES.values(), 'ASSERTION', 'OTHER'))


def category(error):
    current = error
    for _ in range(4):
        state = getattr(current, 'sqlstate', None)
        if type(state) is str and state in SQL_CATEGORIES:
            return SQL_CATEGORIES[state]
        current = getattr(current, '__cause__', None)
        if current is None:
            break
    return 'ASSERTION' if isinstance(error, AssertionError) else 'OTHER'


class DiagnosticResult(TextTestResult):
    def diagnostic(self, error):
        self.stream.writeln()
        self.stream.writeln('E209_DIAGNOSTIC=' + category(error))

    def addError(self, test, err):
        self.diagnostic(err[1])
        super().addError(test, err)

    def addFailure(self, test, err):
        self.diagnostic(err[1])
        super().addFailure(test, err)
