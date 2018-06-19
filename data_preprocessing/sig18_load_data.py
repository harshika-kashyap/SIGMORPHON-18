import pickle 
from nltk import FreqDist
import numpy as np
from collections import deque
from sklearn import preprocessing

MAX_LEN = 20
VOCAB_SIZE = 65
VOCAB_SIZE_WORDS = 30000
msd2id = []
le = preprocessing.LabelEncoder()

def getIndexedWords(X_unique, y_unique, orig=False):
    X_un = [list(x) for x,w in zip(X_unique, y_unique) if len(x) > 0 and len(w) > 0]

    X = X_un

    # build a vocabulary of most frequent characters
    dist = FreqDist(np.hstack(X))
    X_vocab = dist.most_common(89)
    
    # Remove erroneous characters
    for i in X_vocab:
        if i[0] == '\u200d' or i[0] == '\u200b':
            X_vocab.remove(i)

    X_idx2word = [letter[0] for letter in X_vocab]
    X_idx2word.insert(0, 'ZERO') # 'Z' is the starting token
    X_idx2word.append('UNK') # 'U' for out-of-vocab characters
    
    # create letter-to-index mapping
    X_word2idx =  {letter:idx for idx, letter in enumerate(X_idx2word)}

    for i, word in enumerate(X):
        for j, char in enumerate(word):
            if char in X_word2idx:
                X[i][j] = X_word2idx[char]
            else:
                X[i][j] = X_word2idx['UNK']

    if orig == True:
        return X, X_un, X_vocab, X_word2idx, X_idx2word
    else:
        return X

def getIndexedfeatures(X_msd):
    le.fit(X_msd)
    msd2id = list(le.transform(X_msd))
    return msd2id

def load_data(test= False, context1=False, context2=False, context3=False):    
    sentences = pickle.load(open('sentences_train_low', 'rb'))
    rootwords = pickle.load(open('rootwords_train_low', 'rb'))
    features = pickle.load(open('features_train_low', 'rb'))
    
    X_unique = [item for sublist in rootwords for item in sublist]
    X_msd = [item for sublist in features for item in sublist]
    y_unique = [item for sublist in sentences for item in sublist]
    
    X_msd = getIndexedfeatures(X_msd)
    complete_list = [X_unique, X_msd, y_unique]
    # process vocab indexing for X in the function since we will need to call it multiple times
    X, X_un, X_vocab, X_word2idx, X_idx2word = getIndexedWords(X_unique, y_unique, orig=True)
    
    # process vocab indexing for y here, since only single processing required
    y_un = [list(w) for x,w in zip(X_unique, y_unique) if len(x) > 0 and len(w) > 0]    
    y = y_un
        
    for i, word in enumerate(y):
        for j, char in enumerate(word):
            if char in X_word2idx:
                y[i][j] = X_word2idx[char]
            else:
                y[i][j] = X_word2idx['UNK']
         
    # consider a context of 1 word right and left each
    # make two lists by shifting the elements
    if context1 == True or context2 == True or context3 == True: 
        X_left = deque(X_unique)
        X_left_msd = deque(X_msd)  
        
        X_left.append(' ') # all elements would be shifted one left
        X_left.popleft()
        X_left1 = list(X_left)
        X_left1 = getIndexedWords(X_left1, y_unique, orig=False)
        
        X_left_msd.append(' ') # all elements would be shifted one left
        X_left_msd.popleft()
        X_left1_msd = list(X_left_msd)

        
        X_left.append(' ')
        X_left.popleft()
        X_left2 = list(X_left)
        X_left2 = getIndexedWords(X_left2, y_unique, orig=False)
        
        X_left_msd.append(' ') # all elements would be shifted one left
        X_left_msd.popleft()
        X_left2_msd = list(X_left_msd)
        
        X_left.append(' ')
        X_left.popleft()
        X_left3 = list(X_left)
        X_left3 = getIndexedWords(X_left3, y_unique, orig=False)
        
        X_left_msd.append(' ') # all elements would be shifted one left
        X_left_msd.popleft()
        X_left3_msd = list(X_left_msd)
    
        X_right = deque(X_unique)
        X_right_msd = deque(X_msd)
        
        X_right.appendleft(' ') 
        X_right.pop()
        X_right1 = list(X_right)
        X_right1 = getIndexedWords(X_right1, y_unique, orig=False)
    
        X_right_msd.appendleft(' ') 
        X_right_msd.pop()
        X_right1_msd = list(X_right_msd)
        
        X_right.appendleft(' ')
        X_right.pop()
        X_right2 = list(X_right)
        X_right2 = getIndexedWords(X_right2, y_unique, orig=False)
    
        X_right_msd.appendleft(' ') 
        X_right_msd.pop()
        X_right2_msd = list(X_right_msd)
        
        X_right.appendleft(' ')
        X_right.pop()
        X_right3 = list(X_right)
        X_right3 = getIndexedWords(X_right3, y_unique, orig=False)
        
        X_right_msd.appendleft(' ') 
        X_right_msd.pop()
        X_right3_msd = list(X_right_msd)
            
        if context1 == True:
            if test == True:
                complete_list = [X_un, X_msd, y_un]
                return (complete_list, X, len(X_vocab)+2, X_word2idx, X_idx2word, y, len(X_vocab)+2, 
                        X_word2idx, X_idx2word, X_left, X_right, X_left_msd, X_right_msd)
            else:
                return (X, len(X_vocab)+2, X_word2idx, X_idx2word, y, len(X_vocab)+2, X_word2idx,
                        X_idx2word, X_left, X_right, X_left_msd, X_right_msd)
    
        elif context2 == True:
            if test == True:
                complete_list = [X_un, X_msd, y_un]
                return (complete_list, X, len(X_vocab)+2, X_word2idx, X_idx2word, y, 
                        len(X_vocab)+2, X_word2idx, X_idx2word, X_left1, X_left2, X_right1, X_right2,
                        X_left1_msd, X_left2_msd, X_right1_msd, X_right2_msd)
            else:
                return (X, len(X_vocab)+2, X_word2idx, X_idx2word, y, len(X_vocab)+2, 
                        X_word2idx, X_idx2word, X_left1, X_left2, X_right1, X_right2, X_left1_msd,
                        X_left2_msd, X_right1_msd, X_right2_msd)
    
        elif context3 == True:
            if test == True:
                complete_list = [X_un, X_msd, y_un]
                return (complete_list, X, len(X_vocab)+2, X_word2idx, X_idx2word, y, 
                        len(X_vocab)+2, X_word2idx, X_idx2word, X_left1, X_left2, X_left3, X_right1, 
                        X_right2, X_right3, X_left1_msd, X_left2_msd, X_left3_msd, X_right1_msd, X_right2_msd, X_right3_msd)
            else:
                return (X, len(X_vocab)+2, X_word2idx, X_idx2word, y, len(X_vocab)+2, 
                        X_word2idx, X_idx2word, X_left1, X_left2, X_left3, X_right1, X_right2, X_right3,
                        X_left1_msd, X_left2_msd, X_left3_msd, X_right1_msd, X_right2_msd, X_right3_msd)
    else:
        if test == True:
            complete_list = [X_un, X_msd, y_un]
            return (complete_list, X, len(X_vocab)+2, X_word2idx, X_idx2word, y, len(X_vocab)+2, X_word2idx, X_idx2word)
        else:
            return (X, len(X_vocab)+2, X_word2idx, X_idx2word, y, len(X_vocab)+2, X_word2idx, X_idx2word)
            
    
X, X_vocab_len, X_word_to_ix, X_ix_to_word, y, y_vocab_len, y_word_to_ix, y_ix_to_word, X_left, X_right, X_left_msd, X_right_msd = load_data(context1 = True)
