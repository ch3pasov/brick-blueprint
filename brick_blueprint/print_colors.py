"""Color conversion for vector PDF paint operators; no page rasterization."""
from pathlib import Path
import hashlib
import io
import re

INTENTS={'perceptual':0,'relative':1,'saturation':2,'absolute':3}

def channels(value):
    if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):
        raise ValueError('Print export requires six-digit RGB paint colors')
    return tuple(int(value[i:i+2],16) for i in (1,3,5))

class PrintColors:
    def __init__(self, mode='rgb', *, profile=None, intent='relative'):
        if mode not in ('rgb','gray','cmyk'):raise ValueError('Unknown print color mode')
        if intent not in INTENTS:raise ValueError('Unknown rendering intent')
        if mode!='cmyk' and profile is not None:raise ValueError('An ICC output profile is only used in CMYK mode')
        if mode!='cmyk' and intent!='relative':raise ValueError('Rendering intent applies only to CMYK')
        self.mode=mode;self.icc_bytes=None;self.cache={};self.intent=intent
        self.details={'mode':mode,'input_color_assumption':'sRGB','conversion': 'unchanged RGB' if mode=='rgb' else 'linear-light sRGB luminance encoded with the sRGB transfer curve; uncalibrated DeviceGray'}
        if mode=='cmyk':
            if profile is None:raise ValueError('CMYK export requires an explicit --profile from the print provider or chosen output condition')
            p=Path(profile)
            if not p.is_file() or not 128<=p.stat().st_size<=16*1024*1024:raise ValueError('ICC profile must be a file between 128 bytes and 16 MiB')
            data=p.read_bytes()
            if data[36:40]!=b'acsp' or data[16:20]!=b'CMYK' or data[12:16]!=b'prtr':
                raise ValueError('Expected a CMYK output (printer-class) ICC profile')
            if int.from_bytes(data[:4],'big')!=len(data):raise ValueError('ICC declared size does not match the supplied file')
            try:
                from PIL import Image,ImageCms
            except ImportError as error:
                raise ValueError('CMYK conversion needs Pillow with LittleCMS support; install the optional print extra') from error
            try:
                output=ImageCms.ImageCmsProfile(io.BytesIO(data));source=ImageCms.createProfile('sRGB')
                # ICC blending spaces need both device->PCS and PCS->device support.
                if ImageCms.isIntentSupported(output,INTENTS[intent],ImageCms.Direction.OUTPUT)!=1 or ImageCms.isIntentSupported(output,INTENTS[intent],ImageCms.Direction.INPUT)!=1:
                    raise ValueError('ICC profile must support both conversion directions for the selected intent')
                self.transform=ImageCms.buildTransformFromOpenProfiles(source,output,'RGB','CMYK',renderingIntent=INTENTS[intent])
                self.Image=Image;self.ImageCms=ImageCms;self.icc_bytes=data
                self.details={'mode':'cmyk','input_color_assumption':'sRGB','conversion':'LittleCMS ICC transform; 8-bit channel precision','profile_description':ImageCms.getProfileDescription(output).strip(),'profile_sha256':hashlib.sha256(data).hexdigest(),'profile_bytes':len(data),'profile_class':'output','intent':intent,'black_point_compensation':False,'littlecms_version':ImageCms.core.littlecms_version,'color_space':'ICCBased CMYK; profile embedded in PDF; no PDF/X output intent or certification'}
            except (ImageCms.PyCMSError,OSError) as error:
                raise ValueError('ICC transform could not be built: '+str(error)) from error

    def convert(self,value):
        if value in self.cache:return self.cache[value]
        rgb=channels(value)
        if self.mode=='rgb':result=tuple(v/255 for v in rgb)
        elif self.mode=='gray':
            encoded=[v/255 for v in rgb]
            linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in encoded]
            y=sum(a*b for a,b in zip(linear,(.2126,.7152,.0722)))
            result=(12.92*y if y<=.0031308 else 1.055*y**(1/2.4)-.055,)
        else:
            sample=self.Image.new('RGB',(1,1),rgb)
            converted=self.ImageCms.applyTransform(sample,self.transform).getpixel((0,0))
            result=tuple(v/255 for v in converted)
        self.cache[value]=result;return result

    def operator(self,value,stroke=False):
        numbers=' '.join(format(c,'.8f') for c in self.convert(value))
        if self.mode=='cmyk':return '/CSPrint '+('CS' if stroke else 'cs')+' '+numbers+' '+('SCN' if stroke else 'scn')
        return numbers+' '+(('RG' if stroke else 'rg') if self.mode=='rgb' else ('G' if stroke else 'g'))

    def report(self):
        result={**self.details,'unique_source_colors':len(self.cache)}
        if self.mode=='cmyk':
            result['max_paint_ink_percent']=round(max((sum(c)*100 for c in self.cache.values()),default=0),3)
            result['ink_scope']='Maximum sum of one converted paint color; not a separation/overprint or overlapping-transparency coverage audit.'
        return result
