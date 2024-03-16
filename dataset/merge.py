import os
import shutil
import random

path1 = 'bugsplus'
path2 = 'annotationsplus'
paths =  os.listdir(path1)

paths.sort()

# print(paths)
length = len(paths)

index1 = int(0.8*length)

#index2 = int(0.9*length)

if not os.path.exists("bugdatasetfinal1"):
	os.makedirs("./final/train/images")
	os.makedirs("./final/train/labels")

	os.makedirs("./final/val/images")
	os.makedirs("./final/val/labels")


for index, filename in enumerate(paths):
	old1 = os.path.join(path1,filename)
	old2 = os.path.join(path2,filename.split('.')[0]+'.txt')
	if index not in val:
		new1 = os.path.join("./final/train/images",filename)
		new2 = os.path.join("./final/train/labels",filename.split('.')[0]+'.txt')
	else:
		new1 = os.path.join("./final/val/images",filename)
		new2 = os.path.join("./final/val/labels",filename.split('.')[0]+'.txt')
	shutil.copy(old1,new1)
	shutil.copy(old2,new2)