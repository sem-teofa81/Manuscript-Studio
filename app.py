import json,re
import streamlit as st
from engine import import_docx,import_google_doc,chapters,export_pdf,export_docx,block,BULLETS
st.set_page_config(page_title='KDP Manuscript Studio',layout='wide')
st.title('KDP Manuscript Studio')
if 'blocks' not in st.session_state: st.session_state.blocks=[]
if 'opts' not in st.session_state: st.session_state.opts=dict(width=6.,height=9.,margin=.7,font_size=9.5,bullet='Pallino',chapter_breaks=True,title='Manoscritto')
with st.sidebar:
    st.header('Importazione')
    file=st.file_uploader('DOCX esportato da Google Docs',type='docx')
    if file and st.button('Importa DOCX'):
        st.session_state.blocks=import_docx(file.getvalue());st.rerun()
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
    o['bullet']=st.selectbox('Simbolo elenchi',list(BULLETS),index=list(BULLETS).index(o['bullet']))
    for k,label,minimum,maximum,step in [('width','Larghezza pollici',4.,9.,.25),('height','Altezza pollici',6.,12.,.25),('margin','Margini pollici',.3,1.2,.05),('font_size','Dimensione testo pt',8.,14.,.25)]:
        o[k]=st.number_input(label,minimum,maximum,float(o[k]),step)
    o['chapter_breaks']=st.checkbox('Capitoli su nuova pagina',value=o['chapter_breaks'])
    if st.session_state.blocks:
        st.download_button('Esporta PDF',export_pdf(st.session_state.blocks,o),'manoscritto_kdp.pdf','application/pdf',use_container_width=True)
        st.download_button('Esporta DOCX',export_docx(st.session_state.blocks,o),'manoscritto_editabile.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document',use_container_width=True)
blocks=st.session_state.blocks
if not blocks:
    st.info('Importa un documento oppure crea un manoscritto nuovo.')
    if st.button('Nuovo manoscritto'):
        st.session_state.blocks=[block('heading','Capitolo 1',1),block('paragraph','Scrivi qui.')];st.rerun()
else:
    sections=chapters(blocks)
    left,right=st.columns([1,3])
    with left:
        st.subheader('Capitoli')
        selection=st.radio('Navigazione',range(len(sections)),format_func=lambda i:sections[i][0],label_visibility='collapsed')
        st.metric('Blocchi',len(blocks))
    with right:
        title,start,end=sections[selection]
        st.subheader(title)
        kinds=['paragraph','heading','bullet','number','tree','table']
        for i in range(start,end):
            b=blocks[i]
            with st.expander(f'{i+1} · {b["kind"]} · {b.get("text","")[:65]}',expanded=i==start):
                b['kind']=st.selectbox('Tipo di blocco',kinds,index=kinds.index(b['kind']),key=f'kind{i}')
                if b['kind']=='heading':b['level']=st.selectbox('Livello H1–H6',list(range(1,7)),index=max(0,min(5,b.get('level',1)-1)),key=f'level{i}')
                if b['kind']=='table':
                    value=st.text_area('Righe; colonne separate da |','\n'.join(' | '.join(row) for row in b['items']),key=f'table{i}')
                    b['items']=[[x.strip() for x in line.split('|')] for line in value.splitlines() if line.strip()]
                else:b['text']=st.text_area('Testo',b.get('text',''),key=f'text{i}',height=140 if b['kind']=='tree' else 80)
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
