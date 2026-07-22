#!/usr/bin/env python
"""Train a PPO agent on the Uniswap V3 LP environment, with checkpointing for
spot-instance resumability: if a checkpoint exists in --checkpoint-dir,
training resumes from it (losing at most `checkpoint_save_freq` steps),
instead of starting over.

Usage:
    uv run python scripts/train.py --train-start 2024-05-01 --train-end 2024-06-10 \
        --total-timesteps 5000
"""
import argparse
import json
import re
from collections import deque
from pathlib import Path

import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.utils import LinearSchedule
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecNormalize

from t1000.actions import Action
from t1000.data_loading import load_processed_dataset
from t1000.env import UniswapV3LPEnv
from t1000.metrics import compute_episode_metrics

CHECKPOINT_RE = re.compile(r"ppo_model_(\d+)_steps\.zip$")


def _make_learning_rate(cfg):
    """Linear decay from cfg["learning_rate_start"] to cfg["learning_rate_end"]
    over this invocation's --total-timesteps. Resuming with a new decay
    range is a manual step: edit both values in configs/ppo_default.yaml
    before the next resume."""
    return LinearSchedule(start=cfg["learning_rate_start"], end=cfg["learning_rate_end"], end_fraction=1.0)


def make_env_fn(events_df, gas_df, swaps_df, snapshot_index, start_ts, end_ts, cfg):
    def _init():
        env = UniswapV3LPEnv(
            events_df=events_df,
            gas_df=gas_df,
            swaps_df=swaps_df,
            snapshot_index=snapshot_index,
            start_ts=start_ts,
            end_ts=end_ts,
            episode_hours=cfg["episode_hours"],
            step_hours=cfg["step_hours"],
            initial_notional_usd=cfg["initial_notional_usd"],
        )
        # Monitor wraps the raw (pre-VecNormalize) env, so it reports the
        # un-normalized per-episode return/length that SB3 needs to compute
        # rollout/ep_rew_mean and rollout/ep_len_mean.
        return Monitor(env)

    return _init


# Every field mirrored to TensorBoard as a 100-episode rolling mean, so the
# full runs/episode_metrics.jsonl content is visible live without a separate
# script -> TensorBoard tag name.
TB_METRIC_NAMES = {
    "episode_pnl_usd": "ep_pnl_usd_mean",
    "sharpe_ratio": "ep_sharpe_mean",
    "max_drawdown": "ep_drawdown_mean",
    "gas_adjusted_apr": "ep_gas_adjusted_apr_mean",
    "episode_gas_cost_usd": "ep_gas_cost_mean",
    "rebalance_count": "ep_rebalance_count_mean",
}


class EpisodeMetricsCallback(BaseCallback):
    """Logs one JSONL row per completed episode per sub-env: episode P&L,
    Sharpe ratio, max drawdown, gas-adjusted APR (see metrics.py), cumulative
    gas cost, and rebalance count. Every one of those is also mirrored to
    TensorBoard as a rolling mean (see TB_METRIC_NAMES), since the default
    SB3 scalars (ep_rew_mean, entropy_loss, ...) don't cover P&L or gas/
    rebalance behavior."""

    def __init__(self, log_path, step_hours: float, verbose: int = 0):
        super().__init__(verbose)
        self.log_path = Path(log_path)
        self.step_hours = step_hours
        self._histories: dict = {}
        self._gas_histories: dict = {}
        self._rebalance_counts: dict = {}
        self._recent = {name: deque(maxlen=100) for name in TB_METRIC_NAMES}

    def _on_step(self) -> bool:
        infos = self.locals.get("infos", ())
        dones = self.locals.get("dones", ())
        actions = self.locals.get("actions", ())
        for i, info in enumerate(infos):
            pv = info.get("portfolio_value_usd")
            if pv is not None:
                self._histories.setdefault(i, []).append(pv)
                self._gas_histories.setdefault(i, []).append(info.get("gas_cost_usd", 0.0))
                if i < len(actions) and int(actions[i]) != Action.HOLD:
                    self._rebalance_counts[i] = self._rebalance_counts.get(i, 0) + 1
            if i < len(dones) and dones[i]:
                history = self._histories.pop(i, [])
                gas_history = self._gas_histories.pop(i, [])
                rebalance_count = self._rebalance_counts.pop(i, 0)
                if len(history) > 1:
                    metrics = compute_episode_metrics(history, self.step_hours)
                    metrics["timesteps"] = int(self.num_timesteps)
                    metrics["env_index"] = i
                    metrics["episode_gas_cost_usd"] = float(sum(gas_history))
                    metrics["rebalance_count"] = rebalance_count
                    with open(self.log_path, "a") as f:
                        f.write(json.dumps(metrics) + "\n")

                    for field, tb_name in TB_METRIC_NAMES.items():
                        self._recent[field].append(metrics[field])
                        values = self._recent[field]
                        self.logger.record(f"rollout/{tb_name}", sum(values) / len(values))
        return True


def find_latest_checkpoint(checkpoint_dir: Path):
    """Returns (model_path, vecnormalize_path, step_count) for the highest-step
    checkpoint found, or None if no checkpoint exists."""
    candidates = []
    for path in checkpoint_dir.glob("ppo_model_*_steps.zip"):
        m = CHECKPOINT_RE.search(path.name)
        if m:
            candidates.append((int(m.group(1)), path))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    steps, model_path = candidates[-1]
    vecnorm_path = checkpoint_dir / f"ppo_model_vecnormalize_{steps}_steps.pkl"
    return model_path, vecnorm_path, steps


def build_model_or_resume(vec_env, cfg, checkpoint_dir: Path, tensorboard_log: str):
    found = find_latest_checkpoint(checkpoint_dir)
    if found is not None:
        model_path, vecnorm_path, steps = found
        print(f"Resuming from checkpoint at step {steps}: {model_path}")
        vec_env = VecNormalize.load(str(vecnorm_path), vec_env)
        # Hyperparameters below are re-read from cfg (not restored from the
        # checkpoint) so that editing configs/ppo_default.yaml and resuming
        # actually takes effect. net_arch/policy_kwargs are deliberately
        # excluded: the architecture is fixed once trained, overriding it
        # here would break loading the saved weights.
        model = PPO.load(
            str(model_path),
            env=vec_env,
            device=cfg["device"],
            tensorboard_log=tensorboard_log,
            learning_rate=_make_learning_rate(cfg),
            n_steps=cfg["n_steps"],
            batch_size=cfg["batch_size"],
            n_epochs=cfg["n_epochs"],
            gamma=cfg["gamma"],
            gae_lambda=cfg["gae_lambda"],
            clip_range=cfg["clip_range"],
            ent_coef=cfg["ent_coef"],
        )
        return model, vec_env, False

    print("No checkpoint found, starting fresh training run.")
    vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=True)
    model = PPO(
        cfg["policy"],
        vec_env,
        n_steps=cfg["n_steps"],
        batch_size=cfg["batch_size"],
        n_epochs=cfg["n_epochs"],
        gamma=cfg["gamma"],
        gae_lambda=cfg["gae_lambda"],
        clip_range=cfg["clip_range"],
        ent_coef=cfg["ent_coef"],
        learning_rate=_make_learning_rate(cfg),
        policy_kwargs=dict(net_arch=cfg["net_arch"]),
        device=cfg["device"],
        tensorboard_log=tensorboard_log,
        verbose=1,
    )
    return model, vec_env, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/ppo_default.yaml")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--train-start", required=True)
    parser.add_argument("--train-end", required=True)
    parser.add_argument("--total-timesteps", type=int, required=True)
    parser.add_argument("--checkpoint-dir", default="checkpoints")
    parser.add_argument("--log-dir", default="runs")
    parser.add_argument("--n-envs", type=int, default=None)
    parser.add_argument("--subproc", action="store_true", help="use SubprocVecEnv instead of DummyVecEnv")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    n_envs = args.n_envs or cfg["n_envs"]

    checkpoint_dir = Path(args.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    print("Loading processed dataset...")
    events_df, gas_df, swaps_df, snapshot_index = load_processed_dataset(args.processed_dir)
    print(f"  {len(events_df):,} events, {len(snapshot_index.entries)} snapshots")

    env_fns = [
        make_env_fn(events_df, gas_df, swaps_df, snapshot_index, args.train_start, args.train_end, cfg)
        for _ in range(n_envs)
    ]
    vec_env_cls = SubprocVecEnv if args.subproc else DummyVecEnv
    vec_env = vec_env_cls(env_fns)

    tensorboard_log = str(log_dir / "tensorboard")
    model, vec_env, is_fresh = build_model_or_resume(vec_env, cfg, checkpoint_dir, tensorboard_log)

    checkpoint_cb = CheckpointCallback(
        save_freq=max(cfg["checkpoint_save_freq"] // n_envs, 1),
        save_path=str(checkpoint_dir),
        name_prefix="ppo_model",
        save_vecnormalize=True,
    )
    metrics_cb = EpisodeMetricsCallback(log_dir / "episode_metrics.jsonl", cfg["step_hours"])

    model.learn(
        total_timesteps=args.total_timesteps,
        callback=[checkpoint_cb, metrics_cb],
        reset_num_timesteps=is_fresh,
    )

    model.save(str(checkpoint_dir / "ppo_model_final"))
    print(f"Training complete. Final model saved to {checkpoint_dir / 'ppo_model_final.zip'}")


if __name__ == "__main__":
    main()
