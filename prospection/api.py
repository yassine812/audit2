from rest_framework.authtoken.models import Token 
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from datetime import datetime
from django.conf import settings
from .utils.openai_utils import generate_report
from dateutil import tz
from django.db import transaction
import pytz
from django.contrib.auth import authenticate, get_user_model, logout as django_logout
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_200_OK
)
from django.shortcuts import get_object_or_404
from .models import *
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from rest_framework import status
import json
from django.http import JsonResponse
import requests
import logging
from .utils.client_utils import get_base_url

User = get_user_model()

logger = logging.getLogger(__name__)

@api_view(["POST"])
@permission_classes((AllowAny,))
def mobile_login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    remember_me = request.data.get("remember_me", False)

    if not username or not password:
        return Response(
            {'error': 'Both username and password are required'},
            status=HTTP_400_BAD_REQUEST
        )

    user = authenticate(username=username, password=password)
    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=HTTP_404_NOT_FOUND
        )

    # Crée ou récupère le token
    token, created = Token.objects.get_or_create(user=user)
    
    if not remember_me:
        request.session.set_expiry(0)

    return Response({
        'token': token.key,
        'user_id': user.pk,
        'username': user.username,
        'email': user.email,
        'created': created,  
        'expires_in': 24 * 3600 if not remember_me else None,
        'is_superuser': user.is_superuser,
        'is_RC': user.is_RC
    }, status=HTTP_200_OK)
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_logout(request):
    request.user.auth_token.delete()  
    django_logout(request) 
    return Response({"success": True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def societe_list(request):
    user = request.user
    if user.is_superuser:
        societes = Societe.objects.all().order_by('nom')
    elif user.is_RO:
        societes = Societe.objects.filter(id__in=user.societes.values_list('id', flat=True)).order_by('nom')
    elif user.is_RC:
        societes = Societe.objects.filter(id=user.societe.id).order_by('nom')
    else:  # Commercial
        societes = Societe.objects.none() 
    
    data = [{'id': s.id, 'nom': s.nom} for s in societes]
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_calendar_actions(request):
    action_type = request.GET.get('type', 'all') 
    date_filter = request.GET.get('date_filter', 'planned') 
    
    societe_id = request.GET.get('societe_id')
    
    user = request.user
    if user.is_superuser:
        queryset = Action.objects.all().order_by('date_heure_planifie')
    elif user.is_RO:
        queryset = Action.objects.filter(id__in=user.actions.values_list('id', flat=True)).order_by('date_heure_planifie')
    elif user.is_RC:
        queryset = Action.objects.filter(
            Q(created_by__societe=user.societe) | 
            Q(pilote__societe=user.societe)).order_by('date_heure_planifie')
    else:  # Commercial
        queryset = Action.objects.filter(
            Q(created_by=user) | 
            Q(pilote=user))
    
    if action_type != 'all':
        if action_type == 'calls':
            queryset = queryset.filter(is_Appel=True)
        elif action_type == 'emails':
            queryset = queryset.filter(is_Email=True)
        elif action_type == 'meetings':
            queryset = queryset.filter(is_RV=True)
    
    if societe_id:
        queryset = queryset.filter(societe_id=societe_id)
    
    marked_dates = {}
    actions_by_date = {}
    
    for action in queryset:
        date_key = None
        
        if date_filter == 'planned':
            date_key = action.date_heure_planifie.date().isoformat()
        else:
            if action.date_heure_realiser:
                date_key = action.date_heure_realiser.date().isoformat()
            else:
                continue  
        
        if date_key not in marked_dates:
            marked_dates[date_key] = {
                'marked': True,
                'dotColor': '#50cebb',
                'actions': []
            }
        
        marked_dates[date_key]['actions'].append({
            'id': action.id,
            'subject': action.sujet,
            'type': 'Call' if action.is_Appel else 'Email' if action.is_Email else 'Meeting',
            'time': action.date_heure_planifie.strftime('%d/%m/%Y, %H:%M'),
            'competed_date': action.date_heure_realiser.strftime('%d/%m/%Y, %H:%M') if action.date_heure_realiser else None,
            'status': action.etat,
            'company': action.societe.nom if action.societe else None,
            'client': action.entreprise.nom if action.entreprise else None,
            'created_by': action.created_by.username if action.created_by else None
        })
    
    return Response({
        'marked_dates': marked_dates,
        'actions': actions_by_date
    })
    
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def action_detail(request, pk):
    user = request.user
    
    if user.is_superuser:
        queryset = Action.objects.all().order_by('date_heure_planifie')
    elif user.is_RO:
        queryset = Action.objects.filter(id__in=user.actions.values_list('id', flat=True)).order_by('date_heure_planifie')
    elif user.is_RC:
        queryset = Action.objects.filter(
            Q(created_by__societe=user.societe) | 
            Q(pilote__societe=user.societe)).order_by('date_heure_planifie')
    else:  # Commercial
        queryset = Action.objects.filter(
            Q(created_by=user) | 
            Q(pilote=user))
    
    action = get_object_or_404(queryset, pk=pk)
    
    data = {
        'id': action.id,
        'sujet': action.sujet,
        'compte_rendu': action.compte_rendu,
        'notes': action.notes,
        'is_Appel': action.is_Appel,
        'is_Email': action.is_Email,
        'is_RV': action.is_RV,
        'etat': action.etat,
        'date_heure_planifie': action.date_heure_planifie,
        'date_heure_realiser': action.date_heure_realiser,
        'created_by': {
            'id': action.created_by.id,
            'username': action.created_by.username
        } if action.created_by else None,
        'pilote': {
            'id': action.pilote.id,
            'username': action.pilote.username
        } if action.pilote else None,
        'societe': {
            'id': action.societe.id,
            'nom': action.societe.nom
        } if action.societe else None,
    }
    
    return Response(data)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def action_list_create(request):
    user = request.user
    
    if request.method == 'GET':
        queryset = Action.objects.all().order_by('date_heure_planifie')
        
        if not user.is_superuser:
            if user.is_RO:
                queryset = queryset.filter(id__in=user.actions.values_list('id', flat=True))
            if user.is_RC:
                queryset = queryset.filter(societe=user.societe)
            else:
                queryset = queryset.filter(created_by=user)
        
        data = [
            {
                'id': action.id,
                'sujet': action.sujet,
                'date_heure': action.date_heure,
                'date_heure_planifie': action.date_heure_planifie,
                'date_heure_realiser': action.date_heure_realiser,
                'compte_rendu': action.compte_rendu,
                'notes': action.notes,
                'etat': action.etat,
                'is_Appel': action.is_Appel,
                'is_Email': action.is_Email,
                'is_RV': action.is_RV,
                'entreprise': action.entreprise.id if action.entreprise else None,
                'created_by': action.created_by.id if action.created_by else None,
                'pilote': action.pilote.id if action.pilote else None,
                'societe': action.societe.id if action.societe else None,
            } for action in queryset
        ]
        
        return Response(data)

    elif request.method == 'POST':
        data = request.data.copy()
        
        # Validation minimale
        for field in ['sujet', 'date_heure_planifie', 'entreprise']:
            if not data.get(field):
                return Response({'error': f"Le champ {field} est obligatoire"}, status=status.HTTP_400_BAD_REQUEST)

        entreprise_type = data.get('entreprise_type', 'client')
        entreprise_id = data.get('entreprise')

        entreprise = None
        societe = None
        # Récupérer éventuellement la société fournie par le formulaire (id ou nom)
        societe_input = data.get('societe')
        societe_from_form = None
        if societe_input:
            try:
                # Essayer comme ID
                societe_from_form = Societe.objects.filter(id=int(str(societe_input))).first()
            except (ValueError, TypeError):
                societe_from_form = None
            if not societe_from_form:
                # Essayer comme nom
                societe_from_form = Societe.objects.filter(nom=str(societe_input).strip()).first()

        # Déterminer entreprise et societe selon type
        if entreprise_type == 'client':
            # Chercher d'abord en local
            entreprise = Entreprise.objects.filter(num_compte=entreprise_id, is_CLT=True).first()
            if entreprise:
                # Toujours prendre la société de l'entreprise existante
                societe = entreprise.societe
            else:
                # Création via SAGE nécessitant une filiale: utiliser celle fournie dans le formulaire
                societe = societe_from_form
                if not societe:
                    return Response({'error': "Veuillez spécifier la société (id ou nom) pour créer le client"}, status=status.HTTP_400_BAD_REQUEST)
                
                base_url = get_base_url(societe.id)
                if not base_url:
                    return Response({'error': 'Configuration de la société non trouvée'}, status=status.HTTP_400_BAD_REQUEST)
                
                fact_url = f"{settings.SAGE_API_HOST}/WebServices100/{base_url}/TiersService/rest/Clients/{entreprise_id}"
                headers = {'Authorization': settings.SAGE_API_TOKEN, 'Accept': 'application/json'}
                try:
                    client_response = requests.get(fact_url, headers=headers, timeout=10)
                    client_response.raise_for_status()
                    client_data = client_response.json()
                    entreprise = Entreprise.objects.create(
                        nom=client_data.get('Intitule', f'Client {entreprise_id}'),
                        adresse=client_data.get('Adresse', ''),
                        telephone=client_data.get('Telephone', ''),
                        email=client_data.get('Email', ''),
                        num_compte=entreprise_id,
                        is_CLT=True,
                        is_Prospect=False,
                        is_Concurent=False,
                        societe=societe,
                        secteur_activite='',
                        date=datetime.now(tz=tz.gettz(settings.TIME_ZONE))
                    )
                except requests.RequestException as e:
                    return Response({'error': f"Erreur lors de la récupération des données du client: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Prospect par ID
            entreprise = Entreprise.objects.filter(id=entreprise_id, is_Prospect=True).first()
            if not entreprise:
                return Response({'error': f"Le prospect avec l'ID {entreprise_id} n'existe pas ou n'est pas un prospect"}, status=status.HTTP_400_BAD_REQUEST)
            societe = entreprise.societe

        # Déterminer pilote à partir de la filiale
        pilote = None
        if societe:
            pilote = User.objects.filter(societe=societe, is_RC=True).first()

        action_data = {
            'sujet': data['sujet'],
            'date_heure_planifie': data['date_heure_planifie'],
            'date_heure_realiser': data.get('date_heure_realiser'),
            'compte_rendu': data.get('compte_rendu', ''),
            'notes': data.get('notes', ''),
            'etat': data.get('etat', ''),
            'entreprise': entreprise,
            'created_by': user,
            'is_Appel': data.get('is_Appel', False),
            'is_Email': data.get('is_Email', False),
            'is_RV': data.get('is_RV', False),
            'societe': societe,
            'pilote': pilote,
        }

        try:
            new_action = Action.objects.create(**action_data)
            
            # Réponse avec tous les champs
            response_data = {
                'id': new_action.id,
                'sujet': new_action.sujet,
                'date_heure': new_action.date_heure,
                'date_heure_planifie': new_action.date_heure_planifie,
                'date_heure_realiser': new_action.date_heure_realiser,
                'compte_rendu': new_action.compte_rendu,
                'notes': new_action.notes,
                'etat': new_action.etat,
                'is_Appel': new_action.is_Appel,
                'is_Email': new_action.is_Email,
                'is_RV': new_action.is_RV,
                'entreprise': new_action.entreprise.id if new_action.entreprise else None,
                'created_by': new_action.created_by.id,
                'pilote': new_action.pilote.id if new_action.pilote else None,
                'societe': new_action.societe.id if new_action.societe else None,
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la création de l\'action: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def action_count(request):
    user = request.user
    filter_params = Q()

    if not user.is_superuser:
        if user.is_RO:
            ids = list(user.societes.values_list('id', flat=True))
            filter_params &= Q(Q(societe_id__in=ids) | Q(created_by_id__in=ids))
        elif user.is_RC:
            filter_params &= Q(societe=user.societe)
        else:
            filter_params &= Q(created_by=user)

    counts = {
        'calls': Action.objects.filter(filter_params & Q(is_Appel=True)).count(),
        'emails': Action.objects.filter(filter_params & Q(is_Email=True)).count(),
        'appointments': Action.objects.filter(filter_params & Q(is_RV=True)).count(),
    }

    return Response(counts)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def entreprise_list(request):
    is_clt_param = request.query_params.get('is_CLT')
    is_concurent_param = request.query_params.get('is_Concurent')
    
    entreprises = Entreprise.objects.all().order_by('nom')
    
    if is_clt_param is not None:
        is_clt = is_clt_param.lower() == 'true'
        entreprises = entreprises.filter(is_CLT=is_clt)
    
    if is_concurent_param is not None:
        is_concurent = is_concurent_param.lower() == 'true'
        entreprises = entreprises.filter(is_Concurent=is_concurent)
    
    if is_clt_param is None and is_concurent_param is None:
        entreprises = entreprises.filter(Q(is_CLT=True) | Q(is_Prospect=True))

    data = [
        {
            'id': e.id,
            'nom': e.nom,
            'is_CLT': e.is_CLT,
            'is_Prospect': e.is_Prospect,
            'num_compte': e.num_compte if hasattr(e, 'num_compte') else '',
            'societe': e.societe.nom if e.societe else '',
        }
        for e in entreprises
    ]
    
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    request.user.auth_token.delete()
    django_logout(request)
    return Response({"success": True})

# Clients API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_customers_api(request):
    try:
        search_term = request.GET.get("q", "").strip().lower()
        if len(search_term) < 2:
            return JsonResponse({"results": []})

        # Build list of societes to search (id, name, base)
        societes_to_search = []
        show_societe = bool(getattr(request.user, 'is_RO', False) or getattr(request.user, 'is_superuser', False))
        if getattr(request.user, 'is_superuser', False):
            societes_to_search = [(s.id, s.nom, get_base_url(s.id)) 
                                for s in Societe.objects.all() 
                                if get_base_url(s.id)]
        elif getattr(request.user, 'is_RO', False):
            societes_to_search = [(s.id, s.nom, get_base_url(s.id)) 
                                for s in request.user.societes.all() 
                                if get_base_url(s.id)]
        else:
            if not request.user.societe_id:
                return JsonResponse({"error": "Société non reconnue"}, status=400)
            base = get_base_url(request.user.societe_id)
            if not base:
                return JsonResponse({"error": "Base non configurée pour cette société"}, status=400)
            societes_to_search = [(request.user.societe_id, 
                                 getattr(request.user.societe, 'nom', ''), 
                                 base)]

        # 1. Recherche dans la base de données locale
        local_results = []
        societe_ids = [sid for sid, _, _ in societes_to_search]
        local_filters = (Q(nom__icontains=search_term) | 
                        Q(num_compte__icontains=search_term) |
                        Q(num_compte__istartswith=search_term))
        
        clients_local = Entreprise.objects.filter(
            local_filters, 
            is_CLT=True,
            societe_id__in=societe_ids
        ).select_related('societe')[:20]  # Limiter les résultats

        for client in clients_local:
            txt = f"{client.num_compte} - {client.nom}" if client.num_compte else client.nom
            societe_nom = getattr(client.societe, 'nom', '')
            if show_societe and societe_nom:
                txt = f"{txt} - {societe_nom}"
            
            local_results.append({
                'id': client.num_compte or str(client.id),
                'text': txt,
                'nom': client.nom,
                'email': client.email,
                'telephone': client.telephone,
                'societe': societe_nom,
                'source': 'local'
            })

        # 2. Recherche dans Sage
        sage_results = []
        seen_sage_ids = set()
        
        for sid, sname, base in societes_to_search:
            try:
                url = f"{settings.SAGE_API_HOST}/WebServices100/{base}/TiersService/rest/Clients"
                headers = {'Authorization': settings.SAGE_API_TOKEN, 'Accept': 'application/json'}
                
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code != 200:
                    continue
                    
                clients = response.json() or []
                for client in clients:
                    if not isinstance(client, dict):
                        continue
                        
                    numero_tiers = str(client.get("NumeroTiers", "")).lower()
                    intitule = str(client.get("Intitule", "")).lower()
                    
                    if (search_term in numero_tiers or search_term in intitule):
                        sage_id = f"{sid}:{client.get('NumeroTiers')}"
                        if sage_id in seen_sage_ids:
                            continue
                            
                        seen_sage_ids.add(sage_id)
                        txt = f"{client.get('NumeroTiers')} - {client.get('Intitule')}"
                        if show_societe and sname:
                            txt = f"{txt} - {sname}"
                            
                        sage_results.append({
                            'id': client.get("NumeroTiers"),
                            'text': txt,
                            'nom': client.get("Intitule"),
                            'email': client.get("Email"),
                            'societe': sname,
                            'telephone': client.get("Telephone1") or client.get("Telephone2"),
                            'NumeroTiers': client.get("NumeroTiers"),
                            'Intitule': client.get("Intitule"),
                            'Email': client.get("Email"),
                            'Telephone': client.get("Telephone1") or client.get("Telephone2"),
                            'source': 'sage'
                        })
                        
            except Exception as e:
                logger.error(f"Erreur API Sage ({sname}): {str(e)}")
                continue

        # 3. Fusionner et dédupliquer les résultats
        seen = set()
        final_results = []
        
        # Ajouter d'abord les résultats locaux
        for item in local_results:
            key = item.get('id')
            if key not in seen:
                seen.add(key)
                final_results.append(item)
                
        # Puis les résultats Sage qui ne sont pas déjà présents
        for item in sage_results:
            key = item.get('id')
            if key not in seen:
                seen.add(key)
                final_results.append(item)

        # Trier par nom
        final_results.sort(key=lambda x: x.get('nom', '').lower())
        
        # Limiter à 20 résultats au total
        final_results = final_results[:20]

        return JsonResponse({
            "results": final_results,
        })

    except Exception as e:
        logger.error(f"Erreur inattendue dans get_active_customers: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Une erreur est survenue lors de la recherche des clients."}, status=500)
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_client_details_api(request, client_id):
    """Fetch detailed information for a specific client including facturation details"""
    headers = {
        'Authorization': settings.SAGE_API_TOKEN,
        'Accept': 'application/json'
    }
    try:
        societe = request.GET.get('societe')
        base_candidates = []
        if societe:
            societe_id = Societe.objects.filter(nom=societe).first()
            base_candidates = [get_base_url(societe_id.id)]
        else:
            return JsonResponse({"error": "Société non reconnue"}, status=400)

        client_response = None
        for base in base_candidates:
            fact_url = f"{settings.SAGE_API_HOST}/WebServices100/{base}/TiersService/rest/Clients/{client_id}"
            try:
                r = requests.get(fact_url, headers=headers, timeout=10)
            except Exception:
                r = None
            if r is not None and r.status_code == 200:
                client_response = r
                break
        if client_response is None:
            return JsonResponse({"error": "Erreur lors de la récupération des informations du client"}, status=400)

        # Parsing JSON tolérant (correction Expecting value: line 1 column 1)
        try:
            client_data = client_response.json() if client_response.content else {}
        except ValueError:
            client_data = {}

        # Fallback local: chercher l'entreprise
        ent = None
        cid_raw = str(client_id or '').strip()
        # 1) Essayer par PK si client_id est un entier
        try:
            ent_pk = int(cid_raw)
            ent = Entreprise.objects.filter(pk=ent_pk, societe_id=societe_id.id).first()
        except (TypeError, ValueError):
            ent = None
        # 2) Variantes num_compte: exact, iexact, sans zéros de tête, icontains
        if not ent and cid_raw:
            cid_nz = cid_raw.lstrip('0') or cid_raw
            ent = (
                Entreprise.objects.filter(num_compte__iexact=cid_raw, societe_id=societe_id.id).first() or
                Entreprise.objects.filter(num_compte__iexact=cid_nz, societe_id=societe_id.id).first() or
                Entreprise.objects.filter(num_compte__icontains=cid_raw, societe_id=societe_id.id).first()
            )
        # 3) Par nom (fallback)
        if not ent and cid_raw:
            ent = Entreprise.objects.filter(nom__iexact=cid_raw, societe_id=societe_id.id).first()

        def coalesce(*vals):
            for v in vals:
                if v is None:
                    continue
                s = str(v).strip()
                if s:
                    return s
            return ""

        # Extraire champs SAGE avec clés alternatives
        numero_tiers = coalesce(client_data.get("NumeroTiers"), getattr(ent, 'num_compte', None))
        intitule = coalesce(client_data.get("Intitule"), getattr(ent, 'nom', None))

        # Adresse: composer si besoin
        adr = coalesce(
            client_data.get("Adresse"),
            " ".join(filter(None, [
                str(client_data.get("AdresseLigne1", "")),
                str(client_data.get("AdresseLigne2", "")),
                str(client_data.get("CodePostal", "")),
                str(client_data.get("Ville", ""))
            ])).strip(),
            getattr(ent, 'adresse', None)
        )

        email = coalesce(client_data.get("Email"), getattr(ent, 'email', None))
        tel = coalesce(
            client_data.get("Telephone"), client_data.get("Telephone1"), client_data.get("Telephone2"),
            getattr(ent, 'telephone', None)
        )

        result = {
            "NumeroTiers": numero_tiers,
            "Intitule": intitule,
            "fact_adresse": adr,
            "fact_email": email,
            "fact_tel": tel,
        }
        # Ajouter un warning si tout est vide pour informer le front
        if not any([numero_tiers, intitule, adr, email, tel]):
            result["warning"] = "Aucune donnée trouvée pour ce client (SAGE/local)."
        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

#event
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def create_event(request):
    user = request.user
    data = request.data.copy()
    
    required_fields = ['nom', 'lieu', 'secteur_activite', 'date_heure_planifie', 'type']
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
            return Response(
                {'success': False, 'error': f'Champs obligatoires manquants: {", ".join(missing_fields)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    if data['type'] not in ['interne', 'externe']:
        return Response(
            {'error': "Le type d'événement doit être 'InternalEvent' ou 'ExternalEvent'"},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    entreprise_id = data.get('entreprise')
    if entreprise_id == 'null' or entreprise_id == '':
        entreprise_id = None

    societe = None
    pilote = None
    societe_input = data.get('societe')
    if societe_input:
        try:
            # Essayer comme ID
            societe = Societe.objects.filter(id=int(str(societe_input))).first()
            rc_user = User.objects.filter(societe=societe, is_RC=True).first()
            pilote = rc_user
        except (ValueError, TypeError):
            societe = None
        if not societe:
            # Essayer comme nom
            societe = Societe.objects.filter(nom=str(societe_input).strip()).first()
            rc_user = User.objects.filter(societe=societe, is_RC=True).first()
            pilote = rc_user

    entreprise = None
    if data['type'] == 'interne' and entreprise_id:
        try:
            entreprise = Entreprise.objects.get(num_compte=entreprise_id, is_CLT=True)
        except Entreprise.DoesNotExist:
            if not societe:
                return Response(
                    {'error': 'Société non spécifiée'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            base_url = get_base_url(societe.id)
            if not base_url:
                return Response(
                    {'error': 'Configuration de la société non trouvée'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            fact_url = f"{settings.SAGE_API_HOST}/WebServices100/{base_url}/TiersService/rest/Clients/{entreprise_id}"
            headers = {
                'Authorization': settings.SAGE_API_TOKEN,
                'Accept': 'application/json'
            }
            
            try:
                client_response = requests.get(fact_url, headers=headers, timeout=10)
                if client_response.status_code != 200:
                    return Response(
                        {'error': f'Impossible de récupérer les informations du client {entreprise_id}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
                client_data = client_response.json()
                
                # Créer le client directement
                entreprise = Entreprise.objects.create(
                    nom=client_data.get('Intitule', f'Client {entreprise_id}'),
                    adresse=client_data.get('Adresse', ''),
                    telephone=client_data.get('Telephone', ''),
                    email=client_data.get('Email', ''),
                    num_compte=entreprise_id,
                    is_CLT=True,
                    is_Prospect=False,
                    is_Concurent=False,
                    societe=societe,
                    secteur_activite='',
                    date=datetime.now(tz=tz.gettz(settings.TIME_ZONE))
                )
                    
            except requests.RequestException as e:
                return Response(
                    {'error': f'Erreur de connexion lors de la récupération des données du client: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {'error': f'Erreur lors de la création du client: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
    elif data['type'] == 'externe' and entreprise_id:
        # Pour les prospects, on utilise directement l'ID
        try:
            entreprise = Entreprise.objects.get(
                id=entreprise_id,
                is_Prospect=True
            )
        except Entreprise.DoesNotExist:
            return Response(
                {'error': f"Le prospect avec l'ID {entreprise_id} n'existe pas ou n'est pas un prospect"},
                status=status.HTTP_400_BAD_REQUEST
            )
            

    event_data = {
        'nom': data['nom'],
        'lieu': data['lieu'],
        'secteur_activite': data['secteur_activite'],
        'type': data['type'],
        'categorie': data.get('categorie', ''),
        'date_heure_planifie': data['date_heure_planifie'],
        'date_heure_realiser': data.get('date_heure_realiser'),
        'notes': data.get('notes', ''),
        'etat': data.get('etat', ''),
        'entreprise_id': entreprise.id if entreprise else None,
        'created_by': user,
        'societe': societe,
        'pilote': pilote,
    }

    try:
        new_event = Evenement.objects.create(**event_data)
        
        pilote = None
        if new_event.societe:
            pilote = get_user_model().objects.filter(is_RC=True, societe=new_event.societe).first()
            
        response_data = {
            'id': new_event.id,
            'nom': new_event.nom,
            'lieu': new_event.lieu,
            'secteur_activite': new_event.secteur_activite,
            'type': new_event.type,
            'categorie': new_event.categorie,
            'date_heure_planifie': new_event.date_heure_planifie,
            'date_heure_realiser': new_event.date_heure_realiser,
            'notes': new_event.notes,
            'etat': new_event.etat,
            'entreprise': new_event.entreprise.id if new_event.entreprise else None,
            'created_by': new_event.created_by.id,
            'pilote': pilote.id if pilote else None,
            'societe': new_event.societe.id if new_event.societe else None,
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_entreprises_by_type(request):
    is_clt = request.GET.get('is_CLT', None)
    
    queryset = Entreprise.objects.all().order_by('nom')
    
    if is_clt is not None:
        is_clt = is_clt.lower() == 'true'
        if is_clt == True:
            queryset = queryset.filter(is_CLT=True)
        else:
            queryset = queryset.filter(is_CLT=False, is_Prospect=True)
    
    data = [{
        'id': entreprise.id,
        'nom': entreprise.nom,
        'is_CLT': entreprise.is_CLT,
    } for entreprise in queryset]
    
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_prospects(request):
    """Recherche de prospects par nom (autocomplete)."""
    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return Response([])

    queryset = Entreprise.objects.filter(is_Prospect=True, nom__icontains=q).order_by('nom')[:20]

    data = [{
        'id': entreprise.id,
        'nom': entreprise.nom,
        'ville': entreprise.adresse or '',
    } for entreprise in queryset]

    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def event_counts(request):
    user = request.user
    
    internal_filter = Q(type='interne')
    external_filter = Q(type='externe')
    
    if user.is_superuser:
        pass
    elif user.is_RO:
        internal_filter &= Q(societe__in=user.societes.all())
        external_filter &= Q(societe__in=user.societes.all())
    elif hasattr(user, 'is_RC') and user.is_RC:
        internal_filter &= Q(societe=user.societe)
        external_filter &= Q(societe=user.societe)
    else:
        internal_filter &= Q(created_by=user)
        external_filter &= Q(created_by=user)
    
    internal_count = Evenement.objects.filter(internal_filter).count()
    external_count = Evenement.objects.filter(external_filter).count()
    
    return Response({
        'internalEvents': internal_count,
        'externalEvents': external_count
    }, status=status.HTTP_200_OK)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_calendar_events(request):
    try:
        action_type = request.GET.get('type', 'all')
        date_filter = request.GET.get('date_filter', 'planned')
        societe_id = request.GET.get('societe_id')
        event_type = request.GET.get('event_type', 'all')

        user = request.user

        is_RO = getattr(user, 'is_RO', False)
        is_rc = getattr(user, 'is_RC', False)
        user_societe = getattr(user, 'societe', None)
        user_societes_qs = getattr(user, 'societes', None)

        # Query for Actions
        if user.is_superuser:
            action_queryset = Action.objects.all().order_by('date_heure_planifie')
        elif is_RO and user_societes_qs is not None:
            action_queryset = Action.objects.filter(societe__in=user_societes_qs.all()).order_by('date_heure_planifie')
        elif is_rc and user_societe is not None:
            action_queryset = Action.objects.filter(
                Q(created_by__societe=user_societe) |
                Q(pilote__societe=user_societe)
            ).order_by('date_heure_planifie')
        else:  # Commercial
            action_queryset = Action.objects.filter(
                Q(created_by=user) |
                Q(pilote=user)
            )

        if action_type == 'none':
            action_queryset = Action.objects.none()

        if action_type not in ('all', 'none'):
            if action_type == 'calls':
                action_queryset = action_queryset.filter(is_Appel=True)
            elif action_type == 'emails':
                action_queryset = action_queryset.filter(is_Email=True)
            elif action_type == 'meetings':
                action_queryset = action_queryset.filter(is_RV=True)

        if societe_id:
            action_queryset = action_queryset.filter(societe_id=societe_id)

        # Query for Events
        if user.is_superuser:
            event_queryset = Evenement.objects.all().order_by('date_heure_planifie')
        elif is_RO and user_societes_qs is not None:
            event_queryset = Evenement.objects.filter(societe__in=user_societes_qs.all()).order_by('date_heure_planifie')
        elif is_rc and user_societe is not None:
            event_queryset = Evenement.objects.filter(
                Q(created_by__societe=user_societe) |
                Q(pilote__societe=user_societe)
            ).order_by('date_heure_planifie')
        else:  # Commercial
            event_queryset = Evenement.objects.filter(
                Q(created_by=user) |
                Q(pilote=user)
            )

        if event_type == 'none':
            event_queryset = Evenement.objects.none()

        if event_type not in ('all', 'none'):
            event_queryset = event_queryset.filter(type=event_type)

        if societe_id:
            event_queryset = event_queryset.filter(societe_id=societe_id)

        marked_dates = {}

        # Process Actions
        for action in action_queryset:
            planned_dt = getattr(action, 'date_heure_planifie', None)
            done_dt = getattr(action, 'date_heure_realiser', None)

            if date_filter == 'planned':
                if not planned_dt:
                    continue
                date_key = planned_dt.date().isoformat()
            else:
                if not done_dt:
                    continue
                date_key = done_dt.date().isoformat()

            if date_key not in marked_dates:
                marked_dates[date_key] = {
                    'marked': True,
                    'dotColor': '#50cebb',
                    'items': []
                }

            status_display = get_action_status_display(action)

            if action.is_Appel:
                action_type_label = 'Call'
            elif action.is_RV:
                action_type_label = 'Meeting'
            elif action.is_Email:
                action_type_label = 'Email'
            else:
                action_type_label = 'Other'

            marked_dates[date_key]['items'].append({
                'type': 'action',
                'id': action.id,
                'subject': action.sujet,
                'action_type': action_type_label,
                'time': planned_dt.strftime('%H:%M') if planned_dt else None,
                'full_date': planned_dt.strftime('%d/%m/%Y, %H:%M') if planned_dt else None,
                'completed_date': done_dt.strftime('%d/%m/%Y, %H:%M') if done_dt else None,
                'status': status_display,
                'pilote': action.pilote.username if action.pilote else None,
                'company': action.societe.nom if action.societe else None,
                'client': action.entreprise.nom if action.entreprise else None,
                'created_by': action.created_by.username if action.created_by else None,
                'compte_rendu': action.compte_rendu,
                'notes': action.notes
            })

        # Process Events
        for event in event_queryset:
            planned_dt = getattr(event, 'date_heure_planifie', None)
            done_dt = getattr(event, 'date_heure_realiser', None)

            if date_filter == 'planned':
                if not planned_dt:
                    continue
                date_key = planned_dt.date().isoformat()
            else:
                if not done_dt:
                    continue
                date_key = done_dt.date().isoformat()

            if date_key not in marked_dates:
                marked_dates[date_key] = {
                    'marked': True,
                    'dotColor': '#50cebb',
                    'items': []
                }

            marked_dates[date_key]['items'].append({
                'type': 'event',
                'id': event.id,
                'name': event.nom,
                'event_type': event.type,
                'time': planned_dt.strftime('%H:%M') if planned_dt else None,
                'full_date': planned_dt.strftime('%d/%m/%Y, %H:%M') if planned_dt else None,
                'completed_date': done_dt.strftime('%d/%m/%Y, %H:%M') if done_dt else None,
                'location': event.lieu,
                'sector': event.secteur_activite,
                'status': event.get_etat_display() if event.etat else None,
                'pilote': event.pilote.username if event.pilote else None,
                'company': event.societe.nom if event.societe else None,
                'enterprise': event.entreprise.nom if event.entreprise else None,
                'created_by': event.created_by.username if event.created_by else None,
                'notes': event.notes
            })

        return Response({'marked_dates': marked_dates})
    except Exception as e:
        logger.exception('Erreur get_calendar_events: %s', str(e))
        return Response({'error': 'Internal server error while fetching calendar events'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
def get_action_status_display(action):
    if action.is_Appel:
        choices = dict(action.ETAT_CHOICES_APPEL)
    elif action.is_Email:
        choices = dict(action.ETAT_CHOICES_EMAIL)
    elif action.is_RV:
        choices = dict(action.ETAT_CHOICES_RENDEZ_VOUS)
    else:
        choices = {}
    
    return choices.get(action.etat, action.etat or '-')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_notifications(request):
    """Endpoint pour l'app mobile - 5 dernières notifications"""
    notifications = NotificationUtilisateur.objects.filter(
        utilisateur=request.user
    ).select_related('notification').order_by('-notification__date_heure')[:5]
    
    data = [{
        'id': n.id,
        'message': n.notification.message,
        'is_read': n.est_lu,
        'date': n.notification.date_heure.strftime('%Y-%m-%d %H:%M'),
        'notification_id': n.notification.id
    } for n in notifications]
    
    return Response({'notifications': data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_mark_as_read(request):
    """Marquer une notification comme lue depuis l'app mobile"""
    notification_id = request.data.get('notification_id')
    try:
        notification = NotificationUtilisateur.objects.get(
            id=notification_id,
            utilisateur=request.user
        )
        if not notification.est_lu:
            notification.est_lu = True
            notification.save()
        return Response({'status': 'success'})
    except NotificationUtilisateur.DoesNotExist:
        return Response({'status': 'error'}, status=404)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_fcm_token(request):
    token = request.data.get('token')
    if not token:
        return Response({'status': 'error', 'message': 'Token is required'}, status=400)
    
    FCMDevice.objects.update_or_create(
        registration_id=token,
        defaults={
            'user': request.user,
            'active': True
        }
    )
    
    return Response({'status': 'success'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def create_prospect(request):
    user = request.user
    data = request.data.copy()
    
    if not data.get('nom'):
        return Response(
            {'success': False, 'error': 'Le nom du prospect est obligatoire'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Déterminer la société pour le prospect
        societe = None
        is_RO_like = bool(getattr(user, 'is_superuser', False) or getattr(user, 'is_RO', False))
        if is_RO_like:
            societe_input = data.get('societe')
            if not societe_input:
                return Response(
                    {'success': False, 'error': 'La société est obligatoire pour créer un prospect'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Résoudre id ou nom
            try:
                societe = Societe.objects.filter(id=int(str(societe_input))).first()
            except (ValueError, TypeError):
                societe = None
            if not societe:
                societe = Societe.objects.filter(nom=str(societe_input).strip()).first()
            if not societe:
                return Response(
                    {'success': False, 'error': "Société introuvable"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            societe = getattr(user, 'societe', None)
            if not societe:
                return Response(
                    {'success': False, 'error': "Impossible de déterminer la société de l'utilisateur"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        prospect_data = {
            'nom': data['nom'],
            'is_Prospect': True,
            'societe': societe,
            'date': datetime.now(),
            'secteur_activite': data.get('secteur_activite', ''),
            'telephone': data.get('telephone', ''),
            'email': data.get('email', ''),
            'adresse': data.get('adresse', '')
        }

        new_prospect = Entreprise.objects.create(**prospect_data)
        
        response_data = {
            'id': new_prospect.id,
            'nom': new_prospect.nom,
            'is_Prospect': new_prospect.is_Prospect,
            'societe': new_prospect.societe.nom if new_prospect.societe else '',
            'secteur_activite': new_prospect.secteur_activite
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
        
@permission_classes([IsAuthenticated])
@csrf_exempt
def add_swot(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            user_id = data.get('created_by_id')
            if user_id is not None:
                try:
                    user = get_user_model().objects.get(id=user_id)
                except get_user_model().DoesNotExist:
                    user = None 
            else:
                user = None
            
            required_fields = ['type', 'axe', 'entreprise']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'success': False, 
                        'message': f'The {field} field is required'
                    })
            
            try:
                entreprise = Entreprise.objects.get(
                    id=data['entreprise'],
                    is_Concurent=True
                )
            except Entreprise.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'message': 'Invalid competing company'
                })
                
            if not user.is_superuser:
                societe = user.societe
                
            elif user.is_RO:
                societe = Societe.objects.get(id=data.get('societe'))
            else:
                if 'societe' in data and data['societe']:
                    societe_id = data.get('societe')
                    try:
                        societe = Societe.objects.get(id=societe_id)
                    except Societe.DoesNotExist:
                        return JsonResponse({
                            'success': False, 
                            'message': 'Invalid subsidiary'
                })
                            
            swot = Swot(
                type=data.get('type', ''),
                description=data.get('description', ''),
                axe=data.get('axe', ''),
                entreprise=entreprise,
                societe=societe,
                created_by=user
            )            
            swot.save()
                       
            return JsonResponse({
                'success': True, 
                'message': 'SWOT added successfully!',
                'count': 1
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Unauthorized method'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_swot_count(request):
    try:
        user = request.user
        
        if user.is_superuser:
            count = Swot.objects.count()
        else:
            count = Swot.objects.filter(societe=user.societe).count()

        return JsonResponse({'success': True, 'count': count})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
    
@permission_classes([IsAuthenticated])
def get_swot_axes(request):
    try:
        axes = [{'value': key, 'label': label} for key, label in Swot.AXE_CHOICES]
        return JsonResponse({'success': True, 'data': axes})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_concurrents(request):
    entreprises = Entreprise.objects.filter(Q(is_Concurent=True)).order_by('nom')

    data = [
        {
            'id': e.id,
            'nom': e.nom,
        }
        for e in entreprises
    ]
    
    return Response(data)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_action(request, pk):
    try:
        action = Action.objects.get(pk=pk)
        
        if not request.user.is_superuser and not request.user.is_RO and action.created_by != request.user and action.pilote != request.user:
            return Response({'error': 'Permission denied'}, status=403)
        
        if 'date_heure_realiser' in request.data and request.data['date_heure_realiser']:
            try:
                date_str = request.data['date_heure_realiser'].strip()
                if not date_str:
                    action.date_heure_realiser = None
                else:
                    # Convertir la string en datetime conscient du fuseau
                    naive_datetime = datetime.strptime(
                        date_str, 
                        '%d/%m/%Y, %H:%M'
                    )
                    # Rendre le datetime conscient du fuseau
                    tz = pytz.timezone(settings.TIME_ZONE)
                    aware_datetime = tz.localize(naive_datetime)
                    action.date_heure_realiser = aware_datetime
            except ValueError:
                return Response({
                    'error': 'Format de date invalide. Utilisez JJ/MM/AAAA, HH:MM',
                    'received_value': request.data['date_heure_realiser'],
                    'expected_format': 'DD/MM/YYYY, HH:MM'
                }, status=400)
        else:
            action.date_heure_realiser = None
        
        if 'compte_rendu' in request.data:
            action.compte_rendu = request.data['compte_rendu']
        
        if 'notes' in request.data:
            action.notes = request.data['notes']
        
        action.save()
                
        return Response({
            'id': action.id,
            'date_heure_realiser': action.date_heure_realiser.strftime('%d/%m/%Y, %H:%M') if action.date_heure_realiser else None,
            'compte_rendu': action.compte_rendu,
            'notes': action.notes
        })
    
    except Action.DoesNotExist:
        return Response({'error': 'Action not found'}, status=404)
    
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_event(request, pk):
    try:
        event = Evenement.objects.get(pk=pk)
        
        if not request.user.is_superuser and not request.user.is_RO and event.created_by != request.user and event.pilote != request.user:
            return Response({'error': 'Permission denied'}, status=403)
        
        if 'date_heure_realiser' in request.data:
            try:
                naive_datetime = datetime.strptime(
                    request.data['date_heure_realiser'], 
                    '%d/%m/%Y, %H:%M'
                )
                tz = pytz.timezone(settings.TIME_ZONE)
                aware_datetime = tz.localize(naive_datetime)
                event.date_heure_realiser = aware_datetime
            except ValueError:
                return Response({'error': 'Format de date invalide. Utilisez DD/MM/YYYY, HH:MM'}, status=400)
        
        if 'notes' in request.data:
            event.notes = request.data['notes']
        
        event.save()
                
        return Response({
            'id': event.id,
            'date_heure_realiser': event.date_heure_realiser.strftime('%d/%m/%Y, %H:%M') if event.date_heure_realiser else None,
            'notes': event.notes
        })
    
    except Evenement.DoesNotExist:
        return Response({'error': 'Event not found'}, status=404)

def _fetch_client_from_api(numero_tiers: str, societe: Societe):
    if not numero_tiers or not societe:
        return None

    base_url = get_base_url(societe.id)
    if not base_url:
        logger.error("Base URL introuvable pour la société %s", societe.id if societe else None)
        return None

    url = f"{settings.SAGE_API_HOST}/WebServices100/{base_url}/TiersService/rest/Clients/{numero_tiers}"
    headers = {"Authorization": settings.SAGE_API_TOKEN, "Accept": "application/json"}

    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            logger.error("API client %s -> %s : %s", numero_tiers, r.status_code, r.text[:300])
            return None
        data = r.json()
    except Exception as e:
        logger.exception("Erreur d'appel API client: %s", e)
        return None

    intitule = data.get("Intitule") or data.get("intitule") or f"Client {numero_tiers}"
    email = data.get("Email") or data.get("fact_email") or ""
    adresse = data.get("Adresse") or data.get("fact_adresse") or ""
    tel = data.get("Telephone") or data.get("Telephone1") or data.get("Telephone2") or data.get("fact_tel") or ""
    secteur = data.get("SecteurActivite") or ""

    tz = pytz.timezone(settings.TIME_ZONE)
    data = {
        "nom": intitule,
        "num_compte": data.get("NumeroTiers") or numero_tiers,
        "telephone": tel,
        "email": email,
        "adresse": adresse,
        "is_CLT": True,
        "is_Prospect": False,
        "is_Concurent": False,
        "societe": societe,
        "secteur_activite": secteur,
        "date": datetime.now(tz=tz)
    }
    
    return data

def _get_or_create_client_by_numero(numero_tiers: str, societe: Societe):
    if not numero_tiers:
        return None
    existing = Entreprise.objects.filter(num_compte=numero_tiers, is_CLT=True).first()
    if existing:
        return existing
    payload = _fetch_client_from_api(numero_tiers, societe)
    if not payload:
        return None
    try:
        with transaction.atomic():
            return Entreprise.objects.create(**payload)
    except Exception as e:
        logger.exception("Erreur création client local depuis API: %s", e)
        return None
    
def _resolve_contact(contact_raw, societe):
    """
    contact_raw peut être:
      - un ID local d'Entreprise (int/str d'int)
      - un NumeroTiers (str) ; ex "001234" ou "C00123"
      - éventuellement "001234 - Raison sociale"
    On tente ID local, sinon on tente NumeroTiers (création si absent).
    """
    if not contact_raw:
        return None

    # 1) Essai ID local
    try:
        ent = Entreprise.objects.filter(id=contact_raw).first()
        if ent:
            return ent
    except (ValueError, TypeError):
        pass

    # Si on trouve déjà localement par num_compte, on renvoie
    ent = Entreprise.objects.filter(num_compte=contact_raw).first()
    if ent:
        return ent

    # Sinon on crée depuis l'API distante
    return _get_or_create_client_by_numero(contact_raw, societe)

@permission_classes([IsAuthenticated])
@csrf_exempt
def generate_report_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'JSON invalide: {str(e)}'}, status=400)

    # Champs reçus
    company_id = data.get('company')  # peut être None pour non-superuser
    contact_raw = data.get('contact')  # ID local OU NumeroTiers
    action_type = data.get('action_type')
    subject = data.get('subject', '')
    planned_date = data.get('planned_date', '')
    answers = data.get('answers', {})

    # Société: accepter toujours 'company' (id ou nom) envoyé par le front; sinon fallback utilisateur
    try:
        company = None
        if company_id:
            try:
                company = Societe.objects.get(id=int(company_id))
            except (ValueError, TypeError):
                company = Societe.objects.get(nom=str(company_id).strip())
        else:
            company = getattr(request.user, 'societe', None)
        if not company:
            return JsonResponse({'error': "Filiale manquante"}, status=400)
    except Societe.DoesNotExist:
        return JsonResponse({'error': "Filiale invalide"}, status=400)

    # Contact (entreprise)
    if not contact_raw:
        return JsonResponse({'error': 'Veuillez sélectionner une entreprise'}, status=400)

    contact = _resolve_contact(contact_raw, company)
    if not contact:
        return JsonResponse({'error': "Impossible de résoudre l'entreprise"}, status=400)

    # Validations
    if action_type not in ['call', 'email', 'appointment']:
        return JsonResponse({'error': "Type d'action invalide"}, status=400)
    if not subject:
        return JsonResponse({'error': 'Sujet manquant'}, status=400)

    # Templates
    templates = {
        'call': """
        Generate a concise professional call report in French (1 paragraph, 5-7 sentences) for quality control purposes.
        Include these elements:
        - Context: Call with the company {contact} from {company} regarding "{subject}" on {date}
        - Key discussion points: {q0}
        - Client's concerns or reactions: {q1}
        - Agreed actions or next steps: {q2}
        Requirements:
        - Neutral, factual tone
        - Highlight quality control aspects
        - Include sentiment indicators (positive/neutral/negative)
        - No bullet points or examples
        - Focus on factual observations
        - do not mark data other than what I give you, such as the number of participants
        - does not add additional data from you
        """,
        'email': """
        Generate a professional email summary in French (1 paragraph, 5-7 sentences) for quality control tracking.
        Include:
        - Context: Email to the company {contact} at {company} about "{subject}" sent on {date}
        - Main purpose and key content: {q0}
        - Sensitive or critical points addressed: {q1}
        - Required follow-up or response: {q2}
        Requirements:
        - Formal business style
        - Highlight quality/compliance aspects
        - Include tone assessment
        - No greetings or signatures
        - Pure factual summary
        - does not add additional data from you
        - do not mark data other than what I give you, such as the number of participants
        """,
        'appointment': """
        Generate a professional meeting report in French (1 paragraph, 5-7 sentences) for quality control records.
        Include:
        - Context: Meeting with the company {contact} from {company} about "{subject}" on {date}
        - Key discussion topics: {q0}
        - Participant engagement and reactions: {q1}
        - Decisions and action items: {q2}
        Requirements:
        - Professional but concise
        - Note any quality-related observations
        - Include engagement level (high/medium/low)
        - No opinions, only facts
        - Structured as single coherent paragraph
        - does not add additional data from you
        - do not mark data other than what I give you, such as the number of participants
        """
    }

    prompt = templates[action_type].format(
        contact=str(contact),  # __str__ de l’Entreprise
        company=str(company),
        subject=subject,
        date=planned_date,
        q0=answers.get('q0', ''),
        q1=answers.get('q1', ''),
        q2=answers.get('q2', ''),
    )

    # === ICI: appelle ta fonction de génération ===
    try:
        generated_text = generate_report(prompt)  # ta fonction existante
        clean_report = (generated_text or "").strip()
    except Exception as e:
        logger.exception("Erreur generate_report: %s", e)
        return JsonResponse({'error': "Erreur lors de la génération du rapport"}, status=500)

    return JsonResponse({'report': clean_report, 'status': 'success'}, status=200)