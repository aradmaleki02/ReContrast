import torch
import torch.nn as nn
import torch.nn.functional as F


class ReDistill(nn.Module):
    def __init__(
            self,
            encoder,
            bottleneck,
            decoder,
    ) -> None:
        super(ReDistill, self).__init__()
        self.encoder = encoder
        self.encoder.layer4 = None
        self.encoder.fc = None

        self.bottleneck = bottleneck
        self.decoder = decoder

    def forward(self, x):
        en = self.encoder(x)
        de = self.decoder(self.bottleneck(en))
        return en, de

    def train(self, mode=True, encoder_bn_train=False):
        self.training = mode
        if mode is True:
            if encoder_bn_train:
                self.encoder.train(True)
            else:
                self.encoder.train(False)
            self.bottleneck.train(True)
            self.decoder.train(True)
        else:
            self.encoder.train(False)
            self.bottleneck.train(False)
            self.decoder.train(False)
        return self


class ReContrast(nn.Module):
    def __init__(
            self,
            encoder,
            encoder_freeze,
            bottleneck,
            decoder,
    ) -> None:
        super(ReContrast, self).__init__()
        self.encoder = encoder
        self.encoder.layer4 = None
        self.encoder.fc = None

        self.encoder_freeze = encoder_freeze
        self.encoder_freeze.layer4 = None
        self.encoder_freeze.fc = None

        self.bottleneck = bottleneck
        self.decoder = decoder

    def forward(self, x):
        # en = [[1, 256, 64, 64], [1, 512, 32, 32], [1, 1024, 16, 16]]
        en = self.encoder(x)
        
        with torch.no_grad():
            # en_freeze = [[1, 256, 64, 64], [1, 512, 32, 32], [1, 1024, 16, 16]]
            en_freeze = self.encoder_freeze(x)

        # en_2 = [[2, 256, 64, 64], [2, 512, 32, 32], [2, 1024, 16, 16]]
        en_2 = [torch.cat([a, b], dim=0) for a, b in zip(en, en_freeze)]

        # de = [[2, 256, 64, 64],[2, 512, 32, 32], [2, 1024, 16, 16], [2, 256, 64, 64], [2, 512, 32, 32], [2, 1024, 16, 16]]
        # self.bottleneck(en_2) = [[2048, 8, 8], [2048, 8, 8], [2048, 8, 8], [2048, 8, 8]]
        de = self.decoder(self.bottleneck(en_2))
        
        # de = ?
        de = [a.chunk(dim=0, chunks=2) for a in de]
        
        # de=[1,256,64,64], torch.Size([1,512,32,32], [1,1024,16,16], [1,256,64,64], [1,512,32,32], [1,1024,16,16])
        de = [de[0][0], de[1][0], de[2][0], de[3][1], de[4][1], de[5][1]]

        # en_freeze +en = [[1, 256, 64, 64], [1, 512, 32, 32], [1, 1024, 16, 16], [1, 256, 64, 64], [1, 512, 32, 32], [1, 1024, 16, 16]]
        # de=[[1,256,64,64], torch.Size([1,512,32,32], [1,1024,16,16], [1,256,64,64], [1,512,32,32], [1,1024,16,16]]

        return en_freeze + en, de

    def train(self, mode=True, encoder_bn_train=True):
        self.training = mode
        if mode is True:
            if encoder_bn_train:
                self.encoder.train(True)
            else:
                self.encoder.train(False)
            self.encoder_freeze.train(False)  # the frozen encoder is eval()
            self.bottleneck.train(True)
            self.decoder.train(True)
        else:
            self.encoder.train(False)
            self.encoder_freeze.train(False)
            self.bottleneck.train(False)
            self.decoder.train(False)
        return self
