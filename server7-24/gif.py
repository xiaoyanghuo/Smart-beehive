import imageio
import os
import numpy as np
import cv2 as cv
path = 'videoframes/'
path = 'video/'
outfilename = 'videogif/'+'video.gif'
tframes_name = os.listdir(path)
tframes_name.sort()

framelist0 = tframes_name
print(len(framelist0))
max_length = max([len(filename) for filename in framelist0])
print(max_length)
framelist = []
for i in range(1,max_length+1):
    temp = []
    for filename in framelist0:
        if len(filename) == i:
            temp.append(filename)
            print(filename)
    temp.sort()
    framelist.extend(temp)
# framelist = framelist0
tframes_name = framelist

tframes = []
for tframe_name in tframes_name:
    im = cv.imread(path + tframe_name)
    cv.imwrite('video2/'+tframe_name)
    # im = cv.cvtColor(im, cv.COLOR_BGR2RGB)
    im = imageio.imread(path + tframe_name)
    tframes.append(np.array(im))
imageio.mimsave(outfilename, tframes, 'GIF', fps=10)

