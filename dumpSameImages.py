import argparse
import concurrent.futures as cf
import pathlib
import threading

import cv2
import Decorator as D

import readSameImagePickle as rsip
import Utility as U
import utility as u


def getFiles(path, targetPath, extensions=None):
  if extensions is None:
    extensions = [".jpg", ".png", ".webp", ".gif"]
  if targetPath is not None:
    targets = u.getFiles(targetPath, isRecurse=True, extensions=extensions)
    others = u.getFiles(path, isRecurse=True, extensions=extensions)
    others = u.subList(others, targets)
  else:
    targets = u.getFiles(path, isRecurse=True, extensions=extensions)
    others = targets
  return targets, others


def setInfo(data):
  image = u.readImage(data["path"])
  if image is None:
    return False, data
  data["shape"] = image.shape
  data["pHash"] = cv2.img_hash.pHash(image)
  return True, data


def setInfoAll(lt, ex, fails):
  rs = ex.map(setInfo, lt)
  for result in rs:
    success, data = result
    if not success:
      fails.append(data["path"])
      lt.remove(data)


def dump(pm, obj, lock):
  with lock:
    pm.dump(obj)


def check(result, sames, others, fails):
  isSame, diff, other = result
  if isSame:
    others.remove(other)
    other["diff"] = diff
    U.delKeys(other, ["pHash"])
    sames.append(other)
  elif diff is None:
    others.remove(other)
    fails.append(other["path"])


def dumpSameImages(path, pickleOutput, failedPath, targetPath=None, threshold=9.0):
  pm = U.PickleManager(pickleOutput)
  pm.dump(path)
  targets, others = getFiles(path, targetPath)
  lock = threading.Lock()
  phObj = cv2.img_hash.PHash().create()
  fails = []
  with cf.ThreadPoolExecutor() as ex:
    setInfoAll(targets, ex, fails)
    if targetPath is not None:
      setInfoAll(others, ex, fails)
    while len(targets) > 0:
      target = targets.pop()
      target["target"] = True
      sames = [target]
      print(f"\r\x1b[1M{len(others)}: {target['path'].parent.name} {target['path'].name}", end="")
      for other in others[:]:
        r = u.isSameImage(target, other, phObj, threshold)
        check(r, sames, others, fails)
      U.delKeys(target, ["pHash"])
      if len(sames) > 1:
        ex.submit(dump, pm, sames, lock)
  print()
  if len(fails) > 1:
    U.customPrint(fails)
    u.dump(failedPath, fails)


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("path", type=pathlib.Path)
  parser.add_argument("-t", "--targetPath", type=pathlib.Path, default=None)
  parser.add_argument("-o", "--outputPath", type=pathlib.Path, default=None)
  parser.add_argument("-f", "--failedPath", type=pathlib.Path, default=None)
  parser.add_argument("-th", "--threshold", type=float, default=9.0)
  args = parser.parse_args()
  path = args.path.absolute()
  picklePath = pathlib.Path(path, f"pHash_{path.stem}.pkl") if args.outputPath is None else args.outputPath
  failedPath = pathlib.Path(path, f"failed_{path.stem}.pkl") if args.failedPath is None else args.failedPath
  targetPath = args.targetPath.absolute() if args.targetPath is not None else None
  return (path, picklePath, failedPath, targetPath, args.threshold)


if __name__ == "__main__":
  path, picklePath, failedPath, targetPath, threshold = argumentParser()
  print(
    f'directory:  "{path}"\nthreshold:   {threshold}\npicklePath: "{picklePath}"\nfailedPath: "{failedPath}"\ntargetPath: "{targetPath}"'
  )

  dumpSameImages(path, picklePath, failedPath, targetPath, threshold)
  rsip.printSameImagePickle(picklePath)
  print(
    f'directory:  "{path}"\nthreshold:   {threshold}\npicklePath: "{picklePath}"\nfailedPath: "{failedPath}"\ntargetPath: "{targetPath}"'
  )
