# -*- coding: utf-8 -*-
""" Mean squared error function. """

import torch.nn as nn
import torch
import numpy as np
from torch.autograd import Variable
import scipy.ndimage.filters as fi

class MeanSquaredError2__(nn.Module):
    """ Mean squared error (a.k.a. Euclidean loss) function. """

    def __init__(self, use_visibility=False, Nj=14, col=14):
        super(MeanSquaredError2__, self).__init__()
        self.use_visibility = use_visibility
        self.Nj = Nj
        self.col = col
        self.gaussian = 1.0
        self.m = torch.Tensor([0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,1.0,1.0]).cuda()

    def min_max(self, x, axis=None):
        min = x.min(axis=axis, keepdims=True)
        max = x.max(axis=axis, keepdims=True)
        result = (x-min)/(max-min)
        return torch.Tensor(result)

    def min_max_(self, x, dim=1):
        min = x.min(dim=1).float()
        max = x.max(dim=1).float()
        result = (x-min)/(max-min)
        return result

    def checkMatrix(self, xi, yi):
        if xi < 0:
            xi = 0
        if xi > 13:
            xi = 13
        if yi < 0:
            yi = 0
        if yi > 13:
            yi = 13
        return xi, yi

    def forward(self, *inputs):
        os, h, t, v = inputs

        #最終
        scale = 1./float(self.col)
        h2 = h[:, self.Nj:, :, :]
        s = h.size()
        tt = torch.zeros(s).float()
        ti = t*self.col

        '''
        '''
        z = tt[:,0,:,:].view(-1, 1, self.col, self.col).cuda()
        h2_0 = h2[:,0,:,:].view(-1, 1, self.col, self.col)
        h2_1 = h2[:,1,:,:].view(-1, 1, self.col, self.col)
        h2_2 = h2[:,2,:,:].view(-1, 1, self.col, self.col)
        h2_3 = h2[:,3,:,:].view(-1, 1, self.col, self.col)
        h2_0 = torch.cat([h2_0, h2_0, h2_0,], dim=1)
        h2_1 = torch.cat([h2_1, h2_1, h2_1], dim=1)
        h2_2 = torch.cat([h2_2, h2_2, h2_2], dim=1)
        h2_3 = torch.cat([h2_3, h2_3, h2_3], dim=1)

        h3 = torch.cat([ h2_0, h2_1, h2_2, h2_3, z, z], dim=1)
        h3 = (h[:, :14, :, :] + h3) * self.m

        reshaped = h3.view(-1, self.Nj, self.col*self.col)
        _, argmax = reshaped.max(-1)
        yCoords = argmax/self.col
        xCoords = argmax - yCoords*self.col

        x = Variable(torch.zeros(t.size()).float(), requires_grad=True).cuda()
        #vt = Variable(torch.zeros([s[0], 4, self.col, self.col]).float(), requires_grad=True).cuda()
        '''
        '''
        
        for i in range(s[0]):
            for j in range(self.Nj):
                '''
                '''
                #if h3[i, j, yCoords[i, j], xCoords[i, j]] > 0.5:
                x[i, j, 0] = (os[i, j, yCoords[i, j], xCoords[i, j]] + xCoords[i, j].float()) * scale
                x[i, j, 1] = (os[i, j + 14, yCoords[i, j], xCoords[i, j]] + yCoords[i, j].float()) * scale
                '''
                '''
                if int(v[i, j, 0]) == 1:
                    
                    xi, yi = self.checkMatrix(int(ti[i, j, 0]), int(ti[i, j, 1]))
                    
                    # 正規分布に近似したサンプルを得る
                    # 平均は 100 、標準偏差を 1 
                    tt[i, j, yi, xi]  = 1
                    tt[i, j] = self.min_max(fi.gaussian_filter(tt[i, j], self.gaussian))

            #tt[i, self.Nj] = self.min_max_(tt[i, 0] + tt[i, 1] + tt[i, 2])
            #tt[i, self.Nj + 1] = self.min_max_(tt[i, 3] + tt[i, 4] + tt[i, 5])
            #tt[i, self.Nj + 2] = self.min_max_(tt[i, 6] + tt[i, 7] + tt[i, 8])
            #tt[i, self.Nj + 3] = self.min_max_(tt[i, 9] + tt[i, 10] + tt[i, 11])
            
            # 右足
            f_rf = False
            for index in range(3):
                if int(v[i, index, 0]) == 1:
                    f_rf = True
                    xi, yi = self.checkMatrix(int(ti[i, index, 0]), int(ti[i, index, 1]))
                    tt[i, self.Nj, yi, xi]  = 1
            if f_rf == True:
                tt[i, self.Nj] = self.min_max(fi.gaussian_filter(tt[i, self.Nj], self.gaussian))
                #vt[i, 0] = 1

            # 左足
            f_lf = False
            for index in range(3,6):
                if int(v[i, index, 0]) == 1:
                    f_lf = True
                    xi, yi = self.checkMatrix(int(ti[i, index, 0]), int(ti[i, index, 1]))
                    tt[i, self.Nj + 1, yi, xi]  = 1
            if f_lf == True:
                tt[i, self.Nj + 1] = self.min_max(fi.gaussian_filter(tt[i, self.Nj + 1], self.gaussian))
                #vt[i, 1] = 1

            # 右手
            f_rh = False
            for index in range(6,9):
                if int(v[i, index, 0]) == 1:
                    f_rh = True
                    xi, yi = self.checkMatrix(int(ti[i, index, 0]), int(ti[i, index, 1]))
                    tt[i, self.Nj + 2, yi, xi]  = 1
            if f_rh == True:
                tt[i, self.Nj + 2] = self.min_max(fi.gaussian_filter(tt[i, self.Nj + 2], self.gaussian))
                #vt[i, 2] = 1

            # 左手
            f_lh = False
            for index in range(9,12):
                if int(v[i, index, 0]) == 1:
                    f_lh = True
                    xi, yi = self.checkMatrix(int(ti[i, index, 0]), int(ti[i, index, 1]))
                    tt[i, self.Nj + 3, yi, xi]  = 1
            if f_lh == True:
                tt[i, self.Nj + 3] = self.min_max(fi.gaussian_filter(tt[i, self.Nj + 3], self.gaussian))
                #vt[i, 3] = 1
            
        tt = Variable(tt).cuda()

        '''
        diff1 = h3[:, :, yi, xi] - tt[:, :self.Nj, yi, xi]
        vv = v[:,:,0]
        diff1 = diff1*vv
        N1 = (vv.sum()/2).data[0]
        '''
        diff1 = h - tt
        cnt = 0
        for i in range(s[0]):
            for j in range(self.Nj):
                if int(v[i, j, 0]) == 0:
                    diff1[i, j] = diff1[i, j]*0
                else:
                    cnt = cnt + 1
            # 右足
            f_rf = False
            for index in range(3):
                if int(v[i, index, 0]) == 1:
                    f_rf = True
                    cnt = cnt + 1
                    #vt[i, 0] = 1
                    break
            if f_rf == False:
                diff1[i, self.Nj] = diff1[i, self.Nj]*0
            
            # 左足
            f_lf = False
            for index in range(3,6):
                if int(v[i, index, 0]) == 1:
                    f_lf = True
                    cnt = cnt + 1
                    #vt[i, 1] = 1
                    break
            if f_lf == False:
                diff1[i, self.Nj + 1] = diff1[i, self.Nj + 1]*0

            # 右手
            f_rh = False
            for index in range(6,9):
                if int(v[i, index, 0]) == 1:
                    f_rh = True
                    cnt = cnt + 1
                    #vt[i, 2] = 1
                    break
            if f_rh == False:
                diff1[i, self.Nj + 2] = diff1[i, self.Nj + 2]*0

            # 左手
            f_lh = False
            for index in range(9,12):
                if int(v[i, index, 0]) == 1:
                    f_lh = True
                    cnt = cnt + 1
                #vt[i, 3] = 1
                    break
            if f_lh == False:
                diff1[i, self.Nj + 3] = diff1[i, self.Nj + 3]*0
        N1 = tt.sum()

        diff1 = diff1.contiguous().view(-1)
        d1 = diff1.dot(diff1) /(cnt * self.col*self.col)

        diff2 = x - t
        diff2 = diff2*v
        N2 = (v.sum()/2)
        diff2 = diff2.view(-1)
        d2 = diff2.dot(diff2)/N2
        '''
        diff3 = h2 - tt[:, self.Nj:, :, :]
        diff3 = diff3*vt
        N3 = (vt.sum()/2)
        diff3 = diff3.contiguous().view(-1)
        d3 = diff3.dot(diff3) / N3
        '''
        return d1


def mean_squared_error2__(os, h, t, v, use_visibility=False):
    """ Computes mean squared error over the minibatch.

    Args:
        x (Variable): Variable holding an float32 vector of estimated pose.
        t (Variable): Variable holding an float32 vector of ground truth pose.
        v (Variable): Variable holding an int32 vector of ground truth pose's visibility.
            (0: invisible, 1: visible)
        use_visibility (bool): When it is ``True``,
            the function uses visibility to compute mean squared error.
    Returns:
        Variable: A variable holding a scalar of the mean squared error loss.
    """
    return MeanSquaredError2__(use_visibility)(os, h,  t, v)
