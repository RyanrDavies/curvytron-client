#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 27 13:34:01 2018

@author: james
"""
import numpy as np
import matplotlib.pyplot as plt
patch = np.array([list('0001110000'),
                  list('0011011000'),
                  list('0110001100'),
                  list('1100000110'),
                  list('1000000011'),
                  list('0000100001'),
                  list('0000100000'),
                  list('0000100000'),
                  list('0000100000'),
                  list('0000100000')], dtype=float)
patch_odd = np.array([list('00001110000'),
                      list('00011011000'),
                      list('00110001100'),
                      list('01100000110'),
                      list('11000000011'),
                      list('10000100001'),
                      list('00000100000'),
                      list('00000100000'),
                      list('00000100000'),
                      list('00000100000'),
                      list('00000100000')], dtype=float)
                     
#plt.imshow(patch)
#plt.show()
#plt.imshow(patch_odd)
#plt.show()

#end = (
#            (0, idx),   # North
#            (0, pz),    # North East
#            (idx, pz),  # East
#            (pz, pz),   # South East
#            (pz, idx),  # South
#            (pz, 0),    # South West
#            (idx, 0),   # West
#            (0, 0)      # North West  
#        )

DIRECTION = {
    'N':  np.array((-1, 0)),
    'NE': np.array((-1, 1)),
    'E':  np.array(( 0, 1)),
    'SE': np.array(( 1, 1)),
    'S':  np.array(( 1, 0)),
    'SW': np.array(( 1,-1)),
    'W':  np.array(( 0,-1)),
    'NW': np.array((-1,-1))
}


def configure_compass_rays(patch_size):
    if bool(patch_size & 1):  # odd size patch patch
        idx = (patch_size-1) // 2
        start = np.array(((idx,idx),) * 8)
        direc = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        directions = [DIRECTION[dd] for dd in direc]
        ray_conf = dict(zip(direc, zip(start, directions)))
    else:
        raise NotImplementedError('Not implemented for even patch size')
#        idx = (patch_size) // 2
#        start = ((idx,idx),) * 8
#        # Naming example: cNW_N = *central* North West pixel to North pixel
#        names = ['cNW_N', 'cNE_N',
#                 'cNW_NE', 'cNE_NE', 'cSE_NW',
#                 'cNE_E', 'cSE_E'
#                 ]
#        direc = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NE']
#        directions = [DIRECTION[dd] for dd in direc]
#        ray_conf = dict(zip(direc, zip(start, directions)))
    return ray_conf


def get_ray_lengths(patch, ray_conf=None, start_allowance=1, max_len=100):
    """
    Returns the length of a continous string of zeros along the defined rays.
    By default, the rays are defined as starting at the centre and pointing 
    in the direction of compass points N, NE, E, ..., W, NW. To avoid issues 
    with the center being non-zero, `start_allowance` is the maximum number of
    non-zero squares allowed from the centre before starting the count.
    
    N.B. this will break if the obbstructing line is only 1 pix thick and going
    perpendicular to a diagonal ray (the ray will think it can pass straight
    through)
    """
    if ray_conf is None:
        ray_conf = configure_compass_rays(patch.shape[0])
    ray_len = {}
    for ray_id, (start, direc) in ray_conf.items():
        this_ray_len = 0
        for ii in range(max_len):
            idx = start + ii*direc
            if min(idx) < 0 or max(idx) >= patch.shape[0]:
                break
            if patch[idx[0], idx[1]] == 0:
                this_ray_len += 1
            else:
                if ii+1 <= start_allowance:
                    # Simply restart the count and don't break
                    this_ray_len = 0
                else:
                    break
        ray_len[ray_id] = this_ray_len
    return ray_len

from curvytron import State
import math
from skimage.transform import rotate
from skimage.util import pad

mat = np.arange(10**2, dtype='float').reshape(10, -1)

#obs = State(np.arange(10**2, dtype='float').reshape(10, -1), (2.1,5.2), 0.)

np.allclose(patch_odd, rotate(rotate(patch_odd, 90), -90, center=(5,5)))
np.allclose(patch, rotate(rotate(patch, 90), -90, center=(4.5,4.5)))

def extract_patch(state, patch_size=30, thresh=0.1):
    """
    If patch_size is even, define 'central' position of the patch to be the
    south west square and get i.e. for patch of size (10, 10) state.pos 
    will be at point (5, 4). If s is even, there is a central square e.g.
    for patch size 11 state.pos will be at (5, 5).
    
    Rotate the canvas first. This is because if you take the patch then
    rotate this patch to the angle of the player, zeros are used to fill 
    the patch.
    """
    hps = patch_size//2  # floor(half_patch_size)
    x0, x1 = [int(xx) for xx in state.position]
    # The angle of the agent clockwise from 12 o'clock
    angle = math.degrees(state.angle) + 90
    # rotate's angle argument is how many degrees to rotate *anticlockwise*
    # Additionally, the coordinates are reversed in skimage
    ### pixels is the game board oriented in the direction of the agent ###
    pixels = pad(state.pixels, hps+1, mode='constant', constant_values=1)
    # Because of padding x0 <- x0 + hps + 1
    x0, x1 = x0+hps+1, x1+hps+1
    pixels_rot = rotate(image=pixels, angle=angle,
                        center=(x1, x0))
    # Padding with zeros to account for selection near the edges
    if patch_size & 1:  # if patch size is odd
        patch = pixels_rot[(x0-hps):(x0+hps+1), (x1-hps):(x1+hps+1)]
    else:
        # Put resulting centre to be in the SW central square
        patch = pixels_rot[(x0-hps):(x0+hps), (x1-hps+1):(x1+hps+1)]
    return patch > thresh

obs = State(rotate(patch, 90), (5, 5), np.pi)
plt.imshow(obs.pixels)
plt.show()
for ii in range(3, 8):
    plt.imshow(extract_patch(obs, ii))
    plt.show()
    

degrees = 45
obs = State(rotate(patch_odd, degrees), (5, 5), -(degrees/180*np.pi + np.pi/2))
plt.imshow(obs.pixels)
plt.show()
for ii in range(3, 8):
    plt.imshow(extract_patch(obs, ii))
    plt.show()

mat = np.zeros((200, 200))
mat[20, 20] = 1
obs = State(mat, (20, 20), 10*np.pi)
plt.imshow(obs.pixels)
plt.show()
for ii in range(3, 8):
    plt.imshow(extract_patch(obs, ii))
    plt.show()

#    assert ((x+sz)-(x-sz)) == ((y+sz)-(y-sz))
#    assert clipped.shape[0] == clipped.shape[1], "Clipped Shape={}".format(clipped.shape)
#    # rotate expects angle to be anti-clockwise from 12
#    rot = rotate(clipped, angle=angle)
#
#    return rot > 0