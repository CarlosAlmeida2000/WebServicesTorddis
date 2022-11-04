
from tensorflow.keras.layers import Dense, Dropout, Flatten, MaxPooling2D, Conv2D
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam

try:
        # Rutas de las imágenes para entrenar y evaluar
        train_dir = 'data/train'
        val_dir = 'data/test'

        # cantidad de imágenes para el entrenamiento
        num_train = 28709
        # cantidai de imágenes para evaluar el modelo
        num_val = 7178
        # cantidad de lotes, cuando se procesen 448 lotes se completa una época
        batch_size = 64
        # cantidad de épocas
        num_epoch = 50

        # Generar lotes de datos de imágenes de tensorflows con las imágenes de entrenamiento y prueba
        train_datagen = ImageDataGenerator(rescale=1./255)
        val_datagen = ImageDataGenerator(rescale=1./255)
        train_generator = train_datagen.flow_from_directory(
                train_dir,
                target_size = (48,48),
                batch_size = batch_size,
                color_mode = "grayscale",
                class_mode = 'categorical')
        validation_generator = val_datagen.flow_from_directory(
                val_dir,
                target_size = (48,48),
                batch_size = batch_size,
                color_mode = "grayscale",
                class_mode = 'categorical')

        # Construcción de la red neuronal convolucional
        model = Sequential()

        # ************** Capa de entrada
        # Capa convolucional 1 con ReLU-activation
        model.add(Conv2D(32, kernel_size = (3, 3), activation='relu', input_shape = (48, 48, 1)))
        # Capa convolucional 2 con ReLU-activation + un max poling
        model.add(Conv2D(64, kernel_size = (3, 3), activation='relu'))
        # Capa de agrupación MaxPooling2D: Operación de agrupación máxima (2 x 2) para datos espaciales 2D.
        model.add(MaxPooling2D(pool_size = (2, 2)))
        # El abandono o función Dropout() se implementa fácilmente mediante la selección aleatoria de nodos que se abandonarán con una probabilidad dada 
        # (por ejemplo, 25 %) en cada ciclo de actualización de peso
        model.add(Dropout(0.25))

        # ************** Capa oculta
        # Capa convolucional 3 con ReLU-activation + un max poling
        model.add(Conv2D(128, kernel_size = (3, 3), activation = 'relu'))
        # Capa de agrupación  MaxPooling2D: Operación de agrupación máxima (2 x 2) para datos espaciales 2D.
        model.add(MaxPooling2D(pool_size = (2, 2)))
        # Capa convolucional 4 con ReLU-activation + un max poling
        model.add(Conv2D(128, kernel_size = (3, 3), activation = 'relu'))
        # Capa de agrupación MaxPooling2D: Operación de agrupación máxima (2 x 2) para datos espaciales 2D.
        model.add(MaxPooling2D(pool_size = (2, 2)))
        # El abandono o función Dropout() se implementa fácilmente mediante la selección aleatoria de nodos que se abandonarán con una probabilidad dada 
        # (por ejemplo, 25 %) en cada ciclo de actualización de peso
        model.add(Dropout(0.25))

        # ************** Capa de salida
        model.add(Flatten())
        # Primera capa Densa completamente conectada con ReLU-activation.
        model.add(Dense(1024, activation = 'relu'))
        # El abandono o función Dropout() se implementa fácilmente mediante la selección aleatoria de nodos que se abandonarán con una probabilidad dada 
        # (por ejemplo, 50 %) en cada ciclo de actualización de peso
        model.add(Dropout(0.5))
        # Última capa Densa totalmente conectada con activación de softmax - 7 neuronas de salida
        model.add(Dense(7, activation = 'softmax'))

        # se compila el modelo, especificando el algoritmo de optimización Adam y la métrica será precisión
        model.compile(loss = 'categorical_crossentropy', optimizer = Adam(lr = 0.0001, decay = 1e-6), metrics = ['accuracy'])
        # fit_generator() para comenzar con el entrenamiento del modelo
        model_info = model.fit_generator(
                # lotes de datos de entrenamiento
                train_generator,
                # 448 lotes de entrenamiento
                steps_per_epoch = num_train // batch_size,
                # cantidad de épocas
                epochs = num_epoch,
                # lotes de datos de pruebas
                validation_data = validation_generator,
                # 112 lotes de pruebas
                validation_steps = num_val // batch_size)
        # almacenamiento del modelo
        model.save_weights('trained_model\\model.h5')
except Exception as e: 
        print("Error: "+ str(e))

"""
Visión general de los 5 pasos del ciclo de vida del modelo de red neuronal en Keras:
1. Definir grafo.
2. Compilar red.
3. Ajustar red.
4. Evaluar la red.
5. Hacer las predicciones.
"""