# -*- coding: utf-8 -*-
"""Mémoire Supabase. Sans les secrets SUPABASE_*, ce fichier ne fait rien (Phase 1)."""
import datetime as dt, os
import requests

URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
CLE = os.environ.get("SUPABASE_SECRET_KEY", "").strip()


def actif():
    return bool(URL and CLE)


def _appel(methode, chemin, entetes=None, **kw):
    if not actif():
        return None
    h = {"apikey": CLE, "Content-Type": "application/json"}
    if CLE.startswith("eyJ"):  # ancienne clé "service_role"
        h["Authorization"] = "Bearer " + CLE
    h.update(entetes or {})
    try:
        r = requests.request(methode, f"{URL}/rest/v1/{chemin}", headers=h, timeout=60, **kw)
        if r.status_code >= 300:
            print(f"  (Supabase {chemin} -> {r.status_code} {r.text[:200]})")
            return None
        return r.json() if r.text else []
    except Exception as e:
        print(f"  (Supabase indisponible : {e})")
        return None


def inserer(table, lignes, conflit=None):
    if not lignes:
        return
    params = {"on_conflict": conflit} if conflit else None
    pref = "return=minimal" + (",resolution=ignore-duplicates" if conflit else "")
    for i in range(0, len(lignes), 200):
        _appel("POST", table, params=params, json=lignes[i:i + 200], entetes={"Prefer": pref})


def supprimer(table, colonne, valeur):
    _appel("DELETE", table, params={colonne: "eq." + str(valeur)})


def sauver_articles(articles):
    lignes = [{"source": a["source"], "title": a["titre"], "summary": a["resume"], "link": a["lien"],
               "published": a["date"].isoformat()} for a in articles if a["lien"]]
    inserer("articles", lignes, conflit="link")
    limite = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=120)).isoformat()
    _appel("DELETE", "articles", params={"published": "lt." + limite})


def sauver_podcast(jour, secondes, script, blocs):
    if not actif():
        return
    j = jour.isoformat()
    supprimer("podcasts", "date", j)
    supprimer("podcast_topics", "date", j)
    inserer("podcasts", [{"date": j, "duree_s": int(secondes), "script": script}])
    inserer("podcast_topics", [{"date": j, "nom": b["nom"], "domaine": b["domaine"], "texte": b["texte"],
                                "chiffres": b["chiffres"], "a_retenir": b["a_retenir"], "jury": b["jury"],
                                "termes": b["termes"], "approfondi": b["approfondi"]} for b in blocs])
    termes = [{"terme": t["terme"].strip().lower(), "definition": t["definition"], "domaine": b["domaine"],
               "premiere_date": j}
              for b in blocs for t in b["termes"] if isinstance(t, dict) and t.get("terme") and t.get("definition")]
    inserer("glossaire", termes, conflit="terme")


def passages(requete, n=3):
    return _appel("POST", "rpc/chercher_docs", json={"q": requete, "n": n}) or []


def chat_ids():
    lignes = _appel("GET", "utilisateurs", params={"select": "chat_id"}) or []
    return [r["chat_id"] for r in lignes]


def sujets_recents(jours=7):
    depuis = (dt.date.today() - dt.timedelta(days=jours)).isoformat()
    return _appel("GET", "podcast_topics", params={"date": "gte." + depuis, "order": "date.asc",
                                                    "select": "date,nom,domaine,a_retenir,chiffres"}) or []
