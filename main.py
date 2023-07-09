import ray
from ray.rllib.models import ModelCatalog
from t1000.trading_environment import TradingEnvironment
import os
from ray.tune.logger import pretty_print
from ray.tune.registry import get_trainable_cls

def main():
    print("Running")
    ray.init(local_mode=True)

    ModelCatalog.register_custom_model("T-1000", TradingEnvironment)

    # data_frame = get_data_frame()

    config = (
        get_trainable_cls('PPO')
        .get_default_config()
        .environment(TradingEnvironment, env_config={
            'data_frame': {},
        },)
        .framework('torch')
        .rollouts(num_rollout_workers=1)
        .training(
            model={
                "custom_model": "T-1000",
                "vf_share_layers": True,
            }
        )
        # Use GPUs iff `RLLIB_NUM_GPUS` env var set to > 0.
        .resources(num_gpus=int(os.environ.get("RLLIB_NUM_GPUS", "0")))
    )
    config.lr = 1e-3
    algo = config.build()
    for _ in range(50):
        result = algo.train()
        print(pretty_print(result))
    algo.stop()

if __name__ == '__main__':
    main()
