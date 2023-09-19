import os
import re
import csv
import json
import datasets

_DESCRIPTION = "Spanish articles from WikiHow"
_HOMEPAGE = "https://www.wikihow.com"
_LICENSE  = "CC BY-NC-SA 3.0"
_VERSION = "1.1.0"

_DATAPATH = "wikihow_es.jsonl"

_CATEGORIES = [
    "salud",
    "viajes",
    "deportes",
    "relaciones",
    "pasatiempos",
    "adolescentes",
    "vida-familiar",
    "en-el-trabajo",
    "comida-y-diversión",
    "finanzas-y-negocios",
    "mascotas-y-animales",
    "carreras-y-educación",
    "filosofía-y-religión",
    "arte-y-entretenimiento",
    "en-la-casa-y-el-jardín",
    "cuidado-y-estilo-personal",
    "computadoras-y-electrónica",
    "días-de-fiesta-y-tradiciones",
    "automóviles-y-otros-vehículos",
]

def format_methods(methods, short=False):
    EOL = "\n" if short else "\n\n"
    formatted = []
    for method in methods:
        if method["title"].lower() != "pasos":
            content = f"Método {method['number']}: {method['title']}{EOL}"
        else:
            content = f"Sigue los siguientes pasos:{EOL}"
        for step in method["steps"]:
            step_content = re.sub(r"\n+", "\n", step).strip()
            if short:
                step_content = step_content.split("\n")[0]
            content += step_content + EOL
        formatted.append(content.strip())
    return formatted


class WikiHowEs(datasets.GeneratorBasedBuilder):
    """ WikiHowEs: Collection of Spanish tutorials. """

    VERSION = datasets.Version(_VERSION)

    DEFAULT_CONFIG_NAME = "all"
    BUILDER_CONFIGS = [datasets.BuilderConfig(name="all", version=VERSION, description="All articles from WikiHow-ES.")]
    for _CAT in _CATEGORIES:
        BUILDER_CONFIGS.append(
            datasets.BuilderConfig(name=_CAT, version=VERSION, description=f"Articles from the category {_CAT}")
        )

    @staticmethod
    def _info():
        features = datasets.Features(
            {
                "category": datasets.Value("string"),
                "question": datasets.Value("string"),
                "introduction": datasets.Value("string"),
                "answers": datasets.features.Sequence(datasets.Value("string")),
                "short_answers": datasets.features.Sequence(datasets.Value("string")),
                "url": datasets.Value("string"),
                "num_answers": datasets.Value("int32"),
                "num_refs": datasets.Value("int32"),
                "expert_author": datasets.Value("bool"),
            }
        )
        return datasets.DatasetInfo(
            description=_DESCRIPTION,
            features=features,
            homepage=_HOMEPAGE,
            license=_LICENSE,
        )

    @staticmethod
    def _split_generators(dl_manager):
        data_dir = dl_manager.download_and_extract(_DATAPATH)
        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={
                    "filepath": data_dir,
                },
            ),
        ]

    def _generate_examples(self, filepath):
        with open(filepath, encoding="utf-8") as f:
            for key, row in enumerate(f):
                data = json.loads(row)
                if self.config.name in ["all", data["category"].lower()]:
                    yield key, {
                        "category": data["category"],
                        "question": f"¿{data['title']}?",
                        "introduction": data["intro"],
                        "answers": format_methods(data["methods"], short=False),
                        "short_answers": format_methods(data["methods"], short=True),
                        "num_answers": data["num_methods"],
                        "num_refs": data["num_refs"],
                        "expert_author": data["expert_author"],
                        "url": data["url"],
                    }