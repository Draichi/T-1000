import os
import pickle

def find_results_folder():
    return os.getcwd() + '/results'


def get_instruments_from_checkpoint(checkpoint):
    config = {}
    # Load configuration from file
    config_dir = os.path.dirname(checkpoint)
    config_path = os.path.join(config_dir, "params.pkl")
    if not os.path.exists(config_path):
        config_path = os.path.join(config_dir, "../params.pkl")
    if not os.path.exists(config_path):
        raise ValueError(
            "Could not find params.pkl in either the checkpoint dir or "
            "its parent directory.")
    else:
        with open(config_path, "rb") as f:
            config = pickle.load(f)
    if config['env_config']:
        env_config = config['env_config']
        if env_config['assets']:
            assets = env_config['assets']
        else:
            raise ValueError('assets does not exists in env_config')
        if env_config['currency']:
            currency = env_config['currency']
        else:
            raise ValueError('currency does not exists in env_config')
        if env_config['datapoints']:
            datapoints = env_config['datapoints']
        else:
            raise ValueError('datapoints does not exists in env_config')
        if env_config['granularity']:
            granularity = env_config['granularity']
        else:
            raise ValueError('granularity does not exists in env_config')
    else:
        raise ValueError('env_config does not exists in params.pkl')
    if "num_workers" in config:
        config["num_workers"] = min(2, config["num_workers"])
    return config, assets, currency, datapoints, granularity
