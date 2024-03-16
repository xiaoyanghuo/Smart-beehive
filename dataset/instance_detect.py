import os

count = [0,0,0,0,0]

paths = os.listdir("NJU/labels")
for path in paths[0:]:
	file = open("NJU/labels/"+path,'r')
	lines = file.readlines()
	for line in lines:
		count[int(line[0])] = count[int(line[0])] +1
print(count)
count = [0,0,0,0,0]

paths = os.listdir("NJU/labels")
for path in paths[0:]:
	file = open("NJU/labels/"+path,'r')
	lines = file.readlines()
	for line in lines:
		count[int(line[0])] = count[int(line[0])] +1
print(count)
# count = [0,0,0,0,0]
# paths = os.listdir("W/labels")
# for path in paths:
# 	file = open("W/labels/"+path,'r')
# 	lines = file.readlines()
# 	for line in lines:
# 		count[int(line[0])] = count[int(line[0])] +1
# print(count)
# count = [0,0,0,0,0]
# paths = os.listdir("bugdatasetadd/train/labels")
# for path in paths:
# 	file = open("bugdatasetadd/train/labels/"+path,'r')
# 	lines = file.readlines()
# 	for line in lines:
# 		count[int(line[0])] = count[int(line[0])] +1

# print(count)
