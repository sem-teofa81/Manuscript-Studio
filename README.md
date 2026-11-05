# KDP Manuscript Studio — MVP

Editor gratuito Streamlit per trasformare Google Docs / DOCX in un manoscritto impaginato, con modifiche capitolo per capitolo e PDF 6×9.

## Avvio

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Funzioni
- Importa DOCX esportati da Google Docs.
- Importa Google Docs privati con Google Docs API e credenziali di **account di servizio**: condividi il documento con l'email del service account, abilita Docs API e carica il JSON nell'app. Non caricare mai le credenziali su GitHub.
- Modifica paragrafi, titoli H1–H6, elenchi puntati/numerati, tabelle e schemi ad albero capitolo per capitolo.
- Seleziona un simbolo elenco globale per tutto il libro.
- Trasforma alberi indentati (4 spazi = un livello) in figure vettoriali nel PDF.
- Esporta PDF e DOCX editabile, formato e margini configurabili.

## Limiti della prima versione
Non conserva tutte le immagini, formattazioni inline, note e link di Google Docs. I diagrammi con etichette lunghe vanno controllati visivamente. Il DOCX esportato conserva gli alberi come testo, mentre il PDF li rende come figure. Non genera ancora indice automatico o numerazione automatica dei capitoli e non sostituisce il controllo preflight KDP. Lo stato Streamlit non è persistente: scarica il DOCX prima di chiudere la sessione.
