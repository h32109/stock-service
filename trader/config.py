import os
import pathlib
import logging

import dynaconf

get_env = os.environ.get

logger = logging.getLogger("trader")


def init_config(
        service_name: str = "trader",
        default_file_name: str = "default.toml"
):
    """
    # Usage
    ```
    settings = init_config()
    settings.SECRET.KEY # Use uppercase
    ```
    """

    source_dir = pathlib.Path(os.path.dirname(__file__)).parent.absolute()
    file_path = os.path.join(source_dir, "config", service_name)

    os.chdir(file_path)
    env = get_env("TRADER", "local")

    try:
        conf = dynaconf.Dynaconf(
            preload=[os.path.join(file_path, default_file_name)],
            settings_files=[os.path.join(file_path, file) for file in os.listdir()],
            environments=["local", "dev", "prod", "test"],
            env=env,
            load_dotenv=False,
            merge_enabled=True,
        )
    except Exception as e:
        raise AssertionError(f"Failed to load configuration because of \n {e}")
    return conf


if __name__ == "__main__":
    conf = init_config()
    print(conf.ELASTICSEARCH.HOSTS)
