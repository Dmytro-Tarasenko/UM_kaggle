import re

import polars as pl
import pandas as pd
from tqdm import tqdm

df = pl.read_csv('data/train.csv')

eng_rules = df.select('EnglishRules').rows()

eng_tokens_set = set()

for rule in tqdm(eng_rules):
    raw = rule[0]
    raw = re.sub(r'[^a-zA-Z\s]', '', raw)
    splits = raw.lower().split()
    eng_tokens_set |= set(splits)

tokens_records = []
id = 1
for token in eng_tokens_set:
    if any((
        len(token) == 0,
        token.isnumeric()
    )):
        continue
    tokens_records.append(
        {'token': token,
         'code': id}
    )
    id += 1

tokens_df = pd.DataFrame.from_records(tokens_records)
tokens_df.to_csv('eng_tokens.csv', index=False)

with open('eng_tokens.dic', 'w', encoding='utf8') as out:
    for token in tqdm(tokens_records):
        line = token['token']+'\n'
        out.writelines(line)
