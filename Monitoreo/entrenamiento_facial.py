from Persona.models import Personas
from urllib.request import urlopen
from .models import *
import numpy as np
import imutils
import cv2
import os

class EntrenamiFacial:
    def __init__(self):
        self.inicializar()
    
    def inicializar(self):
        self.supervisado = None
        self.supervisado_id = 0
        self.tutor_id = 0
        self.ruta_rostros = 'media\\Perfiles\\img_entrenamiento'
        self.ruta_modelos = 'Monitoreo\\modelos_entrenados\\'
        self.etiquetas = []
        self.datos_rostros = []
        self.cont_etiquetas = 0
        self.clasificador_haar = cv2.CascadeClassifier('Monitoreo\\modelos_entrenados\\haarcascade_frontalface_default.xml')
        self.imagenes_capturar = 400
        self.cont_imagenes = 0
        self.fin_entrenamiento = False

    def entrenar(self):
        try:
            self.supervisado = Supervisados.objects.get(pk = self.supervisado_id)
            os.makedirs(self.ruta_rostros + '\\' + str(self.supervisado.pk) + '_' + self.supervisado.persona.nombres, exist_ok = True)
            # se crean las 200 imágenes de la persona supervisada para después entrenar el modelo de reconocimiento facial
            cap = cv2.VideoCapture(0)
            cap.set(3, 1280) # ancho video
            cap.set(6, 720) # alto video
            while True:
                ret, self.video = cap.read()
                if not ret:
                    break

                self.video =  imutils.resize(self.video, width = 640)
                gray = cv2.cvtColor(self.video, cv2.COLOR_BGR2GRAY)
                auxFrame = self.video.copy()
                rostros = self.clasificador_haar.detectMultiScale(gray, 1.3, 5)
                cv2.putText(self.video, 'Capturando {0} fotos de 400'.format((self.cont_imagenes + 1)), (20, 28), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                for (x, y, w, h) in rostros:
                    cv2.rectangle(self.video, (x, y),(x + w, y + h),(0, 255, 0), 2)
                    rostro = auxFrame[y:y + h, x:x + w]
                    rostro = cv2.resize(rostro,(150, 150),interpolation = cv2.INTER_CUBIC)
                    cv2.imwrite(self.ruta_rostros + '\\' + str(self.supervisado.pk) + '_' + self.supervisado.persona.nombres + '/rotro_{}.png'.format(self.cont_imagenes), rostro)
                    self.cont_imagenes += 1
                cv2.imshow('Video', self.video)
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
            self.fin_entrenamiento = True
            return 'entrenado'
        except Camaras.DoesNotExist or Supervisados.DoesNotExist:
            return 'error'
        except Exception as e: 
            return 'error'
