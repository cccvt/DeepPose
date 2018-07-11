# -*- coding: utf-8 -*-
""" Train pose net. """

import os
import random
import time
from tqdm import tqdm, trange
import torch
import torch.optim as optim
from torch.autograd import Variable
from torchvision import transforms, models
import torch.nn as nn
import subprocess

from modules.errors import FileNotFoundError, GPUNotFoundError, UnknownOptimizationMethodError, NotSupportedError
from modules.models.pytorch import AlexNet, VGG19Net, Inceptionv3, Resnet, MobileNet, MobileNetV2, MobileNet_
from modules.dataset_indexing.pytorch import PoseDataset, Crop, RandomNoise, Scale
from modules.functions.pytorch import mean_squared_error

class TrainLogger(object):
    """ Logger of training pose net.

    Args:
        out (str): Output directory.
    """

    def __init__(self, out):
        try:
            os.makedirs(out)
        except OSError:
            pass
        self.file = open(os.path.join(out, 'log'), 'w')
        self.logs = []

    def write(self, log, colab=False):
        """ Write log. """
        tqdm.write(log)
        tqdm.write(log, file=self.file)
        self.file.flush()
        self.logs.append(log)
        if colab == True:
            subprocess.run(["cp", "./result/pytorch/log", "../drive/result/pytorch/log.txt"])

    def state_dict(self):
        """ Returns the state of the logger. """
        return {'logs': self.logs}

    def load_state_dict(self, state_dict):
        """ Loads the logger state. """
        self.logs = state_dict['logs']
        # write logs.
        tqdm.write(self.logs[-1])
        for log in self.logs:
            tqdm.write(log, file=self.file)


class TrainPoseNet(object):
    """ Train pose net of estimating 2D pose from image.

    Args:
        Nj (int): Number of joints.
        use_visibility (bool): Use visibility to compute loss.
        data-augmentation (bool): Crop randomly and add random noise for data augmentation.
        epoch (int): Number of epochs to train.
        opt (str): Optimization method.
        gpu (bool): Use GPU.
        seed (str): Random seed to train.
        train (str): Path to training image-pose list file.
        val (str): Path to validation image-pose list file.
        batchsize (int): Learning minibatch size.
        out (str): Output directory.
        resume (str): Initialize the trainer from given file.
            The file name is 'epoch-{epoch number}.iter'.
        resume_model (str): Load model definition file to use for resuming training
            (it\'s necessary when you resume a training).
            The file name is 'epoch-{epoch number}.model'.
        resume_opt (str): Load optimization states from this file
            (it\'s necessary when you resume a training).
            The file name is 'epoch-{epoch number}.state'.
    """

    def __init__(self, **kwargs):
        self.Nj = kwargs['Nj']
        self.use_visibility = kwargs['use_visibility']
        self.data_augmentation = kwargs['data_augmentation']
        self.epoch = kwargs['epoch']
        self.gpu = (kwargs['gpu'] >= 0)
        self.NN = kwargs['NN']
        self.opt = kwargs['opt']
        self.seed = kwargs['seed']
        self.train = kwargs['train']
        self.val = kwargs['val']
        self.batchsize = kwargs['batchsize']
        self.out = kwargs['out']
        self.resume = kwargs['resume']
        self.resume_model = kwargs['resume_model']
        self.resume_opt = kwargs['resume_opt']
        self.colab = kwargs['colab']
        # validate arguments.
        self._validate_arguments()

    def _validate_arguments(self):
        if self.seed is not None and self.data_augmentation:
            raise NotSupportedError('It is not supported to fix random seed for data augmentation.')
        if self.gpu and not torch.cuda.is_available():
            raise GPUNotFoundError('GPU is not found.')
        for path in (self.train, self.val):
            if not os.path.isfile(path):
                raise FileNotFoundError('{0} is not found.'.format(path))
        if self.opt not in ('MomentumSGD', 'Adam'):
            raise UnknownOptimizationMethodError(
                '{0} is unknown optimization method.'.format(self.opt))
        if self.resume is not None:
            for path in (self.resume, self.resume_model, self.resume_opt):
                if not os.path.isfile(path):
                    raise FileNotFoundError('{0} is not found.'.format(path))

    def _get_optimizer(self, model):
        if self.opt == 'MomentumSGD':
            optimizer = optim.SGD(model.parameters(), lr=0.0001, momentum=0.9)
        elif self.opt == "Adam":
            optimizer = optim.Adam(model.parameters())
        return optimizer

    def _train(self, model, optimizer, train_iter, log_interval, logger, start_time):
        model.train()
        lr = 0.1
        for iteration, batch in enumerate(tqdm(train_iter, desc='this epoch'), 1):
            image, pose, visibility = Variable(batch[0]), Variable(batch[1]), Variable(batch[2])
            if self.gpu:
                image, pose, visibility = image.cuda(), pose.cuda(), visibility.cuda()
            
            optimizer.zero_grad()
            output = model(image)
            loss = mean_squared_error(output.view(-1, self.Nj, 2), pose, visibility, self.use_visibility)
            loss.backward()
            optimizer.step()
               
            if iteration % log_interval == 0:
                log = 'elapsed_time: {0}, loss: {1}'.format(time.time() - start_time, loss.data[0])
                logger.write(log, self.colab)
                """
                if loss.data[0] < 0.15 and lr > 0.001:
                    lr = 0.001
                    optimizer = optim.SGD(model.parameters(), lr=lr, momentum=0.9)
                elif loss.data[0] < 0.05 and lr > 0.0005:
                    lr = 0.0005
                    optimizer = optim.SGD(model.parameters(), lr=lr, momentum=0.9)
                elif loss.data[0] < 0.01 and lr > 0.0001:
                    lr = 0.0001
                    optimizer = optim.SGD(model.parameters(), lr=lr, momentum=0.9)
                elif loss.data[0] < 0.005 and lr > 0.00001:
                    lr = 0.00001
                    optimizer = optim.SGD(model.parameters(), lr=lr, momentum=0.9)
                """
    def _test(self, model, test_iter, logger, start_time):
        model.eval()
        test_loss = 0
        for batch in test_iter:
            image, pose, visibility = Variable(batch[0]), Variable(batch[1]), Variable(batch[2])
            if self.gpu:
                image, pose, visibility = image.cuda(), pose.cuda(), visibility.cuda()
            output = model(image)
            test_loss += mean_squared_error(output.view(-1, self.Nj, 2), pose, visibility, self.use_visibility).data[0]
        test_loss /= len(test_iter)
        log = 'elapsed_time: {0}, validation/loss: {1}'.format(time.time() - start_time, test_loss)
        logger.write(log, self.colab)

    def _checkpoint(self, epoch, model, optimizer, logger):
        filename = os.path.join(self.out, 'pytorch', 'epoch-{0}'.format(epoch + 1))
        torch.save({'epoch': epoch + 1, 'logger': logger.state_dict()}, filename + '.iter')
        torch.save(model.state_dict(), filename + '.model')
        torch.save(optimizer.state_dict(), filename + '.state')
        if self.colab == True:
            subprocess.run(["cp", "./result/pytorch/epoch-{0}.model".format(epoch + 1), "../drive/result/pytorch/epoch-{0}.model".format(epoch + 1)])


    def start(self):
        """ Train pose net. """
        # set random seed.
        if self.seed is not None:
            random.seed(self.seed)
            torch.manual_seed(self.seed)
            if self.gpu:
                torch.cuda.manual_seed(self.seed)
        # initialize model to train.
        if self.NN == "VGG19":
            model = models.vgg19(pretrained=True)
            # 学習済みデータは最後の層が1000なので、読込後入れ替える
            m3 = nn.Linear(4096, self.Nj*2)
            m3.weight.data.normal_(0, 0.01)
            m3.bias.data.zero_()
            removed = list(model.classifier.children())[:-1]
            model.classifier= torch.nn.Sequential(*removed)
            model.classifier = torch.nn.Sequential(model.classifier, m3)
        elif self.NN == "Inception3":
            model = Inceptionv3( aux_logits = False)
            # 学習済みデータは最後の層が1000なので、読込後入れ替える
            m3 = nn.Linear(2048, self.Nj*2)
            m3.weight.data.normal_(0, 0.01)
            m3.bias.data.zero_()
            # model.fc= m3
        elif self.NN == "ResNet":
            model = Resnet( )
        elif self.NN == "MobileNet":
            model = MobileNet( )
        elif self.NN == "MobileNet_":
            model = MobileNet_( )
        elif self.NN == "MobileNetV2":
            model = MobileNetV2( )
        else :
             model = AlexNet(self.Nj)
           
        if self.resume_model:
            model.load_state_dict(torch.load(self.resume_model))
        # prepare gpu.
        if self.gpu:
            model.cuda()
        # load the datasets.
        input_transforms = [transforms.ToTensor()]
        if self.data_augmentation:
            input_transforms.append(RandomNoise())
        train = PoseDataset(
            self.train,
            input_transform=transforms.Compose(input_transforms),
            output_transform=Scale(),
            transform=Crop(data_augmentation=self.data_augmentation))
        val = PoseDataset(
            self.val,
            input_transform=transforms.Compose([
                transforms.ToTensor()]),
            output_transform=Scale(),
            transform=Crop(data_augmentation=False))
        # training/validation iterators.
        train_iter = torch.utils.data.DataLoader(train, batch_size=self.batchsize, shuffle=True)
        val_iter = torch.utils.data.DataLoader(val, batch_size=self.batchsize, shuffle=False)
        # set up an optimizer.
        optimizer = self._get_optimizer(model)
        if self.resume_opt:
            optimizer.load_state_dict(torch.load(self.resume_opt))
        # set intervals.
        val_interval = 10
        #resume_interval = self.epoch/10
        resume_interval = 20
        log_interval = 10
        # set logger and start epoch.
        logger = TrainLogger(os.path.join(self.out, 'pytorch'))
        start_epoch = 0
        if self.resume:
            resume = torch.load(self.resume)
            start_epoch = resume['epoch']
            logger.load_state_dict(resume['logger'])
        # start training.
        start_time = time.time()
        for epoch in trange(start_epoch, self.epoch, initial=start_epoch, total=self.epoch, desc='     total'):
            self._train(model, optimizer, train_iter, log_interval, logger, start_time)
            if (epoch + 1) % val_interval == 0:
                self._test(model, val_iter, logger, start_time)
            if (epoch + 1) % resume_interval == 0:
                self._checkpoint(epoch, model, optimizer, logger)