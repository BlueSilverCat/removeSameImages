import itertools
import math
import pathlib
from collections import deque

import ImageUtility as IU

import Utility as U


def toGeometry(width, height, left, top):
  return f"{width}x{height}+{left}+{top}"


def checkFileName(path, sep="#", width=2, *, isMakeDir=False):
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


def isSameImage(target, other, threshold, phObj=None, matcher=None, diffRatio=0.2):
  if phObj is not None:
    diff = IU.comparePHash(target["pHash"], other["pHash"], phObj)
  else:
    diff = IU.compareDescriptor(matcher, target["descriptors"], other["descriptors"])

  if diff <= threshold and abs(IU.getRatio(target["shape"]) - IU.getRatio(other["shape"])) <= diffRatio:
    return True, diff
  return False, diff


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
  while n > 2 and len(fts) == 1:  # 素数はペアにならないので避ける  # noqa: PLR2004
    n += 1
    fts = factor(n)
  result = getAllFactorPairs(fts)
  return result[-1]
