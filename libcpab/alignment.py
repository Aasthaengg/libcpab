#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 28 16:13:00 2018

@author: nsde
"""
from .cpab import Cpab
from tqdm import tqdm 

#%%
class CpabAligner(object):
    ''' EXPERIMENTAL, NOT PROPER TESTED
    This class implementes implementes gradient based and sampling based 
    alignment of data by optimizing the parametrization of a given CPAB
    transformation '''
    
    def __init__(self, cpab_class):        
        assert isinstance(cpab_class, Cpab), '''The input class 
            needs to be an instance of the core cpab class '''
        self.T = cpab_class
        
        if self.T.backend_name == 'numpy':
            from .numpy import functions as backend
        elif self.T.backend_name == 'tensorflow':
            from .tensorflow import functions as backend
        elif self.T.backend_name == 'pytorch':
            from .pytorch import functions as backend
        self.backend = backend
    
    #%%
    def alignment_by_sampling(self, x1, x2, maxiter=100, verbose=True):
        ''' MCMC sampling minimization '''
        self.T._check_type(x1)
        self.T._check_type(x2)
        assert x1.shape == x2.shape,' Two data points does not have the same shape '
        outsize = (x2.shape[1], x2.shape[2]) if self.backend != 'pytorch' else  \
            (x2.shape[2], x2.shape[3])

        current_sample = self.T.identity(1)
        current_error = self.backend.norm(x1 - x2)
        accept_ratio = 0
        for i in tqdm(range(maxiter), desc='Alignment of samples', unit='samples'):
            # Sample and transform 
            theta = self.T.sample_transformation(1, mean=current_sample.flatten())
            x1_trans = self.T.transform_data(x1, theta, outsize=outsize)
            
            # Calculate new error
            new_error = self.backend.norm(x1_trans - x2)
            
            if new_error < current_error:
                current_sample = theta
                current_error = new_error
                accept_ratio += 1
        print('Acceptence ratio: ', accept_ratio / maxiter * 100, '%')
        return current_sample    
    
    #%%
    def alignment_by_gradient(self, x1, x2, maxiter=100, lr=1e-4):
        ''' Gradient based minimization '''
        assert self.T.backend_name != 'numpy', \
            ''' Cannot do gradient decent when using the numpy backend '''
        self.T._check_type(x1)
        self.T._check_type(x2)
        
        # TODO: write this as general when tensorflow backend is done
        assert self.T.backend_name == 'pytorch', \
						''' Only works with the pytorch backend at the moment '''
        import torch
        theta = torch.autograd.Variable(self.T.identity(1, epsilon=1e-6), requires_grad=True)
        optimizer = torch.optim.Adam([theta], lr=lr)
        
        loss_list = [ ]
        for i in range(maxiter):
            optimizer.zero_grad()
            x1_trans = self.T.transform_data(x1, theta, outsize=x1.shape[2:])
            loss = self.backend.norm(x1_trans - x2)
            loss.backward()
            optimizer.step()
            print('Epoch {0}/{1}, Loss {2}'.format(i+1, maxiter, loss.item()))
            loss_list.append(loss.item())
        print('Initial loss:', loss_list[0])
        print('Final loss:', loss_list[-1])
        return theta, x1_trans.detach()