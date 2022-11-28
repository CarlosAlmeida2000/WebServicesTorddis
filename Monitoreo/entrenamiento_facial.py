import os
from Persona.models import Personas
import cv2
import imutils
import numpy as np
from urllib.request import urlopen
from .models import *

class EntrenamientoFacial:
    def __init__(self, persona_id, camara_id):
        self.supervisado = None
        self.camara_id = camara_id
        self.persona_id = persona_id
        self.ruta_rostros = 'media\\Perfiles\\img_entrenamiento'
        self.ruta_modelos = 'Monitoreo\\modelos_entrenados\\'
        self.etiquetas = []
        self.datos_rostros = []
        self.cont_etiquetas = 0
        self.clasificador_haar = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.imagenes_capturar = 200
        self.cont_imagenes = 0
        self.byte = bytes()
    
    def entrenar(self):
        try:
            self.supervisado = Supervisados.objects.get(persona_id = self.persona_id)
            os.makedirs(self.ruta_rostros + '\\' + str(self.supervisado.pk) + '_' + self.supervisado.persona.nombres, exist_ok = True)
            # se crean las 200 imágenes de la persona supervisada para después entrenar el modelo de reconocimiento facial
            cap = cv2.VideoCapture(0)
            while True:
                ret, video = cap.read()
                if not ret:
                    break

                video =  imutils.resize(video, width = 640)
                gray = cv2.cvtColor(video, cv2.COLOR_BGR2GRAY)
                auxFrame = video.copy()
                rostros = self.clasificador_haar.detectMultiScale(gray, 1.3, 5)
                for (x, y, w, h) in rostros:
                    cv2.rectangle(video, (x, y),(x + w, y + h),(0, 255, 0), 2)
                    rostro = auxFrame[y:y + h, x:x + w]
                    rostro = cv2.resize(rostro,(150, 150),interpolation = cv2.INTER_CUBIC)
                    cv2.imwrite(self.ruta_rostros + '\\' + str(self.supervisado.pk) + '_' + self.supervisado.persona.nombres + '/rotro_{}.png'.format(self.cont_imagenes), rostro)
                    self.cont_imagenes += 1
                cv2.imshow('Video', cv2.resize(video,(1500, 760), interpolation = cv2.INTER_CUBIC))
                k =  cv2.waitKey(1)
                if k == 27 or self.cont_imagenes >= self.imagenes_capturar:
                    cv2.destroyAllWindows()
                    break
            # entrenamiento del modelo con todas las imágenes
            lista_personas = os.listdir(self.ruta_rostros)
            for persona in lista_personas:
                directorio_persona = self.ruta_rostros + '\\' + persona
                for archivo_foto in os.listdir(directorio_persona):
                    self.etiquetas.append(self.cont_etiquetas)
                    self.datos_rostros.append(cv2.imread(directorio_persona+'\\' + str(archivo_foto), 0))
                self.cont_etiquetas += 1
            reconocedor_facial = cv2.face.LBPHFaceRecognizer_create()
            reconocedor_facial.train(self.datos_rostros, np.array(self.etiquetas)) 
            reconocedor_facial.write(self.ruta_modelos + 'reconocedor_facial.xml')
            print("Modelo de reconocimiento facial almacenado...")
            return 'entrenado'
        except Camaras.DoesNotExist:
            return 'La cámara no está registrada'
        except Supervisados.DoesNotExist:
            return 'No existe el supervisado'
        except Exception as e: 
            return 'error'
