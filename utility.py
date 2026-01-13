import pathlib
from collections import deque

import cv2
import numpy as np
from PIL import Image

import Utility as U

# ReJapanese = regex.compile(r"[\p{sc=Han}\p{sc=Hiragana}\p{Katakana}]+")


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
  result = []
  while len(files) > 0:
    file = files.popleft()
    if file.is_file() and (extensions is None or file.suffix in extensions):
      result.append({"path": file.absolute()})
    elif file.is_dir() and isRecurse:
      files.extend(file.iterdir())
  result.sort(key=lambda x: x["path"])
  return result


def comparePHash(ph1, ph2, phObj=None):
  if phObj is None:
    phObj = cv2.img_hash.PHash().create()
  return phObj.compare(ph1, ph2)


def isSameImage(target, other, phObj=None, threshold=10.0):  # , diffRatio=0.1):
  diff = comparePHash(target["pHash"], other["pHash"], phObj)
  if diff < threshold:  # and abs(getRatio(target["shape"]) - getRatio(other["shape"])) <= diffRatio:
    return True, diff, other
  return False, diff, other


def getRatio(shape, n=4):
  return round(shape[0] / shape[1], n)


# def dump(path, obj):
#   with path.open("wb") as file:
#     pickle.dump(obj, file)

# def remove(lt, key, value):
#   for i, x in enumerate(lt):
#     if x[key] == value:
#       lt.pop(i)
#       return
