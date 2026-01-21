import itertools
import math
import pathlib
import subprocess
from collections import deque

import cv2
import Decorator as D
import numpy as np
from PIL import Image, ImageChops

import Utility as U


def checkFileName(path, sep="#", width=2, isMakeDir=False):
  path = pathlib.Path(path) if isinstance(path, str) else path
  if isMakeDir:
    path.parent.mkdir(exist_ok=True)

  if not path.exists():
    return path

  i = 1
  while True:
    suffix = U.getZeroFillNumberString(i, 0, width)
    name = pathlib.Path(path.parent, f"{path.stem}{sep}{suffix}{path.suffix}")
    if not name.exists():
      return name
    i += 1


def toGeometry(width, height, left, top):
  return f"{width}x{height}+{left}+{top}"


def resizeImage(image, width, height):
  w, h = image.size
  ratio = min(width / w, height / h)
  size = (int(w * ratio), int(h * ratio))
  return image.resize(size, Image.LANCZOS)


def readImage(path):
  if not path.is_file():
    return None
  return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)


def getFiles(path, isRecurse, extensions=None):
  if isinstance(path, str):
    path = pathlib.Path(path)
  files = deque(path.iterdir())
  dirs = {path: {"total": 0, "sames": 0}}
  result = []
  while len(files) > 0:
    file = files.popleft()
    if file.is_file() and (extensions is None or file.suffix in extensions):
      result.append({"path": file.absolute()})
      dirs[file.parent]["total"] += 1
    elif file.is_dir() and isRecurse:
      files.extend(file.iterdir())
      dirs[file] = {"total": 0, "sames": 0}
  result.sort(key=lambda x: x["path"])
  return result, dirs


def comparePHash(ph1, ph2, phObj=None):
  if phObj is None:
    phObj = cv2.img_hash.PHash().create()
  return phObj.compare(ph1, ph2)


def isSameImage(target, other, phObj=None, threshold=9.0):
  diff = comparePHash(target["pHash"], other["pHash"], phObj)
  if diff <= threshold:
    return True, diff
  return False, diff


def getRatio(shape, n=4):
  return round(shape[0] / shape[1], n)


def factor(x):
  if x == 1:
    return [1]
  result = []
  for n in range(2, x + 1):
    if x < n:
      return result
    while x % n == 0:
      result.append(n)
      x //= n
  return result


def getFactorPairs(lt, n):
  if n > len(lt):
    return []
  result = []
  comb = itertools.combinations(lt, r=n)
  for x in comb:
    other = lt.copy()
    for y in x:
      other.remove(y)
    data = sorted([math.prod(x), math.prod(other)])
    if data not in result:
      result.append(data)
  return result


def getAllFactorPairs(fts):
  l = max(2, len(fts))
  result = []
  for i in range(1, l // 2 + 1):
    data = getFactorPairs(fts, i)
    if data not in result:
      result.extend(data)
  return sorted(result)


def getMinFactorPair(n):
  if n == 0:
    n = 1
  fts = factor(n)
  while n > 2 and len(fts) == 1:  # 素数はペアにならないので避ける
    n += 1
    fts = factor(n)
  result = getAllFactorPairs(fts)
  return result[-1]


ColorModes = ["1", "L", "P", "RGB", "RGBA"]  # "CMYK", "YCvCr", "LAB", "HSV", "I", "F"


def makeSameColor(image1, image2):
  m1 = U.indexList(ColorModes, image1.mode)
  m2 = U.indexList(ColorModes, image2.mode)
  mode = ColorModes[max(m1, m2)]
  return image1.convert(mode), image2.convert(mode)


def diffImage(image1, image2):
  size = max(image1.size, image2.size)
  img1 = image1.resize(size, Image.LANCZOS) if image1.size != size else image1
  img2 = image2.resize(size, Image.LANCZOS) if image2.size != size else image2
  img1, img2 = makeSameColor(img1, img2)
  return ImageChops.difference(img1, img2)


def callExplorer(params):
  cmd = ["explorer"] + params
  subprocess.Popen(cmd)
