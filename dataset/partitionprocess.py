import os
import shutil
import random

path1 = 'NJU/images'
path2 = 'NJU/labels'
paths =  os.listdir(path1)

paths.sort()

# print(paths)
length = len(paths)
print(length)
index1 = int(0.8*length)
print(index1)
#index2 = int(0.9*length)

if not os.path.exists("NJUfinal"):
	os.makedirs("./NJUfinal/train/images")
	os.makedirs("./NJUfinal/train/labels")
	# os.makedirs("./bugdatasetplus/test/images")
	# os.makedirs("./bugdatasetpluss/test/labels")
	os.makedirs("./NJUfinal/val/images")
	os.makedirs("./NJUfinal/val/labels")


# for index, filename in enumerate(paths):
# 	old1 = os.path.join(path1,filename)
# 	old2 = os.path.join(path2,filename.split('.')[0]+'.txt')
# 	if index < index1:
# 		new1 = os.path.join("./bugdatasetplus/train/images",filename)
# 		new2 = os.path.join("./bugdatasetplus/train/labels",filename.split('.')[0]+'.txt')

# 	# elif index < index2:
# 	# 	new1 = os.path.join("./bugdatasetplus/test/images",filename)
# 	# 	new2 = os.path.join("./bugdatasetplus/test/labels",filename.split('.')[0]+'.txt')
# 	else:
# 		new1 = os.path.join("./bugdatasetplus/val/images",filename)
# 		new2 = os.path.join("./bugdatasetplus/val/labels",filename.split('.')[0]+'.txt')
# 	shutil.copy(old1,new1)
# 	shutil.copy(old2,new2)
val = set()
while len(val) != length-index1:
	val.add(random.randint(0, length-1))

for index, filename in enumerate(paths):
	old1 = os.path.join(path1,filename)
	old2 = os.path.join(path2,filename.split('.')[0]+'.txt')
	if index not in val:
		new1 = os.path.join("./NJUfinal/train/images",filename)
		new2 = os.path.join("./NJUfinal/train/labels",filename.split('.')[0]+'.txt')
	else:
		new1 = os.path.join("./NJUfinal/val/images",filename)
		new2 = os.path.join("./NJUfinal/val/labels",filename.split('.')[0]+'.txt')
	shutil.copy(old1,new1)
	shutil.copy(old2,new2)