import torch
import torch.nn as nn
from typing import Dict, Callable
from torch.utils.data import DataLoader

class ExperienceReplay:
    def __init__(self, capacity: int = 10):
        self.capacity = capacity
        self.buffer = []

    def push(self, data, target):
        if len(self.buffer) >= self.capacity:
            self.buffer.pop(0)
        self.buffer.append((data, target))

    def sample(self, batch_size: int):
        if len(self.buffer) < batch_size:
            return None
        import random
        batch = random.sample(self.buffer, batch_size)
        return torch.stack([x[0] for x in batch]), torch.stack([x[1] for x in batch])

    def __len__(self):
        return len(self.buffer)

class ElasticWeightConsolidation:
    def __init__(self, model: nn.Module, importance: float = 1e4):
        self.model = model
        self.importance = importance
        self.fisher = {}
        self.optimal_params = {n: p.clone() for n, p in self.model.named_parameters()}
        self._has_fisher = False

    def compute_fisher(
        self,
        reference_loader: DataLoader,
        criterion: Callable[[torch.Tensor, torch.Tensor], torch.Tensor],
        device: str = "cpu",
    ) -> Dict[str, torch.Tensor]:
        self.model.eval()
        fisher_new = {}

        for inputs, targets in reference_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = self.model(inputs)
            loss = criterion(outputs, targets)

            self.model.zero_grad()
            loss.backward(retain_graph=False)

            batch_size_actual = inputs.size(0)
            for name, param in self.model.named_parameters():
                if param.grad is None:
                    continue
                # E[g_i²] ≈ B * E[(grad_mean)²]  (correção por amostras)
                grad_sq = param.grad.detach().clone() ** 2 * batch_size_actual
                if name not in fisher_new:
                    fisher_new[name] = grad_sq
                else:
                    fisher_new[name] += grad_sq

        n_samples = max(1, len(reference_loader.dataset))
        for name in fisher_new:
            fisher_new[name] /= n_samples

        self.fisher = fisher_new
        self._has_fisher = True
        return self.fisher

    def ewc_loss(self, device="cpu"):
        loss = torch.tensor(0.0, device=device)
        for name, param in self.model.named_parameters():
            if name in self.fisher:
                loss += (self.fisher[name].to(device) * (param - self.optimal_params[name].to(device)).pow(2)).sum()
        return self.importance * loss

class ContinualLearningAgent:
    pass
