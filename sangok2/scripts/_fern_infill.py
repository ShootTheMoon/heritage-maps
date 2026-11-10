import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image; import sgk_texbake as T
p=os.path.join(T.OUT,"FERN.png"); src=os.path.join(T.OUT,"FERN_orig.png")
if not os.path.exists(src): Image.open(p).save(src)
T._infill_transparent(Image.open(src)).save(p, optimize=True); print("FERN infilled")
