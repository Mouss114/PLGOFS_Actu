# -*- coding: utf-8 -*-
"""Podcast du matin : collecte -> choix des sujets -> rédaction -> voix -> Telegram."""
import datetime as dt, re, sys, time
import feedparser, requests
import config, lib, memory

UA = {"User-Agent": "Mozilla/5.0 (compatible; PodcastVeille/1.0)"}
MAINTENANT = dt.datetime.now(dt.timezone.utc)
MOTS_CLES = [re.compile((r"\b%s\b" if len(k) <= 3 else r"\b%s") % re.escape(k)) for k in config.MOTS_CLES]


# ------------------------------------------------------------ 1. Collecte
def adresse(src):
    if src.startswith("google:"):
        return f"https://news.google.com/rss/search?q=site:{src[7:]}+when:2d&hl=fr&gl=FR&ceid=FR:fr"
    return src


def nettoyer(html, n):
    texte = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", texte).strip()[:n]


def date_article(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return dt.datetime(*t[:6], tzinfo=dt.timezone.utc) if t else None


def lire_flux(nom, src):
    """Articles récents d'une source (fenêtre de 48 h)."""
    r = requests.get(adresse(src), headers=UA, timeout=20)
    r.raise_for_status()
    flux = feedparser.parse(r.content)
    sortie = []
    for e in flux.entries[:40]:
        d = date_article(e)
        if d and MAINTENANT - d > dt.timedelta(hours=config.FENETRE_HEURES):
            continue
        titre = nettoyer(e.get("title"), 200)
        if not titre:
            continue
        resume = "" if src.startswith("google:") else nettoyer(e.get("summary") or e.get("description"), 400)
        sortie.append({"source": nom, "titre": titre, "resume": resume, "lien": e.get("link", ""), "date": d or MAINTENANT})
    return sortie


def collecter():
    vus, articles = set(), []
    for nom, src in config.SOURCES:
        try:
            lot = lire_flux(nom, src)
        except Exception as e:
            print(f"  ✗ {nom} : {e}")
            continue
        for a in lot:
            cle = a["titre"].lower()[:80]
            if cle not in vus:
                vus.add(cle)
                articles.append(a)
        print(f"  ✓ {nom} : {len(lot)} article(s)")
    return articles


def score(a):
    texte = (a["titre"] + " " + a["resume"]).lower()
    return sum(1 for rx in MOTS_CLES if rx.search(texte))


def pertinents(articles):
    notes = [(score(a), a) for a in articles]
    gardes = [x for x in notes if x[0] > 0] or notes
    gardes.sort(key=lambda x: (x[0], x[1]["date"]), reverse=True)
    return [a for _, a in gardes[:config.MAX_ARTICLES]]


# ------------------------------------------------------------ 2. Choix des sujets
def choisir_sujets(articles):
    liste = "\n".join(f"[{i}] ({a['source']}) {a['titre']}" for i, a in enumerate(articles))
    prompt = lib.fill(config.PROMPT_CHOIX, PERIMETRE=config.PERIMETRE, LISTE=liste, N=config.NB_SUJETS)
    data = lib.parse_json(lib.groq_chat(prompt, json_mode=True, max_tokens=1200, temperature=0.2)) or {}
    sujets = []
    for s in data.get("sujets", []):
        ids = [i for i in s.get("ids", []) if isinstance(i, int) and 0 <= i < len(articles)]
        try:
            importance = int(s.get("importance", 3))
        except (TypeError, ValueError):
            importance = 3
        if ids and s.get("nom"):
            sujets.append({"nom": str(s["nom"]), "ids": ids[:5], "importance": importance})
    if not sujets:  # secours : un sujet par article
        sujets = [{"nom": a["titre"], "ids": [i], "importance": 3} for i, a in enumerate(articles[:config.NB_SUJETS])]
    sujets.sort(key=lambda s: -s["importance"])
    return sujets[:config.NB_SUJETS]


# ------------------------------------------------------------ 3. Rédaction
def texte_article(lien, n=1500):
    if not lien or "news.google.com" in lien:
        return ""
    try:
        import trafilatura
        r = requests.get(lien, headers=UA, timeout=10)
        return (trafilatura.extract(r.text) or "")[:n]
    except Exception:
        return ""


def ecrire_sujet(sujet, articles, approfondi):
    mots = config.MOTS_APPROFONDI if approfondi else config.MOTS_SUJET
    extraits = ""
    for a in articles:
        corps = texte_article(a["lien"]) or a["resume"]
        extraits += f"- (publié le {a['date']:%d/%m/%Y}) {a['titre']}. {corps}\n"
    refs = "".join(f"- ({p['doc']}, p. {p['page']}) {p['content']}\n" for p in memory.passages(sujet["nom"], 3))
    prompt = lib.fill(config.PROMPT_SUJET, NOM=sujet["nom"], EXTRAITS=extraits[:7000], REFS=refs or "(aucun)",
                      MOTS=mots, MIN=mots - 60, MAX=mots + 60, TRANSITIONS=", ".join(config.TRANSITIONS),
                      DOMAINES=" | ".join(config.DOMAINES))
    data, sortie = None, ""
    for essai in range(2):
        sortie = lib.groq_chat(prompt, system=config.SYSTEME, json_mode=True, max_tokens=3000)
        data = lib.parse_json(sortie)
        if data and data.get("texte"):
            break
    if not data or not data.get("texte"):
        data = {"texte": sortie}
    jury = data.get("jury") if isinstance(data.get("jury"), dict) else {}
    return {"nom": sujet["nom"], "approfondi": approfondi, "texte": str(data["texte"]).strip(),
            "domaine": str(data.get("domaine") or ""), "a_retenir": str(data.get("a_retenir") or ""),
            "chiffres": [str(c) for c in (data.get("chiffres") or [])][:5],
            "jury": {"question": str(jury.get("question") or ""), "reponse": str(jury.get("reponse") or "")},
            "termes": [t for t in (data.get("termes") or []) if isinstance(t, dict)]}


def assembler_script(blocs, jour):
    noms = [b["nom"] for b in blocs]
    liste = noms[0] if len(noms) == 1 else ", ".join(noms[:-1]) + " et " + noms[-1]
    parties = [f"Bonjour, voici l'actualité du {lib.date_fr(jour)}. Au programme : {liste}."]
    for i, b in enumerate(blocs, 1):
        intro = "Commençons par le sujet du jour" if b["approfondi"] else f"Sujet numéro {i}"
        morceau = f"{intro} : {b['nom']}.\n{b['texte']}"
        if b["a_retenir"]:
            morceau += f"\nÀ retenir : {b['a_retenir']}"
        if b["jury"]["question"]:
            morceau += f"\nQuestion possible du jury : {b['jury']['question']} … Réponse possible : {b['jury']['reponse']}"
        parties.append(morceau)
    parties.append("C'est tout pour aujourd'hui. Bonne préparation.")
    return "\n\n".join(parties)


# ------------------------------------------------------------ 4. Messages Telegram
PRONONCIATION = {
    "OTAN": "Otan", "EMIA": "É-M-I-A", "UE": "U-E", "PIB": "P-I-B",
    "ONU": "Onu", "FAMAS": "Famas", "n°": "numéro",
}


def _nombre_compact(m):
    return re.sub(r"[\s\u00a0\u202f]", "", m.group(0))


def preparer_voix(texte):
    """Nettoie le script pour la synthèse vocale (le fichier script.txt reste inchangé)."""
    texte = texte.replace(" … Réponse possible", "\n\nRéponse possible")  # pause avant la réponse
    for k, v in PRONONCIATION.items():
        texte = re.sub(r"(?<!\w)%s(?!\w)" % re.escape(k), v, texte)
    texte = texte.replace("M€", " millions d'euros").replace("Md€", " milliards d'euros")
    texte = texte.replace("€", " euros").replace("%", " pour cent")
    texte = re.sub(r"\([^)]*\)", "", texte)  # parenthèses
    texte = re.sub(r"(?<!\d)\d{1,3}(?:[\s\u00a0\u202f]\d{3})+(?!\d)", _nombre_compact, texte)  # 1 200 000 -> 1200000
    texte = texte.replace("…", ",").replace(" - ", ", ")
    return re.sub(r"[ \t]{2,}", " ", texte)


def resume(blocs, jour, minutes):
    lignes = [f"🎧 {lib.date_fr(jour)} — {minutes} min", ""]
    for i, b in enumerate(blocs, 1):
        lignes.append(f"{i}. {b['nom']}" + (" ⭐" if b["approfondi"] else ""))
        if b["a_retenir"]:
            lignes.append(f"   → {b['a_retenir']}")
    chiffres = [c for b in blocs for c in b["chiffres"]][:8]
    if chiffres:
        lignes += ["", "🔢 Chiffres à retenir :"] + [f"• {c}" for c in chiffres]
    lignes += ["", "⚠️ Les chiffres viennent des articles du jour : vérifie les montants importants avant l'oral."]
    return "\n".join(lignes)


def question_du_jour(blocs):
    q = next((b["jury"]["question"] for b in blocs if b["approfondi"] and b["jury"]["question"]), "")
    if not q:
        return ""
    texte = f"❓ Question du jour : {q}"
    if lib.env("BOT_ACTIF"):
        texte += "\n\nRéponds à CE message (texte ou vocal) pour recevoir un retour."
    return texte


# ------------------------------------------------------------ Lancement
def main():
    jour = lib.aujourdhui()
    print("1/5 Collecte des articles")
    articles = collecter()
    if not articles:
        raise RuntimeError("Aucun article récupéré (sources inaccessibles ?)")
    memory.sauver_articles(articles)
    choisis = pertinents(articles)
    print(f"    {len(articles)} articles, {len(choisis)} retenus")

    print("2/5 Choix des sujets")
    sujets = choisir_sujets(choisis)

    print("3/5 Rédaction")
    blocs = []
    for i, s in enumerate(sujets):
        time.sleep(config.PAUSE)
        blocs.append(ecrire_sujet(s, [choisis[k] for k in s["ids"]], approfondi=(i == 0)))
        print(f"    ✓ {s['nom']}")
    script = assembler_script(blocs, jour)
    print(f"    script : {len(script.split())} mots")

    print("4/5 Voix")
    mp3, secondes = lib.texte_vers_mp3(preparer_voix(script), "/tmp/podcast.mp3")
    minutes = round(secondes / 60)
    with open("/tmp/script.txt", "w", encoding="utf-8") as f:
        f.write(script)
    memory.sauver_podcast(jour, secondes, script, blocs)

    print("5/5 Envoi sur Telegram")
    q = question_du_jour(blocs)
    for chat in lib.chat_ids():
        lib.envoyer_audio(chat, mp3, f"Podcast {jour:%d/%m/%Y}", secondes)
        lib.envoyer_texte(chat, resume(blocs, jour, minutes))
        lib.envoyer_document(chat, "/tmp/script.txt", f"script-{jour:%Y-%m-%d}.txt")
        if q:
            lib.envoyer_texte(chat, q)
    print("Terminé.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERREUR :", e)
        try:
            lib.prevenir(f"⚠️ Le podcast du jour a échoué : {e}")
        except Exception:
            pass
        sys.exit(1)
