import numpy as np
import tensorflow as tf
import pickle
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense

# Read the text file
with open('data.txt', 'r', encoding='utf-8') as file:
    text = file.read()

# tokenize the text
tokenizer = Tokenizer()
tokenizer.fit_on_texts([text])
total_words = len(tokenizer.word_index) + 1

# create input sequences
input_sequences = []
for line in text.split('\n'):
    token_list = tokenizer.texts_to_sequences([line])[0]
    for i in range(1, len(token_list)):
        n_gram_sequence = token_list[:i+1]
        input_sequences.append(n_gram_sequence)

# pad sequences
max_sequence_len = max([len(seq) for seq in input_sequences])
input_sequences = np.array(pad_sequences(input_sequences, maxlen=max_sequence_len, padding='pre'))

# create predictors and label (x is input sequence and y is the next word) 
X = input_sequences[:, :-1]
y = input_sequences[:, -1]

# one-hot encode the labels
# y = np.array(tf.keras.utils.to_categorical(y, num_classes=total_words))
y = y.astype('float32')
# build the model
model = Sequential()
# embedding layer converts each word into a vector of fixed size (100 in this case)
model.add(Embedding(total_words, 100, input_length=max_sequence_len-1))
# LSTM layer is a type of recurrent neural network that is good at learning from sequences of data, such as text. It has 150 units in this case.
model.add(LSTM(150))
# Dense layer is a fully connected layer that outputs a probability distribution over the next word in the sequence. The number of units is equal to the total number of words in the vocabulary, and the activation function is softmax, which ensures that the output values are between 0 and 1 and sum to 1.
model.add(Dense(total_words, activation='softmax'))
print(model.summary())

# compile and train the model
model.compile(loss='sparse_categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
model.fit(X, y, epochs=8, verbose=1)

# save model
model.save("next_word_prediction_model.keras")

# save tokenizer
with open("tokenizer.pkl", "wb") as f:
    pickle.dump(tokenizer, f)

print("Model and tokenizer saved successfully!")
