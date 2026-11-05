"""Detect and convert ASCII/Unicode tree diagrams imported as ordinary paragraphs."""
import re

BRANCH=re.compile(r'^\s*(?:[│| ]{0,20})?(?:├──|└──|├─|└─|\+--|\\--|\|--|[├└]─|[│|])\s*(.+)$')
BULLET=re.compile(r'^\s*[•▪●◦]\s+')
def branch_info(line):
    s=line.rstrip()
    m=BRANCH.match(s)
    if not m:return None
    prefix=s[:m.start(1)]
    label=m.group(1).strip()
    if not label or label in ('│','|','─'):return None
    depth=max(1,prefix.count('│')+prefix.count('|')+prefix.count('    ')+prefix.count('├')+prefix.count('└'))
    return depth,label

def convert_diagrams(blocks):
    """Return (new blocks, count). Merge title + connector + branches into one tree block.
    A standalone │ is never treated as a separate diagram.
    """
    out=[];converted=0;i=0
    while i<len(blocks):
        b=blocks[i];kind=b.get('kind');txt=b.get('text','').strip()
        if kind not in ('paragraph','tree') or not txt:
            out.append(b);i+=1;continue
        if kind=='tree':
            out.append(b);i+=1;continue
        # A title followed by vertical connector(s) and at least two branches.
        title=txt;start=i+1
        if BULLET.match(title) or len(title)>130:
            out.append(b);i+=1;continue
        j=start
        while j<len(blocks) and blocks[j].get('kind')=='paragraph' and blocks[j].get('text','').strip() in ('│','|','┃'):
            j+=1
        children=[]
        while j<len(blocks) and blocks[j].get('kind')=='paragraph':
            value=blocks[j].get('text','').strip()
            info=branch_info(value)
            if info:
                children.append(info);j+=1;continue
            if value in ('│','|','┃'):
                j+=1;continue
            break
        if len(children)>=2:
            new=dict(b);new['kind']='tree'
            new['text']=title+'\n'+'\n'.join('    '*max(1,min(depth,5))+label for depth,label in children)
            out.append(new);converted+=1;i=j;continue
        # Multi-line diagram contained in one paragraph.
        lines=txt.splitlines()
        if len(lines)>=3 and sum(branch_info(x) is not None for x in lines[1:])>=2:
            root=lines[0].strip()
            branches=[branch_info(x) for x in lines[1:]]
            new=dict(b);new['kind']='tree'
            new['text']=root+'\n'+'\n'.join('    '*min(5,d)+label for d,label in branches if label)
            out.append(new);converted+=1;i+=1;continue
        out.append(b);i+=1
    return out,converted
