from tensorflow.keras.layers import Dense, Dropout, Flatten, Conv2D, MaxPooling2D
from tensorflow.keras.models import Sequential
from django.core.files.base import ContentFile
from Persona.models import Supervisados
from urllib.request import urlopen
from django.db.models import Q
from datetime import datetime
import cv2, math, os, time
import mediapipe as mp
from .models import *
import numpy as np

class Monitorizar:
    # Tipos de Distracción
    # 1. Reconocer persona
    # 2. Reconocer expresiones
    # 3. Detectar sueño
    # 4. Reconocer objetos
    def __init__(self):
        # atributos generales 

        self.ruta_rostros = 'media\\Perfiles\\img_entrenamiento'
        self.ruta_modelos = 'Monitoreo\\modelos_entrenados\\'
        self.lista_supervisados = []
        self.imagen_evidencia = None
        self.supervisado = None
        self.tipo_distraccion = None
        self.minutos_deteccion = 1
        self.byte = bytes()


        # ------ RECONOCIMIENTO # 1 - Identificador de identidad de las personas
        # cargar el clasificador de detección de rostros pre entrenado de OpenCV
        self.clasificador_haar = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        # cargar el modelo para el reconocimiento facial: El reconocimiento facial se realiza mediante el clasificador de distancia y vecino más cercano
        self.reconocedor_facial = cv2.face.LBPHFaceRecognizer_create()
        self.reconocedor_facial.read(self.ruta_modelos + 'reconocedor_facial.xml')
        # se obtine la lista de personas a reconocer
        self.lista_supervisados = os.listdir(self.ruta_rostros)
        self.persona_identif = None


        # ------ RECONOCIMIENTO # 2 - Reconocer la expresión facial de la persona
        # Construcción de la red neuronal convolucional
        self.modelo_expresiones = Sequential()
        # -- Capa de entrada
        # Capa convolucional 1 con ReLU-activation
        self.modelo_expresiones.add(Conv2D(32, kernel_size = (3, 3), activation='relu', input_shape = (48, 48, 1)))
        # Capa convolucional 2 con ReLU-activation + un max poling
        self.modelo_expresiones.add(Conv2D(64, kernel_size = (3, 3), activation='relu'))
        # MaxPooling2D: Operación de agrupación máxima (2 x 2) para datos espaciales 2D.
        self.modelo_expresiones.add(MaxPooling2D(pool_size = (2, 2)))
        # El abandono o función Dropout() se implementa fácilmente mediante la selección aleatoria de nodos que se abandonarán con una probabilidad dada 
        # (por ejemplo, 25 %) en cada ciclo de actualización de peso
        self.modelo_expresiones.add(Dropout(0.25))
        # -- Capa oculta
        # Capa convolucional 3 con ReLU-activation + un max poling
        self.modelo_expresiones.add(Conv2D(128, kernel_size = (3, 3), activation = 'relu'))
        # MaxPooling2D: Operación de agrupación máxima (2 x 2) para datos espaciales 2D.
        self.modelo_expresiones.add(MaxPooling2D(pool_size = (2, 2)))
        # Capa convolucional 4 con ReLU-activation + un max poling
        self.modelo_expresiones.add(Conv2D(128, kernel_size = (3, 3), activation = 'relu'))
        # MaxPooling2D: Operación de agrupación máxima (2 x 2) para datos espaciales 2D.
        self.modelo_expresiones.add(MaxPooling2D(pool_size = (2, 2)))
        # El abandono o función Dropout() se implementa fácilmente mediante la selección aleatoria de nodos que se abandonarán con una probabilidad dada 
        # (por ejemplo, 25 %) en cada ciclo de actualización de peso
        self.modelo_expresiones.add(Dropout(0.25))
        # -- Capa de salida
        self.modelo_expresiones.add(Flatten())
        # Primera capa Densa completamente conectada con ReLU-activation.
        self.modelo_expresiones.add(Dense(1024, activation = 'relu'))
        # El abandono o función Dropout() se implementa fácilmente mediante la selección aleatoria de nodos que se abandonarán con una probabilidad dada 
        # (por ejemplo, 50 %) en cada ciclo de actualización de peso
        self.modelo_expresiones.add(Dropout(0.5))
        # Última capa Densa totalmente conectada con activación de softmax
        self.modelo_expresiones.add(Dense(7, activation = 'softmax'))
        # diccionario que asigna a cada etiqueta una expresión facial (orden alfabético)
        self.expresion_facial = {0: 'Enfadado', 1: 'Asqueado', 2: 'Temeroso', 3: 'Feliz', 4: 'Neutral', 5: 'Triste', 6: 'Sorprendido'}
        # cargar el modelo entrenado para reconocer expresiones faciales
        self.modelo_expresiones.load_weights(self.ruta_modelos + 'model.h5')
        

        # ------ RECONOCIMIENTO # 3 - Detectar presencia de sueño en la persona
        # variables de conteo de parpadeos
        self.parpadeando = False
        self.cant_parpadeos = 0
        self.tiempo = 0
        self.inicio_sueno = 0
        self.fin_sueno = 0
        self.micro_sueno = 0
        self.duracion_sueno = 0
        # configuración del dibujo
        self.mpDibujo = mp.solutions.drawing_utils
        self.ConfDibu = self.mpDibujo.DrawingSpec(thickness = 1, circle_radius = 1) 
        # objeto donde se almacena la malla facial
        self.mpMallaFacial = mp.solutions.face_mesh
        self.MallaFacial = self.mpMallaFacial.FaceMesh(max_num_faces = 6)
        self.puntos_faciales = []
        


    # se registra el historial de la monitorización
    def guardarHistorial(self, observacion):
        historial = Historial()
        historial.fecha_hora = datetime.now()
        historial.observacion = observacion
        historial.supervisado = self.supervisado[0]
        historial.tipo_distraccion = self.tipo_distraccion
        frame_jpg = cv2.imencode('.png', cv2.resize(self.imagen_evidencia,(450, 450),interpolation = cv2.INTER_CUBIC))
        file = ContentFile(frame_jpg[1])
        historial.imagen_evidencia.save('persona_id_' + str(self.supervisado[0].persona.id) + '_fecha_hora_' + str(historial.fecha_hora) + '.png', file, save = True)
        historial.save()

    def reconocer(self):
        try:
            cap = cv2.VideoCapture(0)
            while True:
                ret, video = cap.read()
                if not ret:
                    break

                # /*/*/*/*/*/*/**/*//*/*/* OJO, MIRAR EL CÓDIGO DE CORREGIR COLOR "frameRGB" PARA EL PROYECTO

                # Lee una imagen de un búfer en la memoria
                gray = cv2.cvtColor(video, cv2.COLOR_BGR2GRAY)
                # correción de color
                frameRGB = cv2.cvtColor(video, cv2.COLOR_BGR2RGB)
                # se crean copias del video
                video_gris = gray.copy()
                video_color = video.copy()


                # ------ RECONOCIMIENTO # 1 - Identificador de identidad de las personas, se encuentra la cascada haar para dibujar la caja delimitadora alrededor de la cara
                rostros = self.clasificador_haar.detectMultiScale(gray, scaleFactor = 1.3, minNeighbors = 5)
                # recorriendo rostros 
                for (x, y, w, h) in rostros:
                    rostro = video_gris[y:y + h, x:x + w]
                    self.imagen_evidencia = video_color[y:y + h, x:x + w]
                    rostro = cv2.resize(rostro, (150, 150), interpolation = cv2.INTER_CUBIC)
                    # reconocimiento facial, se verifica si es una persona registrada
                    self.persona_identif = self.reconocedor_facial.predict(rostro)
                    cv2.putText(video,'{}'.format(self.persona_identif), (x, y - 5), 1, 1.3, (255, 255, 0), 1, cv2.LINE_AA)
                    if self.persona_identif[1] < 70:
                        # Si es una persona registrada, se procede a realizar los otros tipos de reconocimiento
                        self.supervisado = Supervisados.objects.filter(persona_id = self.lista_supervisados[self.persona_identif[0]]).select_related('persona')
                        if(len(self.supervisado)):
                            cv2.putText(video,'{}'.format(self.supervisado[0].persona.nombres), (x, y - 25), 2, 1.1, (0, 255, 0), 1, cv2.LINE_AA)
                            cv2.rectangle(video, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            cv2.rectangle(video, (x, y-50), (x + w, y + h + 10), (255, 0, 0), 2)


                            # ------ RECONOCIMIENTO # 2 - Reconocer la expresión facial de la persona
                            cropped_img = np.expand_dims(np.expand_dims(cv2.resize(rostro, (48, 48)), -1), 0)
                            prediction = self.modelo_expresiones.predict(cropped_img)
                            maxindex = int(np.argmax(prediction))
                            cv2.putText(video, self.expresion_facial[maxindex], (x + 20, y-60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                            # SE REGISTRA UN HISTORIAL DEL CAMBIO DE EXPRESIONES FACIALES DEL SUPERVISADO, CONSIDERAR SI SOLO SE REGISTRA LOS ESTADOS DE ANIMO MAS PREOCUPANTES: ENFADO, TRIZTE Y TEMEROSO


                            # ------ RECONOCIMIENTO # 3 - Detectar presencia de sueño en la persona
                            # observamos los resultados
                            resultados = self.MallaFacial.process(frameRGB)
                            # Se limpiea la lista para los nuevos puntos faciales
                            self.puntos_faciales.clear()
                            if resultados.multi_face_landmarks: # existe un rostro
                                for r in resultados.multi_face_landmarks:

                                    self.mpDibujo.draw_landmarks(video, r, self.mpMallaFacial.FACEMESH_CONTOURS, self.ConfDibu, self.ConfDibu)
                                    # extraer los puntos del rostro detectado
                                    for id, puntos in enumerate(r.landmark):
                                        al, an, c = video.shape
                                        x, y = int(puntos.x * an), int(puntos.y * al)
                                        self.puntos_faciales.append([id, x, y])
                                        if len(self.puntos_faciales) == 468:
                                            # ojo derecho
                                            x1, y1 = self.puntos_faciales[145][1:]
                                            x2, y2 = self.puntos_faciales[159][1:]
                                            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                                            longitud1 = math.hypot(x2 - x1, y2 -y1)
                                            # ojo izquierdo
                                            x3, y3 = self.puntos_faciales[374][1:]
                                            x4, y4 = self.puntos_faciales[386][1:]
                                            cx2, cy2 = (x3 + x4) // 2, (y3 + y4) // 2
                                            longitud2 = math.hypot(x4 - x3, y4 -y3)
                                            cv2.putText(video, f'Parpadeos: {int(self.cant_parpadeos)}', (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                                            cv2.putText(video, f'Micro sueno: {int(self.micro_sueno)}', (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                                            cv2.putText(video, f'Duracion: {int(self.duracion_sueno)}', (30, 140), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
                                            # contar parpadeos
                                            if longitud1 <= 14 and longitud2 <= 14 and self.parpadeando == False: 
                                                self.cant_parpadeos += 1
                                                self.parpadeando = True
                                                self.inicio_sueno = time.time()
                                            elif longitud1 > 14 and longitud2 > 14 and self.parpadeando == True: 
                                                self.parpadeando = False
                                                self.fin_sueno = time.time()
                                            # temporizador
                                            self.tiempo = round(self.fin_sueno - self.inicio_sueno, 0)
                                            # contador micro sueño
                                            if self.tiempo >= 3:
                                                self.micro_sueno += 1
                                                self.duracion_sueno = self.tiempo
                                                self.inicio_sueno = 0
                                                self.fin_sueno = 0

                            # ------ RECONOCIMIENTO # 4 - Reconocer objetos        


                    else:
                        # SE REGISTRA UN HISTORIAL CON EL TIPO DE DISTRACCION = 1. Reconocer persona, con observación: persona desconocida
                        cv2.putText(video,'Desconocido',(x, y - 20), 2, 0.8,(0, 0, 255),1,cv2.LINE_AA)
                        cv2.rectangle(video, (x, y),(x + w, y + h),(0, 0, 255), 2)

                cv2.imshow('Video', cv2.resize(video,(1500, 760), interpolation = cv2.INTER_CUBIC))
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            cv2.destroyAllWindows()
        except Exception as e: 
            print(str(e))