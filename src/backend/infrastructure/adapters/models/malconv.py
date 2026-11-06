"""Gated MalConv with configurable dimensions and MalTorch-compatible weight names.

The original MalTorch default has channels=hidden_size=128, embedding_dim=8,
kernel_size=stride=512 and ReLU; this extends those dimensions without custom code.
"""
import torch
from torch import nn

class MalConv(nn.Module):
    def __init__(self, embedding_dim=8, channels=128, kernel_size=512, stride=512,
                 hidden_size=128, activation="ReLU", padding_idx=256):
        super().__init__()
        self.embedding_1 = nn.Embedding(257, embedding_dim, padding_idx=padding_idx)
        self.conv1d_1 = nn.Conv1d(embedding_dim, channels, kernel_size, stride)
        self.conv1d_2 = nn.Conv1d(embedding_dim, channels, kernel_size, stride)
        self.dense_1 = nn.Linear(channels, hidden_size)
        self.dense_2 = nn.Linear(hidden_size, 1)
        self.activation = getattr(nn, activation)()

    def forward(self, tokens):
        x = self.embedding_1(tokens).transpose(1, 2)
        x = self.activation(self.conv1d_1(x)) * torch.sigmoid(self.conv1d_2(x))
        x = x.amax(dim=2)
        return self.dense_2(self.activation(self.dense_1(x)))
