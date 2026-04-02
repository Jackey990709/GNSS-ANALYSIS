import os

import yaml

from src.util.const import LocalPath
from src.util.param import parameters


def read_yml(folder_path=LocalPath.LOCAL_FOLDER_PATH, filename=LocalPath.YAML_FILE):
    with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def write_yml(
    param, folder_path=LocalPath.LOCAL_FOLDER_PATH, filename=LocalPath.YAML_FILE
):
    with open(os.path.join(folder_path, filename), "w", encoding="utf-8") as f:
        return yaml.dump(
            param, f, default_flow_style=False, encoding="utf-8", allow_unicode=True
        )


if os.path.exists(LocalPath.YAML_FILE):
    parameters.update(read_yml())
else:
    if not os.path.exists(LocalPath.LOCAL_FOLDER_PATH):
        os.makedirs(LocalPath.LOCAL_FOLDER_PATH)
    write_yml(parameters)
