# -*- coding: utf-8 -*-
"""Outils communs : IA (Groq), voix, Telegram."""
import asyncio, datetime as dt, json, os, re, time
from zoneinfo import ZoneInfo
import requests
import config

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def env(nom):
    return os.environ.get(nom, "").strip()


def aujourdhui():
    return dt.datetime.now(ZoneInfo("Europe/Paris")).date()


def date_fr(d):
    jour = "1er" if d.day == 1 else str(d.day)
    return f"{JOURS[d.weekday()]} {jour} {MOIS[d.month - 1]} {d.year}"


def fill(modele, **valeurs):
    for cle, val in valeurs.items():
        modele = modele.replace(f"<<{cle}>>", str(val))
    return modele


def parse_json(texte):
    try:
        return json.loads(texte)
    except Exception:
        pass
    m = re.search(r"\{.*\}", texte or "", re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


# ---------------------------------------------------------------- IA (Groq)
def groq_chat(prompt, system="", max_tokens=1500, json_mode=False, temperature=0.4):
    """Appelle Groq. Réessaie en cas de limite, puis bascule sur le modèle de secours."""
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    derniere = None
    for modele in (config.MODELE_PRINCIPAL, config.MODELE_SECOURS):
        for essai in range(4):
            corps = {"model": modele, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
            if json_mode:
                corps["response_format"] = {"type": "json_object"}
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                  headers={"Authorization": "Bearer " + env("GROQ_API_KEY")}, json=corps, timeout=120)
                if r.status_code == 429:
                    try:
                        attente = float(r.headers.get("retry-after", 30))
                    except ValueError:
                        attente = 30
                    print(f"  limite Groq atteinte, pause de {attente:.0f}s")
                    derniere = "429 (limite gratuite)"
                    time.sleep(min(attente + 2, 90))
                    continue
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                derniere = e
                time.sleep(5)
        print(f"  modèle {modele} indisponible ({derniere}) -> modèle suivant")
    raise RuntimeError(f"Groq a échoué : {derniere}")


# ---------------------------------------------------------------- Voix
def decouper(texte, taille=2500):
    morceaux, courant = [], ""
    for phrase in re.split(r"(?<=[.!?…])\s+", texte):
        if courant and len(courant) + len(phrase) + 1 > taille:
            morceaux.append(courant.strip())
            courant = ""
        courant += phrase + " "
    if courant.strip():
        morceaux.append(courant.strip())
    return morceaux


async def _edge(texte, voix, chemin):
    import edge_tts
    await edge_tts.Communicate(texte, voix).save(chemin)


def texte_vers_mp3(texte, sortie):
    """Texte -> MP3. Essaie edge-tts (voix naturelle), puis gTTS (secours). Retourne (chemin, secondes)."""
    morceaux = decouper(texte)
    fichiers, moteur = [], "edge-tts"
    try:
        for i, m in enumerate(morceaux):
            f = f"/tmp/seg_{i}.mp3"
            for essai in range(3):
                try:
                    asyncio.run(_edge(m, config.VOIX, f))
                    if os.path.getsize(f) > 1000:
                        break
                except Exception as e:
                    print(f"  edge-tts essai {essai + 1} : {e}")
                    time.sleep(4)
            else:
                raise RuntimeError("edge-tts n'a pas répondu")
            fichiers.append(f)
    except Exception as e:
        print(f"  edge-tts indisponible ({e}) -> voix de secours gTTS")
        from gtts import gTTS
        moteur, fichiers = "gtts", []
        for i, m in enumerate(morceaux):
            f = f"/tmp/gseg_{i}.mp3"
            gTTS(m, lang="fr").save(f)
            fichiers.append(f)
    with open(sortie, "wb") as out:
        for f in fichiers:
            with open(f, "rb") as src:
                out.write(src.read())
    taille = os.path.getsize(sortie)
    secondes = taille * 8 / 48000 if moteur == "edge-tts" else len(texte.split()) / 150 * 60
    print(f"  audio ({moteur}) : {secondes / 60:.1f} min, {taille / 1e6:.1f} Mo")
    return sortie, secondes


# ---------------------------------------------------------------- Telegram
def _tg(methode, **kw):
    r = requests.post(f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/{methode}", timeout=180, **kw)
    if not r.ok:
        print(f"  Telegram {methode} : {r.status_code} {r.text[:200]}")
    return r


def chat_ids():
    ids = [x.strip() for x in env("TELEGRAM_CHAT_IDS").split(",") if x.strip()]
    import memory
    for c in memory.chat_ids():
        if str(c) not in ids:
            ids.append(str(c))
    return ids


def envoyer_texte(chat, texte):
    for i in range(0, len(texte), 4000):
        _tg("sendMessage", json={"chat_id": chat, "text": texte[i:i + 4000]})


def envoyer_audio(chat, chemin, titre, secondes):
    with open(chemin, "rb") as f:
        _tg("sendAudio", data={"chat_id": chat, "title": titre, "performer": "Préparation Grand Oral",
                               "duration": int(secondes)}, files={"audio": f})


def envoyer_document(chat, chemin, nom):
    with open(chemin, "rb") as f:
        _tg("sendDocument", data={"chat_id": chat}, files={"document": (nom, f)})


def prevenir(texte):
    for chat in chat_ids():
        envoyer_texte(chat, texte)
