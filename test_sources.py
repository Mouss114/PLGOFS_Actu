# -*- coding: utf-8 -*-
"""Teste chaque source de config.py et dit lesquelles fonctionnent."""
import config
from main import lire_flux

for nom, src in config.SOURCES:
    try:
        lot = lire_flux(nom, src)
        exemple = f"  ex : {lot[0]['titre'][:70]}" if lot else ""
        print(("✅" if lot else "⚠️ ") + f" {nom} : {len(lot)} article(s) récent(s){exemple}")
    except Exception as e:
        print(f"❌ {nom} : {e}")
