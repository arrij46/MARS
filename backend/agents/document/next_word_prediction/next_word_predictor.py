import numpy as np
import pickle
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

class NextWordPredictor:

    def __init__(self, model_path, tokenizer_path):
        self.model = load_model(model_path)

        with open(tokenizer_path, "rb") as f:
            self.tokenizer = pickle.load(f)

        # get input length from model
        self.max_sequence_len = self.model.input_shape[1] + 1

    def predict_next(self, text, num_words=1):
        seed_text = text

        for _ in range(num_words):
            token_list = self.tokenizer.texts_to_sequences([seed_text])[0]
            token_list = pad_sequences(
                [token_list],
                maxlen=self.max_sequence_len - 1,
                padding='pre'
            )

            predicted_probs = self.model.predict(token_list, verbose=0)
            predicted_index = np.argmax(predicted_probs, axis=-1)[0]

            output_word = self.tokenizer.index_word.get(predicted_index, "")

            if output_word == "":
                break

            seed_text += " " + output_word

        return seed_text