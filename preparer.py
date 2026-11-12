# -*- coding: utf-8 -*-
"""Prépare le texte pour la voix : nombres et symboles en toutes lettres, prononciations des sigles et mots anglais."""
import re
import config

PRONONCIATIONS_DEFAUT = {
    "BITD": "bé-i-té-dé", "LPM": "èl-pé-èm", "RNS": "èr-èn-ès", "BCE": "bé-cé-eu", "AMF": "a-èm-èf",
    "UE": "u-eu", "IA": "i-a", "DGA": "dé-gé-a", "DGSE": "dé-gé-ès-eu", "FMI": "èf-èm-i", "OCDE": "o-cé-dé-eu",
    "CICR": "cé-i-cé-èr", "BPI": "bé-pé-i",
    "Fed": "Fèd", "Federal Reserve": "Fédéral Rizerve", "hedge fund": "hèdj feund", "hedge funds": "hèdj feunds",
    "private equity": "praïvète èquiti", "Bloomberg": "Bloumbeurg", "Reuters": "Roïteurs", "Nasdaq": "Nazdak",
    "Dow Jones": "Dao Djones", "S&P 500": "Èsse and Pi 500", "Wall Street": "Oual Strit", "Big Tech": "Bigue Tèque",
    "cloud": "claoud", "cash": "cache", "start-up": "starte-eup", "startup": "starte-eup", "leasing": "lizingue",
    "supply chain": "seuplaï tchène", "stress test": "stresse tèste", "OpenAI": "Opène É-Aï",
    "ChatGPT": "Tchatte Gé-Pé-Té", "Nvidia": "Ènvidia", "Brexit": "Brèxite", "cyber": "saïbeur",
    "Boeing": "Boïngue", "Lockheed Martin": "Lokide Martine", "Raytheon": "Réthéone",
    "Northrop Grumman": "Nortrope Grumane", "Rheinmetall": "Raïnmétal", "Baykar": "Baïkar",
    "Bayraktar": "Baïraktar", "Starlink": "Starelinke", "SpaceX": "Spèce-Ex", "Palantir": "Palantire",
    "BlackRock": "Blak-Roque", "Goldman Sachs": "Gôldmane Saks", "Morgan Stanley": "Morgane Stanli",
}


# ---------------------------------------------------------------- Nombres en toutes lettres
_U = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze",
      "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
_D = {2: "vingt", 3: "trente", 4: "quarante", 5: "cinquante", 6: "soixante"}


def _moins_de_cent(n, final=True):
    if n < 20:
        return _U[n]
    d, u = divmod(n, 10)
    if d in _D:
        return _D[d] + ("" if u == 0 else " et un" if u == 1 else "-" + _U[u])
    if d == 7:
        return "soixante" + (" et onze" if u == 1 else "-" + _U[10 + u])
    if d == 8:
        return "quatre-vingt" + ("s" if u == 0 and final else "") + ("" if u == 0 else "-" + _U[u])
    return "quatre-vingt-" + _U[10 + u]


def _moins_de_mille(n, final=True):
    c, r = divmod(n, 100)
    mots = []
    if c:
        mots.append("cent" if c == 1 else _U[c] + " cent" + ("s" if r == 0 and final else ""))
    if r:
        mots.append(_moins_de_cent(r, final))
    return " ".join(mots)


def en_lettres(n, final=True):
    """123 -> « cent vingt-trois » ; 2024 -> « deux mille vingt-quatre »."""
    if n == 0:
        return "zéro"
    mots = []
    for valeur, nom in ((10 ** 9, "milliard"), (10 ** 6, "million")):
        q, n = divmod(n, valeur)
        if q:
            mots.append(en_lettres(q, False) + " " + nom + ("s" if q > 1 else ""))
    q, n = divmod(n, 1000)
    if q:
        mots.append("mille" if q == 1 else _moins_de_mille(q, False) + " mille")
    if n:
        mots.append(_moins_de_mille(n, final))
    return " ".join(mots)


def _ordinal(n):
    if n == 1:
        return "premier"
    m = en_lettres(n)
    if m.endswith("quatre-vingts") or m.endswith("cents"):
        return m[:-1] + "ième"
    if m.endswith("cinq"):
        return m + "uième"
    if m.endswith("neuf"):
        return m[:-1] + "vième"
    if m.endswith("e"):
        return m[:-1] + "ième"
    return m + "ième"


_NOMBRE = re.compile(r"\b\d{1,3}(?:[\u00a0\u202f ]\d{3})+(?:,\d+)?\b|\b\d+(?:,\d+)?\b")


def _nombre(m):
    s = re.sub(r"[\u00a0\u202f ]", "", m.group(0))
    if len(s) > 15:
        return m.group(0)
    if "," in s:
        entier, dec = s.split(",", 1)
        zeros, reste = len(dec) - len(dec.lstrip("0")), dec.lstrip("0")
        suite = ["zéro"] * zeros + ([en_lettres(int(reste))] if reste else [])
        return en_lettres(int(entier)) + " virgule " + " ".join(suite)
    return en_lettres(int(s))


def preparer_voix(texte, supplements=None):
    """Adapte le texte à la voix : prononciations, symboles et nombres en toutes lettres."""
    dico = dict(PRONONCIATIONS_DEFAUT)
    dico.update(supplements or {})
    dico.update(getattr(config, "PRONONCIATIONS", {}))  # tes réglages passent avant ceux de l'IA
    for mot in sorted(dico, key=len, reverse=True):
        texte = re.sub(r"(?<!\w)" + re.escape(mot) + r"(?!\w)", lambda m, v=dico[mot]: v, texte, flags=re.I)
    texte = re.sub(r"(\d{4})\s*[-–]\s*(\d{4})", r"\1 à \2", texte)
    texte = re.sub(r"\bMds?\s*€", "milliards d'euros", texte)
    texte = re.sub(r"\bM\s*€", "millions d'euros", texte)
    texte = re.sub(r"\bMds?\s*\$", "milliards de dollars", texte)
    texte = re.sub(r"\bM\s*\$", "millions de dollars", texte)
    texte = texte.replace("€", " euros").replace("%", " pour cent").replace("n°", "numéro ")
    texte = re.sub(r"(\d)\s*\$", r"\1 dollars", texte)
    texte = re.sub(r"(?<=[A-Z])(?=\d)", " ", texte)  # G7 -> G 7
    texte = re.sub(r"\b1er\b", "premier", texte)
    texte = re.sub(r"\b1re\b", "première", texte)
    texte = re.sub(r"\b(\d+)(?:e|ème)\b", lambda m: _ordinal(int(m.group(1))), texte)
    texte = _NOMBRE.sub(_nombre, texte)
    return re.sub(r"[ \t]{2,}", " ", texte)
