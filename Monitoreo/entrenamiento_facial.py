import os
import cv2
import imutils
import numpy as np
from urllib.request import urlopen

class EntrenamientoFacial:
    def __init__(self, persona_id):
        self.persona_id = persona_id
        self.dataTrained = 'media\\Perfiles\\Trained'
        self.rutaModelos = 'Monitoreo\\trained_model\\'
        self.labels = []
        self.facesData = []
        self.label = 0
        self.faceClassif = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.imagenesCapturar = 300
        self.contImagenes = 0
        self.byte = bytes()
    
    def entrenar(self):
        try:
            os.makedirs(self.dataTrained + '\\' + str(self.persona_id), exist_ok = True)
            # se crean las 300 imágenes de la persona custodiada para después realizar el entrenamiento
            stream = urlopen('http://192.168.1.108:81/stream')
            while True:
                self.byte += stream.read(4096)
                a = self.byte.find(b'\xff\xd8')
                b = self.byte.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    imagen = self.byte[a:b + 2]
                    self.byte = self.byte[b + 2:]
                    if imagen:
                        video = cv2.imdecode(np.fromstring(imagen, dtype = np.uint8), cv2.IMREAD_COLOR)
                        video =  imutils.resize(video, width = 640)
                        gray = cv2.cvtColor(video, cv2.COLOR_BGR2GRAY)
                        auxFrame = video.copy()
                        faces = self.faceClassif.detectMultiScale(gray, 1.3, 5)
                        for (x, y, w, h) in faces:
                            cv2.rectangle(video, (x, y),(x + w, y + h),(0, 255, 0), 2)
                            rostro = auxFrame[y:y + h, x:x + w]
                            rostro = cv2.resize(rostro,(150, 150),interpolation = cv2.INTER_CUBIC)
                            cv2.imwrite(self.dataTrained + '\\' + str(self.persona_id) + '/rotro_{}.png'.format(self.contImagenes), rostro)
                            self.contImagenes += 1
                        cv2.imshow('Video', cv2.resize(video,(1500, 760), interpolation = cv2.INTER_CUBIC))
                        k =  cv2.waitKey(1)
                        if k == 27 or self.contImagenes >= self.imagenesCapturar:
                            cv2.destroyAllWindows()
                            break
            # entrenamiento del modelo con todas las imágenes
            peopleList = os.listdir(self.dataTrained)
            for nameDir in peopleList:
                personPath = self.dataTrained + '\\' + nameDir
                #print('Leyendo las imágenes')
                for fileName in os.listdir(personPath):
                    #print('Rostros: ', nameDir + '\\' + str(fileName))
                    self.labels.append(self.label)
                    self.facesData.append(cv2.imread(personPath+'\\' + str(fileName), 0))
                self.label = self.label + 1
            face_recognizer = cv2.face.LBPHFaceRecognizer_create()
            #print("Entrenando...")
            face_recognizer.train(self.facesData, np.array(self.labels)) 
            face_recognizer.write(self.rutaModelos + 'modeloLBPHFace.xml')
            print("Modelo de reconocimiento facial almacenado...")
            return 'entrenado'
        except Exception as e: 
            return 'error'
