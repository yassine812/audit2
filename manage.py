#!/usr/bin/env python
"""Commande d'administration Django."""

import os
import sys


def main() -> None:
    """Point d'entrée manage.py."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django n'est pas installé ou l'environnement Python n'est pas activé."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
