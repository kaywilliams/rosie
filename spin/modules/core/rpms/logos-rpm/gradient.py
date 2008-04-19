try:
  import ImageColor
  import ImageDraw
except:
    raise ImportError("missing 'python-imaging' module")

API_VERSION = 5.0

class ImageGradient(object):
  def __init__(self, im):
    self.im = im
    self.width, self.height = im.size

  def draw_gradient(self, start_color, end_color):
    draw = ImageDraw.Draw(self.im)

    if type(start_color) == type(()):
      start_r, start_g, start_b = start_color
    else:
      start_r, start_g, start_b = ImageColor.getrgb(start_color)

    if type(end_color) == type(()):
      end_r, end_g, end_b = end_color
    else:
      end_r, end_g, end_b = ImageColor.getrgb(end_color)

    dr = (end_r - start_r)/float(self.width)
    dg = (end_g - start_g)/float(self.width)
    db = (end_b - start_b)/float(self.width)

    r, g, b = start_r, start_g, start_b
    for i in xrange(self.width):
      draw.line((i, 0, i, self.height), fill=(int(r), int(g), int(b)))
      r, g, b = r+dr, g+dg, b+db
