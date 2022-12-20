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
        self.byte = bytes()

    def entrenar(self):
        try:
            self.supervisado = Supervisados.objects.get(pk = self.supervisado_id)
            os.makedirs(self.ruta_rostros + '\\' + str(self.supervisado.pk), exist_ok = True)
            # se crean las 400 imágenes de la persona supervisada para después entrenar el modelo de reconocimiento facial
            camara_ip = Camaras.objects.get(tutor_id = self.tutor_id).direccion_ruta
            stream = urlopen('http://'+ camara_ip +':81/stream')
            while True:
                self.byte += stream.read(4096)
                a = self.byte.find(b'\xff\xd8')
                b = self.byte.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    imagen = self.byte[a:b + 2]
                    self.byte = self.byte[b + 2:]
                    if imagen:
                        self.video = cv2.imdecode(np.fromstring(imagen, dtype = np.uint8), cv2.IMREAD_COLOR)
                        self.video = cv2.resize(self.video, (1490, 760), interpolation = cv2.INTER_CUBIC)
                        gray = cv2.cvtColor(self.video, cv2.COLOR_BGR2GRAY)
                        auxFrame = self.video.copy()
                        rostros = self.clasificador_haar.detectMultiScale(gray, 1.3, 5)
                        cv2.putText(self.video, 'Capturando {0} fotos de 400'.format((self.cont_imagenes + 1)), (20, 28), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                        for (x, y, w, h) in rostros:
                            cv2.rectangle(self.video, (x, y),(x + w, y + h),(0, 255, 0), 2)
                            rostro = auxFrame[y:y + h, x:x + w]
                            rostro = cv2.resize(rostro,(150, 150),interpolation = cv2.INTER_CUBIC)
                            cv2.imwrite(self.ruta_rostros + '\\' + str(self.supervisado.pk) + '/rotro_{}.png'.format(self.cont_imagenes), rostro)
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
                    self.datos_rostros.append(cv2.imread(directorio_persona + '\\' + str(archivo_foto), 0))
                self.cont_etiquetas += 1
            reconocedor_facial = cv2.face.LBPHFaceRecognizer_create()
            reconocedor_facial.train(self.datos_rostros, np.array(self.etiquetas)) 
            reconocedor_facial.write(self.ruta_modelos + 'reconocedor_facial.xml')
            print("Modelo de reconocimiento facial almacenado...")
            self.fin_entrenamiento = True
            return 'entrenado'
        except Camaras.DoesNotExist or Supervisados.DoesNotExist:
            return 'camara no encontrada'
        except Exception as e: 
            return 'error'
