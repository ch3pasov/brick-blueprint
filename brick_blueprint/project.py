"""Perspective / orthographic projection and instruction-style materials, independent of output."""
from pathlib import Path
import hashlib
import math
from .ldraw import Library, decode_library_text, load_model, material, sha
from .instruction_features import scene_with_features
from .detail_rule import filter_lines
from .style import load_style
from .camera import PerspectiveCamera
from .camera_presets import resolve_camera

def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]
def unit(a):
    n=math.sqrt(dot(a,a))
    if n<1e-12:raise ValueError('Degenerate camera direction')
    return tuple(v/n for v in a)

def project(model, library, destination, *, width=600, height=450, azimuth=None, elevation=None,
            line_width=.32, glass_opacity=None, background=(212,237,252), style_path=None, material_profile=None,
            detail_filter=True, scale=None, viewport=None, projection=None,
            field_of_view=None, camera_distance=None, camera_target=None, near_clip=None,
            camera_roll=None, principal_point=None, camera_preset=None):
    """PDF points; perspective scale is points/LDU at the camera target plane."""
    settings, preset_receipt = resolve_camera(camera_preset, projection=projection,
        azimuth=azimuth, elevation=elevation, field_of_view=field_of_view)
    projection, azimuth, elevation, field_of_view = (settings[k] for k in
        ('projection', 'azimuth', 'elevation', 'field_of_view'))
    if projection not in ("perspective", "orthographic"):raise ValueError("Unknown projection")
    if projection == "orthographic" and any(v is not None for v in (field_of_view,camera_distance,camera_target,near_clip,camera_roll,principal_point)):
        raise ValueError("FOV, distance, target, roll, principal point and near clip require perspective projection")
    if camera_roll is not None and (not math.isfinite(camera_roll) or abs(camera_roll)>180):
        raise ValueError('Camera roll must be finite and between -180 and 180 degrees')
    values=(width,height,azimuth,elevation,line_width,*background)
    if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite render option')
    if not (64<=width<=1000 and 64<=height<=1000):raise ValueError('Page dimensions must be 64..1000 points')
    if not -89<=elevation<=89:raise ValueError('Elevation must be -89..89 degrees')
    if not 0<line_width<=10:raise ValueError('Line width must be >0 and <=10 points')
    if glass_opacity is not None and (not math.isfinite(glass_opacity) or not 0<glass_opacity<=1):raise ValueError('Glass opacity must be >0 and <=1')
    if len(background)!=3 or any(not 0<=v<=255 for v in background):raise ValueError('Background RGB must be 0..255')
    if scale is not None and (not math.isfinite(scale) or scale<=0):raise ValueError('Scale must be positive')
    parts,model_structure=load_model(model)
    style=load_style(style_path,material_profile)
    az,el=math.radians(azimuth),math.radians(elevation)
    direction=unit((math.sin(az)*math.cos(el),-math.sin(el),math.cos(az)*math.cos(el)))
    right=unit(cross((0,-1,0),direction));up=unit(cross(direction,right))
    if camera_roll is not None:
        roll=math.radians(camera_roll);old_right=right;down=tuple(-v for v in up)
        right=tuple(math.cos(roll)*r+math.sin(roll)*d for r,d in zip(old_right,down))
        up=tuple(math.sin(roll)*r-math.cos(roll)*d for r,d in zip(old_right,down))
    with Library(library) as lib:
        triangles,lines,features,line_features=scene_with_features(lib,parts)
        if not triangles:raise ValueError('No surface geometry')
        def projected(v):return dot(v,right),-dot(v,up),dot(v,direction)
        vs=[projected(v) for tri,*_ in triangles for v in tri]
        lo=[min(v[k] for v in vs) for k in range(2)];hi=[max(v[k] for v in vs) for k in range(2)]
        margin=24.
        vx,vy,vw,vh=viewport or (margin,margin,width-2*margin,height-2*margin)
        if vw<=0 or vh<=0 or vx<0 or vy<0 or vx+vw>width or vy+vh>height:raise ValueError('Invalid drawing viewport')
        camera=None
        camera_receipt={'projection':'orthographic','depth_encoding':'linear world depth',
                        'scale_definition':'uniform points per LDU'}
        if projection == 'perspective':
            geometry=[v for tri,*_ in triangles for v in tri]+[v for pts,*_ in lines for v in pts[:2]]
            camera=PerspectiveCamera(geometry,right,tuple(-v for v in up),direction,width,height,(vx,vy,vw,vh),
                                     field_of_view=field_of_view,camera_distance=camera_distance,
                                     camera_target=camera_target,scale=scale,near_clip=.1 if near_clip is None else near_clip,
                                     principal_point=principal_point)
            pt_scale=camera.points_per_ldu;camera_receipt=camera.receipt()
            if camera_roll is not None:camera_receipt['roll_degrees']=camera_roll
            if principal_point is not None:camera_receipt['principal_point_source']='explicit cropped-frame calibration; not assumed to be image centre'
            def screen(v):
                x,y,z=camera.project(v);return 4*x,4*y,z
        else:
            available=(vw,vh)
            pt_scale=scale or min(available[k]/max(hi[k]-lo[k],1) for k in range(2))
            if any((hi[k]-lo[k])*pt_scale>available[k]+1e-8 for k in range(2)):raise ValueError('Model does not fit at requested scale')
            # Legacy vector kernel: input XY /2 -> SVG units; SVG /2 -> PDF points.
            factor=4*pt_scale;ox=4*(vx+vw/2)-(hi[0]+lo[0])*factor/2;oy=4*(vy+vh/2)-(hi[1]+lo[1])*factor/2
            def screen(v):
                x,y,z=projected(v);return ox+x*factor,oy+y*factor,z
        detail={'enabled':False}
        if detail_filter:
            lines,line_features,detail=filter_lines(parts,triangles,lines,line_features,direction,camera.detail_scale_bound if camera else pt_scale,lambda c:material(lib,c)[1],
                                                          camera_position=camera.eye if camera else None)
        flat=[];seen=set()
        for index,(tri,c,owner,step) in enumerate(triangles):
            rgb,alpha=material(lib,c);n=cross(sub(tri[1],tri[0]),sub(tri[2],tri[0]))
            if dot(n,n)<1e-20:continue
            n=unit(n)
            view=sub(camera.eye,tri[0]) if camera else direction
            if dot(n,view)<0:n=tuple(-v for v in n)
            rgb=style.face(c,rgb,n,features[index],alpha=alpha)
            if features[index] in ('stud_cylinder_wall','sideways_stud_cylinder_wall'):alpha=1.
            elif alpha<1 and glass_opacity is not None:alpha=glass_opacity
            key=(owner,c,tuple(sorted(tri)))
            if key in seen:continue
            seen.add(key);flat.append((owner,*rgb,alpha,*(v for p in tri for v in screen(p))))
        segments=[];conditional=0
        for index,(pts,c,is_edge,owner,step) in enumerate(lines):
            if camera:
                if len(pts)==4:
                    if not camera.conditional_visible(pts):continue
                    conditional+=1
                q=tuple(screen(v) for v in pts[:2])
            else:q=tuple(screen(v) for v in pts)
            if len(q)==4:
                a,b,u,v=q;s1=(b[0]-a[0])*(u[1]-a[1])-(b[1]-a[1])*(u[0]-a[0]);s2=(b[0]-a[0])*(v[1]-a[1])-(b[1]-a[1])*(v[0]-a[0])
                if s1*s2<-1e-9:continue
                conditional+=1
            nominal,alpha=material(lib,c);explicit=line_features[index]['explicit']
            # Shared V26 ink contrast, including subdued lines inside glass.
            value=185 if style.light_ink(nominal) and not explicit else 32
            rgb=(value,)*3
            if alpha<1:rgb=tuple(.4*value+.6*e for e in material(lib,c,edge=True)[0])
            segments.append((owner,*rgb,*(v for p in q[:2] for v in p)))
        destination=Path(destination)
        with destination.open('w') as out:
            out.write(f'{width*4} {height*4} '+ ' '.join(map(str,background))+f' {len(flat)}\n')
            for row in flat:out.write(' '.join(format(v,'.12g') for v in row)+'\n')
            out.write(f'{len(segments)} {line_width*4}\n')
            for row in segments:out.write(' '.join(format(v,'.12g') for v in row)+'\n')
        dependencies=[]
        for name in sorted(lib.visited):
            data=lib.read(name);headers=decode_library_text(data).splitlines()
            dependencies.append({'file':name,'sha256':hashlib.sha256(data).hexdigest(),
                                 'authors':[s[2:] for s in headers if s.startswith('0 Author:')],
                                 'licenses':[s[11:] for s in headers if s.startswith('0 !LICENSE ')]})
        return {'model_sha256':sha(model),'model_structure':model_structure,'parts':len(parts),'triangles':len(flat),'lines':len(segments),
                'conditional_edges_shown':conditional,'scene_sha256':sha(destination),
                'page_points':[width,height],'points_per_ldu':pt_scale,'line_width_points':line_width,
                'camera':{**camera_receipt,'azimuth':azimuth,'elevation':elevation,'direction':direction,
                          **({'preset':preset_receipt} if preset_receipt else {})},
                'glass_opacity_override':glass_opacity,'detail_filter':detail,
                'dependencies':dependencies,'library_config':lib.config_receipt,
                'style_sha256':style.sha256,'materials':style.receipt()}
