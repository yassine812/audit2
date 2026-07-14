import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from textblob import TextBlob
from typing import List, Dict, Any
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re, os, logging, nltk, warnings, joblib, unicodedata
from django.utils import timezone
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
 

# Configuration
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Réduction des logs TensorFlow si importé indirectement par transformers
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')  # 0=all,1=warn,2=error,3=fatal
# Pour désactiver oneDNN si variations numériques gênantes (optionnel):
# os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')

# Téléchargement des ressources NLTK
nltk.download('stopwords', quiet=True)

class FrenchSentimentAnalyzer:
    """Analyseur de sentiment optimisé pour le français commercial.
       Entrée: analyze(text:str)
       Sortie: dict(score: [-1,1], confidence: [0,1], keywords: List[str])
    """

    def __init__(self):
        # --- moteurs de base
        self.vader = SentimentIntensityAnalyzer()
        try:
            self.stopwords = set(stopwords.words('french'))
        except LookupError:
            # Si stopwords non téléchargés, fallback minimal
            self.stopwords = {"le","la","les","de","des","du","un","une","et","ou","mais","que","qui","en","dans","au","aux","pour","par","sur","avec","sans","ne","pas"}
        self.stemmer = SnowballStemmer('french')

        # chemins
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.model_dir = os.path.join(BASE_DIR, 'trained_model')
        self.model_path = os.path.join(self.model_dir, 'prospect_scorer_model.joblib')
        os.makedirs(self.model_dir, exist_ok=True)

        # Transformers optionnel
        self.use_hf = os.getenv('USE_HF_SENTIMENT', '0') == '1'
        self._hf_pipeline = None
        if self.use_hf:
            try:
                from transformers import pipeline  # type: ignore
                self._hf_pipeline = pipeline(
                    'sentiment-analysis',
                    model='cardiffnlp/twitter-xlm-roberta-base-sentiment',
                    framework='pt'
                )
            except Exception as e:
                logger.warning(f"Transformers indisponible: {e}. Fallback heuristique.")
                self.use_hf = False

        # --- Règles et ressources FR ---
        self.negations = {"pas","jamais","aucun","aucune","rien","plus","ni","guère","point","nullement"}
        # mots qui coupent la portée de la négation (ponctuation/virgules, connecteurs)
        self.neg_scope_break = {",",";","/","\\","—","–","-"," mais "," cependant "," pourtant "," toutefois "}
        self.intensifiers_pos = {"très":1.2,"vraiment":1.2,"tellement":1.15,"hautement":1.15,"extrêmement":1.3,"super":1.2,"ultra":1.2}
        self.intensifiers_neg = {"trop":1.2,"horriblement":1.3,"affreusement":1.3}
        self.diminishers = {"un_peu":0.8,"assez":0.9,"plutôt":0.9,"relativement":0.9}

        # émojis / émoticônes (liste courte mais utile)
        self.emoji_map = {
            "😀":0.6,"😃":0.7,"😄":0.7,"😁":0.7,"🙂":0.4,"😊":0.5,"😍":0.8,"🤩":0.9,"👍":0.5,"✨":0.4,"🔥":0.4,
            "😐":0.0,"🤔":-0.05,
            "😕":-0.3,"🙁":-0.4,"😞":-0.5,"😠":-0.7,"😡":-0.8,"👎":-0.5,"💸":-0.2,"❌":-0.4,"💔":-0.6
        }
        self.emoticons = {":-)":0.4,":)":0.3,":D":0.6,":(": -0.4,":/": -0.2,":|":0.0,";)":0.2,":'-(": -0.6}

        # Lexique commercial FR (brut) + n-grammes fréquents
        self.lexicon = {
            'positif': {
                'intéressé','satisfait','excellent','accord','oui','bon','positif','positive',
                'content','enthousiaste','motivé','confiant','favorable','convaincu','réussi',
                'succès','opportunité','valider','recommande','rapide','fiable','qualité',
                'parfait','super','formidable','génial','amélioration','gain','bénéfice',
                'réactif','professionnel','sérieux','clair','simple','agréable','wow'
            },
            'négatif': {
                'déçu','problème','difficile','non','refus','insatisfait','négatif','negatif',
                'négative','negative','inquiet','doute','retard','annuler','compliqué','cher',
                'mécontent','plainte','obstacle','rejet','bug','lent','panne','mauvais',
                'horrible','nul','faible','erreur','raté','trompeur','confus','flou','brouillon','abusif'
            }
        }
        # N-grammes commerciaux (désaccentués)
        self.ngrams_pos = {
            "bon rapport","très satisfait","vraiment satisfait","service top","au top","bonne qualité",
            "prix correct","gain de temps","réponse rapide","très clair","super clair","très pro","service nickel"
        }
        self.ngrams_neg = {
            "trop cher","pas clair","pas satisfait","pas content","pas terrible","très cher",
            "support nul","manque de","en retard","ne fonctionne pas","ne marche pas","aucune réponse","pas de réponse",
            "service lent","trop lent","trop compliqué","peu clair","bug récurrent"
        }

        # construire versions stemmées + désaccentuées
        self.lexicon_stemmed = {'positif': set(), 'négatif': set()}
        for cat, words in self.lexicon.items():
            for w in words:
                w_norm = self.strip_accents(w.lower())
                self.lexicon_stemmed[cat].add(self.stemmer.stem(w_norm))

    # ---------- Utils ----------
    def strip_accents(self, s: str) -> str:
        try:
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        except Exception:
            return s

    def _normalize_whitespace(self, s:str)->str:
        return re.sub(r'\s+',' ', s).strip()

    def _replace_repetitions(self, s:str)->str:
        # Réduire caractères répétés (cooool -> cool), mais laisser "!!" utile
        s = re.sub(r'(.)\1{2,}', r'\1\1', s)
        # normaliser ?! multiples
        s = re.sub(r'([!?])\1{1,}', r'\1\1', s)
        return s

    def _map_emojis(self, s:str)->float:
        score = 0.0
        for ch in s:
            score += self.emoji_map.get(ch, 0.0)
        for emo, val in self.emoticons.items():
            if emo in s: score += val
        # borne légère (-1..1)
        return float(np.clip(score, -1, 1))

    def clean_text(self, text):
        """Nettoyage FR conservant ! et ? pour intensité, normalisation commerciale."""
        if not isinstance(text, str):
            return ""
        # garder version brute pour emojis
        emoji_boost = self._map_emojis(text)

        t = text.lower()
        t = self._replace_repetitions(t)
        # normaliser quelques orthographes commerciales fréquentes
        replacements = {
            " bcp ":" beaucoup ",
            " svp ":" s'il vous plaît ",
            " pls ":" s'il vous plaît ",
            " stp ":" s'il te plaît ",
            " ok ":" d'accord ",
        }
        t = f" {t} "
        for k,v in replacements.items():
            t = t.replace(k, v)
        t = t.strip()

        # conserver ! et ? ; supprimer le reste
        t = re.sub(r'[^\w\s!?]', ' ', t)
        t = self._normalize_whitespace(t)
        # Ajout d’un indicateur d’EMPHASE si beaucoup de majuscules dans l’original
        caps_ratio = 0.0
        try:
            letters = re.findall(r'[A-Za-zÀ-ÖØ-öø-ÿ]', text)
            caps = [c for c in letters if c.isupper()]
            if letters:
                caps_ratio = len(caps)/len(letters)
        except Exception:
            pass

        return t, emoji_boost, caps_ratio

    def _apply_negation_scoped(self, tokens:List[str])->List[tuple]:
        """Heuristique de négation portée: marque les tokens affectés par une négation
           jusqu’à une rupture (ponctuation/connecteur) ou 3 tokens."""
        adjusted = []
        i = 0
        n = len(tokens)
        while i < n:
            w = tokens[i]
            if w in self.negations:
                # portée de 1 à 3 mots ou jusqu’à rupture
                j = i+1; span = 0
                while j < n and span < 3:
                    if tokens[j] in self.negations or any(brk in tokens[j] for brk in self.neg_scope_break):
                        break
                    adjusted.append((tokens[j], True))
                    j += 1; span += 1
                adjusted.append((w, False))  # la négation elle-même
                i = j
            else:
                adjusted.append((w, False))
                i += 1
        return adjusted

    def _score_ngrams(self, norm_text:str)->float:
        """Score prior pour n-grammes commerciaux (désaccentué)."""
        txt = " " + self.strip_accents(norm_text) + " "
        pos = sum(1 for g in self.ngrams_pos if f" {g} " in txt)
        neg = sum(1 for g in self.ngrams_neg if f" {g} " in txt)
        if pos==neg==0: return 0.0
        return (pos - neg) / float(pos + neg)

    def _hf_analyze(self, raw_text):
        if not self.use_hf or not self._hf_pipeline:
            return None
        try:
            res = self._hf_pipeline(raw_text, truncation=True)[0]
            label = res.get('label', '').lower()
            score = float(res.get('score', 0))
            if 'positive' in label:
                val = score
            elif 'negative' in label:
                val = -score
            else:
                val = 0.0
            # Pour neutral, `score` représente déjà la confiance de la classe.
            # Pour pos/neg, on garde aussi le score comme proxy de confiance.
            confidence = score
            return {'score': float(np.clip(val, -1, 1)),
                    'confidence': float(np.clip(confidence, 0, 1))}
        except Exception as e:
            logger.warning(f"Erreur HF pipeline: {e}")
            return None

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyse de sentiment combinée (FR)."""
        cleaned, emoji_boost, caps_ratio = self.clean_text(text)
        if not cleaned:
            return {'score': 0.0, 'confidence': 0.0, 'keywords': [], 'label': 'neutral'}

        # 1) Transformers (si dispo)
        hf = self._hf_analyze(text)

        # 2) VADER + TextBlob
        vader_score = self.vader.polarity_scores(cleaned)['compound']  # [-1..1]
        blob_score = TextBlob(cleaned).sentiment.polarity              # [-1..1] approx FR

        # 3) Lexical FR + négations + intensité
        raw_tokens = cleaned.split()
        # normaliser accents (pour matching)
        norm_tokens = [self.strip_accents(w) for w in raw_tokens]
        # joindre bigrammes pour diminisher (un peu -> un_peu)
        norm_tokens_joined = []
        i=0
        while i < len(norm_tokens):
            if i+1 < len(norm_tokens) and f"{norm_tokens[i]}_{norm_tokens[i+1]}" in self.diminishers:
                norm_tokens_joined.append(f"{norm_tokens[i]}_{norm_tokens[i+1]}")
                i += 2
            else:
                norm_tokens_joined.append(norm_tokens[i])
                i += 1

        # stemming (ignorer stopwords)
        stemmed = [self.stemmer.stem(w) for w in norm_tokens_joined if w not in self.stopwords]
        # appliquer négation portée sur tokens stemmés
        tokens_with_neg = self._apply_negation_scoped(stemmed)

        pos_count, neg_count = 0.0, 0.0
        detected = []  # keywords stemmés

        # heuristique explicite “positif/negatif” non-stemmé
        if any(t in {'positif','positive'} for t in norm_tokens): pos_count += 1
        if any(t in {'negatif','négatif','negative','négative'} for t in norm_tokens): neg_count += 1

        # intensificateurs et atténuateurs (calcul sur tokens non-stemmés)
        intensity_factor = 1.0
        for t in norm_tokens_joined:
            if t in self.intensifiers_pos: intensity_factor *= self.intensifiers_pos[t]
            if t in self.intensifiers_neg: intensity_factor *= self.intensifiers_neg[t]
            if t in self.diminishers:      intensity_factor *= self.diminishers[t]
        # borne raisonnable
        intensity_factor = float(np.clip(intensity_factor, 0.7, 1.6))

        for w, negated in tokens_with_neg:
            if w in self.lexicon_stemmed['positif']:
                pos_count += (-1.0 if negated else 1.0)
                detected.append(w)
            elif w in self.lexicon_stemmed['négatif']:
                neg_count += (-1.0 if negated else 1.0)
                detected.append(w)

        # Score lexical normalisé
        lexical_score = 0.0
        denom = abs(pos_count) + abs(neg_count)
        if denom > 0:
            lexical_score = (pos_count - neg_count) / denom

        # 4) N-grammes commerciaux
        ngram_prior = self._score_ngrams(cleaned)

        # 5) Intensité via ponctuation + MAJUSCULES + emojis
        exclam = cleaned.count('!')
        quest  = cleaned.count('?')
        punct_boost = min(0.4, 0.07 * exclam) - min(0.25, 0.03 * quest)  # ? tend à réduire la certitude/polarité
        caps_boost = min(0.25, max(0.0, caps_ratio - 0.15))  # boost si beaucoup de MAJUSCULES
        extra_boost = emoji_boost * 0.5  # max +/-0.5

        # 6) Combinaison (priorité HF si dispo)
        # calibration douce pour limiter l’influence de chaque terme
        def clamp(x): return float(np.clip(x, -1, 1))

        if hf is not None:
            combined = (0.55 * clamp(hf['score']) +
                        0.15 * clamp(vader_score) +
                        0.15 * clamp(lexical_score) +
                        0.10 * clamp(blob_score) +
                        0.05 * clamp(ngram_prior))
            base_conf = hf['confidence']
        else:
            combined = (0.35 * clamp(vader_score) +
                        0.35 * clamp(lexical_score) +
                        0.20 * clamp(blob_score) +
                        0.10 * clamp(ngram_prior))
            # Confiance = accord entre signaux secondaires
            sec = np.array([vader_score, lexical_score, blob_score, ngram_prior], dtype=float)
            base_conf = float(np.clip(1.0 - np.std(sec), 0.0, 1.0))

        # appliquer intensité & boosts
        combined *= intensity_factor
        combined += punct_boost + extra_boost + caps_boost
        combined = clamp(combined)

        # confiance finale = base_conf pondérée par la cohérence des signes
        signals = [vader_score, lexical_score, blob_score]
        if hf is not None: signals.append(hf['score'])
        same_sign = [np.sign(s) for s in signals if abs(s) > 1e-6]
        agreement = 1.0 if not same_sign else (same_sign.count(np.sign(combined)) / float(len(same_sign)))
        confidence = float(np.clip(0.6 * base_conf + 0.4 * agreement, 0.0, 1.0))

        # mots-clés (retour lisible: on remonte la forme non-stem si possible)
        keywords = []
        back_map = {self.stemmer.stem(self.strip_accents(w.lower())): w for w in (self.lexicon['positif']|self.lexicon['négatif'])}
        for st in detected:
            if st in back_map and back_map[st] not in keywords:
                keywords.append(back_map[st])

        # Label robuste (utile pour l'agrégation à grande échelle)
        # Objectif: éviter de classer agressivement pos/neg sur textes courts/ambigus.
        token_count = 0
        try:
            token_count = len(cleaned.split())
        except Exception:
            token_count = 0

        label = 'neutral'
        # Si faible confiance ou texte trop court => neutraliser
        if confidence < 0.35 or token_count < 3:
            label = 'neutral'
        else:
            if combined > 0.20:
                label = 'positive'
            elif combined < -0.20:
                label = 'negative'
            else:
                label = 'neutral'

        return {
            'score': combined,
            'confidence': confidence,
            'keywords': keywords,
            'label': label
        }


class ActionFeaturesGenerator:
    """Génération de features pour les actions"""
    
    def __init__(self):
        self.analyzer = FrenchSentimentAnalyzer()
        
    def extract_features(self, actions):
        """Extrait les features d'une liste d'actions"""
        if not actions:
            return pd.DataFrame()
            
        data = []
        
        for action in actions:
            # Analyse du compte rendu
            sentiment = self.analyzer.analyze(action.compte_rendu)
            
            # Détermination du type d'action
            action_type = self._get_action_type(action)
            
            # Valeur d'état
            state_value = self._get_state_value(action.etat, action_type)
            
            # Calcul des jours depuis la création
            days_ago = (timezone.now() - action.date_heure).days
            
            data.append({
                'type': action_type,
                'sentiment': sentiment['score'],
                'confidence': sentiment['confidence'],
                'state': state_value,
                'days_ago': days_ago,
                'has_notes': len(action.notes) > 10  # Notes significatives
            })
            
        return pd.DataFrame(data)
    
    def _get_action_type(self, action):
        """Détermine le type d'action"""
        if action.is_Appel:
            return 'call'
        elif action.is_Email:
            return 'email'
        elif action.is_RV:
            return 'meeting'
        return 'other'
    
    def _get_state_value(self, state, action_type):
        """Convertit l'état en valeur numérique"""
        state_mapping = {
            'call': {'reussi': 1, 'non_reussi': -1, '': 0},
            'email': {'lu': 0.5, 'non_lu': -0.5, '': 0},
            'meeting': {'termine': 1, 'planifie': 0, 'annule': -1, '': 0}
        }
        
        return state_mapping.get(action_type, {}).get(state, 0)

class ProspectScorer:
    """Calcul du score de prospect"""
    
    def __init__(self):
        self.feature_generator = ActionFeaturesGenerator()
        self.model = None
        self.scaler = StandardScaler()
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(BASE_DIR, 'trained_model', 'prospect_scorer_model.joblib')
        
    def train_model(self, prospects, force_retrain=False):
        """Entraîne ou charge le modèle"""
        try:
            if not force_retrain and os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                return True
                
            # Ici vous devriez avoir des données labellisées pour l'entraînement
            # Pour l'exemple, nous créons un modèle simple
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            
            # Simuler des données d'entraînement (à remplacer par vos vraies données)
            X_train = np.random.rand(100, 5)  # 5 features
            y_train = np.random.randint(0, 2, 100)  # Labels binaires
            
            self.model.fit(X_train, y_train)
            joblib.dump(self.model, self.model_path)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement du modèle: {str(e)}")
            return False
    
    def calculate_prospect_score(self, prospect, actions):
        """Calcule le score complet pour un prospect"""
        if not actions:
            return {
                'score': 0,
                'details': {
                    'activity': 0,
                    'sentiment': 0,
                    'engagement': 0,
                    'conversion_probability': 0
                },
                'actions_analysis': {}
            }
        
        # Génération des features
        features_df = self.feature_generator.extract_features(actions)
        
        # Calcul des métriques de base
        total_actions = len(features_df)
        last_action_days = features_df['days_ago'].min()
        
        # Scores par type d'action
        action_types = features_df['type'].unique()
        type_scores = {}
        
        for action_type in action_types:
            type_df = features_df[features_df['type'] == action_type]
            type_scores[action_type] = {
                'count': len(type_df),
                'avg_sentiment': type_df['sentiment'].mean(),
                'success_rate': type_df[type_df['state'] > 0]['state'].count() / len(type_df) if len(type_df) > 0 else 0
            }
        
        # Score global
        activity_score = min(1, total_actions / 10)  # Normalisé à 10 actions
        sentiment_score = features_df['sentiment'].mean()
        engagement_score = self._calculate_engagement_score(features_df)
        
        # Probabilité de conversion (utilise le modèle si disponible)
        if self.model:
            conversion_prob = self._predict_conversion(features_df)
        else:
            conversion_prob = 0.5 * (sentiment_score + 1)  # Conversion basique
            
        # Score final pondéré
        final_score = (
            0.3 * activity_score + 
            0.3 * sentiment_score + 
            0.2 * engagement_score + 
            0.2 * conversion_prob
        )
        
        return {
            'score': max(0, min(100, final_score * 100)),  # Score sur 100
            'details': {
                'activity': activity_score * 100,
                'sentiment': sentiment_score * 100,
                'engagement': engagement_score * 100,
                'conversion_probability': conversion_prob * 100
            },
            'actions_analysis': type_scores
        }
    
    def _calculate_engagement_score(self, features_df):
        """Calcule un score d'engagement basé sur la récence et la fréquence"""
        if features_df.empty:
            return 0
            
        # Score de récence (plus récent = meilleur)
        recency = 1 - (features_df['days_ago'].min() / 365)  # Normalisé sur 1 an
        
        # Score de fréquence
        frequency = min(1, len(features_df) / 20)  # Normalisé à 20 actions
        
        return 0.6 * recency + 0.4 * frequency
    
    def _predict_conversion(self, features_df):
        """Prédit la probabilité de conversion avec le modèle"""
        if not self.model or features_df.empty:
            return 0.5
            
        # Préparation des features pour le modèle
        X = self._prepare_features_for_model(features_df)
        X_scaled = self.scaler.transform(X)
        
        return self.model.predict_proba(X_scaled)[0][1]  # Probabilité classe positive
    
    def _prepare_features_for_model(self, features_df):
        """Prépare les features pour l'entrée du modèle"""
        # Ici vous devriez mettre les mêmes features que pour l'entraînement
        # Pour l'exemple, nous utilisons des features basiques
        return np.array([
            len(features_df),
            features_df['sentiment'].mean(),
            features_df['confidence'].mean(),
            features_df['days_ago'].min(),
            features_df['state'].mean()
        ]).reshape(1, -1)

class MultilingualSentimentAnalyzer:
    def __init__(self):
        self._hf_pipeline = None
        try:
            from transformers import pipeline  # type: ignore
            self._hf_pipeline = pipeline(
                'sentiment-analysis',
                model='cardiffnlp/twitter-xlm-roberta-base-sentiment',
                framework='pt'
            )
        except Exception:
            self._hf_pipeline = None
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        self._vader = SentimentIntensityAnalyzer()

        try:
            self.stop_fr = set(stopwords.words('french'))
        except LookupError:
            self.stop_fr = set()
        try:
            self.stop_en = set(stopwords.words('english'))
        except LookupError:
            self.stop_en = set()
        try:
            self.stop_de = set(stopwords.words('german'))
        except LookupError:
            self.stop_de = set()

        self.stem_fr = SnowballStemmer('french')
        self.stem_en = SnowballStemmer('english')
        self.stem_de = SnowballStemmer('german')

        self.neg_fr = {"pas","jamais","aucun","aucune","rien","plus","ni","guère","point","nullement"}
        self.neg_en = {"not","never","no","none","nothing","neither","nor","hardly","scarcely"}
        self.neg_de = {"nicht","nie","kein","keine","keiner","keines","keinem","keinen","nichts","weder","noch"}

        self.int_pos_fr = {"très":1.2,"vraiment":1.2,"tellement":1.15,"extrêmement":1.3,"super":1.2}
        self.int_pos_en = {"very":1.2,"really":1.2,"extremely":1.3,"highly":1.15,"super":1.2}
        self.int_pos_de = {"sehr":1.2,"wirklich":1.2,"äußerst":1.3,"hoch":1.1,"super":1.2}
        self.int_neg_fr = {"trop":1.2}
        self.int_neg_en = {"too":1.2}
        self.int_neg_de = {"zu":1.2}
        self.dim_fr = {"un_peu":0.8,"assez":0.9,"plutôt":0.9}
        self.dim_en = {"a_little":0.8,"quite":0.9,"rather":0.9}
        self.dim_de = {"ein_bisschen":0.8,"ziemlich":0.9,"eher":0.9}

        self.lex_pos_fr = {"intéressé","satisfait","excellent","accord","oui","bon","positif","positive","content","enthousiaste","motivé","confiant","favorable","convaincu","réussi","succès","opportunité","valider","recommande","rapide","fiable","qualité","parfait","super","formidable","génial","amélioration","gain","bénéfice","réactif","professionnel","sérieux","clair","simple","agréable","wow"}
        self.lex_neg_fr = {"déçu","problème","difficile","non","refus","insatisfait","négatif","negatif","négative","negative","inquiet","doute","retard","annuler","compliqué","cher","mécontent","plainte","obstacle","rejet","bug","lent","panne","mauvais","horrible","nul","faible","erreur","raté","trompeur","confus","flou","brouillon","abusif"}
        self.lex_pos_en = {"interested","satisfied","excellent","agreement","yes","good","positive","happy","enthusiastic","motivated","confident","favorable","convinced","successful","success","opportunity","approve","recommend","fast","reliable","quality","perfect","great","awesome","improvement","gain","benefit","responsive","professional","serious","clear","simple","pleasant","wow"}
        self.lex_neg_en = {"disappointed","problem","difficult","no","refusal","unsatisfied","negative","worried","doubt","delay","cancel","complicated","expensive","unhappy","complaint","obstacle","rejection","bug","slow","breakdown","bad","horrible","awful","weak","error","failed","misleading","confusing","vague","messy","abusive"}
        self.lex_pos_de = {"interessiert","zufrieden","ausgezeichnet","vereinbarung","ja","gut","positiv","glücklich","begeistert","motiviert","zuversichtlich","günstig","überzeugt","erfolgreich","erfolg","chance","empfehlen","schnell","zuverlässig","qualität","perfekt","toll","großartig","verbesserung","gewinn","vorteil","reaktionsschnell","professionell","ernsthaft","klar","einfach","angenehm","wow"}
        self.lex_neg_de = {"enttäuscht","problem","schwierig","nein","ablehnung","unzufrieden","negativ","besorgt","zweifel","verzögerung","abbrechen","kompliziert","teuer","unhappy","beschwerde","hindernis","zurückweisung","bug","langsam","ausfall","schlecht","schrecklich","furchtbar","schwach","fehler","gescheitert","irreführend","verwirrend","vage","chaotisch","missbräuchlich"}

    def _strip_accents(self, s: str) -> str:
        try:
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        except Exception:
            return s

    def _join_bigrams(self, toks, a, b):
        out = []
        i = 0
        while i < len(toks):
            if i+1 < len(toks) and f"{toks[i]}_{toks[i+1]}" in b:
                out.append(f"{toks[i]}_{toks[i+1]}")
                i += 2
            else:
                out.append(toks[i])
                i += 1
        return out

    def _lang_hint(self, t: str) -> str:
        s = (t or '').lower()
        s_pad = f" {s} "

        # 1) Vote lexical (utile pour textes très courts: ex. "satisfait")
        try:
            cleaned = re.sub(r'[^\w\s!?]', ' ', s)
            toks = [self._strip_accents(w) for w in cleaned.split() if w]
            fr_hits = sum(1 for w in toks if w in self.lex_pos_fr or w in self.lex_neg_fr)
            en_hits = sum(1 for w in toks if w in self.lex_pos_en or w in self.lex_neg_en)
            de_hits = sum(1 for w in toks if w in self.lex_pos_de or w in self.lex_neg_de)
            best = max(fr_hits, en_hits, de_hits)
            if best > 0:
                if fr_hits == best and fr_hits > 0:
                    return 'fr'
                if de_hits == best and de_hits > 0:
                    return 'de'
                if en_hits == best and en_hits > 0:
                    return 'en'
        except Exception:
            pass

        # 2) Heuristique mots fréquents
        if any(w in s_pad for w in (" le ", " la ", " les ", " pas ", " très ", "oui", "non")):
            return 'fr'
        if any(w in s_pad for w in (" the ", " not ", " very ", " yes ", " no ", "maybe")):
            return 'en'
        if any(w in s_pad for w in (" nicht ", " ja ", " nein ", " sehr ", " vielleicht ")):
            return 'de'

        return 'en'

    def _rule_score(self, text: str) -> float:
        if not text:
            return 0.0
        raw = text
        t = raw.lower()
        t = re.sub(r'(.)\1{2,}', r'\1\1', t)
        t = re.sub(r'[^\w\s!?]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        lang = self._lang_hint(t)
        tokens = t.split()
        if lang == 'fr':
            toks = [self._strip_accents(w) for w in tokens]
            toks = self._join_bigrams(toks, self.int_pos_fr, self.dim_fr)
            stem = [self.stem_fr.stem(w) for w in toks if w not in self.stop_fr]
            lex_pos = {self.stem_fr.stem(self._strip_accents(w)) for w in self.lex_pos_fr}
            lex_neg = {self.stem_fr.stem(self._strip_accents(w)) for w in self.lex_neg_fr}
            negs = self.neg_fr
            ip, ineg, dim = self.int_pos_fr, self.int_neg_fr, self.dim_fr
        elif lang == 'de':
            toks = [self._strip_accents(w) for w in tokens]
            toks = self._join_bigrams(toks, self.int_pos_de, self.dim_de)
            stem = [self.stem_de.stem(w) for w in toks if w not in self.stop_de]
            lex_pos = {self.stem_de.stem(self._strip_accents(w)) for w in self.lex_pos_de}
            lex_neg = {self.stem_de.stem(self._strip_accents(w)) for w in self.lex_neg_de}
            negs = self.neg_de
            ip, ineg, dim = self.int_pos_de, self.int_neg_de, self.dim_de
        else:
            toks = tokens
            toks = [w if w != 'a' else 'a' for w in toks]
            toks = [w for w in toks]
            toks = self._join_bigrams(toks, self.int_pos_en, self.dim_en)
            stem = [self.stem_en.stem(w) for w in toks if w not in self.stop_en]
            lex_pos = {self.stem_en.stem(w) for w in self.lex_pos_en}
            lex_neg = {self.stem_en.stem(w) for w in self.lex_neg_en}
            negs = self.neg_en
            ip, ineg, dim = self.int_pos_en, self.int_neg_en, self.dim_en

        intensity = 1.0
        for w in toks:
            if w in ip: intensity *= ip[w]
            if w in ineg: intensity *= ineg[w]
            if w in dim: intensity *= dim[w]
        intensity = float(np.clip(intensity, 0.7, 1.6))

        pos_c = 0.0
        neg_c = 0.0
        i = 0
        while i < len(stem):
            w = stem[i]
            negated = False
            if i > 0 and stem[i-1] in negs:
                negated = True
            if w in lex_pos:
                pos_c += -1.0 if negated else 1.0
            elif w in lex_neg:
                neg_c += -1.0 if negated else 1.0
            i += 1
        base = 0.0
        d = abs(pos_c) + abs(neg_c)
        if d > 0:
            base = (pos_c - neg_c) / d
        exclam = t.count('!')
        quest = t.count('?')
        boost = min(0.4, 0.07 * exclam) - min(0.25, 0.03 * quest)
        sc = float(np.clip(base * intensity + boost, -1, 1))
        return sc

    def analyze(self, text: str) -> Dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            return {'score': 0.0, 'confidence': 0.0, 'label': 'neutral'}

        raw = text.strip()
        lang = self._lang_hint(raw)
        token_count = 0
        try:
            token_count = len(re.sub(r'[^\w\s!?]', ' ', raw.lower()).split())
        except Exception:
            token_count = 0

        def _has_lexical_signal(txt: str) -> bool:
            t = re.sub(r'[^\w\s!?]', ' ', (txt or '').lower())
            toks = [self._strip_accents(w) for w in t.split()]
            if lang == 'fr':
                pos_lex, neg_lex = self.lex_pos_fr, self.lex_neg_fr
            elif lang == 'de':
                pos_lex, neg_lex = self.lex_pos_de, self.lex_neg_de
            else:
                pos_lex, neg_lex = self.lex_pos_en, self.lex_neg_en
            return any(w in pos_lex for w in toks) or any(w in neg_lex for w in toks)

        has_lex = _has_lexical_signal(raw)

        hf_val = None
        hf_conf = None
        hf_label = None
        if self._hf_pipeline is not None:
            try:
                res = self._hf_pipeline(raw, truncation=True)[0]
                hf_label = str(res.get('label', '')).lower()
                score = float(res.get('score', 0) or 0.0)
                if 'positive' in hf_label:
                    hf_val = score
                elif 'negative' in hf_label:
                    hf_val = -score
                else:
                    hf_val = 0.0
                # confiance: le modèle donne la proba de la classe prédite
                hf_conf = float(np.clip(score, 0.0, 1.0))
            except Exception:
                hf_val = None
                hf_conf = None
                hf_label = None

        # règles lexicales + VADER (si anglais) comme fallback robuste
        rule = self._rule_score(raw)
        vader_comp = None
        if lang == 'en':
            try:
                vader_comp = float(self._vader.polarity_scores(raw).get('compound', 0.0) or 0.0)
            except Exception:
                vader_comp = None

        if vader_comp is None:
            base_score = float(np.clip(rule, -1, 1))
            base_conf = 0.65
        else:
            base_score = float(np.clip(0.6 * rule + 0.4 * vader_comp, -1, 1))
            base_conf = float(np.clip(1.0 - abs(rule - vader_comp), 0.5, 1.0))

        # Si HF existe, l'utiliser, mais ne pas laisser la classe "neutral" écraser
        # un signal lexical fort sur des réponses très courtes.
        if hf_val is not None and hf_conf is not None:
            score = float(np.clip(0.65 * hf_val + 0.35 * base_score, -1, 1))
            confidence = float(np.clip(0.7 * hf_conf + 0.3 * base_conf, 0.0, 1.0))
            if (hf_label is not None and 'neutral' in hf_label) and has_lex and abs(base_score) >= 0.35:
                score = base_score
                confidence = max(confidence, base_conf)
        else:
            score = base_score
            confidence = base_conf

        # Label robuste: ne pas neutraliser un seul mot très polarisé (ex: "satisfait")
        label = 'neutral'
        if token_count <= 2 and has_lex and abs(score) >= 0.15:
            label = 'positive' if score > 0 else 'negative'
        else:
            if confidence < 0.35 and not has_lex:
                label = 'neutral'
            else:
                if score > 0.15:
                    label = 'positive'
                elif score < -0.15:
                    label = 'negative'
                else:
                    label = 'neutral'

        return {
            'score': float(np.clip(score, -1, 1)),
            'confidence': float(np.clip(confidence, 0.0, 1.0)),
            'label': label,
        }