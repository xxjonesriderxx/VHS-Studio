"""Small consistent icons drawn locally, without font-dependent symbols."""
from PIL import Image, ImageDraw
import customtkinter as ctk

def icon(name, color='#d5e4e8'):
    image=Image.new('RGBA',(72,72))
    draw=ImageDraw.Draw(image)
    if name=='folder':
        draw.line([(10,58),(10,18),(29,18),(35,26),(62,26),(62,58),(10,58)],fill=color,width=5,joint='curve')
        draw.line([(12,35),(61,35)],fill=color,width=4)
    elif name=='ai':
        draw.polygon([(32,10),(39,29),(58,36),(39,43),(32,62),(25,43),(6,36),(25,29)],outline=color,width=4)
        draw.line([(56,8),(56,22)],fill=color,width=4)
        draw.line([(49,15),(63,15)],fill=color,width=4)
    return ctk.CTkImage(light_image=image,dark_image=image,size=(18,18))
