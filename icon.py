from pathlib import Path
import struct
w=64
pixels=[]
for y in range(w):
 row=[]
 for x in range(w):
  color=(17,24,32,255)
  if 6<=x<=57 and 13<=y<=50:
   color=(105,216,189,255)
  if 9<=x<=54 and 16<=y<=47:
   color=(25,36,46,255)
  if 13<=x<=50 and 21<=y<=37:
   color=(105,216,189,255)
  if 15<=x<=48 and 23<=y<=35:
   color=(17,24,32,255)
  for cx in (24,40):
   d=(x-cx)**2+(y-29)**2
   if 13<=d<=24:color=(105,216,189,255)
  if 20<=x<=43 and 42<=y<=44:
   color=(105,216,189,255)
  r,g,b,a=color
  row.append(bytes((b,g,r,a)))
 pixels.append(b''.join(row))
bmp=struct.pack('<IIIHHIIIIII',40,w,w*2,1,32,0,w*w*4,0,0,0,0)+b''.join(reversed(pixels))+bytes(w*w//8)
Path(__file__).with_name('app.ico').write_bytes(struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',w,w,0,0,1,32,len(bmp),22)+bmp)
