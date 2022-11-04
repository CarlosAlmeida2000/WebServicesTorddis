import os
import cv2
import imutils
import numpy as np
from urllib.request import urlopen
from .models import *

class EntrenamientoFacial:
    def __init__(self, persona_id, camara_id):
        self.persona_id = persona_id
        self.camara_id = camara_id
        self.rostros_entrena = 'media\\Perfiles\\Entrenados'
        self.ruta_modelos = 'Monitoreo\\Modelo_entrenado\\'
        self.etiquetas = []
        self.datos_rostros = []
        self.cont_etiquetas = 0
        self.clasificador_haar = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.imagenes_capturar = 200
        self.cont_imagenes = 0
        self.byte = bytes()
    
    def entrenar(self):
        try:
            os.makedirs(self.rostros_entrena + '\\' + str(self.persona_id), exist_ok = True)
            # se crean las 200 imágenes de la persona supervisada para después entrenar el modelo de reconocimiento facial
            stream = urlopen('http://'+ (Camaras.objects.get(pk = self.camara_id)).direccion_ip +'/stream')
            while True:
                self.byte += stream.read(4096)
                a = self.byte.find(b'\xff\xd8')
                b = self.byte.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    imagen = self.byte[a:b + 2]
                    self.byte = self.byte[b + 2:]
                    if imagen:
                        video = cv2.imdecode(np.fromstring(imagen, dtype = np.uint8), cv2.IMREAD_COLOR)
                        video =  imutils.resize(video, width = 640)
                        gray = cv2.cvtColor(video, cv2.COLOR_BGR2GRAY)
                        auxFrame = video.copy()
                        rostros = self.clasificador_haar.detectMultiScale(gray, 1.3, 5)
                        for (x, y, w, h) in rostros:
                            cv2.rectangle(video, (x, y),(x + w, y + h),(0, 255, 0), 2)
                            rostro = auxFrame[y:y + h, x:x + w]
                            rostro = cv2.resize(rostro,(150, 150),interpolation = cv2.INTER_CUBIC)
                            cv2.imwrite(self.rostros_entrena + '\\' + str(self.persona_id) + '/rotro_{}.png'.format(self.cont_imagenes), rostro)
                            self.cont_imagenes += 1
                        cv2.imshow('Video', cv2.resize(video,(1500, 760), interpolation = cv2.INTER_CUBIC))
                        k =  cv2.waitKey(1)
                        if k == 27 or self.cont_imagenes >= self.imagenes_capturar:
                            cv2.destroyAllWindows()
                            break
            # entrenamiento del modelo con todas las imágenes
            lista_personas = os.listdir(self.rostros_entrena)
            for persona in lista_personas:
                directorio_persona = self.rostros_entrena + '\\' + persona
                for archivo_foto in os.listdir(directorio_persona):
                    self.etiquetas.append(self.cont_etiquetas)
                    self.datos_rostros.append(cv2.imread(directorio_persona+'\\' + str(archivo_foto), 0))
                self.cont_etiquetas += 1
            reconocedor_rostros = cv2.face.LBPHFaceRecognizer_create()
            reconocedor_rostros.train(self.datos_rostros, np.array(self.etiquetas)) 
            reconocedor_rostros.write(self.ruta_modelos + 'modeloLBPHFace.xml')
            print("Modelo de reconocimiento facial almacenado...")
            return 'entrenado'
        except Camaras.DoesNotExist:
            return 'La cámara no está registrada'
        except Exception as e: 
            return 'error'
