"""Markdown manuscript import and inline styling."""
import re
from xml.sax.saxutils import escape

def inline_markup(value):
    tokens=re.split(r'(\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|_[^_\n]+_)',str(value))
    result=[]
    for t in tokens:
        if len(t)>4 and t[:2] in ('**','__') and t.endswith(t[:2]):
            result.append('<b>'+escape(t[2:-2])+'</b>')
        elif len(t)>2 and t[:1] in ('*','_') and t.endswith(t[:1]):
            result.append('<i>'+escape(t[1:-1])+'</i>')
        else:result.append(escape(t))
    return ''.join(result).replace('\n','<br/>')

def import_markdown(raw):
    from engine import block
    lines=raw.splitlines();out=[];i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line or line=='---':i+=1;continue
        if line.startswith(chr(96)*3):
            kind=line[3:].strip().lower();i+=1;parts=[]
            while i<len(lines) and not lines[i].strip().startswith(chr(96)*3):
                parts.append(lines[i]);i+=1
            out.append(block('tree' if kind=='tree' else 'flow' if kind in ('flow','flowchart') else 'paragraph','\n'.join(parts)))
            i+=1;continue
        m=re.match(r'^(#{1,6})\s+(.+)$',line)
        if m:out.append(block('heading',m.group(2),len(m.group(1))));i+=1;continue
        if '|' in line and i+1<len(lines) and re.match(r'^\s*\|?[\s:|\-]+\|[\s:|\-]*$',lines[i+1]):
            header=[x.strip() for x in line.strip('|').split('|')];rows=[header];i+=2
            while i<len(lines) and '|' in lines[i]:
                row=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if len(row)!=len(header):break
                rows.append(row);i+=1
            out.append(block('table',items=rows));continue
        m=re.match(r'^[-*+]\s+(.+)$',line)
        if m:out.append(block('bullet',m.group(1)));i+=1;continue
        m=re.match(r'^\d+[.)]\s+(.+)$',line)
        if m:out.append(block('number',m.group(1)));i+=1;continue
        parts=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#{1,6}\s|[-*+]\s|\d+[.)]\s|---$)',lines[i].strip()) and not lines[i].strip().startswith(chr(96)*3):
            parts.append(lines[i].strip());i+=1
        out.append(block('paragraph','\n'.join(parts)))
    return out

def _is_md_separator(text):
    text=str(text or '').strip().strip('|').strip()
    cells=[cell.strip() for cell in text.split('|')]
    return len(cells)>=2 and all(
        len(cell.strip(':'))>=3 and set(cell.strip(':'))=={'-'}
        for cell in cells
    )

def normalize_markup_blocks(blocks):
    """Recognize Word and Google Docs Markdown headings, lists and tables."""
    normalized=[]
    for b in blocks:
        if b.get('kind')!='paragraph':
            normalized.append(b)
            continue
        value=b.get('text','').strip()
        if not value:continue
        lines=value.splitlines()
        chapter=re.fullmatch(r'\\s*(?:\\*\\*)?\\s*(?:#{1,6}\\s*)?(?:capitolo|chapter)\\s+(\\d+|[IVXLCDM]+)\\s*(?:[.:–—-]\\s*)?(.+?)\\s*(?:\\*\\*)?\\s*',value,re.IGNORECASE)
        if chapter and len(lines)==1:
            title=re.sub(r'^#{1,6}\\s*','',value.strip('* ').strip())
            normalized.append({'kind':'heading','text':title,'level':1,'items':[]})
            continue
        h=re.fullmatch(r'\\s*(#{1,6})\\s+(.+?)\\s*',value)
        if h and len(lines)==1:
            normalized.append({'kind':'heading','text':h.group(2),'level':len(h.group(1)),'items':[]})
            continue
        if len(lines)>1 and any(re.match(r'^\\s*(?:#{1,6}\\s+|[-*+]\\s+|\\d+[.)]\\s+)',line) for line in lines):
            normalized.extend(import_markdown(value))
        elif len(lines)>1 and any('|' in line for line in lines):
            normalized.extend(import_markdown(value))
        elif re.match(r'^\\s*[-*+]\\s+',value):
            normalized.append({'kind':'bullet','text':re.sub(r'^\\s*[-*+]\\s+','',value),'level':0,'items':[]})
        else:normalized.append(b)
    merged=[];i=0
    while i<len(normalized):
        b=normalized[i]
        if b.get('kind')=='paragraph' and '|' in b.get('text','') and i+1<len(normalized):
            sep=normalized[i+1]
            if sep.get('kind')=='paragraph' and _is_md_separator(sep.get('text','')):
                header=[x.strip() for x in b['text'].strip().strip('|').split('|')]
                rows=[header];j=i+2
                while j<len(normalized) and normalized[j].get('kind')=='paragraph' and '|' in normalized[j].get('text',''):
                    cells=[x.strip() for x in normalized[j]['text'].strip().strip('|').split('|')]
                    if len(cells)!=len(header):break
                    rows.append(cells);j+=1
                if len(rows)>1:
                    merged.append({'kind':'table','text':'','level':0,'items':rows});i=j;continue
        merged.append(b);i+=1
    return merged
