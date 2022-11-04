from django.core.files.base import ContentFile
import base64

class Image:
    
    def __init__(self):
        self.base64 = ''
        self.ruta = ''
        self.nombre_file = ''
    
    def get_file(self):
        try:
            format, img_body = self.base64.split(';base64,')
            extension = format.split('/')[-1]
            file = ContentFile(base64.b64decode(img_body), name = self.nombre_file + '.' + extension)
            return file
        except Exception as e:
            return None
    
    def get_base64(self):
        try:
            encoded_string = 'data:image/PNG;base64,' + str(base64.b64encode(open(str('media/' + str(self.ruta)), 'rb').read()))[2:][:-1]
            return encoded_string
        except Exception as e:
            return None