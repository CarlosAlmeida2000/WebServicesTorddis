from tensorflow.keras.layers import Dense, Dropout, Flatten, Conv2D, MaxPooling2D
from Monitoreo.models import Historial
from tensorflow.keras.models import Sequential
from django.core.files.base import ContentFile
from Persona.models import Supervisados
from urllib.request import urlopen
from django.db.models import Q
from datetime import datetime
import numpy as np
import cv2
import os

class Monitorizar:
    def __init__(self):
        # atributos generales 
        self.dataTrained = 'media\\Perfiles\\Trained'
        self.rutaModelos = 'Monitoreo\\trained_model\\'
        self.custodiadosReconocer = []
        self.expresionFacial = ''
        self.imagenExpresion = None
        self.custodiado = Custodiados()
        self.minutosDeteccion = 1
        self.byte = bytes()
        # Construcción de la red neuronal convolucional
        self.model = Sequential()

        # ************** Capa de entrada
        # Capa convolucional 1 con ReLU-activation
        self.model.add(Conv2D(32, kernel_size = (3, 3), activation='relu', input_shape = (48, 48, 1)))
        # Capa convolucional 2 con ReLU-activation + un max poling
        self.model.add(Conv2D(64, kernel_size = (3, 3), activation='relu'))
        # MaxPooling2D: Operación de agrupación máxima (2 x 2) para datos espaciales 2D.
        self.model.add(MaxPooling2D(pool_size = (2, 2)))
        # El abandono o función Dropout() se implementa fácilmente mediante la selección aleatoria de nodos que se abandonarán con una probabilidad dada 
        # (por ejemplo, 25 %) en cada ciclo de actualización de peso
        self.model.add(Dropout(0.25))

        # ************** Capa oculta
        # Capa convolucional 3 con ReLU-activation + un max poling
        self.model.add(Conv2D(128, kernel_size = (3, 3), activation = 'relu'))
        # MaxPooling2D: Operación de agrupación máxima (2 x 2) para datos espaciales 2D.
        self.model.add(MaxPooling2D(pool_size = (2, 2)))
        # Capa convolucional 4 con ReLU-activation + un max poling
        self.model.add(Conv2D(128, kernel_size = (3, 3), activation = 'relu'))
        # MaxPooling2D: Operación de agrupación máxima (2 x 2) para datos espaciales 2D.
        self.model.add(MaxPooling2D(pool_size = (2, 2)))
        # El abandono o función Dropout() se implementa fácilmente mediante la selección aleatoria de nodos que se abandonarán con una probabilidad dada 
        # (por ejemplo, 25 %) en cada ciclo de actualización de peso
        self.model.add(Dropout(0.25))

        # ************** Capa de salida
        self.model.add(Flatten())
        # Primera capa Densa completamente conectada con ReLU-activation.
        self.model.add(Dense(1024, activation = 'relu'))
        # El abandono o función Dropout() se implementa fácilmente mediante la selección aleatoria de nodos que se abandonarán con una probabilidad dada 
        # (por ejemplo, 50 %) en cada ciclo de actualización de peso
        self.model.add(Dropout(0.5))
        # Última capa Densa totalmente conectada con activación de softmax
        self.model.add(Dense(7, activation = 'softmax'))
        
        # evita el uso de openCL y los mensajes de registro innecesarios
        cv2.ocl.setUseOpenCL(False)
        # diccionario que asigna a cada etiqueta una emoción (orden alfabético)
        self.emotion_dict = {0: 'Angry', 1: 'Disgusted', 2: 'Afraid', 3: 'Happy', 4: 'Neutral', 5: 'Sad', 6: 'Surprised'}
        # cargar el clasificador de detección de rostros pre entrenado de OpenCV
        self.faceClassif = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        # cargar el modelo entrenado para reconocer expresiones faciales
        self.model.load_weights(self.rutaModelos + 'model.h5')
        # cargar el modelo para el reconocimiento facial: El reconocimiento facial se realiza mediante el clasificador de distancia y vecino más cercano
        self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.face_recognizer.read(self.rutaModelos + 'modeloLBPHFace.xml')
        # se obtine la lista de personas a reconocer
        self.custodiadosReconocer = os.listdir(self.dataTrained)
    
    # se registra el historial de la persona
    def guardarHistorial(self):
        historial = Historial()
        historial.fecha_hora = datetime.now()
        ultimo_dia = 1
        ultimo_historial = Historial.objects.filter(Q(custodiado_id = self.custodiado[0].id)).order_by('-fecha_hora')
        if (len(ultimo_historial) > 0):
            fecha_historial = datetime.strptime(ultimo_historial[0].fecha_hora.strftime('%Y-%m-%d'), '%Y-%m-%d')
            ultimo_dia = ultimo_historial[0].dia
            # Si la fecha actual es mayor al último historial, significa que el historial a registrar es de un nuevo día
            if (datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d') > fecha_historial):
                ultimo_dia += 1
        historial.dia = ultimo_dia
        historial.expresion_facial = self.expresionFacial
        historial.custodiado = self.custodiado[0]
        frame_jpg = cv2.imencode('.png', cv2.resize(self.imagenExpresion,(450, 450),interpolation = cv2.INTER_CUBIC))
        file = ContentFile(frame_jpg[1])
        historial.imagen_expresion.save('persona_id_' + str(self.custodiado[0].persona.id) + '_fecha_' + str(historial.fecha_hora) + '.png', file, save = True)
        historial.save()

    def reconocer(self):
        try:
            # obtención del streaming de la cámara
            stream = urlopen('http://192.168.1.108:81/stream')
            while (True):
                # lectura del stream con una resolución de 4096 
                self.byte += stream.read(4096)
                a = self.byte.find(b'\xff\xd8')
                b = self.byte.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    imagen = self.byte[a:b + 2]
                    self.byte = self.byte[b + 2:]
                    # si recibimos imagen
                    if imagen:
                        # Lee una imagen de un búfer en la memoria.
                        video = cv2.imdecode(np.fromstring(imagen, dtype = np.uint8), cv2.IMREAD_COLOR)
                        gray = cv2.cvtColor(video, cv2.COLOR_BGR2GRAY)
                        auxFrame = gray.copy()
                        auxFrame_color = video.copy()
                        # detectando rostros - encuentra la cascada haar para dibujar la caja delimitadora alrededor de la cara
                        faces = self.faceClassif.detectMultiScale(gray, scaleFactor = 1.3, minNeighbors = 5)
                        # recorriendo rostros 
                        for (x, y, w, h) in faces:
                            rostro = auxFrame[y:y + h, x:x + w]
                            self.imagenExpresion = auxFrame_color[y:y + h, x:x + w]
                            # reconocimiento facial
                            rostro = cv2.resize(rostro, (150, 150), interpolation = cv2.INTER_CUBIC)
                            persona_identif = self.face_recognizer.predict(rostro)
                            cv2.putText(video,'{}'.format(persona_identif),(x, y - 5),1,1.3,(255, 255, 0), 1, cv2.LINE_AA)
                            # se verifica si es la persona
                            if persona_identif[1] < 70:
                                self.custodiado = Custodiados.objects.filter(persona_id = self.custodiadosReconocer[persona_identif[0]]).select_related('persona')
                                if(len(self.custodiado)):
                                    cv2.putText(video,'{}'.format(self.custodiado[0].persona.nombres),(x, y - 25), 2, 1.1,(0, 255, 0),1,cv2.LINE_AA)
                                    cv2.rectangle(video, (x, y),(x + w,y + h),(0, 255, 0), 2)
                                    # se reconoce la expresión facial
                                    cv2.rectangle(video, (x, y-50), (x + w, y + h + 10), (255, 0, 0), 2)
                                    cropped_img = np.expand_dims(np.expand_dims(cv2.resize(rostro, (48, 48)), -1), 0)
                                    prediction = self.model.predict(cropped_img)
                                    maxindex = int(np.argmax(prediction))
                                    self.expresionFacial = self.emotion_dict[maxindex]
                                    cv2.putText(video, self.expresionFacial, (x + 20, y-60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                                    # se verifica si la última expresión facial registrada en el historial es igual a la expresión facial actual detectada, 
                                    # con el objetivo de no registrar un nuevo historial con esa misma fecha y hora
                                    ultimo_historial = (Historial.objects.filter(Q(custodiado_id = self.custodiado[0].id) & Q(expresion_facial = self.expresionFacial)).order_by('-fecha_hora'))
                                    if(len(ultimo_historial) > 0):
                                        fecha_historial = datetime.strptime(ultimo_historial[0].fecha_hora.strftime('%Y-%m-%d %H:%M:%S.%f') , '%Y-%m-%d %H:%M:%S.%f')
                                        minutos = (datetime.now() - fecha_historial).seconds * 0.0167
                                        if (minutos > self.minutosDeteccion):
                                            self.guardarHistorial()
                                    else:
                                        self.guardarHistorial()
                            else:
                                cv2.putText(video,'Desconocido',(x, y - 20), 2, 0.8,(0, 0, 255),1,cv2.LINE_AA)
                                cv2.rectangle(video, (x, y),(x + w, y + h),(0, 0, 255), 2)
                        cv2.imshow('Video', cv2.resize(video,(1500, 760), interpolation = cv2.INTER_CUBIC))
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            cv2.destroyAllWindows()
        except Exception as e: 
            print(str(e))