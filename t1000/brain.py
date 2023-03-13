class Brain:
    def __init__(self, learning_rate, algorithm='PPO', num_workers=2) -> None:
        self.algorithm = algorithm
        self.num_workers = num_workers
        self.learning_schedule = learning_rate

    @staticmethod
    def rollout():
        pass

    def train(self) -> None:
        pass

    def test(self) -> None:
        pass

    def trial_name_string(self) -> str:
        return 'trial-' + self.algorithm

    def get_instruments_from_checkpoint(self):
        pass
