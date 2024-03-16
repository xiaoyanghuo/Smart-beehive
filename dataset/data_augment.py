import os

paths = os.listdir("annotationsplus")


count = [0,0,0,0]

for path in paths:
	file = open("annotationsplus/"+path,'r')
	lines = file.readlines()
	annos = [] 
	for line in lines:
		# c,cx,cy,w,h = *line[:-1].split(' ')
		# print(c,cx,cy,w,h)
		annos.append([int(line[0])]+[float(num) for num in line[2:-1].split(' ')])
		count[int(line[0])] = count[int(line[0])] +1

	print(annos)