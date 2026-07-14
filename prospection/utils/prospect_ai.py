"""
Recherche AI de prospects via OpenAI, avec repli automatique sur Google Gemini.
"""
import os
import json
import re
import time
import logging
from typing import Dict, List, Any, Optional
from django.conf import settings

OPENAI_MODEL = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"\+?\d[\d\s().-]{6,}\d")
URL_REGEX = re.compile(r"https?://[^\s)]+")


def _get_client():
    """Retourne un client OpenAI configuré."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Le package 'openai' n'est pas installé.")

    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ValueError("OPENAI_API_KEY manquant dans les paramètres.")
    return OpenAI(api_key=api_key)


def _call_ai(prompt: str, system_msg: str, timeout: int = 60) -> str:
    """Appelle OpenAI si configuré, sinon Gemini en repli. Retourne le texte brut."""
    from .openai_utils import _openai_key_valid, _generate_with_gemini

    if not _openai_key_valid():
        logger.info("Clé OpenAI absente ou invalide — repli Gemini pour la recherche prospect.")
        return _generate_with_gemini(prompt, system_msg)

    client = _get_client()
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=8192,
        timeout=timeout,
        response_format={"type": "json_object"},
    )
    raw_text = response.choices[0].message.content
    if not raw_text:
        raise ValueError("Réponse vide de l'API OpenAI")
    return raw_text


def _fallback_parse(text: str) -> Dict[str, List[Dict[str, Any]]]:
    emails = list({m.group(0) for m in EMAIL_REGEX.finditer(text)})
    phones = list({m.group(0) for m in PHONE_REGEX.finditer(text)})
    urls = list({m.group(0) for m in URL_REGEX.finditer(text)})
    return {
        "emails": [{"value": e} for e in emails],
        "phones": [{"value": p} for p in phones],
        "websites": [{"value": u} for u in urls],
        "socials": [],
        "addresses": [],
        "notes": [{"value": text[:1000]}] if text else [],
    }


def _build_research_prompt(
    company_name: str,
    sector: str = "",
    country: str = "",
    language: str = "",
    notes: str = "",
) -> str:
    """Construit un prompt détaillé pour OpenAI."""
    prompt = f"""Tu es un assistant de recherche commerciale expert. Ta mission est de trouver des informations de contact vérifiées et professionnelles sur l'entreprise suivante.

## INFORMATIONS DE L'ENTREPRISE
- Nom de l'entreprise : {company_name}
- Secteur d'activité : {sector or 'Non spécifié'}
- Pays : {country or 'Non spécifié'}
- Langue préférée : {language or 'fr'}
{f'- Instructions supplémentaires : {notes}' if notes else ''}

## OBJECTIFS DE LA RECHERCHE
1. Trouver les informations de contact professionnelles OFFICIELLES et VÉRIFIÉES
2. Privilégier les sources officielles (site web de l'entreprise, pages LinkedIn officielles, annuaires professionnels)
3. Éviter les informations obsolètes, génériques ou non vérifiables
4. Fournir des sources pour chaque information trouvée

## INSTRUCTIONS STRICTES
- Recherche UNIQUEMENT des informations PUBLIQUES et VÉRIFIABLES
- Pour les emails : chercher les contacts généraux (info@, contact@, commercial@) ou dirigeants (prénom.nom@domaine)
- Pour les téléphones : privilégier les numéros fixes professionnels, avec indicatif pays
- Pour les sites web : site officiel principal et pages professionnelles vérifiées
- Pour les réseaux sociaux : pages LinkedIn, Facebook, Twitter OFFICIELLES de l'entreprise
- Pour les adresses : adresse du siège social ou bureaux principaux
- Ignorer les informations non pertinentes, les placeholders, ou les données incertaines

## FORMAT DE RÉPONSE OBLIGATOIRE
Renvoie UNIQUEMENT un objet JSON valide avec cette structure exacte (sans texte avant ou après) :

{{
  "summary": "Résumé concis de l'entreprise et des informations trouvées (2-3 phrases maximum)",
  "confidence": "high|medium|low",
  "data": {{
    "emails": [
      {{
        "value": "email@example.com",
        "label": "Description du contact (ex: Contact général, RH, Commercial)",
        "source_url": "URL source de l'information"
      }}
    ],
    "phones": [
      {{
        "value": "+XXX XXXXXXXXX",
        "label": "Type de numéro (ex: Standard, Service client)",
        "source_url": "URL source"
      }}
    ],
    "websites": [
      {{
        "value": "https://www.example.com",
        "label": "Type de site (ex: Site officiel, Boutique en ligne)",
        "source_url": "URL source"
      }}
    ],
    "socials": [
      {{
        "value": "https://linkedin.com/company/example",
        "label": "Réseau social (ex: LinkedIn officiel, Facebook)",
        "source_url": "URL source"
      }}
    ],
    "addresses": [
      {{
        "value": "Adresse complète avec code postal et ville",
        "label": "Type d'adresse (ex: Siège social, Succursale)",
        "source_url": "URL source"
      }}
    ],
    "notes": [
      {{
        "value": "Informations complémentaires pertinentes (horaires, certifications, etc.)"
      }}
    ]
  }}
}}

## RÈGLES DE VALIDATION
- Si aucune information n'est trouvée pour une catégorie, retourner un tableau vide []
- Ne jamais inventer ou supposer des informations
- Chaque information DOIT avoir une source vérifiable (source_url)
- Les emails doivent être au format valide (xxx@xxx.xxx)
- Les téléphones doivent inclure l'indicatif pays si possible
- Les URLs doivent commencer par http:// ou https://
- La confidence indique le niveau de fiabilité global des informations (high/medium/low)

Réponds UNIQUEMENT avec le JSON, sans aucun texte explicatif avant ou après.
"""
    return prompt


def research_prospect(
    company_name: str,
    sector: str = "",
    extra_query: str = "",
    max_retries: int = 3,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Appelle OpenAI pour effectuer une recherche sur une entreprise.

    Args:
        company_name: Nom de l'entreprise à rechercher
        sector: Secteur d'activité de l'entreprise
        extra_query: Requête supplémentaire contenant pays, langue, notes
        max_retries: Nombre maximum de tentatives en cas d'erreur
        timeout: Timeout en secondes pour la génération

    Returns:
        Dict contenant summary, raw, data avec emails, phones, websites, socials, addresses, notes
    """
    logger.info(f"Début recherche AI pour: {company_name} (secteur: {sector})")

    country = ""
    language = ""
    notes = ""

    if extra_query:
        parts = extra_query.split(";")
        for part in parts:
            part = part.strip()
            if part.lower().startswith("pays:"):
                country = part.split(":", 1)[1].strip()
            elif part.lower().startswith("langue:"):
                language = part.split(":", 1)[1].strip()
            else:
                notes = part if not notes else f"{notes}; {part}"

    prompt = _build_research_prompt(company_name, sector, country, language, notes)

    system_msg = (
        "Tu es un assistant de recherche commerciale expert. "
        "Tu fournis des informations de contact vérifiées au format JSON strict."
    )
    last_error = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Tentative {attempt + 1}/{max_retries} de recherche AI")

            raw_text = _call_ai(prompt, system_msg, timeout=timeout)

            # Nettoyage du JSON
            clean_text = raw_text.strip()
            if clean_text.startswith("```"):
                clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
                clean_text = re.sub(r"\s*```$", "", clean_text)

            parsed = json.loads(clean_text)

            summary = parsed.get("summary", "")
            confidence = parsed.get("confidence", "medium")
            data = parsed.get("data", parsed)

            if not isinstance(data, dict):
                data = _fallback_parse(clean_text)

            logger.info(f"Recherche AI réussie pour {company_name} (confidence: {confidence})")

            return {
                "summary": summary,
                "raw": raw_text,
                "confidence": confidence,
                "data": {
                    "emails": data.get("emails", []),
                    "phones": data.get("phones", []),
                    "websites": data.get("websites", []),
                    "socials": data.get("socials", []),
                    "addresses": data.get("addresses", []),
                    "notes": data.get("notes", []),
                },
            }

        except json.JSONDecodeError as e:
            last_error = f"Erreur parsing JSON: {str(e)}"
            logger.warning(f"Tentative {attempt + 1} - {last_error}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue

        except Exception as e:
            last_error = str(e)
            logger.error(f"Tentative {attempt + 1} - Erreur OpenAI: {last_error}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue

    # Toutes les tentatives ont échoué
    logger.error(f"Échec de la recherche AI pour {company_name} après {max_retries} tentatives: {last_error}")
    return {
        "summary": f"Recherche échouée: {last_error}",
        "raw": "",
        "confidence": "none",
        "data": {
            "emails": [],
            "phones": [],
            "websites": [],
            "socials": [],
            "addresses": [],
            "notes": [],
        },
    }
