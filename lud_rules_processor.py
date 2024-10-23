# LudRule processor

import re
from pathlib import Path
from glob import glob

from tqdm import tqdm
import polars as pl
import pandas as pd

LUD_VAR_RE = r'"[\w\s\(\)\'\/\.\,\:^\-]+"'
GAME_NAME = r'game[\s]+"[\w\s\(\)\'\/\.\,\:^\-]+"'

train_lud_rules_df = pl.read_csv('data/train.csv')

var_nums = {}


def replce_varnames(match: re.Match) -> str:
    raw = match.group(0)
    ind = var_nums.setdefault(raw, len(var_nums)+1)
    if ind > len(var_nums):
        var_nums[raw] = ind
    return " VarName "


lud_files = glob('data/allGames/**', recursive=True)
rules_set = {}
for lud in tqdm(lud_files, total=len(lud_files)):
    if Path(lud).is_file():
        with open(lud, 'r', encoding='utf8') as game_rules:
            game_rule_stripped = ''
            is_new_game = True
            while line := game_rules.readline():
                game_token = re.search(r'game ', line)
                meta_token = re.search(r'metadata', line)
                comment_token = re.search('//', line)
                var_text = re.search(LUD_VAR_RE, line)
                if comment_token is not None:
                    continue
                elif game_token is not None:
                    game_name = var_text.group(0).strip('"')\
                        .rstrip(')')\
                        .replace("'", " ")
                    game_name = re.sub(r' \(', '_', game_name)
                    game_name = game_name.replace(" ", "_")
                    is_in_df = train_lud_rules_df.sql(
                        "SELECT GameRulesetName FROM self WHERE"
                        + f" GameRulesetName = '{game_name}'"
                        )
                    if is_in_df.shape[0] != 0:
                        is_new_game = False
                        break
                    continue
                elif meta_token is not None:
                    break
                else:
                    game_rule_stripped = re.sub(r'[\(\)\{\}]+',
                                                ' ',
                                                game_rule_stripped)
                    game_rule_stripped = line
            if is_new_game:
                game_rule_stripped = re.sub(LUD_VAR_RE,
                                            replce_varnames,
                                            game_rule_stripped)
                rules_set[game_name] = game_rule_stripped
                var_nums = {}

print(len(rules_set))
var_nums = {}

df_rules = train_lud_rules_df.select('LudRules').unique().rows()
for rule in df_rules:
    game_name = re.search(GAME_NAME, rule[0]).group(0)
    game_name = game_name.split(" ", maxsplit=1)[1]
    game_name = re.sub(r"[\(\)']", " ", game_name)
    game_name = game_name.replace(" ", "_").replace('"', ' ')
    game_rule = re.sub(GAME_NAME, " ", rule[0])
    game_rule = re.sub(LUD_VAR_RE, replce_varnames, game_rule)
    var_nums = {}
    is_in_rules = rules_set.get(game_name)
    if is_in_rules is None:
        rules_set[game_name] = game_rule
    else:
        game_name = game_name+'1'
        rules_set[game_name] = game_rule

tokens_set = set()
tokens_records = []

SPLIT_RE = r"[^a-zA-Z0-9]"
for rule in rules_set.values():
    rule = rule.replace('\n', ' ')
    tokens_set |= set(re.split(SPLIT_RE, rule))

concepts_df = pl.read_csv('data/concepts.csv')

names_tuples = concepts_df.select('Name').unique().rows()
names = [i[0] for i in names_tuples]

tokens_set |= set(names)
tokens_set |= set(('(', ')', '{', '}'))

id = 1
tokens_appearance = {}

for token in tokens_set:
    if any((
        len(token) == 0,
        token.isnumeric()
    )):
        continue
    tokens_records.append(
        {'token': token,
         'code': id}
    )
    tokens_appearance[token] = 0
    id += 1

for rule in rules_set.values():
    rule = rule.replace('\n', ' ')
    tokens = re.split(SPLIT_RE, rule)
    for token in tokens:
        if any((
            str(token).isnumeric(),
            token == ''
        )):
            continue
        counter = tokens_appearance.setdefault(token, 0)
        tokens_appearance[token] = counter + 1

print(tokens_appearance)

tokens_stat = []
for name, num in tokens_appearance.items():
    entry = {'token': name,
             'amount': num}
    tokens_stat.append(entry)

tokens_stat_df = pl.from_records(tokens_stat)
tokens_stat_df.write_csv('lud_tokens_stat.csv', float_scientific=False)

# tokens_df = pd.DataFrame.from_records(tokens_records)
# tokens_df.to_csv('lud_tokens.csv', index=False)

# with open('ludii_tokens.dic', 'w', encoding='utf8') as out:
#     for token in tokens_records:
#         line = token['token']+'\n'
#         out.writelines(line)
