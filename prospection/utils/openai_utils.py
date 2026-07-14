"""
Utilitaire IA pour la génération de texte et la recherche de prospects.
Backend principal : OpenAI. Repli automatique : Google Gemini.
"""
import logging
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

OPENAI_MODEL = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')


def _openai_key_valid() -> bool:
    """Vrai si la clé OpenAI semble réellement configurée (et non un placeholder)."""
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or ''
    return api_key.startswith('sk-')


def _get_client():
    """Retourne un client OpenAI configuré."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "Le package 'openai' n'est pas installé. "
            "Ajoutez 'openai' à requirements.txt et relancez pip install."
        )

    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ValueError(
            "La clé API OpenAI n'est pas configurée. "
            "Définissez OPENAI_API_KEY dans les paramètres Django."
        )
    return OpenAI(api_key=api_key)


def _generate_with_gemini(prompt: str, system_instruction: Optional[str] = None) -> str:
    """Génère du texte via l'API REST Google Gemini (repli)."""
    import requests

    api_key = getattr(settings, 'GEMINI_API_KEY', '') or ''
    if not api_key:
        raise ValueError(
            "Aucune clé IA valide configurée. "
            "Définissez OPENAI_API_KEY ou GEMINI_API_KEY dans le fichier .env."
        )

    model = (getattr(settings, 'GEMINI_MODEL', '') or 'models/gemini-1.5-flash')
    model = model.replace('models/', '')
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
    response = requests.post(
        url,
        json={"contents": [{"parts": [{"text": full_prompt}]}]},
        timeout=60,
    )
    if response.status_code != 200:
        raise ValueError(
            f"Erreur Gemini (HTTP {response.status_code}): {response.text[:200]}"
        )
    try:
        text = response.json()['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError, ValueError):
        raise ValueError("Réponse invalide de l'API Gemini.")
    if not text or not text.strip():
        raise ValueError("Réponse vide de l'API Gemini.")
    return text.strip()


def generate_report(prompt: str) -> str:
    """
    Génère un compte rendu via OpenAI, avec repli automatique sur Gemini.

    Args:
        prompt: Le prompt à envoyer à l'API.

    Returns:
        Le texte généré par l'API.

    Raises:
        ValueError: Si le prompt est vide ou si une erreur survient.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Le prompt ne peut pas être vide.")

    system_msg = (
        "Tu es un assistant commercial expert. "
        "Tu génères des comptes rendus professionnels, clairs et concis."
    )

    if not _openai_key_valid():
        logger.info("Clé OpenAI absente ou invalide — utilisation du repli Gemini.")
        return _generate_with_gemini(prompt, system_msg)

    client = _get_client()

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=2048,
        )

        generated_text = response.choices[0].message.content
        if not generated_text or not generated_text.strip():
            raise ValueError("Réponse vide ou invalide de l'API OpenAI.")

        return generated_text.strip()

    except ValueError:
        raise
    except Exception as e:
        logger.error("Erreur lors de la génération OpenAI: %s", str(e), exc_info=True)
        # Repli Gemini en cas d'échec OpenAI (clé révoquée, quota, etc.)
        try:
            logger.info("Échec OpenAI — tentative de repli Gemini.")
            return _generate_with_gemini(prompt, system_msg)
        except Exception as gemini_error:
            logger.error("Repli Gemini également en échec: %s", gemini_error)
            raise ValueError(f"Erreur lors de la génération avec OpenAI: {str(e)}")
