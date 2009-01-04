size(100,100)

stroke(0, 0, 100)
strokewidth(.5)
line(0,0, 100,0)
line(0,0, 0,100)
stroke(0, 0, 40)
strokewidth(.25)
for x in range(20, 120, 20):
    line(x, 0, x, 100)
for y in range(20, 120, 20):
    line(0, y, 100, y)
