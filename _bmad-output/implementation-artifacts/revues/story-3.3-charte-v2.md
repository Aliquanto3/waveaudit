## Revue

### Passe 2 (2026-11-06, SHA revu 475a657)
- Aucun constat Important. Delta 874196f..475a657 relu.
- Filet or : `w:pBdr/w:bottom` unique, val=single, sz=24 (3 pt), color=8F6300, sans themeColor ; couvert par `test_theme_generique_filet_or_sous_le_titre`.
- Empreinte des jetons : sha256 de couples `cle:VALEUR` extraits par regex et joints par `\n`, donc indépendante des fins de ligne (CRLF/LF) et de l'OS. OK.
- Mutation manuelle (`background-color: var(--primaire-vif)` sur `button`) : 2 tests échouent (aplat bleu, bouton neutre). Fichier restauré.
- ruff check/format OK ; test_contraste + test_export_docx : 47 passés.
