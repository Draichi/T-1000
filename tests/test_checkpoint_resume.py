from datetime import timedelta

from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv

from scripts.train import build_model_or_resume, find_latest_checkpoint, make_env_fn
from tests.test_env import BASE_TS, N_HOURS, _build_synthetic_dataset

TEST_CFG = {
    "policy": "MlpPolicy",
    "net_arch": [16, 16],
    "n_steps": 32,
    "batch_size": 16,
    "n_epochs": 2,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.01,
    "learning_rate_start": 3e-4,
    "learning_rate_end": 1e-5,
    "device": "cpu",
    "episode_hours": 24,
    "step_hours": 1.0,
    "initial_notional_usd": 10_000.0,
}


def test_checkpoint_resume_continues_training(tmp_path):
    events_df, gas_df, swaps_df, index = _build_synthetic_dataset(tmp_path / "data")
    start_ts = BASE_TS
    end_ts = BASE_TS + timedelta(hours=N_HOURS)

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()

    def make_vec_env():
        env_fn = make_env_fn(events_df, gas_df, swaps_df, index, start_ts, end_ts, TEST_CFG)
        return DummyVecEnv([env_fn])

    vec_env = make_vec_env()
    model, vec_env, is_fresh = build_model_or_resume(vec_env, TEST_CFG, checkpoint_dir, tensorboard_log=None)
    assert is_fresh
    assert find_latest_checkpoint(checkpoint_dir) is None

    checkpoint_cb = CheckpointCallback(
        save_freq=32, save_path=str(checkpoint_dir), name_prefix="ppo_model", save_vecnormalize=True
    )
    model.learn(total_timesteps=64, callback=checkpoint_cb, reset_num_timesteps=is_fresh)

    found = find_latest_checkpoint(checkpoint_dir)
    assert found is not None
    model_path, vecnorm_path, steps = found
    assert steps >= 32
    assert model_path.exists()
    assert vecnorm_path.exists()

    # Simulate a spot-instance restart: fresh process state, load from checkpoint.
    vec_env2 = make_vec_env()
    model2, vec_env2, is_fresh2 = build_model_or_resume(vec_env2, TEST_CFG, checkpoint_dir, tensorboard_log=None)
    assert not is_fresh2
    assert model2.num_timesteps == steps

    model2.learn(total_timesteps=32, callback=checkpoint_cb, reset_num_timesteps=is_fresh2)
    assert model2.num_timesteps > steps
