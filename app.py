import json,re
from datetime import date
from frontmatter import export_front_cover
from diagram_conversion import convert_diagrams
from table_conversion import convert_tables
from markup import import_markdown
import streamlit as st
from engine import import_docx,import_google_doc,chapters,export_pdf,export_docx,block,BULLETS
st.set_page_config(page_title='KDP Manuscript Studio',layout='wide')
st.title('KDP Manuscript Studio')
if 'blocks' not in st.session_state: st.session_state.blocks=[]
if 'opts' not in st.session_state: st.session_state.opts=dict(width=6.,height=9.,margin=.7,font_size=9.5,bullet='Pallino',chapter_breaks=True,title='Manoscritto',subtitle='',author='',year=str(date.today().year),isbn='',edition='Prima edizione',copyright_note='',title_page=True,copyright_page=True,toc=True)
with st.sidebar:
    st.header('Importazione')
    file=st.file_uploader('DOCX esportato da Google Docs',type='docx')
    if file and st.button('Importa DOCX'):
        st.session_state.blocks=import_docx(file.getvalue());st.rerun()
    md_file=st.file_uploader('Manoscritto Markdown (.md o .txt)',type=['md','txt'])
    if md_file and st.button('Importa Markdown'):
        st.session_state.blocks=import_markdown(md_file.getvalue().decode('utf-8-sig'));st.rerun()
    st.divider()
    url=st.text_input('URL Google Docs')
    secret=st.file_uploader('Credenziali account di servizio Google (JSON)',type='json')
    if st.button('Importa Google Docs'):
        m=re.search(r'/document/d/([\w-]+)',url)
        if not m or not secret:st.error('Servono URL valido e credenziali JSON. Condividi il documento con l’account di servizio.')
        else:
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                auth=service_account.Credentials.from_service_account_info(json.loads(secret.getvalue()),scopes=['https://www.googleapis.com/auth/documents.readonly'])
                data=build('docs','v1',credentials=auth,cache_discovery=False).documents().get(documentId=m.group(1)).execute()
                st.session_state.blocks=import_google_doc(data);st.rerun()
            except Exception as e:st.error(str(e))
    st.divider();st.header('Impostazioni globali')
    o=st.session_state.opts
    o['title']=st.text_input('Titolo',o['title'])
    st.subheader('Pagine iniziali e indice')
    o['subtitle']=st.text_input('Sottotitolo',o.get('subtitle',''))
    o['author']=st.text_input('Autore',o.get('author',''))
    o['year']=st.text_input('Anno copyright',o.get('year',str(date.today().year)))
    o['isbn']=st.text_input('ISBN (facoltativo)',o.get('isbn',''))
    o['edition']=st.text_input('Edizione',o.get('edition','Prima edizione'))
    o['copyright_note']=st.text_area('Note editoriali / diritti',o.get('copyright_note',''),height=70)
    o['title_page']=st.checkbox('Pagina del titolo',value=o.get('title_page',True))
    o['copyright_page']=st.checkbox('Pagina dei diritti',value=o.get('copyright_page',True))
    o['toc']=st.checkbox('Indice automatico H1–H2',value=o.get('toc',True))
    o['bullet']=st.selectbox('Simbolo elenchi',list(BULLETS),index=list(BULLETS).index(o['bullet']))
    for k,label,minimum,maximum,step in [('width','Larghezza pollici',4.,9.,.25),('height','Altezza pollici',6.,12.,.25),('margin','Margini pollici',.3,1.2,.05),('font_size','Dimensione testo pt',8.,14.,.25)]:
        o[k]=st.number_input(label,minimum,maximum,float(o[k]),step)
    o['chapter_breaks']=st.checkbox('Capitoli su nuova pagina',value=o['chapter_breaks'])
    o['chapters_recto']=st.checkbox('Capitoli su pagina dispari (destra / recto)',value=o.get('chapters_recto',True),disabled=not o['chapter_breaks'])
    o['gutter']=st.number_input('Margine interno aggiuntivo (pollici)',min_value=0.0,max_value=0.5,value=float(o.get('gutter',0.12)),step=0.02)
    st.caption('Stampa KDP: le pagine dispari sono a destra. Se necessario viene inserita una pagina bianca a sinistra; il frontespizio e la pagina dei diritti non mostrano il numero di pagina.')
    st.download_button('Esporta bozza piatto anteriore (PDF)',export_front_cover(o),'bozza_piatto_anteriore.pdf','application/pdf',use_container_width=True)
    st.caption('Il piatto anteriore è una bozza separata: per la copertina KDP completa servono anche dorso, retro e abbondanze, calcolati sul numero finale di pagine e sul tipo di carta.')
    if st.session_state.blocks:
        st.download_button('Esporta PDF',export_pdf(st.session_state.blocks,o),'manoscritto_kdp.pdf','application/pdf',use_container_width=True)
        st.download_button('Esporta DOCX',export_docx(st.session_state.blocks,o),'manoscritto_editabile.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document',use_container_width=True)
blocks=st.session_state.blocks
if not blocks:
    st.info('Importa un documento oppure crea un manoscritto nuovo.')
    if st.button('Nuovo manoscritto'):
        st.session_state.blocks=[block('heading','Capitolo 1',1),block('paragraph','Scrivi qui.')];st.rerun()
else:
    st.subheader('Conversione diagrammi testuali')
    st.caption('Riconosce automaticamente schemi con │, ├── e └──, unisce titolo e rami e li trasforma in blocchi grafici modificabili. Il testo originale resta invariato finché non premi il pulsante.')
    if st.button('Trasforma tutti i diagrammi in grafici',type='primary'):
        converted,count=convert_diagrams(blocks)
        st.session_state.blocks=converted
        st.session_state.diagram_count=count
        st.rerun()
    if 'diagram_count' in st.session_state:
        st.success(f"Diagrammi convertiti: {st.session_state.pop('diagram_count')}")
    st.subheader('Conversione tabelle testuali')
    st.caption('Converte gruppi di righe separate da |, │ o tabulazioni in tabelle impaginate. Le tabelle Word già strutturate restano inalterate.')
    if st.button('Trasforma tutte le tabelle testuali in tabelle grafiche'):
        converted,count=convert_tables(blocks)
        st.session_state.blocks=converted
        st.session_state.table_count=count
        st.rerun()
    if 'table_count' in st.session_state:
        st.success(f"Tabelle convertite: {st.session_state.pop('table_count')}")
    h1=sum(b.get('kind')=='heading' and int(b.get('level',0))==1 for b in blocks)
    h2=sum(b.get('kind')=='heading' and int(b.get('level',0))==2 for b in blocks)
    st.info(f'Titoli riconosciuti: {h1} capitoli (H1), {h2} sezioni (H2). L’indice PDF viene generato da questi titoli.')
    if not h1:
        st.warning('Nessun capitolo H1 rilevato: controlla i titoli importati. Senza H1 l’indice dei capitoli non può essere compilato.')
    sections=chapters(blocks)
    left,right=st.columns([1,3])
    with left:
        st.subheader('Capitoli')
        selection=st.radio('Navigazione',range(len(sections)),format_func=lambda i:sections[i][0],label_visibility='collapsed')
        st.metric('Blocchi',len(blocks))
    with right:
        title,start,end=sections[selection]
        st.subheader(title)
        kinds=['paragraph','heading','bullet','number','tree','flow','table']
        for i in range(start,end):
            b=blocks[i]
            with st.expander(f'{i+1} · {b["kind"]} · {b.get("text","")[:65]}',expanded=i==start):
                b['kind']=st.selectbox('Tipo di blocco',kinds,index=kinds.index(b['kind']),key=f'kind{i}')
                if b['kind']=='heading':b['level']=st.selectbox('Livello H1–H6',list(range(1,7)),index=max(0,min(5,b.get('level',1)-1)),key=f'level{i}')
                if b['kind']=='table':
                    value=st.text_area('Righe; colonne separate da |','\n'.join(' | '.join(row) for row in b['items']),key=f'table{i}')
                    b['items']=[[x.strip() for x in line.split('|')] for line in value.splitlines() if line.strip()]
                else:b['text']=st.text_area('Testo',b.get('text',''),key=f'text{i}',height=170 if b['kind'] in ('tree','flow') else 80)
                a,c,d=st.columns(3)
                if a.button('Aggiungi sotto',key=f'add{i}'):
                    blocks.insert(i+1,block('paragraph','Nuovo paragrafo'));st.rerun()
                if c.button('Sposta su',key=f'up{i}',disabled=i==0):
                    blocks[i-1],blocks[i]=blocks[i],blocks[i-1];st.rerun()
                if d.button('Elimina',key=f'delete{i}'):
                    blocks.pop(i);st.rerun()
        st.subheader('Nuovo diagramma ad albero')
        st.caption('Usa 4 spazi per ogni livello. Es.: Argomento, poi quattro spazi e Sottoargomento.')
        tree=st.text_area('Schema testuale',height=130)
        if st.button('Inserisci figura ad albero',disabled=not tree.strip()):
            blocks.insert(end,block('tree',tree));st.rerun()

        st.subheader('Nuovo diagramma di flusso')
        st.caption('Una riga per nodo: START: Inizio, ACTION: Operazione, DECISION: Domanda? | Sì | No, END: Fine. Le etichette dei rami sono descrittive; per percorsi ramificati complessi serve una struttura esplicita.')
        flow=st.text_area('Passaggi del flusso',value='START: Inizio\nACTION: Leggi il testo\nDECISION: Hai capito? | Sì | No\nACTION: Scrivi il riassunto\nEND: Fine',height=160)
        if st.button('Inserisci diagramma di flusso',disabled=not flow.strip()):
            blocks.insert(end,block('flow',flow));st.rerun()
