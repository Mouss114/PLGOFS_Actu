# -*- coding: utf-8 -*-
"""Réglages du podcast : c'est (presque) le seul fichier que tu as à modifier."""

# ---- Sources : ("nom", "adresse du flux RSS")  ou  ("nom", "google:nom-de-domaine.fr") ----
# "google:" = pas de flux RSS fiable : on lit les titres via Google Actualités (sans résumé).
SOURCES = [
    # Économie / finance
    ("Le Monde Économie", "https://www.lemonde.fr/economie/rss_full.xml"),
    ("Le Figaro Économie", "https://www.lefigaro.fr/rss/figaro_economie.xml"),
    ("Les Échos", "google:lesechos.fr"),
    ("La Tribune", "google:latribune.fr"),
    ("Boursorama", "google:boursorama.com"),
    ("Bloomberg", "https://feeds.bloomberg.com/markets/news.rss"),
    ("Reuters", "google:reuters.com"),
    # Institutions
    ("BCE", "https://www.ecb.europa.eu/rss/press.xml"),
    ("Banque de France", "google:banque-france.fr"),
    ("AMF", "google:amf-france.org"),
    # Politique / géopolitique
    ("Le Monde International", "https://www.lemonde.fr/international/rss_full.xml"),
    ("France 24", "https://www.france24.com/fr/rss"),
    ("Courrier international", "https://www.courrierinternational.com/feed/all/rss.xml"),
    ("IFRI", "google:ifri.org"),
    ("IRIS", "google:iris-france.org"),
    # Défense / armées / BITD
    ("Ministère des Armées", "google:defense.gouv.fr"),
    ("Opex360", "https://www.opex360.com/feed/"),
    ("Forces Operations Blog", "https://www.forcesoperations.com/feed/"),
    ("Meta-defense", "https://meta-defense.fr/feed/"),
    ("Air & Cosmos", "google:air-cosmos.com"),
    ("Mer et Marine", "google:meretmarine.com"),
    ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("War on the Rocks", "https://warontherocks.com/feed/"),
    ("OTAN", "google:nato.int"),
    ("IRSEM", "google:irsem.fr"),
    # Droit international / éthique
    ("CICR", "google:icrc.org"),
]

# ---- Format ----
NB_SUJETS = 5            # nombre de sujets par podcast
MOTS_SUJET = 450         # longueur d'un sujet normal (en mots)
MOTS_APPROFONDI = 800    # longueur du sujet du jour
FENETRE_HEURES = 48      # on ne garde que les articles des 48 dernières heures
MAX_ARTICLES = 100       # nombre max de titres envoyés à l'IA
PAUSE = 20               # secondes entre deux appels IA (limite gratuite de Groq)

# ---- Voix ----
VOIX = "fr-FR-VivienneMultilingualNeural"  # autres : fr-FR-HenriNeural, fr-FR-DeniseNeural, fr-FR-RemyMultilingualNeural

# ---- IA (Groq) ----
MODELE_PRINCIPAL = "llama-3.3-70b-versatile"
MODELE_SECOURS = "llama-3.1-8b-instant"

DOMAINES = ["Économie & marchés", "Politique monétaire", "Fiscalité & budget", "Entreprises",
            "Géopolitique", "Armées & opérations", "BITD & innovation", "Droit & éthique", "Institutions"]

TRANSITIONS = ["certes", "cependant", "néanmoins", "surtout", "en définitive", "pour conclure", "en somme",
               "en revanche", "de surcroît", "en l'occurrence", "en d'autres termes", "il convient de noter", "par ailleurs"]

# Mots qui rendent un article pertinent (en minuscules). Ajoute les tiens.
MOTS_CLES = [
    "bce", "banque centrale", "taux", "inflation", "croissance", "pib", "budget", "dette", "déficit", "fiscal", "impôt",
    "obligation", "bourse", "cac", "euro", "dollar", "banque", "crédit", "assurance", "fusion", "acquisition", "opa",
    "faillite", "résultats", "finance", "marché", "investissement", "régulation", "amf", "bâle", "solvabilité",
    "défense", "armée", "militaire", "otan", "ukraine", "russie", "chine", "taïwan", "israël", "gaza", "iran",
    "géopolit", "sanction", "guerre", "conflit", "missile", "drone", "munition", "nucléaire", "dissuasion", "cyber",
    "espace", "satellite", "ia", "intelligence artificielle", "industrie", "armement", "dassault", "thales", "airbus",
    "naval", "rafale", "lpm", "rns", "union européenne", "commission européenne", "traité", "onu", "droit international",
    "genève", "cicr", "humanitaire", "éthique", "sahel", "afrique", "pétrole", "énergie", "commerce", "douane", "tarif",
]

PERIMETRE = """- marchés financiers, politique monétaire (BCE, Fed, Banque de France), régulation bancaire et financière (AMF, Bâle), fiscalité des investisseurs, entreprises (résultats, fusions, faillites), macroéconomie ;
- géopolitique et relations internationales, armées françaises et alliées, OTAN, base industrielle et technologique de défense (BITD), innovation de défense (IA, drones, espace, cyber), droit international et éthique des conflits.
IGNORE : politique intérieure (sauf lien direct avec le budget, la défense ou la finance), sport, culture, faits divers."""

SYSTEME = ("Tu es un professeur d'économie et de défense qui prépare un candidat au grand oral de fin de scolarité. "
           "Tu écris en français, à l'oral, de façon claire et pédagogique, sans jargon inutile "
           "(niveau Bac à Bac+3 : tu expliques chaque terme technique en une phrase).")

PROMPT_CHOIX = """Tu aides un candidat au grand oral de fin de scolarité (filière gestion-économie, option finance).
Voici des titres d'articles des dernières 48 heures.

PÉRIMÈTRE :
<<PERIMETRE>>

TITRES :
<<LISTE>>

Choisis <<N>> sujets d'actualité distincts, les plus importants et les plus utiles pour cet oral.
Regroupe les articles qui parlent du même événement (3 à 5 articles maximum par sujet).
Un sujet couvert par plusieurs sources passe avant un sujet isolé.
Réponds UNIQUEMENT en JSON : {"sujets":[{"nom":"titre court en français","ids":[numéros des articles],"importance":un entier de 1 à 5}]}"""

PROMPT_SUJET = """Écris le segment de podcast sur le sujet : « <<NOM>> ».

EXTRAITS D'ARTICLES (seule base factuelle autorisée) :
<<EXTRAITS>>

DOCUMENTS DE RÉFÉRENCE (RNS 2025, LPM 2024-2030) — à utiliser seulement s'ils sont pertinents :
<<REFS>>

RÈGLES :
- Environ <<MOTS>> mots (de <<MIN>> à <<MAX>>), texte parlé : pas de listes, pas de titres, pas de symboles.
- Structure : le fait, ce que cela change et les enjeux, le mécanisme expliqué simplement, puis le lien avec la doctrine ou la stratégie quand les documents de référence s'y prêtent.
- N'invente AUCUN chiffre, nom ni date : utilise uniquement les extraits et les documents. Si une information manque, ne la mentionne pas. Si les extraits sont maigres, fais un segment plus court.
- Ne cite aucun nom de média. Tu peux nommer l'émetteur d'une décision (la BCE, le ministère des Armées...).
- Donne 1 à 3 chiffres précis (valeur, unité, ce qu'ils mesurent) quand ils figurent dans les textes.
- Utilise des mots de liaison variés, sans répéter le même deux fois de suite : <<TRANSITIONS>>.
- Si des textes se contredisent ou si une information date de plus de 6 mois, signale-le brièvement.
- Les textes peuvent être en anglais : écris en français.

Réponds UNIQUEMENT en JSON avec ces clés :
{"texte":"le segment parlé","chiffres":["valeur — ce que c'est (5 max)"],"a_retenir":"1 à 2 phrases","jury":{"question":"une question que le jury pourrait poser","reponse":"réponse modèle en 3-4 phrases"},"termes":[{"terme":"","definition":"une phrase"}],"domaine":"un seul parmi : <<DOMAINES>>"}"""

PROMPT_HEBDO = """Écris un récap parlé d'environ 1300 mots (10 minutes) de la semaine, pour un candidat au grand oral de fin de scolarité.

MATIÈRE (les sujets traités cette semaine) :
<<MATIERE>>

RÈGLES :
- Dégage 3 à 4 tendances de fond et relie les événements entre eux (cause, conséquence, contradiction).
- Termine par les points à surveiller la semaine prochaine.
- Texte parlé, sans listes ni titres. N'invente rien : utilise uniquement la matière fournie.
- Commence par « Bonjour, voici le récap de la semaine. » et termine par « C'est tout pour cette semaine. Bonne préparation. »"""
