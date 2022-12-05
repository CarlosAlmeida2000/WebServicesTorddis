from tensorflow.keras.layers import Dense, Dropout, Flatten, Conv2D, MaxPooling2D
from tensorflow.keras.models import Sequential
from django.core.files.base import ContentFile
from Persona.models import Supervisados
from keras.models import load_model
from urllib.request import urlopen
from django.db.models import Q
from Monitoreo.models import *
from datetime import datetime
import cv2, math, os, time
import mediapipe as mp
import numpy as np

class Monitorizar:
    
    def __init__(self, tutor_id):
        # Atributos generales 
        self.ruta_rostros = 'media\\Perfiles\\img_entrenamiento'
        self.ruta_modelos = 'Monitoreo\\modelos_entrenados\\'
        self.lista_supervisados = []
        self.expresiones_recono = {}
        self.imagen_evidencia = None
        self.supervisado = ''
        self.tutor_id = tutor_id
        self.byte = bytes()
        # --- Reloj para el registro de un historial
        self.reg_ini_expresion = True
        # tiempo de registro de historial en segundos
        self.tiempo_registro = 30
        # tiempo en el que aparece una persona desconocida
        self.reloj_personas = 0
        # tiempo en el que cambia una expresion facial
        self.reloj_expresiones = 0
        # --- ID de los tipos de distraccion
        # 1. Reconocer persona
        self.dis_pers_id = 1
        # 2. Reconocer expresiones
        self.dis_expre_id = 2
        # 3. Detectar sueño
        self.dis_suen_id = 3
        # 4. Reconocer objetos
        self.dis_obj_id = 4


        # ------ RECONOCIMIENTO # 1 - Identificador de identidad de las personas
        # Cargar el clasificador de detección de rostros pre entrenado de OpenCV
        self.clasificador_haar = cv2.CascadeClassifier('Monitoreo\\modelos_entrenados\\haarcascade_frontalface_default.xml')
        # Cargar el modelo para el reconocimiento facial: El reconocimiento facial se realiza mediante el clasificador de distancia y vecino más cercano
        self.reconocedor_facial = cv2.face.LBPHFaceRecognizer_create()
        self.reconocedor_facial.read(self.ruta_modelos + 'reconocedor_facial.xml')
        # Se obtine la lista de personas a reconocer
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
        # Diccionario que asigna a cada etiqueta una expresión facial (orden alfabético)
        self.expresion_facial = {0: 'Enfadado', 1: 'Disgustado', 2: 'Temeroso', 3: 'Feliz', 4: 'Neutral', 5: 'Triste', 6: 'Sorprendido'}
        # Cargar el modelo entrenado para reconocer expresiones faciales
        self.modelo_expresiones.load_weights(self.ruta_modelos + 'model.h5')
        

        # ------ RECONOCIMIENTO # 3 - Detectar presencia de sueño en la persona
        # Variables de conteo de parpadeos
        self.parpadeando = False
        self.cant_parpadeos = 0
        self.tiempo_dormido = 0
        self.sueno_permitido = 15
        self.inicio_sueno = 0
        # Configuración del dibujo
        self.mp_dibujo = mp.solutions.drawing_utils
        self.conf_dibujo = self.mp_dibujo.DrawingSpec(thickness = 1, circle_radius = 1) 
        # Objeto donde se almacena la malla facial
        self.mp_malla_fac = mp.solutions.face_mesh
        self.malla_facial = self.mp_malla_fac.FaceMesh(max_num_faces = 4)
        self.puntos_faciales = []


        # ------ RECONOCIMIENTO # 4 - Reconocer objetos                
        # Cargar el modelo
        self.modelo_objetos = load_model(self.ruta_modelos + 'keras_model.h5')
        # Crear el array de la forma adecuada para alimentar el modelo keras con las imágenes de 224 x 244 pixeles
        self.data_entrena_objet = np.ndarray(shape = (1, 224, 224, 3), dtype = np.float32)
        # Cargar las clases de objetos
        self.labels = list()
        file_labels = open(self.ruta_modelos + 'labels.txt', 'r')
        for i in file_labels: 
            self.labels.append(i.split()[1])


    # se registra un historial de la monitorización
    def guardarHistorial(self, observacion, tipo_distraccion_id):
        try:
            if self.supervisado != '':
                from .models import Historial, TiposDistraccion
                self.historial = Historial()
                self.historial.fecha_hora = datetime.now()
                self.historial.observacion = observacion
                self.historial.supervisado = Supervisados.objects.get(pk = self.supervisado.split('_')[0])
                self.historial.tipo_distraccion = TiposDistraccion.objects.get(pk = tipo_distraccion_id)
                foto_450 = cv2.resize(self.imagen_evidencia, (450, 450), interpolation = cv2.INTER_CUBIC)
                frame_jpg = cv2.imencode('.png', foto_450)
                file = ContentFile(frame_jpg[1]) 
                self.historial.imagen_evidencia.save('dis_' + str(tipo_distraccion_id) + '_id_' + str(self.historial.supervisado.persona.id) + '_' + str(self.historial.fecha_hora) + '.png', file, save = True)
                self.historial.save()
        except Exception as e:
            pass
    
    def convertir_min_seg(self, segundos):
        horas = int(segundos / 60 / 60)
        segundos -= horas * 60 * 60
        minutos = int(segundos / 60)
        segundos -= minutos * 60
        return f"{minutos}:{int(segundos)}"

    def obtener_rostros(self, imagen):
        return self.clasificador_haar.detectMultiScale(cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY), scaleFactor = 1.3, minNeighbors = 5)

    def reconocer(self):
        try:
            cap = cv2.VideoCapture(0)
            # CUANDO SE PRUEBE CON EL DISPOSITIVO, AJUSTAR ABAJO LAS LONGITUDES CUANDO SE CIERRA Y ABRE UN OJO, 14 ES CUANDO SE USA LA RESOLUCION DE 1280 X 720
            cap.set(3, 1280) # ancho ventana
            cap.set(6, 720) # alto ventana
            while True:
                ret, video = cap.read()
                if not ret:
                    break
                # Convierte el video en escala de grises para reconocimiento de identididad y de expresiones facial
                gray = cv2.cvtColor(video, cv2.COLOR_BGR2GRAY)
                # Correción de color para la malla facial que reconoce la presencia de sueño y el reconocimiento de objetos
                frameRGB = cv2.cvtColor(video, cv2.COLOR_BGR2RGB)
                # Copia del video a color para caputurar la imagen que se guardará en el historial
                video_color = video.copy()
                # Se obtienen todos los rostros del video, se encuentra la cascada haar para dibujar la caja delimitadora alrededor de la cara
                rostros = self.obtener_rostros(video)
                # Recorriendo cada rostro
                for (x, y, w, h) in rostros:
                    rostro = gray[y:y + h, x:x + w]


                    # ------ RECONOCIMIENTO # 1 - Identificador de identidad de las personas, se realiza el reconocimiento facial para verificar si es una persona registrada
                    rostro_150 = cv2.resize(rostro, (150, 150), interpolation = cv2.INTER_CUBIC)
                    self.persona_identif = self.reconocedor_facial.predict(rostro_150)
                    if self.persona_identif[1] < 70:
                        # Si es una persona registrada, se procede a realizar los otros tipos de reconocimiento
                        self.supervisado = self.lista_supervisados[self.persona_identif[0]]
                        cv2.putText(video,'{}'.format(self.supervisado.split('_')[1]), (x, y - 25), 2, 1.1, (0, 255, 0), 1, cv2.LINE_AA)
                        cv2.rectangle(video, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.rectangle(video, (x, y - 50), (x + w, y + h + 10), (255, 0, 0), 2)
                    else:
                        if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_pers_id))) and self.supervisado != '':
                            if self.reloj_personas == 0:
                                self.reloj_personas = time.time()
                            cv2.putText(video,'Desconocido',(x, y - 20), 2, 0.8,(0, 0, 255),1,cv2.LINE_AA)
                            cv2.rectangle(video, (x, y),(x + w, y + h),(0, 0, 255), 2)
                            # Se captura la imagen de la persona desconocida
                            self.imagen_evidencia = video_color[y:y + h, x:x + w]
                            if (round(time.time() - self.reloj_personas, 0) >= self.tiempo_registro):
                                self.reloj_personas = 0
                                if(len(self.obtener_rostros(self.imagen_evidencia))):
                                    self.guardarHistorial('Se identificó una persona desconocida', self.dis_pers_id)


                    # ------ RECONOCIMIENTO # 2 - Reconocer la expresión facial de la persona
                    if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_expre_id))) and self.supervisado != '':
                        if self.reloj_expresiones == 0:
                            self.reloj_expresiones = time.time()
                        rostro_48 = cv2.resize(rostro, (48, 48), interpolation = cv2.INTER_CUBIC)
                        self.imagen_evidencia = video_color[y:y + h, x:x + w]
                        cropped_img = np.expand_dims(np.expand_dims(rostro_48, -1), 0)
                        prediction = self.modelo_expresiones.predict(cropped_img)
                        expresion = self.expresion_facial[int(np.argmax(prediction))]
                        supervisado_id = self.supervisado.split('_')[0]
                        # Mejorar precisión del reconocimiento de expresiones, después de estar analizando durante 15 segundos se escoge la expresión con mayor manifestación
                        contador_expresion = 1
                        if self.expresiones_recono.get(supervisado_id, -1) != -1:
                            if self.expresiones_recono.get(supervisado_id, -1).get(expresion, -1) != -1:
                                contador_expresion = self.expresiones_recono.get(supervisado_id, -1).get(expresion, -1)
                                contador_expresion += 1
                                self.expresiones_recono[supervisado_id][expresion] = contador_expresion
                            else:
                                self.expresiones_recono.get(supervisado_id, -1).update({expresion: 1})
                        else:
                            self.expresiones_recono = {supervisado_id: {expresion: 1}}
                        emociones = self.expresiones_recono.get(supervisado_id, -1)
                        expresion = max(emociones, key=emociones.get)
                        cv2.putText(video, expresion, (x + 20, y - 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                        if (round(time.time() - self.reloj_expresiones, 0) >= (self.tiempo_registro - 15) or self.reg_ini_expresion):
                            ultimo_historial = (Historial.objects.filter(Q(supervisado_id = supervisado_id) & Q(tipo_distraccion_id = self.dis_expre_id)).order_by('-fecha_hora'))[0]
                            # Solo se registra ún historial si la expresión facial reconocida es diferente a la última registrada
                            if(ultimo_historial.observacion != expresion):
                                self.reloj_expresiones = 0
                                self.reg_ini_expresion = False
                                self.expresiones_recono = {}
                                if(len(self.obtener_rostros(self.imagen_evidencia))):
                                    self.guardarHistorial(expresion, self.dis_expre_id)
                            else:
                                self.reloj_expresiones = 0
                                self.reg_ini_expresion = False
                                self.expresiones_recono = {}


                    # ------ RECONOCIMIENTO # 3 - Detectar presencia de sueño en la persona
                    if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_suen_id))):
                        # Observamos los resultados
                        resultados = self.malla_facial.process(frameRGB)
                        # Se limpia la lista para los nuevos puntos faciales
                        self.puntos_faciales.clear()
                        if resultados.multi_face_landmarks: # existe un rostro
                            for rostro_detec in resultados.multi_face_landmarks:
                                self.mp_dibujo.draw_landmarks(video, rostro_detec, self.mp_malla_fac.FACEMESH_CONTOURS, self.conf_dibujo, self.conf_dibujo)
                                # Extraer los puntos del rostro detectado
                                for id, puntos in enumerate(rostro_detec.landmark):
                                    al, an, c = video.shape
                                    punto_x, punto_y = int(puntos.x * an), int(puntos.y * al)
                                    self.puntos_faciales.append([id, punto_x, punto_y])
                                    if len(self.puntos_faciales) == 468:
                                        # Ojo derecho
                                        x1, y1 = self.puntos_faciales[145][1:]
                                        x2, y2 = self.puntos_faciales[159][1:]
                                        longitud1 = math.hypot(x2 - x1, y2 -y1)
                                        # Ojo izquierdo
                                        x3, y3 = self.puntos_faciales[374][1:]
                                        x4, y4 = self.puntos_faciales[386][1:]
                                        longitud2 = math.hypot(x4 - x3, y4 -y3)
                                        cv2.putText(video, f'Parpadeos: {int(self.cant_parpadeos)}', (30, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                                        # Contar parpadeos
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
                                            # Temporizador
                                            self.tiempo_dormido = round(time.time() - self.inicio_sueno, 0)
                                            if self.tiempo_dormido >= self.sueno_permitido:
                                                self.inicio_sueno = 0
                                                self.cant_parpadeos = 0
                                                if(len(self.obtener_rostros(self.imagen_evidencia))):
                                                    self.guardarHistorial('Presencia de sueño, durmió un tiempo de {0} / minutos:segundos'.format(self.convertir_min_seg(self.tiempo_dormido)), self.dis_suen_id)
                                                


                    # ------ RECONOCIMIENTO # 4 - Reconocer objetos                
                    if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_obj_id))):
                        frame = cv2.flip(video, 1)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        imagen_objetos = cv2.resize(frame, (224, 224), fx=0, fy=0, interpolation = cv2.INTER_AREA)
                        # convertir la imagen en un array de numpy
                        image_array = np.asarray(imagen_objetos)
                        # normalizar la imagen
                        self.data_entrena_objet[0] = (image_array.astype(np.float32) / 127.0) - 1
                        # realizar reconocimiento de objetos
                        prediction = self.modelo_objetos.predict(self.data_entrena_objet)
                        for i in range(len(prediction[0])):
                            # Solo mostrar objetos que tengan una precisión a partir del 40 %
                            if (prediction[0][i] >= 0.40):
                                objeto = PermisosObjetos.objects.filter(Q(tutor_id = self.tutor_id) & Q(objeto_id = (i + 1)))
                                if len(objeto):
                                    cv2.putText(video, str(self.labels[i]) + ' - CON PERMISO - prob: ' + str(prediction[0][i]), (20, 40 + (i * 20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                                else:
                                    self.imagen_evidencia = video_color
                                    self.guardarHistorial('Se identificó el uso del objeto {0} sin autorización'.format(self.labels[i]), self.dis_obj_id)
                                    cv2.putText(video, str(self.labels[i]) + ' - SIN PERMISO - prob: ' + str(prediction[0][i]), (20, 40 + (i * 20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

                            
                cv2.imshow('Video', video)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            cv2.destroyAllWindows()
        except Exception as e: 
            print(str(e))
            pass