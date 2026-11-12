# -*- coding: utf-8 -*-
"""Charge les PDF du dossier references/ dans la mémoire Supabase (RNS, LPM...)."""
import glob, os, re, sys
from pypdf import PdfReader
import memory


def morceaux(texte, taille=900, recouvrement=150):
    sortie, i = [], 0
    while i < len(texte):
        j = min(len(texte), i + taille)
        if j < len(texte):
            k = texte.rfind(". ", i + taille // 2, j)
            if k != -1:
                j = k + 1
        sortie.append(texte[i:j].strip())
        if j >= len(texte):
            break
        i = max(j - recouvrement, i + 1)
    return [m for m in sortie if len(m) > 80]


def main():
    if not memory.actif():
        sys.exit("Secrets SUPABASE_URL / SUPABASE_SECRET_KEY manquants.")
    fichiers = sorted(glob.glob("references/*.pdf"))
    if not fichiers:
        sys.exit("Aucun PDF dans le dossier references/.")
    echecs = 0
    for chemin in fichiers:
        doc = os.path.basename(chemin)[:-4]
        print(f"Lecture de {doc} ...")
        try:
            lignes = []
            for no, page in enumerate(PdfReader(chemin).pages, 1):
                texte = re.sub(r"\s+", " ", page.extract_text() or "").strip()
                lignes += [{"doc": doc, "page": no, "content": m} for m in morceaux(texte)]
        except Exception as e:
            print(f"  ÉCHEC de lecture : {e}")
            echecs += 1
            continue
        if memory.supprimer("documents", "doc", doc) and memory.inserer("documents", lignes):
            print(f"  {len(lignes)} passages enregistrés")
        else:
            print("  ÉCHEC : rien n'a été enregistré (vérifie SUPABASE_URL et SUPABASE_SECRET_KEY)")
            echecs += 1
    if echecs:
        sys.exit(f"{echecs} document(s) en échec.")


if __name__ == "__main__":
    main()
