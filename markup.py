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
    """Recognize headings and remove Markdown fences from imported DOCX."""
    from engine import block
    out=[]
    for b in blocks:
        if b.get('kind')!='paragraph':
            out.append(b);continue
        raw=str(b.get('text','')).strip()
        if not raw:continue
        if raw.startswith(chr(96)*3):
            continue
        chapter=re.fullmatch(r'(?:#{1,6}\s*)?(?:\*\*)?\s*(?:capitolo|chapter)\s+(\d+|[IVXLCDM]+)\s*[:.\-–—]?\s*(.+?)\s*(?:\*\*)?',raw,re.I)
        numbered=re.fullmatch(r'(\d{1,2})\.\s+(.{5,110})',raw)
        subsection=re.fullmatch(r'(\d{1,2}(?:\.\d+){1,3})\s+(.{4,140})',raw)
        md_heading=re.fullmatch(r'(#{1,6})\s+(.+)',raw)
        if chapter:
            out.append(block('heading',raw.strip('* #'),1));continue
        if subsection:
            out.append(block('heading',raw,2 if subsection.group(1).count('.')==1 else 3));continue
        if md_heading:
            out.append(block('heading',md_heading.group(2).strip(),len(md_heading.group(1))));continue
        if numbered and 1<=int(numbered.group(1))<=40 and not numbered.group(2).endswith(('.', ';', '?', '!')):
            out.append(block('heading',raw,1));continue
        if '\n' in raw and any(re.match(r'^\s*(?:#{1,6}\s+|[-*+]\s+)',line) for line in raw.splitlines()):
            out.extend(import_markdown(raw));continue
        out.append(b)
    merged=[];i=0
    while i<len(out):
        b=out[i]
        if b.get('kind')=='paragraph' and '|' in b.get('text','') and i+1<len(out) and out[i+1].get('kind')=='paragraph' and _is_md_separator(out[i+1].get('text','')):
            head=[v.strip() for v in b['text'].strip().strip('|').split('|')]
            rows=[head];j=i+2
            while j<len(out) and out[j].get('kind')=='paragraph' and '|' in out[j].get('text',''):
                cells=[v.strip() for v in out[j]['text'].strip().strip('|').split('|')]
                if len(cells)!=len(head):break
                rows.append(cells);j+=1
            if len(rows)>1:
                merged.append(block('table',items=rows));i=j;continue
        merged.append(b);i+=1
    return merged
