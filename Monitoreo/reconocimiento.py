from tensorflow.keras.layers import Dense, Dropout, Flatten, Conv2D, MaxPooling2D
from tensorflow.keras.models import Sequential
from django.core.files.base import ContentFile
from Persona.models import Supervisados
from urllib.request import urlopen
from django.db.models import Q
from Monitoreo.models import *
from datetime import datetime
import cv2, math, os, time
import mediapipe as mp
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
        self.supervisado = '1_pedro'
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
        self.expresion_facial = {0: 'Enfadado', 1: 'Disgustado', 2: 'Temeroso', 3: 'Feliz', 4: 'Neutral', 5: 'Triste', 6: 'Sorprendido'}
        # cargar el modelo entrenado para reconocer expresiones faciales
        self.modelo_expresiones.load_weights(self.ruta_modelos + 'model.h5')
        

        # ------ RECONOCIMIENTO # 3 - Detectar presencia de sueño en la persona
        # variables de conteo de parpadeos
        self.parpadeando = False
        self.cant_parpadeos = 0
        self.tiempo_dormido = 0
        self.tiempo_permitido = 7
        self.inicio_sueno = 0
        self.fin_sueno = 0
        self.duracion_sueno = 0
        # configuración del dibujo
        self.mpDibujo = mp.solutions.drawing_utils
        self.ConfDibu = self.mpDibujo.DrawingSpec(thickness = 1, circle_radius = 1) 
        # objeto donde se almacena la malla facial
        self.mpMallaFacial = mp.solutions.face_mesh
        self.MallaFacial = self.mpMallaFacial.FaceMesh(max_num_faces = 4)
        self.puntos_faciales = []


        # Reloj para el registro del historial
        self.inicio_tiempo = 0
        self.tiempo_registro = 0
        self.registro_inicial = True
        self.tiempo_deteccion = 60


    # se registra el historial de la monitorización
    def guardarHistorial(self, observacion, tipo_distraccion_id):
        from .models import Historial, TiposDistraccion
        self.historial = Historial()
        self.historial.fecha_hora = datetime.now()
        self.historial.observacion = observacion
        self.historial.supervisado = Supervisados.objects.get(pk = self.supervisado.split('_')[0])
        self.historial.tipo_distraccion = TiposDistraccion.objects.get(pk = tipo_distraccion_id)
        frame_jpg = cv2.imencode('.png', cv2.resize(self.imagen_evidencia,(450, 450),interpolation = cv2.INTER_CUBIC))
        file = ContentFile(frame_jpg[1]) 
        self.historial.imagen_evidencia.save('dis_' + str(tipo_distraccion_id) + '_id_' + str(self.historial.supervisado.persona.id) + '_' + str(self.historial.fecha_hora) + '.png', file, save = True)
        self.historial.save()

    def reconocer(self):
        try:
            cap = cv2.VideoCapture(0)
            # CUANDO SE PRUEBE CON EL DISPOSITIVO, AJUSTAR ABAJO LAS LONGITUDES CUANDO SE CIERRA Y ABRE UN OJO, 14 ES CUANDO SE USA LA RESOLUCION DE 1280 X 720
            cap.set(3, 1280) # ancho ventana
            cap.set(6, 720) # alto ventana
            self.inicio_tiempo = time.time()
            while True:
                ret, video = cap.read()
                if not ret:
                    break
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
                    # reconocimiento facial, se verifica si es una persona registrada
                    self.persona_identif = self.reconocedor_facial.predict(cv2.resize(rostro, (150, 150), interpolation = cv2.INTER_CUBIC))
                    cv2.putText(video,'{}'.format(self.persona_identif), (x, y - 5), 1, 1.3, (255, 255, 0), 1, cv2.LINE_AA)
                    if self.persona_identif[1] < 70:
                        # Si es una persona registrada, se procede a realizar los otros tipos de reconocimiento
                        self.supervisado = self.lista_supervisados[self.persona_identif[0]]
                        cv2.putText(video,'{}'.format(self.supervisado.split('_')[1]), (x, y - 25), 2, 1.1, (0, 255, 0), 1, cv2.LINE_AA)
                        cv2.rectangle(video, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.rectangle(video, (x, y - 50), (x + w, y + h + 10), (255, 0, 0), 2)
                        # ------ RECONOCIMIENTO # 2 - Reconocer la expresión facial de la persona
                        cropped_img = np.expand_dims(np.expand_dims(cv2.resize(rostro, (48, 48), interpolation = cv2.INTER_CUBIC), -1), 0)
                        prediction = self.modelo_expresiones.predict(cropped_img)
                        expresion = self.expresion_facial[int(np.argmax(prediction))]
                        cv2.putText(video, expresion, (x + 20, y - 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                        ultimo_historial = (Historial.objects.filter(Q(supervisado_id = self.supervisado.split('_')[0]) & Q(observacion = expresion)).order_by('-fecha_hora'))
                        if(len(ultimo_historial)):
                            fecha_historial = datetime.strptime(ultimo_historial[0].fecha_hora.strftime('%Y-%m-%d %H:%M:%S.%f') , '%Y-%m-%d %H:%M:%S.%f')
                            if ((datetime.now() - fecha_historial).seconds > self.tiempo_deteccion):
                                self.guardarHistorial(expresion, 2)
                        else:
                            self.guardarHistorial(expresion, 2)
                        # ------ RECONOCIMIENTO # 3 - Detectar presencia de sueño en la persona
                        # observamos los resultados
                        resultados = self.MallaFacial.process(frameRGB)
                        # Se limpia la lista para los nuevos puntos faciales
                        self.puntos_faciales.clear()
                        if resultados.multi_face_landmarks: # existe un rostro
                            for rostro_detec in resultados.multi_face_landmarks:
                                self.mpDibujo.draw_landmarks(video, rostro_detec, self.mpMallaFacial.FACEMESH_CONTOURS, self.ConfDibu, self.ConfDibu)
                                # extraer los puntos del rostro detectado
                                for id, puntos in enumerate(rostro_detec.landmark):
                                    al, an, c = video.shape
                                    punto_x, punto_y = int(puntos.x * an), int(puntos.y * al)
                                    self.puntos_faciales.append([id, punto_x, punto_y])
                                    if len(self.puntos_faciales) == 468:
                                        # ojo derecho
                                        x1, y1 = self.puntos_faciales[145][1:]
                                        x2, y2 = self.puntos_faciales[159][1:]
                                        longitud1 = math.hypot(x2 - x1, y2 -y1)
                                        # ojo izquierdo
                                        x3, y3 = self.puntos_faciales[374][1:]
                                        x4, y4 = self.puntos_faciales[386][1:]
                                        longitud2 = math.hypot(x4 - x3, y4 -y3)
                                        cv2.putText(video, f'Parpadeos: {int(self.cant_parpadeos)}', (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                                        # contar parpadeos
                                        if longitud1 <= 14 and longitud2 <= 14 and self.parpadeando == False: 
                                            # Cerró los ojos
                                            self.cant_parpadeos += 1
                                            self.parpadeando = True
                                            self.inicio_sueno = time.time()
                                            # Justo el momento que cerró los ojos se captura la imagen
                                            self.imagen_evidencia = video_color[y:y + h, x:x + w]
                                        elif longitud1 > 14 and longitud2 > 14 and self.parpadeando == True: 
                                            # Abrió los ojos
                                            self.parpadeando = False
                                            self.fin_sueno = time.time()
                                        # temporizador
                                        self.tiempo_dormido = round(self.fin_sueno - self.inicio_sueno, 0)
                                        # contador micro sueño
                                        if self.tiempo_dormido >= self.tiempo_permitido:
                                            self.guardarHistorial('Presencia de sueño, parpadeo {0} veces'.format(self.cant_parpadeos), 3)
                                            self.inicio_sueno = 0
                                            self.fin_sueno = 0
                                            self.cant_parpadeos = 0

                                    # ------ RECONOCIMIENTO # 4 - Reconocer objetos        

                    else:
                        cv2.putText(video,'Desconocido',(x, y - 20), 2, 0.8,(0, 0, 255),1,cv2.LINE_AA)
                        cv2.rectangle(video, (x, y),(x + w, y + h),(0, 0, 255), 2)
                        self.tiempo_registro = round(time.time() - self.inicio_tiempo, 0)
                        if (self.tiempo_registro >= self.tiempo_deteccion or self.registro_inicial):
                            # Se captura la imagen de la persona desconocida
                            self.imagen_evidencia = video_color[y:y + h, x:x + w]
                            self.inicio_tiempo = time.time()
                            self.registro_inicial = False
                            self.guardarHistorial('Se identificó una persona desconocida', 1)
                            
                cv2.imshow('Video', video)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            cv2.destroyAllWindows()
        except Exception as e: 
            print(str(e))