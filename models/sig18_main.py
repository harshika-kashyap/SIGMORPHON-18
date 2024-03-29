import pickle
import tensorflow as tf 
from sig18_load_data import load_data_for_seq2seq, load_test_data

import keras.backend as K
from keras import initializers, regularizers, constraints
from keras.preprocessing.text import text_to_word_sequence
from keras.preprocessing.sequence import pad_sequences
from keras.models import Sequential,Model
from keras.layers import dot, Activation, TimeDistributed, Dense, RepeatVector, recurrent, Embedding, Input, merge
from keras.layers.recurrent import LSTM, SimpleRNN, GRU
from keras.layers.wrappers import Bidirectional
from keras.layers.core import Layer
from keras.optimizers import Adam, RMSprop, SGD, Adadelta, Adagrad
from keras.utils import plot_model
from keras.callbacks import EarlyStopping, ModelCheckpoint, Callback
from keras.engine.topology import Layer, InputSpec
from keras import initializers, regularizers, constraints
from sig18_attention_decoder import AttentionDecoder 

from nltk import FreqDist
import numpy as np
import os
import datetime
import sys
import gc 

MODE='train'

HIDDEN_DIM = 40
EPOCHS = 20
dropout = 0.2
TIME_STEPS = 20
EMBEDDING_DIM = 150
BATCH_SIZE = 10
LAYER_NUM = 2

def create_model(X_vocab_len, X_max_len, y_vocab_len, y_max_len, hidden_size, num_layers):

	def smart_merge(vectors, **kwargs):
			return vectors[0] if len(vectors)==1 else merge(vectors, **kwargs)		
	
	root_word_in = Input(shape=(X_max_len,), dtype='int32')
	
	emb_layer = Embedding(X_vocab_len, EMBEDDING_DIM, 
				input_length=X_max_len,
				mask_zero=True) 
	
	word_embedding = emb_layer(root_word_in) # POSITION of layer

	BidireLSTM_vector= Bidirectional(LSTM(40, dropout=0, return_sequences=True))(word_embedding)
	'''
	att = AttentionWithContext()(BidireLSTM_vector)
	#print(att.shape)
	RepLayer= RepeatVector(y_max_len)
	RepVec= RepLayer(att)
	Emb_plus_repeat=[hindi_word_embedding]
	Emb_plus_repeat.append(RepVec)
	Emb_plus_repeat = smart_merge(Emb_plus_repeat, mode='concat')
	
	
	for _ in range(num_layers):
		LtoR_LSTM = Bidirectional(LSTM(40, dropout=dropout, return_sequences=True))
		temp = LtoR_LSTM(Emb_plus_repeat)
	
	# for each time step in the input, we intend to output |y_vocab_len| time steps
	time_dist_layer = TimeDistributed(Dense(y_vocab_len))(temp)
	outputs = Activation('softmax')(time_dist_layer)
	'''
	outputs = AttentionDecoder(HIDDEN_DIM, X_vocab_len)(BidireLSTM_vector)

	all_inputs = [root_word_in]
	model = Model(input=all_inputs, output=outputs)
	opt = Adam()
	model.compile(optimizer='rmsprop', loss='categorical_crossentropy', metrics=['accuracy'])
	
	return model

def process_data(word_sentences, max_len, word_to_ix):
	# Vectorizing each element in each sequence
	sequences = np.zeros((len(word_sentences), max_len, len(word_to_ix)))
	for i, sentence in enumerate(word_sentences):
		for j, word in enumerate(sentence):
			sequences[i, j, word] = 1
	return sequences

sentences = pickle.load(open('sentences_train_low', 'rb'))
rootwords = pickle.load(open('rootwords_train_low', 'rb'))
features = pickle.load(open('features_train_low', 'rb'))

# we keep X_idx2word and y_idx2word the same
X, X_vocab_len, X_word_to_ix, X_ix_to_word, y, y_vocab_len, y_word_to_ix, y_ix_to_word = load_data_for_seq2seq(sentences, rootwords)

# should be all equal for better results
print(X_vocab_len)
print(len(X_word_to_ix))
print(len(X_ix_to_word))
print(len(y_word_to_ix))
print(len(y_ix_to_word))


X_max = max([len(word) for word in X])
y_max = max([len(word) for word in y])
X_max_len = max(X_max,y_max)
y_max_len = max(X_max,y_max)

print(X_max_len)
print(y_max_len)

print("Zero padding .. ")
X = pad_sequences(X, maxlen= X_max_len, dtype = 'int32', padding='post')
y = pad_sequences(y, maxlen = y_max_len, dtype = 'int32', padding='post')

print("Compiling Model ..")
model = create_model(X_vocab_len, X_max_len, y_vocab_len, y_max_len, HIDDEN_DIM, LAYER_NUM)

saved_weights = "simpleRootWord_withAtt.hdf5"

if MODE == 'train':
	print("Training model ..")
	y_sequences = process_data(y, y_max_len, y_word_to_ix)

	history = model.fit(X, y_sequences, validation_split=0.1, 
		batch_size=BATCH_SIZE, epochs=EPOCHS, verbose=1, 
		callbacks=[EarlyStopping(patience=20, verbose=1),
		ModelCheckpoint('simpleRootWord_withAtt.hdf5', save_best_only=True,
			verbose=1)])
	print(history.history.keys())
	print(history)

else:
	if len(saved_weights) == 0:
		print("network hasn't been trained!")
		sys.exit()
	else:
		test_sample_num = 0

		test_sentences = pickle.load(open('sentences_dev', 'rb'))
		test_roots = pickle.load(open('rootwords_dev', 'rb'))
		test_features = pickle.load(open('features_dev', 'rb'))
		
		X_test, X_unique, y_unique = load_test_data(test_sentences, test_roots, X_word_to_ix)

		X_test = pad_sequences(X_test, maxlen=X_max_len, dtype='int32', padding='post')
		
		model.load_weights(saved_weights)

		plot_model(model, to_file="model2_arch.png", show_shapes=True)

		predictions = np.argmax(model.predict(X_test), axis=2)
		print(predictions)

		sequences = []

		for i in predictions:
			test_sample_num += 1

			char_list = []
			for idx in i:
				if idx > 0:
					char_list.append(y_ix_to_word[idx])

			sequence = ''.join(char_list)
			print(test_sample_num,":", sequence)
			sequences.append(sequence)

		filename = "model2_out.txt"
		with open(filename, 'w', encoding='utf-8') as f:
			f.write("Words" + '\t' + 'Original Roots' + '\t' + "Predicted roots" + '\n')
			for a,b,c in zip(X_unique, y_unique, sequences):
				f.write(str(a) + '\t\t' + str(b) + '\t\t' + str(c) + '\n')


