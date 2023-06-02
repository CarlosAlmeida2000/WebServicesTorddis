from tensorflow.keras.layers import Dense, Dropout, Flatten, Conv2D, MaxPooling2D
from tensorflow.keras.models import Sequential
from Persona.models import Supervisados
from keras.models import load_model
from urllib.request import urlopen
from django.db.models import Q
from Monitoreo.models import *
import cv2, math, os, time
import mediapipe as mp
import numpy as np

class Distraccion:
    
    def __init__(self):
        self.inicializar()

    def inicializar(self):
        try:
            # Atributos generales 
            self.ruta_rostros = 'media\\Perfiles\\img_entrenamiento'
            self.ruta_modelos = 'Monitoreo\\modelos_entrenados\\'
            self.supervisado = ''
            self.tutor_id = 0
            self.fin_vigilancia = False
            self.byte = bytes()
            self.incremen_ausente = 60
            self.incremen_registro = 30
            self.incremen_sueno_per = 15
            # --- Reloj para el registro de un historial
            # tiempo de registro de historial en segundos
            self.tiempo_registro = self.incremen_registro
            # tiempo de espera en ausencia de un supervisado en segundos
            self.tiempo_espera_sup = self.incremen_ausente
            # tiempo de inicio que aparece una persona desconocida
            self.reloj_desconocido = 0
            # tiempo de inicio que un supervisado se ausenta
            self.reloj_supervisado = 0
            # tiempo de inicio de una expresion facial
            self.reloj_expresiones = 0
            # tiempo de inicio que aparece un objeto
            self.reloj_objetos = 0

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
            self.personas_desconocidas = 0
            self.es_desconocido = False
            self.reconocer_personas = False
            self.tiempo_ausente = 0


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
            self.expresiones_recono = {}
            self.imagenes_expresiones = {}
            self.imagen_expresion = None
        

            # ------ RECONOCIMIENTO # 3 - Detectar presencia de sueño en la persona
            # Variables de reconocimiento de sueño
            self.parpadeando = False
            self.tiempo_dormido = 0
            self.sueno_permitido = self.incremen_sueno_per
            self.inicio_sueno = 0
            self.imagen_dormido = None
            # Configuración del dibujo
            self.mp_dibujo = mp.solutions.drawing_utils
            self.conf_dibujo = self.mp_dibujo.DrawingSpec(thickness = 1, circle_radius = 1) 
            # Objeto donde se almacena la malla facial
            self.mp_malla_fac = mp.solutions.face_mesh
            self.malla_facial = self.mp_malla_fac.FaceMesh(max_num_faces = 4)
            self.puntos_faciales = []
            self.parpadeo = 0


            # ------ RECONOCIMIENTO # 4 - Reconocer objetos                
            # Cargar el modelo
            self.modelo_objetos = load_model(self.ruta_modelos + 'keras_model2.h5')
            # Crear el array de la forma adecuada para alimentar el modelo keras con las imágenes de 224 x 244 pixeles
            self.data_entrena_objet = np.ndarray(shape = (1, 224, 224, 3), dtype = np.float32)
            self.objetos_recono = {}
            self.imagenes_objetos = {}
            # Cargar las clases de objetos
            self.labels_objetos = list()
            for i in open(self.ruta_modelos + 'labels2.txt', 'r', encoding='utf8'): 
                self.labels_objetos.append(i.split()[1])
        except Exception as e:
            pass

    def convertirMinSeg(self, segundos):
        horas = int(segundos / 60 / 60)
        segundos -= horas * 60 * 60
        minutos = int(segundos / 60)
        segundos -= minutos * 60
        return minutos, int(segundos)

    def obtenerRostros(self, imagen):
        return self.clasificador_haar.detectMultiScale(cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY), scaleFactor = 1.3, minNeighbors = 5)
    
    def monitorear(self):
        try:
            # ***** Código para usar la CAMARA del dispositivo
            camara_ip = Camaras.objects.get(tutor_id = self.tutor_id).direccion_ruta
            stream = urlopen('http://'+ camara_ip +':81/stream')
            # ***** fin
            while len(Monitoreo.objects.filter(tutor_id = self.tutor_id)):
                
                self.fin_vigilancia = False

                # ***** Código para usar la CAMARA del dispositivo
                self.byte += stream.read(4096)
                alto_imagen = self.byte.find(b'\xff\xd8')
                ancho_imagen = self.byte.find(b'\xff\xd9')
                if alto_imagen != -1 and ancho_imagen != -1:
                    imagen = self.byte[alto_imagen:ancho_imagen + 2]
                    self.byte = self.byte[ancho_imagen + 2:]
                    # Si se reconoce una imagen
                    if imagen:
                # ***** fin

                # ***** Código para usar CAMARA WEB
                # cap = cv2.VideoCapture(0)
                # while True:
                #     ret, imagen = cap.read()
                #     if not ret:
                #         break
                # ***** fin
                
                        # ***** Código para usar la CAMARA del dispositivo
                        self.video = cv2.imdecode(np.fromstring(imagen, dtype = np.uint8), cv2.IMREAD_COLOR)
                        self.video = cv2.resize(self.video, (1490, 760), interpolation = cv2.INTER_CUBIC)
                        # ***** fin

                    # ***** Código para usar CAMARA WEB
                    # self.video = cv2.resize(imagen, (1490, 760), interpolation = cv2.INTER_CUBIC)
                    # ***** fin

                        # Convierte el video en escala de grises para reconocimiento de identididad y de expresiones facial
                        gray = cv2.cvtColor(self.video, cv2.COLOR_BGR2GRAY)
                        # Correción de color para la malla facial que reconoce la presencia de sueño y el reconocimiento de objetos
                        frameRGB = cv2.cvtColor(self.video, cv2.COLOR_BGR2RGB)
                        # Copia del video a color para caputurar la imagen que se guardará en el historial
                        video_color = self.video.copy()
                        # Se obtienen todos los rostros del video, se encuentra la cascada haar para dibujar la caja delimitadora alrededor de la cara
                        rostros = self.obtenerRostros(self.video)
                        self.reconocer_personas = True if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_pers_id))) else False
                        # Si hay un tiempo de inicio que desapareció el supervisado y este no aparece durante el tiempo de espera configurado, se registra el historial
                        self.tiempo_ausente = round(time.time() - self.reloj_supervisado, 0)
                        if (self.reconocer_personas and self.reloj_supervisado > 0 and (self.tiempo_ausente >= self.tiempo_espera_sup) and self.supervisado != ''):
                            self.tiempo_espera_sup += self.incremen_ausente
                            minutos, segundos = self.convertirMinSeg(self.tiempo_ausente)
                            Supervisados.cambiarEstado(self.supervisado, True)
                            Historial.crear(self.supervisado, 'El niño(a) lleva un tiempo de {0} minutos ausente del área de estudio'.format(minutos), self.dis_pers_id, video_color)
                        # Se reinicia el conteo de personas desconocidas, porque se obtienen nuevos rostros
                        self.personas_desconocidas = 0
                        # Recorriendo cada rostro
                        for (x, y, w, h) in rostros:
                            rostro = gray[y:y + h, x:x + w]


                            # ------ RECONOCIMIENTO # 1 - Identificador de identidad de las personas, se realiza el reconocimiento facial para verificar si es una persona registrada
                            rostro_150 = cv2.resize(rostro, (150, 150), interpolation = cv2.INTER_CUBIC)
                            self.persona_identif = self.reconocedor_facial.predict(rostro_150)
                            if self.persona_identif[1] < 70 and len(self.lista_supervisados):
                                # Si es una persona registrada, se procede a realizar los otros tipos de reconocimiento
                                self.supervisado = self.lista_supervisados[self.persona_identif[0]]
                                self.es_desconocido = False
                                nombre = Supervisados.objects.get(pk = self.supervisado)
                                cv2.putText(self.video,'{}'.format(nombre.persona.nombres), (x, y - 25), 2, 1.1, (0, 255, 0), 1, cv2.LINE_AA)
                                cv2.rectangle(self.video, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            else:
                                if self.reconocer_personas and self.supervisado != '':
                                    if self.reloj_desconocido == 0:
                                        self.reloj_desconocido = time.time()
                                    self.personas_desconocidas += 1
                                    self.es_desconocido = True
                                    cv2.putText(self.video,'Desconocido',(x, y - 20), 2, 0.8,(0, 0, 255),1,cv2.LINE_AA)
                                    cv2.rectangle(self.video, (x, y),(x + w, y + h),(0, 0, 255), 2)
                                    if (round(time.time() - self.reloj_desconocido, 0) >= self.tiempo_registro):
                                        self.reloj_desconocido = 0
                                        img_desconocido = video_color[y:y + h, x:x + w]
                                        if(len(self.obtenerRostros(img_desconocido)) and self.supervisado != ''):
                                            Historial.crear(self.supervisado, 'Se identificó una persona desconocida', self.dis_pers_id, img_desconocido)


                            # ------ RECONOCIMIENTO # 2 - Reconocer la expresión facial de la persona
                            if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_expre_id))) and self.supervisado != '' and not self.es_desconocido:
                                if self.reloj_expresiones == 0:
                                    self.reloj_expresiones = time.time()
                                rostro_48 = cv2.resize(rostro, (48, 48), interpolation = cv2.INTER_CUBIC)
                                self.imagen_expresion = video_color[y:y + h, x:x + w]
                                cropped_img = np.expand_dims(np.expand_dims(rostro_48, -1), 0)
                                prediction = self.modelo_expresiones.predict(cropped_img)
                                expresion = self.expresion_facial[int(np.argmax(prediction))]
                                # Mejorar la precisión del reconocimiento de expresiones, después de estar analizando durante 30 segundos se registra la expresión con mayor manifestación
                                if (round(time.time() - self.reloj_expresiones, 0) == 10.0 or round(time.time() - self.reloj_expresiones, 0) == 20.0): 
                                    self.reloj_expresiones -= 1                    
                                    self.expresiones_recono = {}
                                    self.imagenes_expresiones = {}
                                contador_expresion = 1
                                if self.expresiones_recono.get(self.supervisado, -1) != -1:
                                    if self.expresiones_recono.get(self.supervisado, -1).get(expresion, -1) != -1:
                                        contador_expresion = self.expresiones_recono.get(self.supervisado, -1).get(expresion, -1)
                                        contador_expresion += 1
                                        self.expresiones_recono[self.supervisado][expresion] = contador_expresion
                                        self.imagenes_expresiones[self.supervisado][expresion] = self.imagen_expresion
                                    else:
                                        self.expresiones_recono.get(self.supervisado, -1).update({expresion: 1})
                                        self.imagenes_expresiones.get(self.supervisado, -1).update({expresion: self.imagen_expresion})
                                else:
                                    self.expresiones_recono = {self.supervisado: {expresion: 1}}
                                    self.imagenes_expresiones = {self.supervisado: {expresion: self.imagen_expresion}}
                                emociones = self.expresiones_recono.get(self.supervisado, -1)
                                expresion = max(emociones, key = emociones.get)
                                cv2.putText(self.video, expresion, (x + 20, y - 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                                # Se verifica si ya cumple con el tiempo estimado para proceder el registro del historial
                                if (round(time.time() - (self.reloj_expresiones + 2), 0) >= (self.tiempo_registro)):
                                    ultimo_historial = (Historial.objects.filter(Q(supervisado_id = self.supervisado) & Q(tipo_distraccion_id = self.dis_expre_id)).order_by('-fecha_hora'))
                                    # Solo se registra ún historial si la expresión facial reconocida es diferente a la última registrada
                                    if(len(ultimo_historial)):
                                        if(ultimo_historial[0].observacion != expresion):
                                            self.reloj_expresiones = 0
                                            self.expresiones_recono = {}
                                            foto_expresion = self.imagenes_expresiones.get(self.supervisado, -1).get(expresion, -1)
                                            if(len(self.obtenerRostros(foto_expresion)) and self.supervisado != ''):
                                                Historial.crear(self.supervisado, expresion, self.dis_expre_id, foto_expresion)
                                            self.reloj_expresiones = 0
                                            self.expresiones_recono = {}
                                    else:
                                        self.reloj_expresiones = 0
                                        self.expresiones_recono = {}
                                        foto_expresion = self.imagenes_expresiones.get(self.supervisado, -1).get(expresion, -1)
                                        if(len(self.obtenerRostros(foto_expresion)) and self.supervisado != ''):
                                            Historial.crear(self.supervisado, expresion, self.dis_expre_id, foto_expresion)


                            # ------ RECONOCIMIENTO # 3 - Detectar presencia de sueño en la persona
                            if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_suen_id))):
                                # Observamos los resultados
                                resultados = self.malla_facial.process(frameRGB)
                                # Se limpia la lista para los nuevos puntos faciales
                                self.puntos_faciales.clear()
                                if resultados.multi_face_landmarks: # existe un rostro
                                    for rostro_detec in resultados.multi_face_landmarks:
                                        self.mp_dibujo.draw_landmarks(self.video, rostro_detec, self.mp_malla_fac.FACEMESH_CONTOURS, self.conf_dibujo, self.conf_dibujo)
                                        # Extraer los puntos del rostro detectado
                                        for id, puntos in enumerate(rostro_detec.landmark):
                                            al, an, c = self.video.shape
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
                                                # Contar parpadeos
                                                
                                                cv2.putText(self.video, f'Parpadeos: {int(self.parpadeo)}', (300, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                                                if longitud1 <= 12 and longitud2 <= 12 and self.parpadeando == False: 
                                                    # Cerró los ojos
                                                    print("---- CERRÓ LOS OJOS", longitud1, longitud2)
                                                    self.parpadeo = self.parpadeo + 1
                                                    self.parpadeando = True
                                                    self.inicio_sueno = time.time()
                                                    # Justo el momento que cerró los ojos se captura la imagen
                                                    self.imagen_dormido = video_color[y:y + h, x:x + w]
                                                elif longitud1 > 14 and longitud2 > 14 and self.parpadeando == True: 
                                                    # Abrió los ojos
                                                    self.parpadeando = False
                                                    self.inicio_sueno = 0
                                                    self.sueno_permitido = self.incremen_sueno_per
                                                    Supervisados.cambiarEstado(self.supervisado, False)
                                                # Temporizador
                                                if self.inicio_sueno != 0:
                                                    self.tiempo_dormido = round(time.time() - self.inicio_sueno, 0)
                                                    if self.tiempo_dormido >= self.sueno_permitido:
                                                        self.sueno_permitido += self.incremen_sueno_per
                                                        #if(len(self.obtenerRostros(self.imagen_dormido)) and self.supervisado != ''):
                                                        minutos, segundos = self.convertirMinSeg(self.tiempo_dormido)
                                                        Supervisados.cambiarEstado(self.supervisado, True)
                                                        Historial.crear(self.supervisado, 'Presencia de sueño, lleva dormido un tiempo de {0} minutos y {1} segundos'.format(minutos, segundos), self.dis_suen_id, self.imagen_dormido)
                                                    


                            # ------ RECONOCIMIENTO # 4 - Reconocer objetos                
                            if len(Monitoreo.objects.filter(Q(tutor_id = self.tutor_id) & Q(tipo_distraccion_id = self.dis_obj_id))) and self.supervisado != '':
                                if self.reloj_objetos == 0:
                                    self.reloj_objetos = time.time()
                                frame = cv2.flip(self.video, 1)
                                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                imagen_objetos = cv2.resize(frame, (224, 224), fx=0, fy=0, interpolation = cv2.INTER_AREA)
                                # convertir la imagen en un array de numpy
                                image_array = np.asarray(imagen_objetos)
                                # normalizar la imagen
                                self.data_entrena_objet[0] = (image_array.astype(np.float32) / 127.0) - 1
                                # realizar reconocimiento de objetos
                                prediction = self.modelo_objetos.predict(self.data_entrena_objet)
                                # Cada 10 segundos hasta cumplir el tiempo de registro se limpia el diccionario de objetos reconocidos
                                if (round(time.time() - self.reloj_objetos, 0) == 10 or round(time.time() - self.reloj_objetos, 0) == 20): 
                                    self.reloj_objetos -= 1                    
                                    self.objetos_recono = {}
                                for i in range(len(prediction[0])):
                                    # Solo los objetos que tengan una precisión superior del 60 %
                                    if (prediction[0][i] >= 0.60):
                                        # Mejorar la precisión del reconocimiento de los objetos
                                        contador_objeto = 1
                                        nombre_objeto = self.labels_objetos[i]
                                        if self.objetos_recono.get(self.supervisado, -1) != -1:
                                            if self.objetos_recono.get(self.supervisado, -1).get(nombre_objeto, -1) != -1:
                                                contador_objeto = self.objetos_recono.get(self.supervisado, -1).get(nombre_objeto, -1)
                                                contador_objeto += 1
                                                self.objetos_recono[self.supervisado][nombre_objeto] = contador_objeto
                                                self.imagenes_objetos[self.supervisado][nombre_objeto] = video_color
                                            else:
                                                self.imagenes_objetos.get(self.supervisado, -1).update({nombre_objeto: video_color})
                                                self.objetos_recono.get(self.supervisado, -1).update({nombre_objeto: 1})
                                        else:
                                            self.imagenes_objetos = {self.supervisado: {nombre_objeto: video_color}}
                                            self.objetos_recono = {self.supervisado: {nombre_objeto: 1}}
                                # Después de estar analizando durante 30 segundos se registran los objetos con número mayor de 5 manifestaciones 
                                print(self.objetos_recono)
                                if (round(time.time() - (self.reloj_objetos + 2), 0) >= (self.incremen_sueno_per)):
                                    lista_objetos = self.objetos_recono.get(self.supervisado, None)
                                    if lista_objetos != None:
                                        for objeto in lista_objetos:
                                            # Si tiene la probabilidad de más de 5 apariciones el objeto, se procede a verificar el permiso de uso
                                            if self.objetos_recono.get(self.supervisado).get(objeto) > 5:
                                                tiene_permiso = PermisosObjetos.objects.filter(Q(tutor_id = self.tutor_id) & Q(objeto__nombre__startswith = objeto))
                                                if len(tiene_permiso):
                                                    print(str(objeto) + ' - CON PERMISO')
                                                else:
                                                    print(str(objeto) + ' - SIN PERMISO')
                                                    if self.supervisado != '':
                                                        # se escoge la imagen del objeto desde el diccionario general de imagenes en array
                                                        Historial.crear(self.supervisado, 'Se identificó el uso del objeto {0} sin autorización'.format(objeto), self.dis_obj_id, (self.imagenes_objetos.get(self.supervisado, -1).get(objeto, -1)))
                                        self.reloj_objetos = 0
                                        self.objetos_recono = {}
                                        self.imagenes_objetos = {}
                                    

                        # Reiniciando variables 
                        if self.reconocer_personas and self.supervisado != '':
                            # Si no hay personas desconocidas se cancela el cronómetro
                            if self.personas_desconocidas == 0:
                                self.reloj_desconocido = 0
                            # Si todos los rostros son desconocidos, pero antes si hubo un supervisado, se inicia el cronómetro
                            if self.reloj_supervisado == 0 and (len(rostros) == 0 or len(rostros) == self.personas_desconocidas):
                                # Se fue el supervisado
                                self.reloj_supervisado = time.time()  
                            elif len(rostros) != self.personas_desconocidas and self.reloj_supervisado > 0:
                                # Llegó el supervisado
                                self.reloj_supervisado = 0
                                self.tiempo_espera_sup = self.incremen_ausente
                                Supervisados.cambiarEstado(self.supervisado, False)
                            # Mostrar mensaje de presencia / ausencia
                            if self.reloj_supervisado == 0:
                                cv2.putText(self.video, 'Presente', (20, 28), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                            else:
                                cv2.putText(self.video, 'Ausente, conteo iniciado!', (20, 28), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                            
                        # Detener el proceso de monitoreo                
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.fin_vigilancia = True
                            return 0
                        pass

                        cv2.imshow('Video', self.video)
            cv2.destroyAllWindows()
            self.fin_vigilancia = True
        except Supervisados.DoesNotExist:
            pass
        except Exception as e: 
            print('Error durante el monitoreo: ' + str(e))
            self.fin_vigilancia = True
        return 0