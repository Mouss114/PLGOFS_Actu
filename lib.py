# -*- coding: utf-8 -*-
"""Outils communs : IA (Groq), voix, Telegram."""
import asyncio, datetime as dt, json, os, re, subprocess, tempfile, time
from zoneinfo import ZoneInfo
import requests
import edge_tts
import config
from preparer import preparer_voix

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
ATEMPO = 1.08  # vitesse de lecture appliquée par ffmpeg (1.0 = normal, 1.15 = plus rapide)
# Voix de rechange si config.VOIX ne répond pas : toutes françaises de France, hommes d'abord, puis femme.
VOIX_ALTERNATIVES = ["fr-FR-RemyMultilingualNeural", "fr-FR-HenriNeural", "fr-FR-DeniseNeural"]
ATTENTES = (5, 15, 30, 60, 120)  # secondes d'attente entre les essais d'un même morceau
PAUSE_ENTRE_MORCEAUX = 0.7       # secondes : évite de se faire refuser par le service gratuit
VOIX_ROBOT = getattr(config, "VOIX_ROBOT", "non")  # "oui" dans config.py = accepte la voix robotique gTTS en dernier recours


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
    await edge_tts.Communicate(texte, voix).save(chemin)


def _silence(chemin, secondes):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(secondes),
                    "-c:a", "libmp3lame", "-b:a", "48k", chemin], check=True, capture_output=True)


def _edge_segment(texte, chemin, candidates):
    """Essaie chaque voix, patiemment (6 essais, attentes croissantes). Retourne la voix qui a fonctionné."""
    for voix in candidates:
        for essai in range(len(ATTENTES) + 1):
            try:
                asyncio.run(_edge(texte, voix, chemin))
                if os.path.getsize(chemin) > 1000:
                    return voix
            except Exception as e:
                print(f"  edge-tts ({voix}) essai {essai + 1} : {e}")
            if essai < len(ATTENTES):
                time.sleep(ATTENTES[essai])
    raise RuntimeError("edge-tts n'a pas répondu")


def _signaler_echec(script):
    """Aucune voix naturelle : on envoie le script texte et on prévient, sans audio robotique."""
    try:
        with open("/tmp/script.txt", "w", encoding="utf-8") as f:
            f.write(script)
        for chat in chat_ids():
            envoyer_texte(chat, "🔇 La voix naturelle est indisponible ce matin (service Microsoft). "
                                "Voici le script texte. Relance « Podcast du matin » (Run workflow) dans quelques minutes pour l'audio.")
            envoyer_document(chat, "/tmp/script.txt", "script.txt")
    except Exception as e:
        print(f"  (envoi du script impossible : {e})")


def texte_vers_mp3(texte, sortie, prononciations=None):
    """Texte -> MP3 avec pauses et volume normalisé. edge-tts, voix de rechange, puis (si autorisé) gTTS. Retourne (chemin, secondes)."""
    script = texte
    texte = preparer_voix(texte, prononciations)  # années, chiffres, sigles et mots anglais
    # liste de (morceau de texte, pause après lui en secondes)
    morceaux = []
    for bloc in [b for b in texte.split("\n\n") if b.strip()]:
        lignes = [l.strip() for l in bloc.split("\n") if l.strip()]
        for li, ligne in enumerate(lignes):
            parts = decouper(ligne)
            for pi, p in enumerate(parts):
                if pi < len(parts) - 1:
                    pause = 0.1
                elif li < len(lignes) - 1:
                    pause = 0.3
                else:
                    pause = 0.8
                morceaux.append((p, pause))

    with tempfile.TemporaryDirectory() as tmp:
        silences = {}
        for p in {pause for _, pause in morceaux}:
            silences[p] = f"{tmp}/sil_{p}.mp3"
            _silence(silences[p], p)

        voix_ok = [None]

        def synth(moteur):
            fichiers = []
            for i, (m, pause) in enumerate(morceaux):
                f = f"{tmp}/seg_{i}.mp3"
                if moteur == "edge-tts":
                    candidates = [voix_ok[0]] if voix_ok[0] else list(dict.fromkeys([config.VOIX] + VOIX_ALTERNATIVES))
                    voix_ok[0] = _edge_segment(m, f, candidates)
                    time.sleep(PAUSE_ENTRE_MORCEAUX)
                else:
                    from gtts import gTTS
                    gTTS(m, lang="fr").save(f)
                fichiers += [f, silences[pause]]
            return fichiers

        moteur = "edge-tts"
        try:
            fichiers = synth("edge-tts")
            moteur = f"edge-tts, {voix_ok[0]}"
        except Exception as e:
            print(f"  edge-tts indisponible ({e})")
            if VOIX_ROBOT != "oui":
                _signaler_echec(script)
                raise RuntimeError("Voix naturelle indisponible (edge-tts)")
            moteur = "gtts"
            try:
                prevenir("⚠️ Voix de secours gTTS utilisée aujourd'hui (edge-tts indisponible).")
            except Exception:
                pass
            fichiers = synth("gtts")

        liste = f"{tmp}/liste.txt"
        with open(liste, "w") as fh:
            fh.write("\n".join(f"file '{f}'" for f in fichiers))
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", liste,
                        "-af", f"atempo={ATEMPO},loudnorm=I=-16:TP=-1.5:LRA=11",
                        "-ar", "44100", "-b:a", "96k", sortie],
                       check=True, capture_output=True)

    duree = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", sortie],
                           capture_output=True, text=True, check=True).stdout
    secondes = float(duree.strip())
    print(f"  audio ({moteur}) : {secondes / 60:.1f} min, {os.path.getsize(sortie) / 1e6:.1f} Mo")
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
