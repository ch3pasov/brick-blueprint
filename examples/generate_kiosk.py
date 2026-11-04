"""Recreate the original Little Blue Kiosk sample; no external files or downloads.

This project-created design is not reconstructed from a commercial set.
DAT geometry is supplied separately. Output is a new directory, never replaced.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

I = (1,0,0,0,1,0,0,0,1)
Y90 = (0,0,1,0,1,0,-1,0,0)


def design():
    rows=[]

    def part(step, ref, color, x, y, z, rotation=I, role=''):
        rows.append(dict(id=f'p{len(rows)+1:03}', step=step, part=ref+'.dat',
                         color=color, xyz=[x,y,z], matrix=list(rotation), role=role))

    part(1,'41539',71,0,0,0,role='8 x 8 foundation')
    for z in (50,70):part(1,'2431',71,0,-8,z,role='pavement')
    part(2,'3009',15,0,-24,-50,role='rear sill')
    for x in (-50,50):part(2,'3004',15,x,-24,-20,Y90,'side sill')
    part(2,'3009',1,0,-24,10,role='counter base')
    part(3,'3020',15,0,-32,20,role='counter overhang')
    for z in (10,30):part(3,'2431',15,0,-40,z,role='counter surface')
    part(4,'3010',1,0,-48,-50,role='rear wall')
    for x in (-50,50):
        part(4,'3005',1,x,-48,-50,role='rear corner')
        part(4,'3004',47,x,-48,-20,Y90,'clear side glazing')
        part(4,'3005',1,x,-48,10,role='front post')
    part(5,'3009',1,0,-72,-50,role='rear wall')
    for x in (-50,50):
        part(5,'3004',47,x,-72,-20,Y90,'clear side glazing')
        part(5,'3005',1,x,-72,10,role='front post')
    for x in (-50,50):part(6,'3004',15,x,-96,-20,Y90,'side header')
    for z in (-50,10):part(6,'3009',15,0,-96,z,role='front or rear header')
    part(7,'3035',1,0,-104,-20,role='roof')
    for index,x in enumerate(range(-70,71,20)):
        part(7,'3623',15 if index%2==0 else 1,x,-112,10,Y90,'striped canopy')
    for x in (-40,40):part(7,'2431',1,x,-112,-50,role='roof trim')
    for x in (-50,50):
        part(8,'3062b',14,x,-24,50,role='bollard')
        part(8,'98138',4,x,-32,50,role='bollard cap')
    return rows


def line(row, *, xyz=None):
    values=[row['color'],*(row['xyz'] if xyz is None else xyz),*row['matrix']]
    return '1 '+' '.join(map(str,values))+' '+row['part']


def write(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    rows=design()
    header=['0 Little Blue Kiosk — original Brick Blueprint sample',
            '0 Created for this project with AI assistance; not a LEGO set reconstruction.',
            '0 Axes: +X right, +Z counter/front, -Y up; 20 LDU stud pitch.',
            '0 Library DAT geometry and material definitions are supplied separately.',
            '0 Digital illustration sample; physical clutch and stability untested.']
    flat=header.copy()
    for step in range(1,9):
        if step>1:flat.append('0 STEP')
        for row in rows:
            if row['step']==step:flat.extend(['0 !SOURCE_ID '+row['id'],line(row)])
    flat_text='\n'.join(flat)+'\n'
    (output/'kiosk.ldr').write_text(flat_text,encoding='utf-8')
    mpd=['0 FILE kiosk.ldr',*header]
    for step in range(1,8):
        if step>1:mpd.append('0 STEP')
        mpd.append('1 16 0 0 0 1 0 0 0 1 0 0 0 1 stage-'+str(step)+'.ldr')
    mpd.append('0 STEP')
    for x in (-50,50):mpd.append(f'1 16 {x} 0 50 1 0 0 0 1 0 0 0 1 bollard.ldr')
    for step in range(1,8):
        mpd.append('0 FILE stage-'+str(step)+'.ldr')
        mpd.extend(line(row) for row in rows if row['step']==step)
    mpd.append('0 FILE bollard.ldr')
    mpd.extend([line(rows[-2],xyz=[0,-24,0]),line(rows[-1],xyz=[0,-32,0]),'0 NOFILE'])
    (output/'kiosk.mpd').write_text('\n'.join(mpd)+'\n',encoding='utf-8')
    bom=Counter((r['part'],r['color']) for r in rows)
    wrappers=output/'parts';wrappers.mkdir()
    tray=[]
    for (ref,color),quantity in sorted(bom.items()):
        name=ref.removesuffix('.dat')+'-'+str(color)+'.ldr'
        single=dict(part=ref,color=color,xyz=[0,0,0],matrix=list(I))
        (wrappers/name).write_text('0 Original kiosk BOM specimen; external DAT required.\n'+line(single)+'\n')
        tray.append(dict(model='parts/'+name,quantity=quantity))
    (output/'bom-tray.json').write_text(json.dumps(dict(items=tray),indent=2)+'\n')
    # A fixed four-part control for presentation studies, deliberately quantity-1
    # so the no-count edition can use the same geometry without hiding counts.
    selected=[('3009',1),('3004',15),('3004',47),('3062b',14)]
    (output/'presentation-tray.json').write_text(json.dumps(dict(items=[
        dict(model=f'parts/{ref}-{color}.ldr',quantity=1) for ref,color in selected]),indent=2)+'\n')
    canopy=['0 Original kiosk canopy subset; unchanged placements from design stage 7.',
            '0 Display module only; not an official set or physical certification.']
    canopy.extend(line(row) for row in rows if row['step']==7)
    (output/'canopy.ldr').write_text('\n'.join(canopy)+'\n')
    receipt=dict(name='Little Blue Kiosk',parts=len(rows),steps=8,
                 design_origin='Created from stud-grid coordinates for Brick Blueprint on 2026-10-26 with AI assistance. No commercial set instructions or model were used.',
                 axes=dict(right='+X',front='+Z',up='-Y',stud_pitch_ldu=20),
                 geometry_source='External LDraw library; DAT geometry is not included.',
                 color_scope='Nominal LDraw colors; physical color availability was not catalog-verified.',
                 validation_scope='A digital illustration model, not a physically built or certified set.',
                 files={name:hashlib.sha256((output/name).read_bytes()).hexdigest()
                        for name in ('kiosk.ldr','kiosk.mpd')},
                 bom=[dict(part=p,color=c,quantity=n) for (p,c),n in sorted(bom.items())],
                 placements=rows)
    (output/'design.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    result=write(args.output)
    print(json.dumps(dict(parts=result['parts'],steps=result['steps'],files=result['files']),indent=2))


if __name__=='__main__':main()
