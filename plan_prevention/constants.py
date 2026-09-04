"""Catalogue des 14 risques prédéfinis pour le Plan de Prévention Simplifié (PDP).

Basé sur le document de référence: Plan de prévention simplifié AB Serve.doc
"""

DEFAULT_PREDEFINED_RISKS = [
    {
        "code": "pieton",
        "libelle": "Circulation et déplacement piéton dans l'enceinte de l'E.U. (chute de plain-pied, trébuchement, collision, etc.)",
        "mesures_default": "",
        "ordre": 1,
    },
    {
        "code": "vehicules",
        "libelle": "Circulation de véhicules et des engins de manutention (heurt, collision, écrasement, etc.)",
        "mesures_default": "",
        "ordre": 2,
    },
    {
        "code": "manutention_manuelle",
        "libelle": "Manutention manuelle de charge lourde ou difficilement accessible",
        "mesures_default": "",
        "ordre": 3,
    },
    {
        "code": "manutention_mecanisee",
        "libelle": "Manutention mécanisée (chariot élévateur, transgerbeur, palan, transpalette, etc.)",
        "mesures_default": "",
        "ordre": 4,
    },
    {
        "code": "stockage_gerbage",
        "libelle": "Stockage, gerbage (stockage en hauteur, effondrement, chutes d'objets, etc.)",
        "mesures_default": "",
        "ordre": 5,
    },
    {
        "code": "mecanismes_mouvement",
        "libelle": "Mécanismes en mouvement (machines, appareils, etc.)",
        "mesures_default": "",
        "ordre": 6,
    },
    {
        "code": "manipulation_pieces",
        "libelle": "Manipulation de pièces et petits outillages",
        "mesures_default": "",
        "ordre": 7,
    },
    {
        "code": "outils_portatifs",
        "libelle": "Utilisation d'outils portatifs et mobiles (électriques, pneumatiques, etc.)",
        "mesures_default": "",
        "ordre": 8,
    },
    {
        "code": "projections",
        "libelle": "Risques de projections (meules, produits chimiques, soufflettes, soudure, etc.)",
        "mesures_default": "",
        "ordre": 9,
    },
    {
        "code": "produits_chimiques",
        "libelle": "Emploi et stockage de produits chimiques (toxiques, corrosifs, inflammables, etc.)",
        "mesures_default": "",
        "ordre": 10,
    },
    {
        "code": "incendie_explosion",
        "libelle": "Incendie / Explosion (explosion, fumées, charges de batteries, etc.)",
        "mesures_default": "",
        "ordre": 11,
    },
    {
        "code": "ambiance_physique",
        "libelle": "Ambiance physique (bruit, poussières, vibrations, luminosité, chaleur, etc.)",
        "mesures_default": "",
        "ordre": 12,
    },
    {
        "code": "haute_tension",
        "libelle": "Travaux à proximité d'installations électriques haute tension",
        "mesures_default": "",
        "ordre": 13,
    },
    {
        "code": "autres",
        "libelle": "Autres risques (à préciser)",
        "mesures_default": "",
        "ordre": 14,
    },
]
