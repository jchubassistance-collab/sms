
import re

from django.core.exceptions import ValidationError


class PasswordComplexityValidator:
    """
    Validateur de complexité du mot de passe.

    Le mot de passe doit contenir :
    - au moins 12 caractères ;
    - au moins une lettre majuscule ;
    - au moins une lettre minuscule ;
    - au moins un chiffre ;
    - au moins un caractère spécial.
    """

    def validate(self, password, user=None):
        errors = []

        if len(password) < 12:
            errors.append(
                "Le mot de passe doit contenir au moins 12 caractères."
            )

        if not re.search(r"[A-Z]", password):
            errors.append(
                "Le mot de passe doit contenir au moins une lettre majuscule."
            )

        if not re.search(r"[a-z]", password):
            errors.append(
                "Le mot de passe doit contenir au moins une lettre minuscule."
            )

        if not re.search(r"\d", password):
            errors.append(
                "Le mot de passe doit contenir au moins un chiffre."
            )

        if not re.search(r"[^\w\s]", password):
            errors.append(
                "Le mot de passe doit contenir au moins un caractère spécial."
            )

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            "Le mot de passe doit contenir au moins 12 caractères, "
            "avec au moins une majuscule, une minuscule, "
            "un chiffre et un caractère spécial."
        )

