import torch
from torch import nn
from torch.utils.data import Dataset

class MatchSequenceDataset(Dataset):
    def __init__(self, x, y):
        self.x = torch.as_tensor(x, dtype=torch.float32)
        self.y = torch.as_tensor(y, dtype=torch.float32)
    def __len__(self):
        return len(self.y)
    def __getitem__(self, index):
        return self.x[index], self.y[index]

class RecurrentRegressor(nn.Module):
    def __init__(self, input_size, kind='lstm', hidden=32):
        super().__init__()
        if kind not in {'lstm', 'gru'}:
            raise ValueError('Expected lstm or gru')
        self.rnn = (nn.LSTM if kind == 'lstm' else nn.GRU)(input_size, hidden, batch_first=True)
        self.head = nn.Linear(hidden, 1)
    def forward(self, x):
        output, _ = self.rnn(x)
        return self.head(output[:, -1]).squeeze(-1)
