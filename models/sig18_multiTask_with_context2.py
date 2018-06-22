import pickle
import tensorflow as tf 
from data_preprocessing.sig18_load_data import*
import keras.backend as K
from keras.utils import np_utils
from keras import initializers, regularizers, constraints
from keras.preprocessing.text import text_to_word_sequence
from keras.preprocessing.sequence import pad_sequences
from keras.models import Sequential,Model
from keras.layers import dot, Activation, TimeDistributed, Dense, RepeatVector, recurrent, Embedding, Input, merge, concatenate
from keras.layers.recurrent import LSTM, SimpleRNN, GRU
from keras.layers.wrappers import Bidirectional
from keras.layers.core import Layer
from keras.optimizers import Adam, RMSprop, SGD, Adadelta, Adagrad
from keras.utils import plot_model
from keras.callbacks import EarlyStopping, ModelCheckpoint, Callback
from keras.engine.topology import Layer, InputSpec
from models.utils.sig18_attention_decoder import AttentionDecoder 
from models.utils.sig18_attention_encoder import AttentionWithContext

from nltk import FreqDist
import numpy as np
import pandas as pd 
import os
import datetime
import sys 
from nltk import FreqDist
import numpy as np
import pandas as pd 
import sys
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.metrics import roc_curve, auc, precision_recall_fscore_support, f1_score
from collections import Counter, deque
from models.utils.sig18_predict_with_features import plot_model_performance
#from curve_plotter import plot_precision_recall

MODE='trai'
HIDDEN_DIM = 40
EPOCHS = 200
dropout = 0.2
TIME_STEPS = 20
EMBEDDING_DIM = 150
BATCH_SIZE = 100
LAYER_NUM = 2

class_labels = []


def write_words_to_file(orig_words, predictions):
    print("Writing to file ..")
    
    X = [item for sublist in rootwords for item in sublist]
    Y = [item for sublist in orig_words for item in sublist]

    filename = "./outputs/multitask_context2_out.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("Rootwords" + '\t\t\t' + "Original Words" + '\t\t' + "Predicted words" + '\n')
        for a,b,c in zip(X, Y, predictions):
            f.write(str(a) + '\t\t' + str(b) + '\t\t\t' + str(c) + '\n')

    print("Success writing to file !")

def create_model(X_vocab_len, X_max_len, y_vocab_len, y_max_len, hidden_size, num_layers, context1=False, context2=False):

    def smart_merge(vectors, **kwargs):
            return vectors[0] if len(vectors)==1 else merge(vectors, **kwargs)        
    
    current_root = Input(shape=(X_max_len,), dtype='int32')
    right_word1 = Input(shape=(X_max_len,), dtype='int32')
    right_word2 = Input(shape=(X_max_len,), dtype='int32')
    left_word1 = Input(shape=(X_max_len,), dtype='int32')
    left_word2 = Input(shape=(X_max_len,), dtype='int32')

    emb_layer = Embedding(X_vocab_len, EMBEDDING_DIM, 
                input_length=X_max_len,
                mask_zero=True) 
    
    current_root_embedding = emb_layer(current_root) # POSITION of layer
    right_word_embedding1 = emb_layer(right_word1) # these are the left shifted X by 1
    right_word_embedding2 = emb_layer(right_word2) # left shifted by 2

    left_word_embedding1 = emb_layer(left_word1) # these are the right shifted X by 1, i.e. the left word is at current position
    left_word_embedding2 = emb_layer(left_word2)

    BidireLSTM_curr= Bidirectional(LSTM(40, dropout=dropout, return_sequences=True))(current_root_embedding)
    BidireLSTM_right1 = Bidirectional(LSTM(40, dropout=dropout, return_sequences=True))(right_word_embedding1)
    BidireLSTM_right2 = Bidirectional(LSTM(40, dropout=dropout, return_sequences=True))(right_word_embedding2)
    BidireLSTM_left1 = Bidirectional(LSTM(40, dropout=dropout, return_sequences=True))(left_word_embedding1)
    BidireLSTM_left2 = Bidirectional(LSTM(40, dropout=dropout, return_sequences=True))(left_word_embedding2)
    
    concatenated_encodings = [BidireLSTM_left2]
    concatenated_encodings.append(BidireLSTM_left1)
    concatenated_encodings.append(BidireLSTM_curr)
    concatenated_encodings.append(BidireLSTM_right1)
    concatenated_encodings.append(BidireLSTM_right2)

    concatenated_encodings = smart_merge(concatenated_encodings, mode='concat')

    att = AttentionWithContext()(concatenated_encodings)
    RepLayer= RepeatVector(y_max_len)
    RepVec= RepLayer(att)
    Emb_plus_repeat=[current_root_embedding]
    Emb_plus_repeat.append(RepVec)
    Emb_plus_repeat = smart_merge(Emb_plus_repeat, mode='concat')
    att = AttentionWithContext()(BidireLSTM_curr)
    #print(att.shape)
    RepLayer= RepeatVector(y_max_len)
    RepVec= RepLayer(att)
    Emb_plus_repeat=[current_root_embedding]
    Emb_plus_repeat.append(RepVec)
    Emb_plus_repeat = smart_merge(Emb_plus_repeat, mode='concat')
    
    
    for _ in range(num_layers):
        LtoR_LSTM = Bidirectional(LSTM(40, dropout=dropout, return_sequences=True))
        temp = LtoR_LSTM(Emb_plus_repeat)
    
    # for each time step in the input, we intend to output |y_vocab_len| time steps
    time_dist_layer = TimeDistributed(Dense(y_vocab_len))(temp)
    outputs = Activation('softmax')(time_dist_layer)
    
    all_inputs = [current_root, right_word1, right_word2, left_word1, left_word2]
    all_outputs = [outputs]

    model = Model(inputs=all_inputs, outputs=all_outputs)
    opt = Adam()
    model.compile(optimizer='rmsprop', loss='categorical_crossentropy', metrics=['accuracy'], 
        loss_weights=[1.])
    
    return model

def process_data(word_sentences, max_len, word_to_ix):
    # Vectorizing each element in each sequence
    sequences = np.zeros((len(word_sentences), max_len, len(word_to_ix)))
    #print(len(word_sentences))
    for i, sentence in enumerate(word_sentences):
        for j, word in enumerate(sentence):
            sequences[i, j, word] = 1
    return sequences

sentences = pickle.load(open('./pickel_dumps/sentences_train_low', 'rb'))
rootwords = pickle.load(open('./pickel_dumps/rootwords_train_low', 'rb'))
features = pickle.load(open('./pickel_dumps/features_train_low', 'rb'))

# we keep X_idx2word and y_idx2word the same
# X_left & X_right = X shifted to one and two positions left and right for context2
X, X_vocab_len, X_word_to_ix, X_ix_to_word, y, y_vocab_len, y_word_to_ix, y_ix_to_word, X_left1, X_left2, X_right1, X_right2 = \
    load_data(sentences, rootwords,test=False, context2=True)

# should be all equal for better results
print(len(X))
print(X_vocab_len)
print(len(X_word_to_ix))
print(len(X_ix_to_word))
#print(len(y_word_to_ix))
print(len(y_ix_to_word))


X_max = max([len(word) for word in X])
y_max = max([len(word) for word in y])
X_max_len = max(X_max,y_max)
y_max_len = max(X_max,y_max)

print(X_max_len)
print(y_max_len)

print("Zero padding .. ")
X = pad_sequences(X, maxlen= X_max_len, dtype = 'int32', padding='post')
X_left1 = pad_sequences(X_left1, maxlen = X_max_len, dtype='int32', padding='post')
X_left2 = pad_sequences(X_left2, maxlen = X_max_len, dtype='int32', padding='post')
X_right1 = pad_sequences(X_right1, maxlen = X_max_len, dtype='int32', padding='post')
X_right2 = pad_sequences(X_right2, maxlen = X_max_len, dtype='int32', padding='post')
y = pad_sequences(y, maxlen = y_max_len, dtype = 'int32', padding='post')

print("Compiling Model ..")
model = create_model(X_vocab_len, X_max_len, y_vocab_len, y_max_len,
                     HIDDEN_DIM, LAYER_NUM, context1=False, context2=True)

saved_weights = "./model_weights/multiTask_with_context2.hdf5"

if MODE == 'train':
    print("Training model ..")
    y_sequences = process_data(y, y_max_len, y_word_to_ix)
    hist = model.fit([X, X_left1, X_left2, X_right1, X_right2], [y_sequences], 
        validation_split=0.25, 
        batch_size=BATCH_SIZE, epochs=EPOCHS,  
        callbacks=[EarlyStopping(patience=7),
        ModelCheckpoint('./model_weights/multiTask_with_context2.hdf5', save_best_only=True,
            verbose=1)])

    print(hist.history.keys())
    print(hist)
    plot_model_performance(
        train_loss=hist.history.get('loss', []),
        train_acc=hist.history.get('acc', []),
        train_val_loss=hist.history.get('val_loss', []),
        train_val_acc=hist.history.get('val_acc', [])
    )

                                                                                                                                                                                                                                                                                                    
else:
    if len(saved_weights) == 0:
        print("network hasn't been trained!")
        sys.exit()
    else:
        test_sample_num = 0

        test_sentences = pickle.load(open('./pickel_dumps/sentences_dev', 'rb'))
        test_roots = pickle.load(open('./pickel_dumps/rootwords_dev', 'rb'))
        test_features = pickle.load(open('./pickel_dumps/features_dev', 'rb'))

        #print(test_sentences[:80])
        complete_list,X_test, X_vcab_len, X_wrd_to_ix, X_ix_to_wrd, y_test, y_vcab_len, y_wrd_to_ix, y_ix_to_wrd, X_left1, X_left2, X_right1, X_right2 = \
                load_data(test_sentences, test_roots, test=True, context1=False, context2=True)
        
        X_orig, y_orig= complete_list

        X_test = pad_sequences(X_test, maxlen=X_max_len, dtype='int32', padding='post')
        X_left1 = pad_sequences(X_left1, maxlen=X_max_len, dtype='int32', padding='post')
        X_right1 = pad_sequences(X_right1, maxlen=X_max_len, dtype='int32', padding='post')
        X_left2 = pad_sequences(X_left2, maxlen=X_max_len, dtype='int32', padding='post')
        X_right2 = pad_sequences(X_right2, maxlen=X_max_len, dtype='int32', padding='post')
        y_test = pad_sequences(y_test, maxlen=X_max_len, dtype='int32', padding='post')
        #print(y_test[:80])
        y_test_seq = process_data(y_test, y_max_len, y_word_to_ix)
        #print(y_test_seq)
        model.load_weights(saved_weights)

        plot_model(model, to_file="multi_task_attEnc_arch_with_context2.png", show_shapes=True)

        print(model.evaluate([X_test, X_left1, X_left2, X_right1, X_right2], [y_test_seq]))
        print(model.metrics_names)
        
        words = model.predict([X_test, X_left1, X_left2, X_right1, X_right2])
        
        predictions = np.argmax(words, axis=2)
        
        ######### Post processing of predicted roots ##############
        sequences = []

        for i in predictions:
            test_sample_num += 1

            char_list = []
            for idx in i:
                if idx > 0:
                    char_list.append(y_ix_to_word[idx])

            sequence = ''.join(char_list)
            #print(test_sample_num,":", sequence)
            sequences.append(sequence)

        write_words_to_file(test_roots, sequences)



