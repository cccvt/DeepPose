import torch.nn as nn
import torch.nn.functional as F

import sys
sys.path.append("./")
from modules.models.pytorch.ReLU6_ import ReLU6_


class Discriminator(nn.Module):

    def __init__(self):
        super(Discriminator, self).__init__()

        self.conv = nn.Sequential(
            nn.Conv2d(14, 96, 3, stride=2, bias=False),
            nn.BatchNorm2d(96),
            nn.LeakyReLU(0.2, inplace=True),

            nn.Conv2d(96, 256, 3, padding=2, bias=False),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.2, inplace=True),

            nn.Conv2d(256, 384, 3, bias=False),
            nn.BatchNorm2d(384),
            nn.LeakyReLU(0.2, inplace=True),

            nn.Conv2d(384, 384, 3, bias=False),
            nn.BatchNorm2d(384),
            nn.LeakyReLU(0.2, inplace=True),

            nn.Conv2d(384, 256, 3, bias=False),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.2, inplace=True),
        )
        self.last = nn.Sequential(
            nn.Conv2d(256, 1, 2, bias=False),
            nn.Sigmoid()
        )

        #self.linear = nn.Linear(256*2*2, 1)
        '''
        self.conv1 = nn.Conv2d(14, 96, 3, stride=2)
        self.conv2 = nn.Conv2d(96, 256, 3, padding=2)
        self.conv3 = nn.Conv2d(256, 384, 3)
        self.conv4 = nn.Conv2d(384, 384, 3)
        self.conv5 = nn.Conv2d(384, 256, 3)
        self.bn1 = nn.BatchNorm2d(96)
        '''

    def forward(self, x):

        #x = self.conv1(x)
        #x = self.bn1(x)
        #x = self.conv2(x)
        #x = self.conv3(x)
        #x = self.conv4(x)
        #x = self.conv5(x)
        x = self.conv(x)
        x = self.last(x)

        #x = x.view(-1, 256*2*2)
        #x = F.dropout(x, training=self.training)
        #x = self.linear(x)
        return x.squeeze()
