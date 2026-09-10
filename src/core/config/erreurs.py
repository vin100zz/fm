class ConfigInvalide(Exception):
    """Config invalide, incomplete or containing an unknown key.

    Raised at startup, never caught by business code: an invalid config
    must stop the process, not degrade silently.
    """

    def __init__(self, erreurs: list[str]) -> None:
        self.erreurs = erreurs
        super().__init__("\n".join(erreurs))
