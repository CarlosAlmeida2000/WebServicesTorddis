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
        self.imagenes_capturar = 200
        self.cont_imagenes = 0
        self.fin_entrenamiento = False
        self.estado = ''
        self.byte = bytes()

    def entrenar(self):
        try:
            self.supervisado = Supervisados.objects.get(pk = self.supervisado_id)
            os.makedirs(self.ruta_rostros + '\\' + str(self.supervisado.pk), exist_ok = True)

            # ***** Código para usar la CAMARA del dispositivo
            camara_ip = Camaras.objects.get(tutor_id = self.tutor_id).direccion_ruta
            stream = urlopen('http://'+ camara_ip +':81/stream')
            # ***** fin

            # ***** Código para usar CAMARA WEB
            # cap = cv2.VideoCapture(0)
            # ***** fin
            
            while self.cont_imagenes < self.imagenes_capturar:

                # ***** Código para usar la CAMARA del dispositivo
                self.byte += stream.read(4096)
                alto_imagen = self.byte.find(b'\xff\xd8')
                ancho_imagen = self.byte.find(b'\xff\xd9')
                if alto_imagen != -1 and ancho_imagen != -1:
                    imagen = self.byte[alto_imagen:ancho_imagen + 2]
                    self.byte = self.byte[ancho_imagen + 2:]
                    if imagen:
                # ***** fin

                # ***** Código para usar CAMARA WEB
                # ret, imagen = cap.read()
                # if not ret:
                #     break
                # ***** fin

                        # ***** Código para usar la CAMARA del dispositivo
                        self.video = cv2.imdecode(np.fromstring(imagen, dtype = np.uint8), cv2.IMREAD_COLOR)
                        self.video = cv2.resize(self.video, (1490, 760), interpolation = cv2.INTER_CUBIC)
                        # ***** fin

                # ***** Código para usar CAMARA WEB
                # self.video = cv2.resize(imagen, (1490, 760), interpolation = cv2.INTER_CUBIC)
                # ***** fin


                        gray = cv2.cvtColor(self.video, cv2.COLOR_BGR2GRAY)
                        auxFrame = self.video.copy()
                        rostros = self.clasificador_haar.detectMultiScale(gray, 1.3, 5)
                        self.estado = '{0} fotos de {1}'.format((self.cont_imagenes + 1), self.imagenes_capturar)
                        cv2.putText(self.video, self.estado, 
                        (20, 28), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                        for (x, y, w, h) in rostros:
                            cv2.rectangle(self.video, (x, y),(x + w, y + h),(0, 255, 0), 2)
                            rostro = cv2.resize(auxFrame[y:y + h, x:x + w],(150, 150),interpolation = cv2.INTER_CUBIC)
                            cv2.imwrite(self.ruta_rostros + '\\' + str(self.supervisado.pk) + '/rotro_{}.png'
                            .format(self.cont_imagenes), rostro)
                            self.cont_imagenes += 1
                        cv2.imshow('Video', self.video)
                        k =  cv2.waitKey(1)
                        if k == 27:
                            break

            cv2.destroyAllWindows()
            self.fin_entrenamiento = True
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
            return 'entrenado'
        except Camaras.DoesNotExist or Supervisados.DoesNotExist:
            return 'camara no encontrada'
        except Exception as e: 
            return 'error'