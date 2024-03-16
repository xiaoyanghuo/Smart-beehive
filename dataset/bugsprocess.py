# import os
# #print(os.listdir("bugs"))
# for i, imgname in enumerate(os.listdir("bugs")):
# 	os.rename("bugs/"+imgname, "bugs/bugs_"+str(i)+".jpg")
import os,tqdm
import numpy as np
import cv2 as cv

path1 = "wasp/images/"
path2 = "wasp/labels/"
for i, txtname in enumerate(os.listdir(path2)):
 	os.rename(path1+txtname[:-4]+'.jpg', path1+"wasp_"+str(i)+".jpg")
 	os.rename(path2+txtname[:-4]+'.txt', path2+"wasp_"+str(i)+".txt")

# path = "background/"
# for i, txtname in enumerate(os.listdir(path)):
#  	file = open(path+txtname[:-4]+".txt",'w')
#  	file.close()

print("done")
