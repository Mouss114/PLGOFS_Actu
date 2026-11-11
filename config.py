# -*- coding: utf-8 -*-
"""Réglages du podcast : c'est (presque) le seul fichier que tu as à modifier."""

# ---- Sources : ("nom", "adresse du flux RSS")  ou  ("nom", "google:nom-de-domaine.fr") ----
# "google:" = pas de flux RSS fiable : on trouve les liens via Google Actualités.
# Le script doit ensuite OUVRIR chaque lien et lire l'article (voir LIRE_ARTICLES_COMPLETS plus bas).
# Retirés après le test du 11/11/2026 : Meta-defense (410 Gone, flux supprimé) et Reuters (0 article).
SOURCES = [
    # Économie / finance
    ("Le Monde Économie", "https://www.lemonde.fr/economie/rss_full.xml"),
    ("Le Figaro Économie", "https://www.lefigaro.fr/rss/figaro_economie.xml"),
    ("Bloomberg", "https://feeds.bloomberg.com/markets/news.rss"),
    # Institutions
    ("BCE", "https://www.ecb.europa.eu/rss/press.xml"),
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("Banque de France", "google:banque-france.fr"),
    ("AMF", "https://www.amf-france.org/fr/flux-rss/display/25"),
    # Politique / géopolitique
    ("Le Monde International", "https://www.lemonde.fr/international/rss_full.xml"),
    ("France 24", "https://www.france24.com/fr/rss"),
    # Défense / armées / BITD
    ("Ministère des Armées", "google:defense.gouv.fr"),
    ("Opex360", "https://www.opex360.com/feed/"),
    ("Forces Operations Blog", "https://www.forcesoperations.com/feed/"),
    ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("War on the Rocks", "https://warontherocks.com/feed/"),
    ("OTAN", "google:nato.int"),
    ("IRSEM", "google:irsem.fr"),
    # Droit international / éthique
    ("CICR", "google:icrc.org"),
]

# ---- Lecture des articles (le script doit utiliser ces valeurs) ----
LIRE_ARTICLES_COMPLETS = True   # ouvrir chaque lien et extraire le texte, pas seulement le titre
ARTICLES_PAR_SUJET = 4          # nombre d'articles lus en entier pour chaque sujet retenu
MAX_CARACTERES_ARTICLE = 6000   # texte conservé par article (évite de dépasser la limite de tokens)
TIMEOUT_HTTP = 60               # secondes avant d'abandonner un flux ou un article
IGNORER_SOURCE_EN_PANNE = True  # une source qui échoue ne doit jamais bloquer le podcast
MIN_SOURCES_OK = 1              # en dessous, le script s'arrête avec un message clair

# ---- Format ----
NB_SUJETS = 5            # nombre de sujets par podcast
MOTS_SUJET = 550         # longueur d'un sujet normal (en mots)
MOTS_APPROFONDI = 800    # longueur du sujet du jour
FENETRE_HEURES = 48      # on ne garde que les articles des 48 dernières heures
MAX_ARTICLES = 60        # nombre max de titres envoyés à l'IA (réduit pour tenir dans les limites gratuites)
PAUSE = 20               # secondes entre deux appels IA (limite gratuite de Groq)

# ---- Voix ----
VOIX = "fr-FR-HenriNeural"  # autres : fr-FR-HenriNeural, fr-FR-DeniseNeural, fr-FR-RemyMultilingualNeural

# ---- IA (Groq) ----
# llama-3.3-70b-versatile et llama-3.1-8b-instant sont arrêtés depuis le 16/08/2026
# pour les comptes gratuits : ils sont remplacés par les modèles recommandés par Groq.
MODELE_PRINCIPAL = "openai/gpt-oss-120b"
MODELE_SECOURS = "openai/gpt-oss-20b"

DOMAINES = ["Économie & marchés", "Politique monétaire", "Fiscalité & budget", "Entreprises",
            "Géopolitique", "Armées & opérations", "BITD & innovation", "Droit & éthique", "Institutions", "Bourse", "Guerre", "Mondialisation"]

TRANSITIONS = ["certes", "cependant", "néanmoins", "surtout", "en définitive", "pour conclure", "en somme",
               "en revanche", "de surcroît", "en l'occurrence", "en d'autres termes", "il convient de noter", "par ailleurs", "premièrement", "tout d'abord", "puis", "mais enfin", "de plus"]

# Mots qui rendent un article pertinent (en minuscules). Ajoute les tiens.
# "ia" et "cac" ont été retirés/remplacés : ils correspondaient à une multitude de mots sans rapport.
MOTS_CLES = [
    # Les grands sujets
    "bce", "banque centrale", "taux", "inflation", "croissance", "pib", "budget", "dette", "déficit", "fiscal", "impôt",
    "obligation", "bourse", "cac 40", "euro", "dollar", "banque", "crédit", "assurance", "fusion", "acquisition", "opa",
    "faillite", "résultats", "finance", "marché", "investissement", "régulation", "amf", "bâle", "solvabilité",
    "défense", "armée", "militaire", "otan", "ukraine", "russie", "chine", "taïwan", "israël", "gaza", "iran",
    "géopolit", "sanction", "guerre", "conflit", "missile", "drone", "munition", "nucléaire", "dissuasion", "cyber",
    "espace", "satellite", "intelligence artificielle", "industrie", "armement", "dassault", "thales", "airbus",
    "naval", "rafale", "lpm", "rns", "union européenne", "commission européenne", "traité", "onu", "droit international",
    "genève", "cicr", "humanitaire", "éthique", "sahel", "afrique", "pétrole", "énergie", "commerce", "douane", "tarif",
    # Doctrine, stratégie et programmation
    "revue nationale stratégique", "loi de programmation militaire", "livre blanc", "autonomie stratégique",
    "boussole stratégique", "effort de défense", "économie de guerre", "réarmement", "readiness",
    "fonds européen de défense", "pesco", "safe", "dissuasion nucléaire", "force de frappe",
    "flanc est", "article 5", "défense collective", "défense européenne", "pilier européen",
    # Armées, organisation et commandement
    "armée de terre", "marine nationale", "armée de l'air", "gendarmerie", "forces spéciales",
    "état-major", "chef d'état-major", "cema", "dga", "commandement", "opération extérieure", "opex",
    "mission sentinelle", "forces prépositionnées", "projection", "réserve opérationnelle", "garde nationale",
    "service national", "recrutement militaire", "fidélisation", "condition militaire", "statut des militaires",
    # Leadership, éthique et droit
    "chef militaire", "leadership", "obéissance", "discipline militaire", "déontologie", "éthique militaire",
    "droit des conflits armés", "droit international humanitaire", "conventions de genève", "crime de guerre",
    "cour pénale internationale", "cpi", "légitime défense", "proportionnalité", "armes autonomes",
    "robots tueurs", "responsabilité du chef", "livre bleu", "livre vert", 
    # Terrains et crises
    "donbass", "front ukrainien", "mer rouge", "houthis", "détroit d'ormuz", "indo-pacifique", "arctique",
    "baltique", "mer noire", "sahel", "niger", "mali", "tchad", "djibouti", "nouvelle-calédonie",
    "cyberattaque", "guerre hybride", "désinformation", "ingérence", "guerre informationnelle", "afrique", "asie", "europe",
    # Capacités et équipements
    "scaf", "rafale", "leclerc", "griffon", "jaguar", "serval", "caesar", "porte-avions", "sous-marin", "snle",
    "frégate", "sol-air", "samp/t", "munition téléopérée", "guerre électronique", "hypersonique",
    "commandement de l'espace", "cyberdéfense", "intelligence artificielle", "robotique", "mgcs", "main ground combat system", "programme scorpion", 
    # Industrie et finance de défense
    "knds", "knds", "mbda", "naval group", "safran", "arquus", "rheinmetall", "bitd", "direction générale de l'armement",
    "commande publique", "exportation d'armes", "contrat d'armement", "cadence de production", "stocks de munitions",
    "financement de la défense", "épargne de défense", "taxonomie européenne",
    # Anglais (Defense News, War on the Rocks, Fed)
    "readiness", "force posture", "munitions stockpile", "air defense", "electronic warfare", "hypersonic",
    "hybrid warfare", "indo-pacific", "arctic", "defense budget", "defense spending", "deterrence",
    "rules of engagement", "laws of armed conflict", "civil-military", "officer corps", "central bank", 
    "federal reserve", "interest rate", "inflation", "tariff", "sanctions", "defense", "defence",
    "military", "nato", "ceasefire", "missile", "navy", "air force", "procurement", "budget", "bond", 
    "treasury", "war", "united nations organisation", "france", "european union"
]

PERIMETRE = """- marchés financiers, politique monétaire (BCE, Fed, Banque de France), régulation bancaire et financière (AMF, Bâle), fiscalité des investisseurs, entreprises (résultats, fusions, faillites), macroéconomie ;
- géopolitique et relations internationales, armées françaises et alliées, OTAN, base industrielle et technologique de défense (BITD), innovation de défense (IA, drones, espace, cyber), droit international et éthique des conflits.
IGNORE : politique intérieure (sauf lien direct avec le budget, la défense ou la finance), sport, culture, faits divers."""

SYSTEME = ("Tu es un professeur d'économie et de défense qui prépare un candidat au grand oral de fin de scolarité. "
           "Tu écris en français, à l'oral, de façon claire et pédagogique, sans jargon inutile "
           "(niveau Bac à Bac+3 : tu expliques chaque terme technique en une phrase).")

PROMPT_CHOIX = """Tu aides un candidat a son oral de fin de scolarité (domaine défense, filière gestion-économie, option finance).
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

PROMPT_HEBDO = """Écris un récap parlé d'environ 1300 mots (10 minutes) de la semaine, pour un candidat au grand oral de fin de scolarité domaine défense et économie.

MATIÈRE (les sujets traités cette semaine) :
<<MATIERE>>

RÈGLES :
- Dégage 3 à 4 tendances de fond et relie les événements entre eux (cause, conséquence, contradiction).
- Termine par les points à surveiller la semaine prochaine.
- Texte parlé, sans listes ni titres. N'invente rien : utilise uniquement la matière fournie.
- Commence par « Bonjour, voici le récap de la semaine. » et termine par « C'est tout pour cette semaine. Bonne préparation. »"""
