import json
import pandas as pd

def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_corpus():
    texts = []
    intents = []
    training_files = [
        'data/processed/base-corpus.json',
        'data/processed/rhcp-corpus.json'
    ]
    for file_path in training_files:
        corpus = load_json_file(file_path)
        for item in corpus['data']:
            if item['intent'] != 'None':
                for utterance in item['utterances']:
                    texts.append(utterance)
                    intents.append(item['intent'])
    return texts, intents

texts, intents = load_corpus()
df = pd.DataFrame({'text': texts, 'intent': intents})
print(f"Loaded {len(df)} samples.")
df.head()