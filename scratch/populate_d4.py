import os, sys, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from reclamation_client.models import ReclamationClient, AnalyseCausesDoubleAxeD4

rec = ReclamationClient.objects.filter(reference='REC2608010').first()
if rec:
    d4, created = AnalyseCausesDoubleAxeD4.objects.get_or_create(reclamation=rec)
    d4.cause_principale_non_detection = "Non détection du défaut au contrôle visuel (Absence d'utilisation systématique de la loupe & gamme imprecise)."
    d4.cause_principale_technique = "Mix des pièces chez le client final suite à l'absence d'identification unitaire au poste d'assemblage."
    
    d4.pourquoi_non_detection = [
        {
            "branche": 1,
            "chain": [
                {"etape": 1, "pourquoi": "L'opérateur n'a pas détecté le défaut"},
                {"etape": 2, "pourquoi": "L'opérateur n'a pas procédé par comparaison (deux pièces à la fois)"},
                {"etape": 3, "pourquoi": "Pas demandé dans la gamme"},
                {"etape": 4, "pourquoi": "Eviter les détériorations des pièces entre elles"},
                {"etape": 5, "pourquoi": "Principe général sur le site"},
            ],
            "statut": "avere",
            "justification": "Avéré : on augmente le niveau de détection lorsqu'on prend deux pièces à la fois"
        },
        {
            "branche": 2,
            "chain": [
                {"etape": 1, "pourquoi": "L'opérateur n'a pas détecté le défaut"},
                {"etape": 2, "pourquoi": "L'opérateur n'a pas utilisé la loupe"},
                {"etape": 3, "pourquoi": "Pas demandé dans la gamme"},
                {"etape": 4, "pourquoi": "Jugement que le défaut est détectable à l'oeil nu"},
            ],
            "statut": "avere",
            "justification": "Avéré : la loupe améliore le niveau de détection"
        },
        {
            "branche": 3,
            "chain": [
                {"etape": 1, "pourquoi": "L'opérateur n'a pas détecté le défaut"},
                {"etape": 2, "pourquoi": "L'opérateur n'a pas utilisé la loupe"},
                {"etape": 3, "pourquoi": "Pas demandé dans la gamme"},
                {"etape": 4, "pourquoi": "Le défaut est visible par différence de lumière en l'inclinant"},
            ],
            "statut": "non_avere",
            "justification": "Non avéré : la méthode est peu fiable"
        },
        {
            "branche": 4,
            "chain": [
                {"etape": 1, "pourquoi": "L'opérateur n'a pas détecté le défaut"},
                {"etape": 2, "pourquoi": "Le défaut est difficilement détectable"},
                {"etape": 3, "pourquoi": "Le défaut est trop petit pour être détecté visuellement"},
            ],
            "statut": "non_avere",
            "justification": "Non avéré : l'opérateur a écarté des pièces présentant des défauts plus petits"
        }
    ]

    d4.pourquoi_technique = [
        {
            "branche": 1,
            "chain": [
                {"etape": 1, "pourquoi": "Mix des pièces (sécurisés et pas) chez le Client final"},
                {"etape": 2, "pourquoi": "Pas d'identification unitaire sur les pièces"},
                {"etape": 3, "pourquoi": "Identification sur l'unité de Manutention"},
            ],
            "statut": "avere",
            "justification": "Avéré : un marquage unitaire aurait permis de distinguer les pièces"
        },
        {
            "branche": 2,
            "chain": [
                {"etape": 1, "pourquoi": "Client final réclame sur des faces différentes que prévu à la gamme"},
                {"etape": 2, "pourquoi": "La sécurisation concerne les surfaces critiques"},
                {"etape": 3, "pourquoi": "Les défauts sur les autres surfaces n'impactent pas la fonctionnalité"},
            ],
            "statut": "avere",
            "justification": "Avéré : les deux surfaces sont identifiées sur la gamme"
        }
    ]
    d4.save()
    print("D4 test data populated successfully for REC2608010!")
