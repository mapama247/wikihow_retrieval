import os
import re
import json
import pandas as pd
from glob import glob

DATA_DIR = "./output_final"

def format_methods(methods):
    formatted = []
    for method in methods:
        if method["title"].lower() != "pasos":
            content = f"Método {method['number']}: {method['title']}\n\n"
            for step in method["steps"]:
                step_content = re.sub(r"\n+", "\n", step).strip()
                content += step_content + "\n\n"
        else:
            content = "Sigue los siguientes pasos:\n\n"
            for step in method["steps"]:
                step_content = re.sub(r"\n+", "\n", step).strip()
                content += step_content + "\n\n"
        formatted.append(content.strip())
    return formatted

data_files = glob(os.path.join(DATA_DIR, "wikihow_es_*.jsonl"))

dfs = []
for data_file in data_files:
    category = data_file.split(".")[-2].split("_")[-1]
    language = data_file.split(".")[-2].split("_")[-2]
    curr_df = pd.read_json(data_file, lines=True)
    curr_df["language"] = language
    curr_df["category"] = category
    dfs.append(curr_df)

df = pd.concat(dfs, ignore_index=False)
df = df[["language", "category", "url", "title", "intro", "methods", "num_methods", "is_steps", "expert_author", "num_refs"]]

aux_bool = True
while aux_bool:
    df = df.sample(frac=1)
    import pdb; pdb.set_trace()

# df["content"] = df["methods"].apply(lambda x: format_methods(x)) # better to do this directly in the dataloader
df["num_refs"] = df["num_refs"].fillna(0)
df["num_refs"] = df["num_refs"].astype(int)

out_filename = os.path.join(DATA_DIR, "wikihow_es.jsonl")

list_dicts = df.to_dict("records")
with open(out_filename, "w") as f:
    f.write('\n'.join(json.dumps(i, ensure_ascii=False) for i in list_dicts))