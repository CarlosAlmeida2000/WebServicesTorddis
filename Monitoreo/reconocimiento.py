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
        self.imagen_evidencia = None
        self.supervisado = '1_pedro'
        self.tutor_id = tutor_id
        self.byte = bytes()
        # Reloj para el registro del historial
        self.inicio_tiempo = 0
        self.tiempo_registro = 0
        self.registro_inicial = True
        self.tiempo_deteccion = 60
        # ID de los tipos de distraccion
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
        self.sueno_permitido = 7
        self.inicio_sueno = 0
        self.fin_sueno = 0
        self.duracion_sueno = 0
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
                # Convierte el video en escala de grises para reconocimiento de identididad y de expresiones facial
                gray = cv2.cvtColor(video, cv2.COLOR_BGR2GRAY)
                # Correción de color para la malla facial que reconoce la presencia de sueño y el reconocimiento de objetos
                frameRGB = cv2.cvtColor(video, cv2.COLOR_BGR2RGB)
                # Copia del video a color para caputurar la imagen que se guardará en el historial
                video_color = video.copy()
                # ------ RECONOCIMIENTO # 1 - Identificador de identidad de las personas, se encuentra la cascada haar para dibujar la caja delimitadora alrededor de la cara
                rostros = self.clasificador_haar.detectMultiScale(gray, scaleFactor = 1.3, minNeighbors = 5)
                # Recorriendo rostros 
                for (x, y, w, h) in rostros:
                    rostro = gray[y:y + h, x:x + w]
                    # Reconocimiento facial, se verifica si es una persona registrada
                    rostro_150 = cv2.resize(rostro, (150, 150), interpolation = cv2.INTER_CUBIC)
                    self.persona_identif = self.reconocedor_facial.predict(rostro_150)
                    if self.persona_identif[1] < 70:
                        # Si es una persona registrada, se procede a realizar los otros tipos de reconocimiento
                        self.supervisado = self.lista_supervisados[self.persona_identif[0]]
                        cv2.putText(video,'{}'.format(self.supervisado.split('_')[1]), (x, y - 25), 2, 1.1, (0, 255, 0), 1, cv2.LINE_AA)
                        cv2.rectangle(video, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.rectangle(video, (x, y - 50), (x + w, y + h + 10), (255, 0, 0), 2)
                        # ------ RECONOCIMIENTO # 2 - Reconocer la expresión facial de la persona
                        if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_expre_id))):
                            rostro_48 = cv2.resize(rostro, (48, 48), interpolation = cv2.INTER_CUBIC)
                            self.imagen_evidencia = video_color[y:y + h, x:x + w]
                            cropped_img = np.expand_dims(np.expand_dims(rostro_48, -1), 0)
                            prediction = self.modelo_expresiones.predict(cropped_img)
                            expresion = self.expresion_facial[int(np.argmax(prediction))]
                            cv2.putText(video, expresion, (x + 20, y - 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                            ultimo_historial = (Historial.objects.filter(Q(supervisado_id = self.supervisado.split('_')[0]) & Q(observacion = expresion)).order_by('-fecha_hora'))
                            if(len(ultimo_historial)):
                                fecha_historial = datetime.strptime(ultimo_historial[0].fecha_hora.strftime('%Y-%m-%d %H:%M:%S.%f') , '%Y-%m-%d %H:%M:%S.%f')
                                if ((datetime.now() - fecha_historial).seconds > self.tiempo_deteccion):
                                    self.guardarHistorial(expresion, self.dis_expre_id)
                            else:
                                self.guardarHistorial(expresion, self.dis_expre_id)

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
                                            cv2.putText(video, f'Parpadeos: {int(self.cant_parpadeos)}', (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
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
                                                self.fin_sueno = time.time()
                                            # Temporizador
                                            self.tiempo_dormido = round(self.fin_sueno - self.inicio_sueno, 0)
                                            # Contador micro sueño
                                            if self.tiempo_dormido >= self.sueno_permitido:
                                                self.guardarHistorial('Presencia de sueño, parpadeo {0} veces'.format(self.cant_parpadeos), self.dis_suen_id)
                                                self.inicio_sueno = 0
                                                self.fin_sueno = 0
                                                self.cant_parpadeos = 0

                        # ------ RECONOCIMIENTO # 4 - Reconocer objetos                
                        if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_obj_id))):
                            
                            
                            imagen_objetos = cv2.resize(frameRGB, (224, 224), fx=0, fy=0, interpolation = cv2.INTER_AREA)
                            # convertir la imagen en un array de numpy
                            image_array = np.asarray(imagen_objetos)
                            # normalizar la imagen
                            self.data_entrena_objet[0] = (image_array.astype(np.float32) / 127.0) - 1
                            # realizar reconocimiento de objetos
                            prediction = self.modelo_objetos.predict(self.data_entrena_objet)
                            for i in range(len(prediction[0])):
                                # Solo mostrar objetos que tengan una precisión a partir del 40 %
                                if (prediction[0][i] >= 0.40):
                                    cv2.putText(video, str(self.labels[i]) + ' - prob: ' + str(prediction[0][i]), (20, 40 + (i * 28)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)



                    else:
                        if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_pers_id))):
                            cv2.putText(video,'Desconocido',(x, y - 20), 2, 0.8,(0, 0, 255),1,cv2.LINE_AA)
                            cv2.rectangle(video, (x, y),(x + w, y + h),(0, 0, 255), 2)
                            self.tiempo_registro = round(time.time() - self.inicio_tiempo, 0)
                            if (self.tiempo_registro >= self.tiempo_deteccion or self.registro_inicial):
                                # Se captura la imagen de la persona desconocida
                                self.imagen_evidencia = video_color[y:y + h, x:x + w]
                                self.inicio_tiempo = time.time()
                                self.registro_inicial = False
                                self.guardarHistorial('Se identificó una persona desconocida', self.dis_pers_id)
                            
                cv2.imshow('Video', video)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            cv2.destroyAllWindows()
        except Exception as e: 
            print(str(e))
            pass