class ImportInvalide(Exception):
    """Provided data is invalid, incomplete, or references something
    that doesn't exist. Raised at startup, matching ConfigInvalide's
    contract in core/config/erreurs.py: stop, list every problem found.
    """

    def __init__(self, erreurs: list[str]) -> None:
        self.erreurs = erreurs
        super().__init__("\n".join(erreurs))
