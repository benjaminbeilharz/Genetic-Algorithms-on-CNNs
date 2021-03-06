# coding utf-8
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
"""
Defines layers used in networks
"""


class ConvolutionBlock(nn.Module):
    """
    Convolution block defined by encoding

    Args:
        nn (CNN): Convolution block
    """
    def __init__(self, c_in: int, c_out: int, device: torch.device):
        """
        Initialize ConvolutionBlock

        Args:
            c_in (int): Input channels
            c_out (int): Output channels
            device (torch.device): Device to move model to
        """
        super(ConvolutionBlock, self).__init__()
        self.c_in = c_in
        self.c_out = c_out
        self.device = device
        self.filter_size = (3, 3)
        self.conv_stride = (1, 1)
        self.conv = nn.Conv2d(self.c_in, self.c_out, self.filter_size,
                              self.conv_stride, 1)
        self.bn = nn.BatchNorm2d(self.c_out)
        self.relu = nn.ReLU()

    def padding(self, x: Tensor) -> Tensor:
        """
        Calculates padding sizes

        Args:
            x (Tensor): Input Tensor

        Returns:
            Tensor: Torch Tensor
        """
        in_height, in_width = x.shape[2:]
        filter_height, filter_width = 3, 3
        strides = (None, 1, 1)
        #The total padding applied along the height and width is computed as:

        if (in_height % strides[1] == 0):
            pad_along_height = max(filter_height - strides[1], 0)
        else:
            pad_along_height = max(filter_height - (in_height % strides[1]), 0)
        if (in_width % strides[2] == 0):
            pad_along_width = max(filter_width - strides[2], 0)
        else:
            pad_along_width = max(filter_width - (in_width % strides[2]), 0)

        #Finally, the padding on the top, bottom, left and right are:

        pad_top = pad_along_height // 2
        pad_bottom = pad_along_height - pad_top
        pad_left = pad_along_width // 2
        pad_right = pad_along_width - pad_left

        return F.pad(x, (pad_left, pad_right, pad_top, pad_bottom)).to(
            self.device)

    def forward(self, x: Tensor):
        x = x.to(self.device)
        x = self.padding(x).to(self.device)
        out = self.conv(x)
        out = self.bn(out)
        out = self.relu(out)
        return out


class ModelFromDecoding(nn.Module):
    """
    String decoder which builds nn
    """
    def __init__(self, encoding: str, device: torch.device):
        """Initialization

        Args:
            encoding (str): String reprensentation of NN
            device (torch.device): Device to put model on
        """
        super(ModelFromDecoding, self).__init__()
        self.device = device
        self.architecture = []
        self.enc = encoding

        self.kernel_size = self.pool_stride = (2, 2)
        self._decode()
        self.softmax = nn.Softmax(0)

        self.net = nn.Sequential(*self.architecture)

    def _decode(self):
        """
        Decodes string and creates architecture
        """
        prev = 16
        conv = ConvolutionBlock(3, prev, self.device)
        self.architecture.append(conv)
        for m in self.enc.split('-'):
            if m == '-': continue
            m = float(m) if '.' in m else int(m)
            if isinstance(m, int):
                conv = ConvolutionBlock(prev, m, self.device)
                prev = m
                self.architecture.append(conv)
            if isinstance(m, float):
                pool = nn.MaxPool2d(self.kernel_size, self.pool_stride,
                                    (1, 1)) if m > 0.5 else nn.AvgPool2d(
                                        self.kernel_size, self.pool_stride,
                                        (1, 1))
                self.architecture.append(pool)

    def forward(self, x):
        x = self.net(x).to(self.device)
        dim = x.shape[1] * x.shape[2] * x.shape[3]
        x = x.view(-1, dim).to(self.device)
        fc = nn.Linear(x.shape[-1],
                       10).to(self.device)  # to project dims onto n-classes
        return F.relu(fc(x)).to(self.device)
