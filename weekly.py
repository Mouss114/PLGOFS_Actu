# -*- coding: utf-8 -*-
"""Récap de la semaine (dimanche soir) : un podcast de 10 minutes."""
import config, lib, memory
 
 
def resume(lignes, jour, minutes):
    """Message Telegram : sujets de la semaine, à retenir et chiffres (sans appel IA)."""
    out = [f"🎧 Récap de la semaine, {lib.date_fr(jour)} — {minutes} min", ""]
    vus = set()
    for l in lignes:
        if l["nom"] in vus:
            continue
        vus.add(l["nom"])
        out.append(f"• {l['nom']}")
        if l.get("a_retenir"):
            out.append(f"   → {l['a_retenir']}")
    chiffres = []
    for l in lignes:
        chiffres += [str(c) for c in (l.get("chiffres") or [])]
    if chiffres:
        out += ["", "🔢 Chiffres de la semaine :"] + [f"• {c}" for c in chiffres[:12]]
    out += ["", "⚠️ Vérifie les montants importants avant l'oral."]
    return "\n".join(out)
 
 
def main():
    lignes = memory.sujets_recents(7)
    if len(lignes) < 3:
        lib.prevenir("Pas assez de podcasts cette semaine pour faire un récap.")
        return
    matiere = "\n".join(
        f"- {l['date']} | {l['nom']} | {l['a_retenir']} | chiffres : {'; '.join(map(str, l.get('chiffres') or []))}"
        for l in lignes)[:6000]
    texte = lib.groq_chat(lib.fill(config.PROMPT_HEBDO, MATIERE=matiere), system=config.SYSTEME,
                          max_tokens=3500, temperature=0.5)
    mp3, secondes = lib.texte_vers_mp3(texte, "/tmp/hebdo.mp3")
    with open("/tmp/hebdo.txt", "w", encoding="utf-8") as f:
        f.write(texte)
    jour = lib.aujourdhui()
    message = resume(lignes, jour, round(secondes / 60))
    for chat in lib.chat_ids():
        lib.envoyer_audio(chat, mp3, f"Récap de la semaine {jour:%d/%m/%Y}", secondes)
        lib.envoyer_texte(chat, message)
        lib.envoyer_document(chat, "/tmp/hebdo.txt", f"recap-{jour:%Y-%m-%d}.txt")
 
 
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERREUR :", e)
        lib.prevenir(f"⚠️ Le récap de la semaine a échoué : {e}")
        raise
 
